import json
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from .models import Match, Seat, Booking, SeatCategory, Team


def index(request):
    matches = Match.objects.select_related('home_team','away_team').all().order_by('start_time')
    if matches.count() == 0:
        return render(request, 'matches/index.html', {'matches': matches, 'note': 'Belum ada pertandingan. Buat data Match lewat admin atau shell.'})
    return render(request, 'matches/index.html', {'matches': matches})


def match_detail(request, pk):
    match = get_object_or_404(Match.objects.select_related('home_team','away_team'), pk=pk)

    # prefer related Team objects, fallback to parsing title
    def _team_label(team_obj):
        if not team_obj:
            return None
        if isinstance(team_obj, Team):
            return team_obj.short_name or team_obj.name
        return str(team_obj).strip()

    team_left = _team_label(match.home_team)
    team_right = _team_label(match.away_team)

    # fallback parse from title if any side missing
    if not team_left or not team_right:
        parts = re.split(r'\s+v(?:s)?\.?\s+|\s+vs\.?\s+|\s+v\s+|\s+-\s+', match.title or '', flags=re.IGNORECASE)
        if len(parts) >= 2:
            if not team_left:
                team_left = parts[0].strip()
            if not team_right:
                team_right = parts[1].strip()

    # final fallback
    if not team_left:
        team_left = 'Team A'
    if not team_right:
        team_right = 'Team B'

    return render(request, 'matches/match_detail.html', {
        'match': match,
        'team_left': team_left,
        'team_right': team_right,
    })


def match_seats_api(request, pk):
    match = get_object_or_404(Match, pk=pk)
    seats = match.seats.select_related('category').all()
    data = []
    for s in seats:
        data.append({
            'id': s.id,
            'label': f"{s.row}{s.col}",
            'row': s.row,
            'col': s.col,
            'category': s.category.name,
            'price': s.category.price,
            'color': s.category.color,
            'is_booked': s.is_booked,
        })
    return JsonResponse({'seats': data})


@csrf_exempt
def api_book(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')
    try:
        payload = json.loads(request.body.decode())
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    match_id = payload.get('match_id')
    seat_ids = payload.get('seat_ids', [])
    passengers = payload.get('passengers', []) or []
    buyer_name = payload.get('buyer_name') or (passengers[0]['name'] if passengers else None)
    buyer_email = payload.get('buyer_email') or (passengers[0].get('email') if passengers and passengers[0].get('email') else '')

    if not (match_id and seat_ids and buyer_name):
        return HttpResponseBadRequest('missing fields')

    if passengers and len(passengers) != len(seat_ids):
        return HttpResponseBadRequest('passengers length must match seat_ids length')

    with transaction.atomic():
        seats_qs = Seat.objects.select_for_update().filter(id__in=seat_ids, is_booked=False).select_related('category')
        seats = list(seats_qs)
        if len(seats) != len(seat_ids):
            return JsonResponse({'ok': False, 'msg': 'Beberapa kursi sudah terisi'}, status=400)

        if passengers:
            seat_map = {s.id: s for s in seats}
            for idx, sid in enumerate(seat_ids):
                p = passengers[idx]
                pc = p.get('category')
                if pc:
                    seat = seat_map.get(sid)
                    if not seat:
                        return JsonResponse({'ok': False, 'msg': f'Kursi {sid} tidak ditemukan'}, status=400)
                    if seat.category.name != pc:
                        return JsonResponse({'ok': False, 'msg': f'Kategori untuk kursi {seat.row}{seat.col} tidak cocok (expected {seat.category.name}, got {pc})'}, status=400)

        total = sum(s.category.price for s in seats)
        booking = Booking.objects.create(
            match_id=match_id,
            buyer_name=buyer_name,
            buyer_email=buyer_email or '',
            total_price=total,
            passengers=passengers
        )
        booking.seats.add(*seats)
        Seat.objects.filter(id__in=[s.id for s in seats]).update(is_booked=True)

        assigned = []
        if passengers:
            for idx, p in enumerate(passengers):
                sid = seat_ids[idx]
                s = next((x for x in seats if x.id == sid), None)
                assigned.append({
                    'passenger': p,
                    'seat_id': sid,
                    'seat_label': f"{s.row}{s.col}" if s else None
                })

    return JsonResponse({
        'ok': True,
        'booking_id': booking.id,
        'total_price': total,
        'assigned': assigned,
        'passengers': passengers
    })


@csrf_exempt
def api_book_quantity(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')
    try:
        payload = json.loads(request.body.decode())
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    match_id = payload.get('match_id')
    passengers = payload.get('passengers', []) or []
    quantity = int(payload.get('quantity') or (len(passengers) if passengers else 0))
    top_category = payload.get('category_name')
    buyer_name = payload.get('buyer_name') or (passengers[0]['name'] if passengers else None)
    buyer_email = payload.get('buyer_email') or (passengers[0].get('email') if passengers and passengers[0].get('email') else '')

    if not (match_id and quantity and buyer_name):
        return HttpResponseBadRequest('missing fields')

    if passengers and len(passengers) != quantity:
        return HttpResponseBadRequest('passengers length must match quantity')

    allocation = {}
    if passengers and any(p.get('category') for p in passengers):
        for p in passengers:
            cat = p.get('category')
            if not cat:
                return HttpResponseBadRequest('Each passenger must have category when mixing categories.')
            allocation[cat] = allocation.get(cat, 0) + 1
    else:
        if not top_category:
            return HttpResponseBadRequest('category_name required when passengers do not specify per-passenger category')
        allocation[top_category] = quantity

    with transaction.atomic():
        allocated_seats = []
        for cat_name, need in allocation.items():
            seats_qs = Seat.objects.select_for_update().filter(
                match_id=match_id,
                category__name=cat_name,
                is_booked=False
            ).order_by('id')[:need]
            seats_list = list(seats_qs)
            if len(seats_list) != need:
                return JsonResponse({'ok': False, 'msg': f'Tidak cukup kursi tersedia di kategori {cat_name} (minta {need}, tersedia {len(seats_list)})'}, status=400)
            allocated_seats.extend(seats_list)

        total = sum(s.category.price for s in allocated_seats)
        booking = Booking.objects.create(
            match_id=match_id,
            buyer_name=buyer_name,
            buyer_email=buyer_email or '',
            total_price=total,
            passengers=passengers
        )
        booking.seats.add(*allocated_seats)
        Seat.objects.filter(id__in=[s.id for s in allocated_seats]).update(is_booked=True)

        assigned = []
        if passengers:
            seats_pool = list(allocated_seats)
            for p in passengers:
                desired_cat = p.get('category')
                found_idx = next((i for i, s in enumerate(seats_pool) if s.category.name == desired_cat), None)
                if found_idx is None:
                    assigned.append({'passenger': p, 'seat_id': None, 'seat_label': None})
                else:
                    s = seats_pool.pop(found_idx)
                    assigned.append({
                        'passenger': p,
                        'seat_id': s.id,
                        'seat_label': f"{s.row}{s.col}"
                    })
        else:
            assigned = [{'seat_id': s.id, 'seat_label': f"{s.row}{s.col}", 'category': s.category.name} for s in allocated_seats]

        seat_labels = [a.get('seat_label') for a in assigned if a.get('seat_label')]

    return JsonResponse({
        'ok': True,
        'booking_id': booking.id,
        'total_price': total,
        'assigned': assigned,
        'seat_labels': seat_labels,
        'passengers': passengers
    })


def checkout(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    seats_param = request.GET.get('seats', '')
    seat_ids = []
    if seats_param:
        seat_ids = [int(s) for s in seats_param.split(',') if s.isdigit()]

    base = int(getattr(match, 'price_from', 0) or 0)
    perunggu_price = int(base)
    perak_price = int(round(base * 1.5)) if base else 0
    emas_price = int(round(base * 2)) if base else 0

    colors = {
        'Perunggu': '#cd7f32',
        'Perak': '#C0C0C0',
        'Emas': '#D4AF37',
    }

    desired = [
        ('Perunggu', perunggu_price),
        ('Perak', perak_price),
        ('Emas', emas_price),
    ]

    categories = []
    for name, price in desired:
        cat, created = SeatCategory.objects.get_or_create(
            name=name,
            defaults={'price': price or 0, 'color': colors.get(name, '')}
        )
        if not created and (cat.price == 0 and price):
            cat.price = price
            cat.color = cat.color or colors.get(name, '')
            cat.save(update_fields=['price', 'color'])
        categories.append(cat)

    categories_data = [{'name': c.name, 'price': c.price, 'color': c.color} for c in categories]

    return render(request, 'matches/checkout.html', {
        'match': match,
        'preselected_seat_ids': seat_ids,
        'categories': categories,
        'categories_data': categories_data,
    })

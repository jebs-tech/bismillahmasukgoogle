import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Match, Seat
from payment.models import Pembelian

def index(request):
    """
    Halaman root: tampilkan daftar match (singkat) atau redirect bila hanya 1 match.
    """
    matches = Match.objects.all().order_by('start_time')
    # jika tidak ada match, tampilkan halaman kosong dengan instruksi
    if matches.count() == 0:
        return render(request, 'matches/index.html', {'matches': matches, 'note': 'Belum ada pertandingan. Buat data Match lewat admin atau shell.'})

    # jika hanya 1 match, redirect langsung ke detail (opsional)
    # uncomment baris berikut jika Anda ingin redirect otomatis ketika ada 1 match
    # if matches.count() == 1:
    #     return redirect('matches:match_detail', pk=matches.first().id)

    return render(request, 'matches/index.html', {'matches': matches})

def match_detail(request, pk):
    match = get_object_or_404(Match, pk=pk)
    return render(request, 'matches/match_detail.html', {'match': match})

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
    buyer_name = payload.get('buyer_name')
    buyer_email = payload.get('buyer_email')
    if not (match_id and seat_ids and buyer_name and buyer_email):
        return HttpResponseBadRequest('missing fields')

    with transaction.atomic():
        seats_qs = Seat.objects.select_for_update().filter(id__in=seat_ids, is_booked=False)
        if seats_qs.count() != len(seat_ids):
            return JsonResponse({'ok': False, 'msg': 'Beberapa kursi sudah terisi'}, status=400)

        total = sum(s.category.price for s in seats_qs)
        booking = Pembelian.objects.create(match_id=match_id, buyer_name=buyer_name, buyer_email=buyer_email, total_price=total)
        booking.seats.add(*seats_qs)
        seats_qs.update(is_booked=True)

    return JsonResponse({'ok': True, 'booking_id': booking.id, 'total_price': total})      
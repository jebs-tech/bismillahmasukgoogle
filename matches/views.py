import json
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Match, Seat, SeatCategory, MatchSeatCapacity
from payment.models import Pembelian
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .forms import MatchForm
from django.contrib import messages

def is_staff(user):
    return user.is_staff

def match_list(request):
    matches = Match.objects.select_related('team_a', 'team_b', 'venue').order_by('start_time')
    month_filter = request.GET.get('month')
    
    if month_filter:
        matches = matches.filter(start_time__month=month_filter)
    
    # AJAX request: return partial HTML only
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'match_filter.html', {
            'matches': matches,
            'selected_month': month_filter,
        })
    
    # Normal request: return full page
    return render(request, 'match_list.html', {
        'matches': matches,
        'selected_month': month_filter,
    })


# Di matches/views.py

def match_detail(request, pk):
    # Ganti 'team_a' dan 'away_team' menjadi 'team_a' dan 'team_b'
    match = get_object_or_404(Match.objects.select_related('team_a', 'team_b'), pk=pk) 
    
    # Fungsi helper disederhanakan
    def _team_label(team_obj):
        # Asumsi model Team punya field 'name'
        return team_obj.name if team_obj else None

    team_left = _team_label(match.team_a)
    team_right = _team_label(match.team_b)

    # Logika fallback/parsing yang kompleks dihapus untuk kebersihan view
    # Jika Team A/B null, kita gunakan fallback default
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


# Di matches/views.py

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
    # Hapus passengers dari sini. Logika ini seharusnya di checkout page.

    # Ganti buyer_name/email dengan data user jika sudah login (best practice)
    user = request.user if request.user.is_authenticated else None
    
    # Ambil nama/email dari payload jika user anonim, atau dari objek user jika login
    # Asumsi buyer_name dan buyer_email dikirim dari frontend jika user anonim
    buyer_name = payload.get('buyer_name')
    buyer_email = payload.get('buyer_email')

    if not (match_id and seat_ids):
        return HttpResponseBadRequest('Missing required fields: match_id, seat_ids')

    # Validasi user dan info pembeli
    if user:
        buyer_name = user.profile.nama_lengkap if hasattr(user, 'profile') else user.username
        buyer_email = user.email
    elif not (buyer_name and buyer_email):
        return HttpResponseBadRequest('Missing buyer name or email for anonymous user.')

    with transaction.atomic():
        seats_qs = Seat.objects.select_for_update().filter(id__in=seat_ids, is_booked=False).select_related('category')
        seats = list(seats_qs)
        if len(seats) != len(seat_ids):
            return JsonResponse({'ok': False, 'msg': 'Beberapa kursi sudah terisi atau tidak valid.'}, status=400)

        # Hitung Total Harga
        total = sum(s.category.price for s in seats)
        
        # --- GANTI Booking.objects.create MENJADI Pembelian.objects.create ---
        pembelian = Pembelian.objects.create(
            user=user,
            match_id=match_id,
            nama_lengkap_pembeli=buyer_name,
            email=buyer_email or '',
            total_price=total,
            status='PENDING'
        )
        pembelian.seats.add(*seats)
        Seat.objects.filter(id__in=[s.id for s in seats]).update(is_booked=True)

    return JsonResponse({
        'ok': True,
        'order_id': pembelian.order_id,
        'total_price': total,
        'seat_labels': [f"{s.row}{s.col}" for s in seats]
    })

# Di matches/views.py

@csrf_exempt
def api_book_quantity(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')
    try:
        payload = json.loads(request.body.decode())
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    match_id = payload.get('match_id')
    # Hapus passengers dari sini. Logika ini seharusnya di checkout page.
    
    quantity = int(payload.get('quantity') or 0)
    top_category_name = payload.get('category_name')

    # Validasi user dan info pembeli (Sama seperti api_book)
    user = request.user if request.user.is_authenticated else None
    buyer_name = payload.get('buyer_name')
    buyer_email = payload.get('buyer_email')

    if not (match_id and quantity and top_category_name):
        return HttpResponseBadRequest('Missing fields: match_id, quantity, or category_name')
    
    if user:
        buyer_name = user.profile.nama_lengkap if hasattr(user, 'profile') else user.username
        buyer_email = user.email
    elif not (buyer_name and buyer_email):
        return HttpResponseBadRequest('Missing buyer name or email for anonymous user.')
    
    # Ambil Kategori
    try:
        top_category = SeatCategory.objects.get(name__iexact=top_category_name)
    except SeatCategory.DoesNotExist:
        return JsonResponse({'ok': False, 'msg': 'Kategori kursi tidak ditemukan.'}, status=404)


    with transaction.atomic():
        # Cari dan Kunci Kursi Tersedia
        seats_qs = Seat.objects.select_for_update().filter(
            match_id=match_id,
            category=top_category,
            is_booked=False
        ).order_by('id')[:quantity]
        
        seats = list(seats_qs)
        if len(seats) != quantity:
            return JsonResponse({'ok': False, 'msg': f'Tidak cukup kursi tersedia di kategori {top_category.name} (minta {quantity}, tersedia {len(seats)})'}, status=400)
            
        # Hitung Total Harga
        total = sum(s.category.price for s in seats)
        
        # --- GANTI Booking.objects.create MENJADI Pembelian.objects.create ---
        pembelian = Pembelian.objects.create(
            user=user,
            match_id=match_id,
            nama_lengkap_pembeli=buyer_name,
            email=buyer_email or '',
            total_price=total,
            status='PENDING'
        )
        pembelian.seats.add(*seats)
        Seat.objects.filter(id__in=[s.id for s in seats]).update(is_booked=True)

        assigned_seats = [{'seat_id': s.id, 'seat_label': f"{s.row}{s.col}"} for s in seats]

    return JsonResponse({
        'ok': True,
        'order_id': pembelian.order_id,
        'total_price': total,
        'assigned_seats': assigned_seats,
        'seat_labels': [s['seat_label'] for s in assigned_seats]
    })


def checkout(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    seats_param = request.GET.get('seats', '')
    seat_ids = []
    if seats_param:
        seat_ids = [int(s) for s in seats_param.split(',') if s.isdigit()]

    # --- PERBAIKAN: HANYA AMBIL KATEGORI YANG SUDAH ADA ---
    # Logika pembuatan kategori lama dihapus karena sudah dilakukan di admin/shell.
    categories = SeatCategory.objects.all().order_by('price')

    categories_data = [{'name': c.name, 'price': c.price, 'color': c.color, 'id': c.id} for c in categories]
    # ----------------------------------------------------

    # Anda mungkin ingin mengambil data kursi yang sudah dipilih untuk display
    preselected_seats = Seat.objects.filter(id__in=seat_ids).select_related('category')

    return render(request, 'matches/checkout.html', {
        'match': match,
        'preselected_seat_ids': seat_ids, # IDs kursi yang dipilih
        'preselected_seats': preselected_seats, # Objek kursi yang dipilih
        'categories': categories, # List objek kategori
        'categories_data': categories_data, # List dict kategori (untuk JS)
    })


@login_required
@user_passes_test(is_staff)
def match_create(request):
    if request.method == 'POST':
        print("🔵 CREATE POST request received")
        print("POST data:", request.POST)
        
        form = MatchForm(request.POST)
        if form.is_valid():
            match = form.save()
            print(f"✅ Match created: {match}")
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('matches:match_list')
        else:
            print(f"❌ Form validation errors: {form.errors}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = MatchForm()
    
    return render(request, 'match_form.html', {'form': form})

@login_required
@user_passes_test(is_staff)
def match_edit(request, pk):
    match = get_object_or_404(Match, pk=pk)
    
    if request.method == 'POST':
        print(f"🔵 EDIT POST request received for match {pk}")
        print("POST data:", request.POST)
        
        form = MatchForm(request.POST, instance=match)
        if form.is_valid():
            form.save()
            print(f"✅ Match updated: {match}")
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('match_list')
        else:
            print(f"❌ Form validation errors: {form.errors}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = MatchForm(instance=match)
    
    return render(request, 'match_form.html', {'form': form})

@login_required
@user_passes_test(is_staff)
def match_delete(request, pk):
    match = get_object_or_404(Match, pk=pk)
    
    if request.method == 'POST':
        print(f"🔵 DELETE request received for match {pk}")
        match.delete()
        print(f"✅ Match deleted: {pk}")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('match_list')
    
    return render(request, 'match_delete.html', {'match': match})

@user_passes_test(lambda u: u.is_staff, login_url='/admin/login/')
@transaction.atomic
def match_create_update(request, pk=None):
    instance = None
    if pk:
        instance = get_object_or_404(Match, pk=pk)
        
    form = MatchForm(request.POST or None, instance=instance)
    
    if request.method == 'POST' and form.is_valid():
        match = form.save()  # seat akan dibuat otomatis oleh signal
        msg = "berhasil diperbarui." if pk else "berhasil dibuat."
        messages.success(request, f"Pertandingan {match.title} {msg}")
        return redirect('matches:match_list')
    
    context = {
        'form': form,
        'is_edit': pk is not None,
        'match': instance,
        'title': 'Edit Pertandingan' if pk else 'Tambah Pertandingan'
    }
    return render(request, 'matches/match_form.html', context)
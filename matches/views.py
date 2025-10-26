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
    
    return render(request, 'matches/match_form.html', {'form': form, 'is_edit': False})

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
            return redirect('matches:match_list')
        else:
            print(f"❌ Form validation errors: {form.errors}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = MatchForm(instance=match)
    
    return render(request, 'matches/match_form.html', {'form': form, 'is_edit': True})

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
        return redirect('matches:match_list')
    
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
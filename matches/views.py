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

@csrf_exempt
def api_match_list(request):
    """API endpoint for Flutter app (returns JSON)"""
    try:
        matches = Match.objects.select_related('team_a', 'team_b', 'venue').order_by('start_time')
        
        # Filter by month
        month_filter = request.GET.get('month')
        if month_filter:
            matches = matches.filter(start_time__month=int(month_filter))
        
        # Build JSON response
        data = []
        for match in matches:
            data.append({
                'id': match.id,
                'title': match.title,
                'team_a': {
                    'name': match.team_a.name,
                    'logo': match.team_a.logo.url if match.team_a.logo else None
                },
                'team_b': {
                    'name': match.team_b.name,
                    'logo': match.team_b.logo.url if match.team_b.logo else None
                },
                'venue': {
                    'name': match.venue.name,
                    'address': match.venue.address
                },
                'start_time': match.start_time.isoformat(),
                'description': match.description,
                'price_from': match.price_from
            })
        
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  
def api_match_delete(request, id):
    """API endpoint to delete match"""
    if request.method == 'POST':
        try:
            match = Match.objects.get(id=id)
            match.delete()
            return JsonResponse({'success': True})
        except Match.DoesNotExist:
            return JsonResponse({'error': 'Match not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def show_json_by_id(request, pk):
    try:
        matches = Match.objects.select_related('user').get(pk=pk)
        data = {
            'id': str(matches.id),
            'name': matches.name,
            'description': matches.description,
            'category': matches.category,
            'thumbnail': matches.thumbnail,
            'views': matches.views,
            'created_at': matches.created_at.isoformat() if matches.created_at else None,
            'is_featured': matches.is_featured,
            'user_id': matches.user_id,
            'user_username': matches.user.username if matches.user_id else None,
        }
        return JsonResponse(data)
    except Match.DoesNotExist:
        return JsonResponse({'detail': 'Not found'}, status=404)

def show_json(request):
    """Return JSON untuk model Match (pertandingan voli)"""
    matches_list = Match.objects.select_related('team_a', 'team_b', 'venue').all()
    
    data = []
    for match in matches_list:
        data.append({
            'id': match.id,
            'title': match.title or f"{match.team_a.name if match.team_a else 'Team A'} vs {match.team_b.name if match.team_b else 'Team B'}",
            'team_a': {
                'name': match.team_a.name if match.team_a else 'Team A',
                'logo': match.team_a.logo.url if match.team_a and match.team_a.logo else None,
            },
            'team_b': {
                'name': match.team_b.name if match.team_b else 'Team B',
                'logo': match.team_b.logo.url if match.team_b and match.team_b.logo else None,
            },
            'venue': {
                'name': match.venue.name if match.venue else 'Unknown',
                'address': match.venue.address if match.venue else '',
            },
            'start_time': match.start_time.isoformat(),
            'description': match.description or '',
            'price_from': match.price_from,
        })
    
    return JsonResponse(data, safe=False)

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
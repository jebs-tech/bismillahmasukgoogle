from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .models import Match
from .forms import MatchForm

def is_staff(user):
    return user.is_staff

def match_list(request):
    matches = Match.objects.select_related('home_team', 'away_team', 'venue').order_by('start_time')
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
            return redirect('match_list')
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
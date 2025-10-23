from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Match, Team, Venue
from .forms import MatchForm
from django.http import JsonResponse

def is_staff(user):
    return user.is_staff

def match_list(request):
    matches = Match.objects.select_related('home_team', 'away_team', 'venue').order_by('start_time')
    
    # FILTER BULAN DOANG
    month_filter = request.GET.get('month')
    
    if month_filter:
        matches = matches.filter(start_time__month=month_filter)
    
    return render(request, 'match_list.html', {
        'matches': matches,
        'selected_month': month_filter,  # ← cuma ini doang
    })

@login_required
@user_passes_test(is_staff)
def match_create(request):
    if request.method == 'POST':
        form = MatchForm(request.POST)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('match_list')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = MatchForm()
    
    return render(request, 'match_form.html', {'form': form})
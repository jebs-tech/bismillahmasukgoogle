import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
# Perbaikan: Hapus UserCreationForm ganda
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm 
from .forms import ServetixUserCreationForm
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
# Asumsi model ini ada di 'user.models'
from user.models import Purchase, Ticket, Profile 

@login_required(login_url='/login')
def user_profile_view(request):
    user = request.user
    
    try:
        preferred_teams = user.profile.preferred_teams.all()
    except Profile.DoesNotExist:
        preferred_teams = [] 

    purchase_history = Purchase.objects.filter(user=user).order_by('-created_at')
    active_tickets = Ticket.objects.filter(user=user, status='active').order_by('event__event_date')
    
    context = {
        'purchase_history': purchase_history,
        'active_tickets': active_tickets,
        'preferred_teams': preferred_teams,
    }
    
    return render(request, 'profile/dashboard.html', context)


# (View promo_list_view kamu yang di-comment biarkan saja)

def register(request):
    if request.user.is_authenticated:
        return redirect('user:profile') 

    # 2. Ganti UserCreationForm menjadi ServetixUserCreationForm
    form = ServetixUserCreationForm()

    if request.method == "POST":
        # 3. Ganti juga di sini
        form = ServetixUserCreationForm(request.POST) 
        if form.is_valid():
            form.save()
            messages.success(request, 'Akun berhasil dibuat! Silakan login.')
            return redirect('user:login') 
            
    context = {'form':form}
    return render(request, 'registration/register.html', context)

def login_user(request):
    # Jika user sudah login, jangan biarkan ke halaman login lagi
    if request.user.is_authenticated:
        return redirect('user:profile') # Arahkan ke profil

    if request.method == 'POST':
        # Perbaikan: Kirim 'request' juga ke form
        form = AuthenticationForm(request, data=request.POST) 

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Perbaikan: Arahkan ke 'user:profile' (view profile di atas)
            response = HttpResponseRedirect(reverse("user:profile")) 
            response.set_cookie('last_login', str(datetime.datetime.now()))
            return response

    else:
        form = AuthenticationForm(request)
    context = {'form': form}
    return render(request, 'registration/login.html', context)

def logout_user(request):
    logout(request)
    # Perbaikan: Arahkan ke 'user:login'
    response = HttpResponseRedirect(reverse('user:login')) 
    response.delete_cookie('last_login')
    messages.info(request, "Anda telah berhasil logout.") # Tambahan: pesan logout
    return response
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm 
from .forms import ServetixUserCreationForm
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from user.models import Purchase, Ticket, Profile, Event
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.forms import SetPasswordForm
from .forms import ProfileEditForm
from django.views.decorators.http import require_POST
from django.db.models import Count, Q


from collections import namedtuple

@login_required(login_url='/login')
def user_profile_view(request):
    user = request.user
    
    try:
        preferred_teams = user.profile.preferred_teams.all()
    except Profile.DoesNotExist:
        preferred_teams = [] 

    purchase_history = Purchase.objects.filter(user=user).order_by('-created_at')
    active_tickets = Ticket.objects.filter(user=user, status='active').order_by('event__event_date')
    nama_lengkap = user.profile.nama_lengkap if hasattr(user, 'profile') else ''
    
    context = {
        'nama_lengkap': nama_lengkap,
        'purchase_history': purchase_history,
        'active_tickets': active_tickets,
        'preferred_teams': preferred_teams,
    }
    
    return render(request, 'profile/dashboard.html', context)

@login_required(login_url='/login')
def edit_profile(request):
    profile = request.user.profile 
    
    template_name = 'profile/edit_profile.html'
    
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil Anda berhasil diperbarui!')
            # TIDAK ADA REDIRECT. Biarkan render di bawah.
        else:
            messages.error(request, 'Silakan perbaiki kesalahan di bawah ini.')
    else:
        form = ProfileEditForm(instance=profile)
    
    context = {
        'form': form
    }
    # Selalu render partial template, baik untuk GET maupun POST
    return render(request, template_name, context)

@login_required(login_url='/login')
def get_delete_form(request):
    return render(request, 'profile/_delete_account_form.html')

@login_required(login_url='/login')
@require_POST
def delete_account_confirm(request):
    user = request.user
    
    # Lakukan logout terlebih dahulu
    logout(request)
    
    # Hapus user (profile akan terhapus otomatis via on_delete=CASCADE)
    user.delete()
    
    # Kirim response dengan htmx header untuk me-redirect seluruh halaman
    response = HttpResponse()
    response['HX-Redirect'] = reverse('user:login') # Arahkan ke homepage
    return response

@login_required(login_url='/login')
def get_active_tickets(request):
    active_tickets = Ticket.objects.filter(user=request.user, status='active') 
    
    context = {
        'active_tickets': active_tickets
    }
    return render(request, 'profile/_active_tickets.html', context)

@login_required(login_url='/login')
def get_purchase_history(request):
    finished_event_ids = Ticket.objects.filter(
        user=request.user
    ).exclude(
        status='active'
    ).values_list('event__id', flat=True).distinct()
    
    purchase_history_items = Event.objects.filter(
        id__in=finished_event_ids
    ).annotate(
        ticket_count=Count(
            'tickets', 
            filter=Q(tickets__user=request.user, tickets__status__in=['used', 'expired'])
        )
    ).select_related('team_a', 'team_b').order_by('-event_date') # Urutkan berdasarkan tanggal event

    context = {
        'purchase_history': purchase_history_items
    }
    return render(request, 'profile/_purchase_history.html', context)

@login_required(login_url='/login')
def get_preferred_teams(request):
    """
    Mengembalikan HTML partial HANYA untuk tim favorit.
    """
    preferred_teams = []
    try:
        preferred_teams = request.user.profile.preferred_teams.all()
    except Profile.DoesNotExist:
        pass
        
    context = {'preferred_teams': preferred_teams}
    return render(request, 'profile/_preferred_teams.html', context)

@login_required(login_url='/login')
def purchase_detail(request, event_id):
    
    event = get_object_or_404(Event, id=event_id)
    
    tickets = Ticket.objects.filter(
        user=request.user,
        event=event
    ).exclude(
        status='active'
    ).order_by('id') # Urutkan berdasarkan ID tiket
    
    context = {
        'event': event,
        'tickets': tickets
    }
    return render(request, 'profile/_purchase_detail.html', context)

@login_required(login_url='/login')
def ticket_detail(request, ticket_id):
    
    # Ambil tiket, pastikan itu milik user yang login
    ticket = get_object_or_404(
        Ticket.objects.select_related('event', 'event__team_a', 'event__team_b'), 
        id=ticket_id, 
        user=request.user
    )
    
    context = {
        'ticket': ticket,
    }
    # Render template modal
    return render(request, 'profile/_ticket_detail_modal.html', context)



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
            response.set_cookie('last_login', str(datetime.now()))
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

def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            # 1. Cari user berdasarkan email
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None
            
        if user:
            # 2. Buat token & uid
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # 3. Bangun URL untuk link di email
            current_site = get_current_site(request)
            domain = current_site.domain
            # Kita pakai 'user:password_reset_confirm' karena ini view kustom kita
            link = reverse('user:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            full_link = f"http://{domain}{link}"

            # 4. Render template email
            email_html = render_to_string('registration/password_reset_email.html', {
                'user': user,
                'full_link': full_link, # Kirim link lengkap ke template
            })

            # 5. Kirim email
            send_mail(
                subject="Reset Password Anda di Serve.Tix",
                message=f"Klik link ini untuk reset password: {full_link}", # Fallback plain text
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=email_html
            )

        # PENTING: Selalu redirect ke 'done'
        # Ini mencegah orang menebak-nebak email mana yang terdaftar
        messages.info(request, "Jika email Anda terdaftar, Anda akan menerima link reset.")
        return redirect('user:password_reset_done')
    
    return render(request, 'registration/password_reset_form.html')

def password_reset_confirm(request, uidb64=None, token=None):
    try:
        # 1. Decode UID dan ambil user
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # 2. Cek apakah user ada DAN token-nya valid
    if user is None or not default_token_generator.check_token(user, token):
        # Jika link tidak valid, tampilkan error
        messages.error(request, "Link reset password tidak valid atau sudah kadaluarsa.")
        return render(request, 'registration/password_reset_invalid.html')

    # 3. Jika link VALID, proses form
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save() # Simpan password baru
            messages.success(request, "Password berhasil diubah. Silakan login.")
            return redirect('user:password_reset_complete')
    else:
        # Tampilkan form kosong
        form = SetPasswordForm(user)

    return render(request, 'registration/password_reset_confirm.html', {'form': form})
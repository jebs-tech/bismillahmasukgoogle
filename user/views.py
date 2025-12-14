# Django Core Imports
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q

# Auth Imports
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.views.decorators.http import require_POST

# Password Reset Imports
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site

# --- Impor Model & Form yang SUDAH BENAR (Setelah Refaktor) ---
from .forms import ServetixUserCreationForm, ProfileEditForm
from .models import Profile
from matches.models import Match, Seat, Team
from payment.models import Pembelian
# -------------------------------------------------------------


#
# ==================================
# == BAGIAN AUTENTIKASI & REGISTRASI ==
# ==================================
#
def register(request):
    if request.user.is_authenticated:
        return redirect('user:profile') 

    form = ServetixUserCreationForm()

    if request.method == "POST":
        form = ServetixUserCreationForm(request.POST) 
        if form.is_valid():
            form.save()
            messages.success(request, 'Akun berhasil dibuat! Silakan login.')
            return redirect('user:login') 
            
    context = {'form':form}
    return render(request, 'registration/register.html', context)


def login_user(request):
    if request.user.is_authenticated:
        return redirect('user:profile') 

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST) 
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            response = HttpResponseRedirect(reverse("homepage:homepage")) 
            response.set_cookie('last_login', str(datetime.now()))
            return response
    else:
        form = AuthenticationForm(request)
        
    context = {'form': form}
    return render(request, 'registration/login.html', context)


def logout_user(request):
    logout(request)
    response = HttpResponseRedirect(reverse('user:login')) 
    response.delete_cookie('last_login')
    messages.info(request, "Anda telah berhasil logout.")
    return response

#
# ==========================
# == BAGIAN RESET PASSWORD ==
# ==========================
#
def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None
            
        if user:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            current_site = get_current_site(request)
            domain = current_site.domain
            link = reverse('user:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            full_link = f"http://{domain}{link}"
            email_html = render_to_string('registration/password_reset_email.html', {
                'user': user,
                'full_link': full_link,
            })
            send_mail(
                subject="Reset Password Anda di Serve.Tix",
                message=f"Klik link ini untuk reset password: {full_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=email_html
            )

        messages.info(request, "Jika email Anda terdaftar, Anda akan menerima link reset.")
        return redirect('user:password_reset_done')
    
    return render(request, 'registration/password_reset_form.html')


def password_reset_confirm(request, uidb64=None, token=None):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "Link reset password tidak valid atau sudah kadaluarsa.")
        return render(request, 'registration/password_reset_invalid.html')

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password berhasil diubah. Silakan login.")
            return redirect('user:password_reset_complete')
    else:
        form = SetPasswordForm(user)

    return render(request, 'registration/password_reset_confirm.html', {'form': form})

#
# =======================
# == BAGIAN DASHBOARD ==
# =======================
#
@login_required(login_url='/login')
def user_profile_view(request):
    """
    View utama yang merender 'dashboard.html'.
    HTMX akan memuat konten dari view lain ke dalam halaman ini.
    """
    context = {
        'nama_lengkap': request.user.profile.nama_lengkap if hasattr(request.user, 'profile') else ''
    }
    return render(request, 'profile/dashboard.html', context)


@login_required(login_url='/login')
def get_active_tickets(request):
    """
    Mengambil tiket untuk pertandingan yang BELUM TERJADI.
    """
    from payment.models import Pembelian
    import logging
    
    logger = logging.getLogger(__name__)
    
    now = timezone.now()
    print(f"DEBUG get_active_tickets: User: {request.user.username} (ID: {request.user.id})")
    print(f"DEBUG get_active_tickets: Current time: {now}")
    
    # Query dengan prefetch untuk seats
    active_purchases = Pembelian.objects.filter(
        user=request.user,
        status='CONFIRMED',
        match__start_time__gt=now # gt = greater than (di masa depan)
    ).select_related(
        'match', 
        'match__team_a', 
        'match__team_b',
        'match__venue'
    ).prefetch_related(
        'seats',
        'seats__category'
    ).order_by('match__start_time')
    
    print(f"DEBUG get_active_tickets: Found {active_purchases.count()} active purchases")
    for purchase in active_purchases:
        print(f"DEBUG: Purchase {purchase.order_id} - User: {purchase.user}, Status: {purchase.status}, Match: {purchase.match.title if purchase.match else 'None'}")
    
    context = {
        'active_purchases': active_purchases
    }
    return render(request, 'profile/_active_tickets.html', context)

@login_required(login_url='/login')
def get_active_tickets_modal(request): # <-- Nama fungsi baru
    """
    Mengambil tiket aktif HANYA untuk ditampilkan di modal navbar.
    """
    now = timezone.now()
    active_purchases = Pembelian.objects.filter(
        user=request.user,
        status='CONFIRMED',
        match__start_time__gt=now 
    ).select_related(
        'match', 
        'match__venue' # Cukup venue, tim tidak perlu di modal simpel
    ).prefetch_related('seats', 'seats__category').order_by('match__start_time') # Ambil seats & category

    context = {
        'active_purchases': active_purchases
    }
    # Render template BARU
    return render(request, 'profile/_active_tickets_modal.html', context)


@login_required(login_url='/login')
def get_purchase_history(request):
    """
    Mengambil pertandingan yang SUDAH LEWAT dan menghitung tiketnya.
    """
    now = timezone.now()
    
    past_match_ids = Pembelian.objects.filter(
        user=request.user,
        status='CONFIRMED',
        match__start_time__lte=now # lte = less than or equal (di masa lalu)
    ).values_list('match__id', flat=True).distinct()
    
    purchase_history_items = Match.objects.filter(
        id__in=past_match_ids
    ).annotate(
        ticket_count=Count(
            'seats', 
            filter=Q(pembelian_set__user=request.user, pembelian_set__status='CONFIRMED')
        )
    ).select_related('team_a', 'team_b').order_by('-start_time')
    
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
def purchase_detail(request, event_id): # event_id adalah match_id
    """
    Menampilkan detail riwayat pembelian (daftar tiket/kursi).
    """
    match = get_object_or_404(Match, id=event_id)
    
    try:
        purchase = Pembelian.objects.get(
            user=request.user, 
            match=match, 
            status='CONFIRMED'
        )
        tickets = purchase.seats.all().order_by('row', 'col')
    except Pembelian.DoesNotExist:
        tickets = []
        purchase = None
    
    context = {
        'event': match, # 'event' agar template lama berfungsi
        'tickets': tickets,
        'purchase': purchase
    }
    return render(request, 'profile/_purchase_detail.html', context)


login_required(login_url='/login')
def ticket_detail(request, ticket_id): # ticket_id adalah seat_id
    """
    Menampilkan modal detail untuk satu tiket/kursi, 
    TERMASUK mengambil data Pembelian terkait untuk QR Code.
    """
    seat = get_object_or_404(
        Seat.objects.select_related('match', 'category', 'match__venue', 'match__team_a', 'match__team_b'), 
        id=ticket_id, 
        pembelian_set__user=request.user,
        pembelian_set__status='CONFIRMED'
    )
    
    # --- AMBIL PEMBELIAN TERKAIT ---
    try:
        # Asumsi satu kursi hanya bisa dimiliki oleh satu pembelian yang confirmed
        pembelian_terkait = Pembelian.objects.get(seats=seat, user=request.user, status='CONFIRMED')
    except Pembelian.DoesNotExist:
        pembelian_terkait = None # Handle jika pembelian tidak ditemukan
    except Pembelian.MultipleObjectsReturned:
        # Kasus aneh jika satu kursi terhubung ke >1 pembelian confirmed user ini
        pembelian_terkait = Pembelian.objects.filter(seats=seat, user=request.user, status='CONFIRMED').first()
        print(f"Peringatan: Kursi {seat.id} terhubung ke beberapa pembelian!")
    # -------------------------------
    
    context = {
        'ticket': seat, # 'ticket' adalah objek Seat
        'pembelian': pembelian_terkait # <-- KIRIM PEMBELIAN KE TEMPLATE
    }
    return render(request, 'profile/_ticket_detail_modal.html', context)

#
# ============================
# == BAGIAN AKSI PROFIL (AJAX) ==
# ============================
#
@login_required(login_url='/login')
def edit_profile(request):
    profile = request.user.profile 
    template_name = 'profile/edit_profile.html'
    
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil Anda berhasil diperbarui!')
        else:
            messages.error(request, 'Silakan perbaiki kesalahan di bawah ini.')
    else:
        form = ProfileEditForm(instance=profile)
    
    context = {
        'form': form
    }
    return render(request, template_name, context)


@login_required(login_url='/login')
def get_delete_form(request):
    return render(request, 'profile/_delete_account_form.html')


@login_required(login_url='/login')
@require_POST
def delete_account_confirm(request):
    user = request.user
    logout(request)
    user.delete()
    response = HttpResponse()
    response['HX-Redirect'] = reverse('user:login')
    return response
# Django Core Imports
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
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
from django.contrib.auth import authenticate, login as auth_login
from django.db import IntegrityError
import json

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
from django.views.decorators.csrf import csrf_exempt
# -------------------------------------------------------------

#
# ==================================
# == BAGIAN AUTENTIKASI & REGISTRASI FLUTTER ==
# ==================================
#
@csrf_exempt
def login_flutter(request):
    if request.method == 'POST':
        # 1. Coba ambil dari request.POST (Untuk Form Data / pbp_django_auth default)
        username = request.POST.get('username')
        password = request.POST.get('password')

        # 2. Jika kosong, coba ambil dari JSON (Fallback jika pakai raw JSON)
        if not username or not password:
            try:
                data = json.loads(request.body)
                username = data.get('username')
                password = data.get('password')
            except json.JSONDecodeError:
                pass # Biarkan kosong jika bukan JSON valid

        # 3. Validasi Akhir
        if not username or not password:
             return JsonResponse({
                "status": False,
                "message": "Username dan Password tidak boleh kosong."
            }, status=400)

        # 4. Proses Autentikasi (Sama seperti sebelumnya)
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                auth_login(request, user)
                return JsonResponse({
                    "username": user.username,
                    "status": True,
                    "message": "Login successful!"
                }, status=200)
            else:
                return JsonResponse({
                    "status": False,
                    "message": "Akun dinonaktifkan."
                }, status=401)
        else:
            return JsonResponse({
                "status": False,
                "message": "Username atau password salah."
            }, status=401)
            
    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)
        
@csrf_exempt
def register_flutter(request):
    if request.method == 'POST':
        # 1. Coba Form Data
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email') # Ambil email juga

        # 2. Coba JSON
        if not username or not password:
            try:
                data = json.loads(request.body)
                username = data.get('username')
                password = data.get('password')
                email = data.get('email')
            except:
                pass
        
        # Validasi
        if not username or not password: # Email opsional tergantung kebutuhan
            return JsonResponse({"status": False, "message": "Data tidak lengkap"}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                "status": False,
                "message": "Username sudah terdaftar."
            }, status=400)

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            user.save()
            return JsonResponse({
                "status": True,
                "message": "Akun berhasil dibuat! Silakan login."
            }, status=201)
        except IntegrityError:
            return JsonResponse({
                "status": False,
                "message": "Terjadi kesalahan saat membuat akun."
            }, status=500)

    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)

@csrf_exempt
def logout_flutter(request):
    if request.user.is_authenticated:
        logout(request)
        return JsonResponse({
            "status": True,
            "message": "Logout berhasil!"
        }, status=200)
    else:
        return JsonResponse({
            "status": False,
            "message": "Anda belum login."
        }, status=401)
        
@csrf_exempt
def reset_password_flutter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({"status": False, "message": "Email harus diisi."}, status=400)

        try:
            user = User.objects.get(email=email)
            
            # Generate token dan UID
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # GANTI 'yourdomain.com' atau '10.0.2.2:8000' (emulator)
            # Link ini harus mengarah ke view 'password_reset_confirm' versi WEB biasa
            # agar user bisa ganti password via browser.
            domain = "10.0.2.2:8000" # Contoh untuk Android Emulator localhost
            protocol = 'http'
            
            # Anda harus memastikan URL 'user:password_reset_confirm' sudah ada di urls.py (versi web biasa)
            link = f"/user/reset/{uid}/{token}/" # Sesuaikan dengan path di urls.py Anda
            full_link = f"{protocol}://{domain}{link}"
            
            email_html = render_to_string('registration/password_reset_email.html', {
                'user': user,
                'full_link': full_link,
            })
            
            send_mail(
                subject="Reset Password Serve.Tix",
                message=f"Klik link untuk reset: {full_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=email_html
            )
            
            return JsonResponse({
                "status": True,
                "message": "Link reset password telah dikirim ke email Anda."
            }, status=200)

        except User.DoesNotExist:
            # Demi keamanan, tetap return success walaupun email tidak ada
            return JsonResponse({
                "status": True,
                "message": "Jika email terdaftar, link reset akan dikirim."
            }, status=200)
            
    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)

#
# ==================================
# == BAGIAN DASHBOARD FLUTTER ==
# ==================================
#

@csrf_exempt
def dashboard_flutter(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": False, "message": "Belum login"}, status=401)

    user = request.user
    
    # Ambil data profile
    nama_lengkap = ""
    preferred_teams = []
    
    if hasattr(user, 'profile'):
        nama_lengkap = user.profile.nama_lengkap
        # Ambil list tim favorit
        for team in user.profile.preferred_teams.all():
            preferred_teams.append({
                "id": team.id,
                "name": team.name, # Sesuaikan dengan field di model Team
                "logo": team.logo.url if team.logo else "" # Jika ada logo
            })

    return JsonResponse({
        "status": True,
        "username": user.username,
        "email": user.email,
        "nama_lengkap": nama_lengkap,
        "preferred_teams": preferred_teams
    }, status=200)
    
@csrf_exempt
def edit_profile_flutter(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": False, "message": "Belum login"}, status=401)

    if request.method == 'POST':
        try:
            # Baca data gabungan (Form Data atau JSON)
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            user = request.user
            profile = user.profile

            # 1. Update Data Dasar
            profile.nama_lengkap = data.get('nama_lengkap', profile.nama_lengkap)
            profile.nomor_telepon = data.get('nomor_telepon', profile.nomor_telepon) # Pastikan field ini ada di model
            
            # Update Email di User model
            new_email = data.get('email')
            if new_email and new_email != user.email:
                # Cek unik email jika perlu
                user.email = new_email
                user.save()

            # 2. Update Tim Favorit (Many-to-Many)
            # Flutter akan mengirim list ID tim, misal: [1, 3, 5]
            team_ids = data.get('preferred_teams', []) 
            
            # Jika data dikirim sebagai string (format form-data), perlu di-parse
            if isinstance(team_ids, str):
                try:
                    team_ids = json.loads(team_ids)
                except:
                    team_ids = []

            if team_ids is not None:
                # Reset tim favorit lalu set ulang sesuai pilihan baru
                profile.preferred_teams.clear()
                for team_id in team_ids:
                    try:
                        team = Team.objects.get(id=int(team_id))
                        profile.preferred_teams.add(team)
                    except Team.DoesNotExist:
                        continue
            
            profile.save()
            return JsonResponse({"status": True, "message": "Profil berhasil diperbarui!"}, status=200)

        except Exception as e:
            return JsonResponse({"status": False, "message": str(e)}, status=500)

    return JsonResponse({"status": False, "message": "Method not allowed"}, status=405)

@csrf_exempt
def get_active_tickets_flutter(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": False, "message": "Belum login"}, status=401)

    now = timezone.now()
    active_purchases = Pembelian.objects.filter(
        user=request.user,
        status='CONFIRMED',
        match__start_time__gt=now
    ).select_related('match', 'match__team_a', 'match__team_b', 'match__venue').order_by('match__start_time')

    data_tickets = []
    for purchase in active_purchases:
        # Hitung jumlah kursi/tiket dalam satu pembelian
        jumlah_tiket = purchase.seats.count()
        
        data_tickets.append({
            "purchase_id": purchase.id,
            "match_title": f"{purchase.match.team_a} vs {purchase.match.team_b}",
            "venue": purchase.match.venue.name if purchase.match.venue else "TBA",
            "date": purchase.match.start_time.strftime("%d %B %Y, %H:%M"), # Format tanggal cantik
            "total_tickets": jumlah_tiket,
            "total_price": purchase.total_price # Asumsi ada field ini
        })

    return JsonResponse({
        "status": True,
        "active_tickets": data_tickets
    }, status=200)
    
@csrf_exempt
def get_purchase_history_flutter(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": False, "message": "Belum login"}, status=401)

    now = timezone.now()
    
    # Logic sama seperti get_purchase_history di views asli
    past_match_ids = Pembelian.objects.filter(
        user=request.user,
        status='CONFIRMED',
        match__start_time__lte=now
    ).values_list('match__id', flat=True).distinct()
    
    purchase_history_items = Match.objects.filter(
        id__in=past_match_ids
    ).annotate(
        ticket_count=Count(
            'seats', 
            filter=Q(pembelian_set__user=request.user, pembelian_set__status='CONFIRMED')
        )
    ).select_related('team_a', 'team_b').order_by('-start_time')

    data_history = []
    for match in purchase_history_items:
        data_history.append({
            "match_id": match.id,
            "match_title": f"{match.team_a} vs {match.team_b}",
            "date": match.start_time.strftime("%d %B %Y"),
            "ticket_count": match.ticket_count, # Hasil anotasi Count tadi
        })

    return JsonResponse({
        "status": True,
        "history": data_history
    }, status=200)
    
@csrf_exempt
def ticket_detail_flutter(request, purchase_id):
    if not request.user.is_authenticated:
        return JsonResponse({"status": False, "message": "Belum login"}, status=401)
        
    try:
        purchase = Pembelian.objects.get(id=purchase_id, user=request.user)
        seats = purchase.seats.all()
        
        list_seats = []
        for seat in seats:
            list_seats.append({
                "seat_id": seat.id,
                "category": seat.category.name,
                "row": seat.row,
                "col": seat.col,
                "code": f"{seat.category.name}-{seat.row}{seat.col}" # Contoh kode kursi
            })
            
        return JsonResponse({
            "status": True,
            "match": str(purchase.match),
            "seats": list_seats
        }, 200)
    except Pembelian.DoesNotExist:
        return JsonResponse({"status": False, "message": "Pembelian tidak ditemukan"}, status=404)


from matches.models import Team # <--- Pastikan import ini benar sesuai model kamu

@csrf_exempt
def get_all_teams_flutter(request):
    # Mengambil semua tim untuk ditampilkan di checklist
    teams = Team.objects.all()
    data = []
    for team in teams:
        data.append({
            "id": team.id,
            "name": team.name,
        })
    return JsonResponse({"status": True, "teams": data}, status=200)

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
    now = timezone.now()
    active_purchases = Pembelian.objects.filter(
        user=request.user,
        status='CONFIRMED',
        match__start_time__gt=now # gt = greater than (di masa depan)
    ).select_related(
        'match', 
        'match__team_a', 
        'match__team_b'
    ).order_by('match__start_time')
    
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
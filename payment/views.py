from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import random
import string
import traceback
import os
import logging
from django.conf import settings
from io import BytesIO
from django.core.files.base import ContentFile
import qrcode
from django.core.mail import EmailMessage
from django.db import transaction, IntegrityError
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import Pembelian
from matches.models import Seat, Venue, Match, SeatCategory
from django.contrib.auth import get_user_model

User = get_user_model()
from voucher.utils import validate_and_apply_voucher
from voucher.models import VoucherUsage, Voucher

# --- SIMULASI DATA DARI HALAMAN DETAIL PERTANDINGAN (Priyz) ---
# Di aplikasi nyata, ini diambil dari Session atau Query Parameter setelah klik kursi.
SIMULASI_DATA_PERTANDINGAN = {
    'lapangan_terpilih': 'Istora Senayan',
    'kategori_terpilih': 'SILVER', # Harus Uppercase sesuai KATEGORI_CHOICES di Model Tiket
}
# -------------------------------------------------------------

SUMULASI_MATCH_ID = 1  # Ganti dengan ID Match yang valid di database Anda untuk pengujian

def detail_pembeli_view(request):
    """Menampilkan halaman Detail Pembeli, menyediakan kategori tiket untuk dipilih."""

    # 1. AMBIL MATCH ID (Kunci yang dioper dari halaman Priyz)
    match_id = request.GET.get('match_id', SUMULASI_MATCH_ID)

    # 2. Ambil objek Match dan kategori yang tersedia
    # Jika Match ID tidak ada atau Match tidak ditemukan, akan menampilkan 404
    match = get_object_or_404(Match, pk=match_id)

    # Ambil semua SeatCategory yang ada (Karena SeatCategory milik Priyz sepertinya global)
    categories = SeatCategory.objects.all().order_by('-price')

    context = {
        'match': match,
        'categories': categories, # Dikirim ke template untuk dropdown
        'max_tiket_per_transaksi': 5,
        'default_kategori': categories.first().name if categories.exists() else 'N/A'
    }

    return render(request, 'payment/detail_pembeli.html', context)

# -----------------------------

# Setup logger
logger = logging.getLogger(__name__)

@require_POST
@transaction.atomic
def simpan_pembelian_ajax(request):
    """
    Endpoint untuk menyimpan data pembelian.
    Menggunakan transaction.atomic untuk memastikan konsistensi data.
    """

    try:
        # Log request info untuk debugging - GUNAKAN print juga untuk memastikan muncul di log
        print("=" * 50)
        print("DEBUG: simpan_pembelian_ajax called")
        print(f"Request method: {request.method}")
        print(f"User: {request.user if request.user.is_authenticated else 'Anonymous'}")
        print(f"Content-Type: {request.META.get('CONTENT_TYPE')}")
        print(f"CSRF Token in header: {request.META.get('HTTP_X_CSRFTOKEN', 'NOT FOUND')}")
        print("=" * 50)

        logger.info(f"Request received from: {request.META.get('REMOTE_ADDR')}")
        logger.info(f"User: {request.user if request.user.is_authenticated else 'Anonymous'}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Content-Type: {request.META.get('CONTENT_TYPE')}")

        # Parse JSON body
        try:
            body_str = request.body.decode('utf-8')
            print(f"DEBUG: Request body: {body_str[:200]}...")  # Print first 200 chars
            data = json.loads(body_str)
            logger.info(f"DEBUG: Data received: {data}")
            print(f"DEBUG: Parsed data keys: {list(data.keys())}")
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error: {str(e)}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            return JsonResponse({
                "status": "error",
                "message": "Format JSON tidak valid"
            }, status=400)
        except Exception as e:
            error_msg = f"Error parsing request body: {str(e)}"
            print(f"ERROR: {error_msg}")
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return JsonResponse({
                "status": "error",
                "message": f"Error membaca data: {str(e)}"
            }, status=400)

        # Convert ke integer jika string
        try:
            match_id = int(data.get("match_id")) if data.get("match_id") else None
            kategori_id = int(data.get("kategori_id")) if data.get("kategori_id") else None
        except (ValueError, TypeError) as e:
            return JsonResponse({
                "status": "error",
                "message": f"Format match_id atau kategori_id tidak valid: {str(e)}"
            }, status=400)

        tickets = data.get("tickets")

        if not match_id or not kategori_id or not tickets:
            return JsonResponse({
                "status": "error",
                "message": "Data tidak lengkap"
            }, status=400)

        # Validasi data pembeli
        nama_lengkap = data.get("nama_lengkap", "").strip()
        email = data.get("email", "").strip()
        nomor_telepon = data.get("nomor_telepon", "").strip()

        if not nama_lengkap or not email or not nomor_telepon:
            return JsonResponse({
                "status": "error",
                "message": "Nama lengkap, email, dan nomor telepon wajib diisi"
            }, status=400)

        # Validasi format email sederhana
        if '@' not in email or '.' not in email.split('@')[-1]:
            return JsonResponse({
                "status": "error",
                "message": "Format email tidak valid"
            }, status=400)

        # Validasi panjang field
        if len(nama_lengkap) > 100:
            return JsonResponse({
                "status": "error",
                "message": "Nama lengkap terlalu panjang (maksimal 100 karakter)"
            }, status=400)

        if len(nomor_telepon) > 20:
            return JsonResponse({
                "status": "error",
                "message": "Nomor telepon terlalu panjang (maksimal 20 karakter)"
            }, status=400)

        match = Match.objects.get(id=match_id)
        kategori = SeatCategory.objects.get(id=kategori_id)

        # Hitung total harga
        jumlah_tiket = len(tickets)
        total_harga = jumlah_tiket * kategori.price

        # Cek apakah ada seat untuk match dan kategori ini
        total_seats = Seat.objects.filter(
            match=match,
            category=kategori
        ).count()

        if total_seats == 0:
            return JsonResponse({
                "status": "error",
                "message": f"Tidak ada kursi yang tersedia untuk kategori {kategori.name} pada pertandingan ini. Silakan hubungi administrator."
            }, status=400)

        # Cek jumlah seat yang tersedia SEBELUM mengambil
        total_available = Seat.objects.filter(
            match=match,
            category=kategori,
            is_booked=False
        ).count()

        print(f"DEBUG: Match ID: {match_id}, Kategori ID: {kategori_id}, Total seats: {total_seats}, Total available: {total_available}, Dibutuhkan: {jumlah_tiket}")

        if total_available < jumlah_tiket:
            return JsonResponse({
                "status": "error",
                "message": f"Tidak cukup kursi tersedia. Tersedia: {total_available}, Dibutuhkan: {jumlah_tiket}"
            }, status=400)

        # Ambil seat yang tersedia
        available_seats = list(Seat.objects.filter(
            match=match,
            category=kategori,
            is_booked=False
        )[:jumlah_tiket])

        if len(available_seats) < jumlah_tiket:
            return JsonResponse({
                "status": "error",
                "message": f"Tidak cukup kursi tersedia saat ini. Silakan coba lagi."
            }, status=400)

        print(f"DEBUG: Found {len(available_seats)} available seats")

        # Simpan seat IDs untuk rollback jika diperlukan
        seat_ids = [seat.id for seat in available_seats]

        # Buat Pembelian
        try:
            pembelian = Pembelian.objects.create(
                match=match,
                user=request.user if request.user.is_authenticated else None,
                nama_lengkap_pembeli=nama_lengkap,
                email=email,
                nomor_telepon=nomor_telepon,
                total_price=total_harga,
                status='PENDING'
            )
            print(f"DEBUG: Pembelian created with order_id: {pembelian.order_id}")
        except Exception as e:
            print(f"ERROR creating Pembelian: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                "status": "error",
                "message": f"Gagal membuat pembelian: {str(e)}"
            }, status=500)

        # Hubungkan seat ke pembelian (setelah Pembelian dibuat)
        try:
            pembelian.seats.set(available_seats)
            print(f"DEBUG: {len(available_seats)} seats linked to pembelian")
        except Exception as e:
            print(f"ERROR linking seats: {e}")
            print(traceback.format_exc())
            # Hapus pembelian jika gagal link seat
            pembelian.delete()
            return JsonResponse({
                "status": "error",
                "message": f"Gagal menghubungkan seat: {str(e)}"
            }, status=500)

        # Update is_booked untuk setiap seat SETELAH semuanya berhasil
        try:
            Seat.objects.filter(id__in=seat_ids).update(is_booked=True)
            print(f"DEBUG: {len(available_seats)} seats marked as booked")
        except Exception as e:
            print(f"ERROR updating seat status: {e}")
            print(traceback.format_exc())
            # Rollback: hapus pembelian dan unlink seats
            pembelian.seats.clear()
            pembelian.delete()
            return JsonResponse({
                "status": "error",
                "message": f"Gagal update status seat: {str(e)}"
            }, status=500)

        return JsonResponse({
            "status": "success",
            "order_id": pembelian.order_id
        })

    except (ValueError, TypeError) as e:
        print(f"ERROR ValueError/TypeError: {e}")
        print(traceback.format_exc())
        return JsonResponse({
            "status": "error",
            "message": f"Format data tidak valid: {str(e)}"
        }, status=400)

    except Match.DoesNotExist as e:
        error_msg = f"Match tidak ditemukan: {e}"
        print(f"ERROR: {error_msg}")
        logger.error(error_msg)
        return JsonResponse({"status": "error", "message": "Match tidak ditemukan"}, status=404)

    except SeatCategory.DoesNotExist as e:
        error_msg = f"Kategori tidak ditemukan: {e}"
        print(f"ERROR: {error_msg}")
        logger.error(error_msg)
        return JsonResponse({"status": "error", "message": "Kategori tidak ditemukan"}, status=404)

    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exc()

        # Print ke console (akan muncul di log PWS)
        print("=" * 50)
        print(f"CRITICAL ERROR in simpan_pembelian_ajax")
        print(f"Error Type: {error_type}")
        print(f"Error Message: {error_message}")
        print("Full Traceback:")
        print(error_traceback)
        print("=" * 50)

        # Log juga menggunakan logger
        logger.error(f"ERROR simpan_pembelian_ajax [{error_type}]: {error_message}")
        logger.error(error_traceback)

        # Berikan pesan error yang lebih informatif berdasarkan tipe error
        if "database" in error_message.lower() or "connection" in error_message.lower():
            user_message = "Terjadi masalah dengan database. Silakan coba lagi dalam beberapa saat."
        elif "timeout" in error_message.lower():
            user_message = "Request timeout. Silakan coba lagi."
        elif "memory" in error_message.lower():
            user_message = "Server kehabisan memori. Silakan hubungi administrator."
        elif "does not exist" in error_message.lower():
            user_message = "Data yang diminta tidak ditemukan di database."
        else:
            user_message = f"Terjadi kesalahan: {error_message}"

        return JsonResponse({
            "status": "error",
            "message": user_message,
            "error_type": error_type if settings.DEBUG else None  # Hanya tampilkan di development
        }, status=500)


def detail_pembayaran_view(request, order_id):
    pembelian = get_object_or_404(Pembelian, order_id=order_id, status='PENDING')

    # --- HAPUS SEMUA LOGIKA VOUCHER DARI VIEW INI ---
    diskon_amount = 0 # Set diskon 0 secara default (hanya untuk template)

    try:
        total_price_mentah = int(pembelian.total_price)
    except (TypeError, ValueError):
        total_price_mentah = 0 # Safety net jika total_price aneh

    # Formatting hanya untuk display di HTML
    total_harga_formatted = "{:,.0f}".format(total_price_mentah).replace(',', 'X').replace('.', ',').replace('X', '.')

    context = {
        'pembelian': pembelian,
        'order_id': pembelian.order_id,
        'diskon_amount': diskon_amount, # Diskon 0 saat load
       'total_harga_formatted': total_harga_formatted,
        'total_price_mentah': total_price_mentah
    }

    return render(request, 'payment/detail_pembayaran.html', context)

def generate_qr_code(qr_data):
    """Membuat QR Code dan mengembalikannya sebagai objek ContentFile."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Simpan gambar ke buffer memori
    buffer = BytesIO()
    img.save(buffer, format='PNG')

    # Bungkus dalam ContentFile agar bisa disimpan oleh Django ImageField
    filename = f'qr_{qr_data}.png'
    return ContentFile(buffer.getvalue(), name=filename)

# --- VIEW UTAMA AJAX UNTUK PEMBAYARAN ---

@require_POST
@csrf_exempt
@transaction.atomic
def proses_bayar_ajax(request, order_id):
    pembelian = get_object_or_404(Pembelian, order_id=order_id, status='PENDING')

    metode = request.POST.get('metode_pembayaran')
    bukti_transfer = request.FILES.get('bukti_transfer')

    if not metode:
        return JsonResponse({'status': 'error', 'message': 'Metode pembayaran wajib diisi.'}, status=400)

    if metode in ['BRI', 'BCA', 'Mandiri'] and not bukti_transfer:
        return JsonResponse({'status': 'error', 'message': 'Bukti transfer wajib untuk metode bank.'}, status=400)

    try:
        # =====================
        # UPDATE PEMBELIAN
        # =====================
        pembelian.metode_pembayaran = metode
        if bukti_transfer:
            pembelian.bukti_transfer = bukti_transfer
        pembelian.status = 'CONFIRMED'

        # Assign user jika user sudah login (untuk memastikan tiket muncul di dashboard)
        if request.user.is_authenticated and not pembelian.user:
            pembelian.user = request.user

        pembelian.save()

        # =====================
        # GENERATE QR PER TIKET
        # =====================
        etickets = []

        for seat in pembelian.seats.all():
            qr_data = f"SERVETIX|{pembelian.order_id}|SEAT-{seat.id}"
            seat.qrcode_data = qr_data

            qr_file = generate_qr_code(qr_data)
            filename = f"{pembelian.order_id}_seat_{seat.id}.png"

            seat.file_qr_code.save(filename, qr_file, save=True)

            etickets.append({
                "seat_id": seat.id,
                "seat": f"{seat.row}{seat.col}",
                "category": seat.category.name,
                "qr_url": seat.file_qr_code.url,
                "qr_data": qr_data
            })

        # =====================
        # RESPONSE KE FRONTEND
        # =====================
        return JsonResponse({
            "status": "success",
            "message": "Pembayaran berhasil, e-ticket siap.",
            "order_id": pembelian.order_id,
            "match_title": pembelian.match.title if pembelian.match else "N/A",
            "match_venue": pembelian.match.venue.name if pembelian.match and pembelian.match.venue else "N/A",
            "match_date": pembelian.match.start_time.strftime("%d %B %Y, %H:%M") if pembelian.match else "N/A",
            "tickets": etickets
        }, status=200)

    except Exception as e:
        print("ERROR PEMBAYARAN:", e)
        return JsonResponse({
            "status": "error",
            "message": "Terjadi kesalahan saat memproses pembayaran."
        }, status=500)


@require_POST
@csrf_exempt
def check_voucher_ajax(request):
    """Endpoint AJAX untuk memeriksa dan mengaplikasikan voucher secara real-time."""
    try:
        data = json.loads(request.body)
        voucher_code = data.get('code', '').strip()
        total_amount_raw = data.get('total', 0)

        if not voucher_code:
            return JsonResponse({'status': 'error', 'message': 'Kode wajib diisi.'}, status=400)

        # Pastikan total_amount selalu float valid
        try:
            total_amount = float(str(total_amount_raw).replace('Rp', '').replace(',', '').replace('.', '').strip())
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Format total tidak valid.'}, status=400)

        # Validasi voucher
        discount_amount, error_message = validate_and_apply_voucher(
            voucher_code,
            request.user,
            total_amount
        )

        if error_message:
            return JsonResponse({'status': 'error', 'message': error_message}, status=400)

        # Pastikan discount selalu float
        discount_value = float(discount_amount or 0)
        new_total = max(total_amount - discount_value, 0)

        return JsonResponse({
            'status': 'success',
            'discount_amount': discount_value,
            'new_total': new_total,
            'code': voucher_code
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
    except Exception as e:
        print(f"Error saat cek voucher: {e}")
        return JsonResponse({'status': 'error', 'message': 'Kesalahan Server saat validasi.'}, status=500)
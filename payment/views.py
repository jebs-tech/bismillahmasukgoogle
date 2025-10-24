from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import random
from django.conf import settings
from io import BytesIO
from django.core.files.base import ContentFile
import qrcode
from django.core.mail import EmailMessage
from django.db import transaction
from .models import Pembelian
from matches.models import Seat, Venue, Match, SeatCategory
# Import untuk Upload File di View Lanjutan
from django.core.files.uploadedfile import InMemoryUploadedFile
from voucher.utils import validate_and_apply_voucher
from voucher.models import VoucherUsage, Voucher # Import model penggunaan


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


# Di atas file payment/views.py
import json
import random
import string
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, IntegrityError

# --- Import Model yang BENAR ---
from .models import Pembelian
from matches.models import Match, Seat, SeatCategory 
# -----------------------------

@require_POST
@csrf_exempt 
@transaction.atomic 
def simpan_pembelian_ajax(request):
    """Endpoint AJAX: Pilih kategori & jumlah, server cari kursi, dan terapkan diskon voucher."""
    
    try:
        data = json.loads(request.body)
        
        # --- (TAMBAHAN VOUCHER) ---
        voucher_code = data.get('kode_voucher', '').strip() # Ambil kode voucher
        # ---------------------------
        
        required_fields = ['nama_lengkap', 'email', 'nomor_telepon', 'match_id', 'kategori_id', 'tickets']
        # Pastikan kita tidak crash jika tiket kosong (sudah dicek di bawah)
        if not all(field in data for field in required_fields if field != 'kode_voucher'): 
            return JsonResponse({'status': 'error', 'message': 'Data input tidak lengkap.'}, status=400)
            
        jumlah_tiket_diminta = len(data['tickets'])
        if jumlah_tiket_diminta <= 0:
             return JsonResponse({'status': 'error', 'message': 'Jumlah tiket tidak valid.'}, status=400)

        # 3. Ambil Objek Match dan Kategori
        try:
            match = Match.objects.get(id=data['match_id'])
            kategori = SeatCategory.objects.get(id=data['kategori_id'])
        except Match.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Pertandingan tidak ditemukan.'}, status=404)
        except SeatCategory.DoesNotExist:
             return JsonResponse({'status': 'error', 'message': 'Kategori kursi tidak ditemukan.'}, status=404)

        # 4. Cari Kursi Tersedia
        available_seats = Seat.objects.select_for_update(skip_locked=True).filter(
            match=match,
            category=kategori,
            is_booked=False
        )[:jumlah_tiket_diminta] 

        # Cek apakah kursi cukup
        if len(available_seats) < jumlah_tiket_diminta:
            return JsonResponse({'status': 'error', 'message': f'Maaf, hanya tersisa {len(available_seats)} tiket untuk kategori {kategori.name}.'}, status=409)

        # 5. Hitung Total Harga DASAR
        total_harga_dasar = jumlah_tiket_diminta * kategori.price
        total_harga_final = total_harga_dasar
        discount_amount = 0
        
        # --- 6. VALIDASI DAN APLIKASI VOUCHER (BARU) ---
        applied_code = ""
        if voucher_code:
            discount_amount, error_message = validate_and_apply_voucher(
                voucher_code, 
                request.user, 
                float(total_harga_dasar)
            )
            
            if error_message:
                # Jika ada error validasi voucher, kembalikan error 400
                return JsonResponse({'status': 'error', 'message': error_message}, status=400)
            
            if discount_amount > 0:
                total_harga_final -= discount_amount
                applied_code = voucher_code
            # Catatan: Jika diskon 0, kita abaikan kode vouchernya.
        # -----------------------------------------------------

        # 7. Buat Objek Pembelian (Simpan HARGA FINAL dan KODE VOUCHER)
        pembelian = Pembelian.objects.create(
            user=request.user if request.user.is_authenticated else None,
            match=match,
            nama_lengkap_pembeli=data['nama_lengkap'],
            email=data['email'],
            nomor_telepon=data['nomor_telepon'],
            total_price=total_harga_final, # <-- SIMPAN HARGA FINAL SETELAH DISKON
            kode_voucher=applied_code, # <-- SIMPAN KODE VOUCHER YANG BERHASIL
            status='PENDING'
        )
        
        # 8. Asosiasikan Kursi dan Tandai is_booked=True (Logika sama)
        pembelian.seats.set(available_seats)
        seat_ids_to_book = [seat.id for seat in available_seats]
        Seat.objects.filter(id__in=seat_ids_to_book).update(is_booked=True)
        
        # 9. Kirim Response Sukses
        return JsonResponse({
            'status': 'success', 
            'message': 'Booking berhasil disimpan. Lanjut ke pembayaran.', 
            'order_id': pembelian.order_id,
            'total_harga': total_harga_final,
            'discount_amount': discount_amount # Kirim nilai diskon untuk konfirmasi UI (opsional)
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Format data JSON tidak valid.'}, status=400)
    except IntegrityError: 
         return JsonResponse({'status': 'error', 'message': 'Konflik saat booking kursi, coba lagi.'}, status=409)
    except Exception as e:
        print(f"Error saat menyimpan pembelian (auto-assign): {e}") 
        return JsonResponse({'status': 'error', 'message': f'Terjadi kesalahan di server.'}, status=500)

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
        # 1. Update Pembelian
        pembelian.metode_pembayaran = metode
        if bukti_transfer:
            pembelian.bukti_transfer = bukti_transfer
        pembelian.status = 'CONFIRMED'
        pembelian.save() # Simpan perubahan status & bukti dulu

        # --- PERBAIKAN DI SINI: Generate QR per Seat ---
        # 2. Generate QR Code UNTUK SETIAP KURSI
        seats_in_purchase = pembelian.seats.all() 
        for seat in seats_in_purchase:
            # Buat data unik untuk QR (misal: order_id + seat_id)
            qr_data_string = f"SERVETIX-{pembelian.order_id}-{seat.id}" 
            seat.qr_code_data = qr_data_string
            
            qr_file = generate_qr_code(qr_data_string)
            # Simpan file QR ke objek Seat
            seat.file_qr_code.save(qr_file.name, qr_file, save=True)
        # --- AKHIR PERBAIKAN ---

        # 4. Berhasil!
        return JsonResponse({
            'status': 'success', 
            'message': f'Pembayaran {pembelian.order_id} dikonfirmasi. E-Ticket dikirim ke email.',
            'order_id': pembelian.order_id,
            'redirect_url': f'/payment/sukses/{pembelian.order_id}/' 
        }, status=200)

    except Exception as e:
        print(f"Processing Error (per ticket QR): {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Pemrosesan pembayaran gagal.'}, status=500)
    
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
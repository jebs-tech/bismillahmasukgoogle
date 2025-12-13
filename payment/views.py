from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import random
import string
import traceback
import os
from django.conf import settings
from io import BytesIO
from django.core.files.base import ContentFile
import qrcode
from django.core.mail import EmailMessage
from django.db import transaction, IntegrityError
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import Pembelian
from matches.models import Seat, Venue, Match, SeatCategory
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

@require_POST
def simpan_pembelian_ajax(request):
    try:
        data = json.loads(request.body)

        match_id = data.get("match_id")
        kategori_id = data.get("kategori_id")
        tickets = data.get("tickets")

        if not match_id or not kategori_id or not tickets:
            return JsonResponse({
                "status": "error",
                "message": "Data tidak lengkap"
            }, status=400)

        match = Match.objects.get(id=match_id)
        kategori = Category.objects.get(id=kategori_id)

        order = Order.objects.create(
            match=match,
            kategori=kategori,
            nama_lengkap=data.get("nama_lengkap"),
            email=data.get("email"),
            nomor_telepon=data.get("nomor_telepon"),
            total_harga=len(tickets) * kategori.price
        )

        for t in tickets:
            Ticket.objects.create(
                order=order,
                nama=t["nama"],
                jenis_kelamin=t["jenis_kelamin"],
                kategori=kategori
            )

        return JsonResponse({
            "status": "success",
            "order_id": order.id
        })

    except Match.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Match tidak ditemukan"}, status=404)

    except Category.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Kategori tidak ditemukan"}, status=404)

    except Exception as e:
        print("ERROR simpan_pembelian_ajax:", e)
        return JsonResponse({
            "status": "error",
            "message": "Internal Server Error"
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
                "seat": f"{seat.row}{seat.col}",
                "category": seat.category.name,
                "qr_url": seat.file_qr_code.url
            })

        # =====================
        # RESPONSE KE FRONTEND
        # =====================
        return JsonResponse({
            "status": "success",
            "message": "Pembayaran berhasil, e-ticket siap.",
            "order_id": pembelian.order_id,
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
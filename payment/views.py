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
from django.db import transaction # Import transaction jika Anda mau menggunakannya
from django.db.models import F, Sum

# HAPUS: from .models import Pembelian, Tiket, Venue
from .models import Pembelian, Tiket # HAPUS Venue
from matches.models import Match, SeatCategory # IMPOR DARI APLIKASI PRIYZ

# Import untuk Upload File di View Lanjutan (Jika diperlukan, tergantung implementasi)
from django.core.files.uploadedfile import InMemoryUploadedFile


# SIMULASI: Match ID mana yang Anda jual tiketnya.
# Ganti dengan ID match yang valid di DB untuk testing (misal ID 1)
SIMULASI_MATCH_ID = 2 

# --- FUNGSI PEMBANTU (generate_qr_code dan simulasikan_kirim_email_eticket tetap sama) ---
def generate_qr_code(qr_data):
    # ... (kode QR code sama)
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    filename = f'qr_{qr_data}.png'
    return ContentFile(buffer.getvalue(), name=filename)

def simulasikan_kirim_email_eticket(pembelian):
    # ... (kode email sama)
    # CATATAN: Karena kode ini menggunakan tiket.file_qr_code.path,
    # Anda perlu memastikan setting MEDIA_ROOT sudah benar di settings.py
    print(f"SIMULASI: E-Ticket untuk {pembelian.order_id} berhasil 'dikirim' ke {pembelian.email}")
    return True
# ----------------------------------------------------------------------------------------


def detail_pembeli_view(request):
    """Menampilkan halaman Detail Pembeli, menyediakan kategori tiket untuk dipilih."""
    
    # 1. AMBIL MATCH ID (Kunci yang dioper dari halaman Priyz)
    match_id = request.GET.get('match_id', SIMULASI_MATCH_ID) 
    
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


@require_POST
@csrf_exempt 
def simpan_pembelian_ajax(request):
    """Endpoint AJAX: Menerima Pilihan Kategori dan menyimpan Pembelian/Tiket."""
    
    try:
        data = json.loads(request.body)
        
        # 1. Parsing Data
        match_id = data.get('match_id')
        kategori_id = data.get('kategori_id')
        
        # 2. Validasi & Re-Check Harga (KEAMANAN SERVER SIDE)
        if not data.get('nama_lengkap') or not data.get('email') or not data.get('tickets') or not kategori_id:
            return JsonResponse({'status': 'error', 'message': 'Data wajib belum lengkap.'}, status=400)
             
        try:
            kategori = SeatCategory.objects.get(pk=kategori_id)
            harga_satuan = kategori.price
            match = Match.objects.get(pk=match_id)
            
            if harga_satuan <= 0:
                return JsonResponse({'status': 'error', 'message': 'Harga tiket tidak valid.'}, status=400)
        except (SeatCategory.DoesNotExist, Match.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': 'Match atau Kategori tidak ditemukan.'}, status=400)

        # 3. Hitung Total Harga
        jumlah_tiket = len(data['tickets'])
        total_harga = jumlah_tiket * harga_satuan

        # 4. Buat Objek Pembelian (Transaksi)
        pembelian = Pembelian.objects.create(
            match=match, # Relasi Match
            nama_lengkap_pembeli=data['nama_lengkap'],
            email=data['email'],
            nomor_telepon=data['nomor_telepon'],
            total_harga=total_harga,
        )
        
        # 5. Buat Objek Tiket
        for i, ticket_data in enumerate(data['tickets']):
            qr_data = f"{pembelian.order_id}-{i+1}-{random.randint(100, 999)}"
            Tiket.objects.create(
                pembelian=pembelian,
                nama_pemegang=ticket_data['nama'],
                jenis_kelamin=ticket_data['jenis_kelamin'],
                kategori_kursi=kategori.name.upper(), # Simpan nama kategori (contoh: SILVER)
                qr_code_data=qr_data
            )
            
        return JsonResponse({
            'status': 'success', 
            'order_id': pembelian.order_id,
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Server error: {str(e)}'}, status=500)


def detail_pembayaran_view(request, order_id):
    # ... (View ini tidak berubah)
    pembelian = get_object_or_404(Pembelian, order_id=order_id, status='PENDING')
    
    total_harga_formatted = "{:,.0f}".format(pembelian.total_harga).replace(',', 'X').replace('.', ',').replace('X', '.')
    
    context = {
        'pembelian': pembelian,
        'order_id': pembelian.order_id,
        'total_harga_formatted': total_harga_formatted,
    }
    
    return render(request, 'payment/detail_pembayaran.html', context)


@require_POST
@csrf_exempt 
def proses_bayar_ajax(request, order_id):
    # ... (View ini tidak berubah)
    pembelian = get_object_or_404(Pembelian, order_id=order_id, status='PENDING')
    
    metode = request.POST.get('metode_pembayaran')
    bukti_transfer = request.FILES.get('bukti_transfer')
    
    # ... (Logika validasi dan update status)
    
    try:
        # 1. Update Detail Pembelian
        pembelian.metode_pembayaran = metode
        if bukti_transfer:
            pembelian.bukti_transfer = bukti_transfer
        
        pembelian.status = 'CONFIRMED'
        pembelian.save()

        # 3. Generate QR Code untuk semua tiket
        for tiket in pembelian.tikets.all():
            qr_file = generate_qr_code(tiket.qr_code_data)
            tiket.file_qr_code.save(qr_file.name, qr_file, save=True)
            
        # 4. Kirim E-Ticket (Simulasi SendGrid)
        simulasikan_kirim_email_eticket(pembelian)
        
        # 5. Berhasil!
        return JsonResponse({
            'status': 'success', 
            'order_id': pembelian.order_id,
            'redirect_url': f'/payment/sukses/{pembelian.order_id}/'
        }, status=200)

    except Exception as e:
        print(f"Processing Error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Pemrosesan pembayaran gagal: {str(e)}'}, status=500)
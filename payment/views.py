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

from .models import Pembelian, Tiket, Venue
# Import untuk Upload File di View Lanjutan
from django.core.files.uploadedfile import InMemoryUploadedFile


# --- SIMULASI DATA DARI HALAMAN DETAIL PERTANDINGAN (Priyz) ---
# Di aplikasi nyata, ini diambil dari Session atau Query Parameter setelah klik kursi.
SIMULASI_DATA_PERTANDINGAN = {
    'lapangan_terpilih': 'Istora Senayan',
    'kategori_terpilih': 'SILVER', # Harus Uppercase sesuai KATEGORI_CHOICES di Model Tiket
}
# -------------------------------------------------------------


def detail_pembeli_view(request):
    """Menampilkan halaman Detail Pembeli"""
    
    # --- LOGIKA MENGAMBIL HARGA DARI DB ---
    lapangan = SIMULASI_DATA_PERTANDINGAN['lapangan_terpilih']
    kategori = SIMULASI_DATA_PERTANDINGAN['kategori_terpilih']
    
    try:
        venue = Venue.objects.get(nama_lapangan=lapangan)
        harga_satuan = venue.get_price_by_category(kategori)
    except Venue.DoesNotExist:
        harga_satuan = 0
    except Exception:
        harga_satuan = 0

    # Pastikan harga adalah integer atau 0
    harga_satuan = int(harga_satuan) if harga_satuan else 0
    # -------------------------------------

    context = {
        'harga_satuan': harga_satuan,
        'kategori_terpilih': kategori.title(), # Ubah ke Title Case untuk tampilan di HTML
        'lapangan_terpilih': lapangan,
        'max_tiket_per_transaksi': 5,
    }
    
    return render(request, 'payment/detail_pembeli.html', context)


@require_POST
@csrf_exempt # HARAP HAPUS CSRF_EXEMPT INI DI PROD! Gunakan {% csrf_token %} dan AJAX Header yang benar.
def simpan_pembelian_ajax(request):
    """Endpoint AJAX untuk menyimpan Detail Pembeli dan tiket ke DB."""
    
    try:
        # 1. Parsing Data JSON
        data = json.loads(request.body)
        
        # 2. Validasi Data
        if not data.get('nama_lengkap') or not data.get('email') or not data.get('tickets'):
            return JsonResponse({'status': 'error', 'message': 'Data wajib (nama, email, tiket) belum lengkap.'}, status=400)

        # 3. Ambil Harga (Re-Check di Server Side untuk keamanan)
        lapangan = data.get('lapangan_terpilih')
        kategori = data.get('kategori_terpilih').upper()
        
        try:
            venue = Venue.objects.get(nama_lapangan=lapangan)
            harga_satuan = venue.get_price_by_category(kategori)
            harga_satuan = int(harga_satuan) if harga_satuan else 0

            if not harga_satuan or harga_satuan <= 0:
                return JsonResponse({'status': 'error', 'message': 'Kategori tiket tidak valid atau tidak tersedia.'}, status=400)
        except Venue.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Venue tidak ditemukan.'}, status=400)

        # 4. Hitung Total Harga
        jumlah_tiket = len(data['tickets'])
        total_harga = jumlah_tiket * harga_satuan

        # 5. Buat Objek Pembelian (Transaksi)
        pembelian = Pembelian.objects.create(
            nama_lengkap_pembeli=data['nama_lengkap'],
            email=data['email'],
            nomor_telepon=data['nomor_telepon'],
            total_harga=total_harga,
        )
        
        # 6. Buat Objek Tiket
        for i, ticket_data in enumerate(data['tickets']):
            qr_data = f"{pembelian.order_id}-{i+1}-{random.randint(100, 999)}"
            Tiket.objects.create(
                pembelian=pembelian,
                nama_pemegang=ticket_data['nama'],
                jenis_kelamin=ticket_data['jenis_kelamin'],
                kategori_kursi=kategori,
                qr_code_data=qr_data # Hanya menyimpan data, QR image digenerate di tahap pembayaran
            )
            
        return JsonResponse({
            'status': 'success', 
            'message': 'Data pembelian disimpan. Lanjut ke pembayaran.', 
            'order_id': pembelian.order_id,
            'total_harga': total_harga
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Server error: {str(e)}'}, status=500)


def detail_pembayaran_view(request, order_id):
    """Menampilkan halaman Detail Pembayaran"""
    pembelian = get_object_or_404(Pembelian, order_id=order_id, status='PENDING')
    
    # Format Rupiah
    total_harga_formatted = "{:,.0f}".format(pembelian.total_harga).replace(',', 'X').replace('.', ',').replace('X', '.')
    
    context = {
        'pembelian': pembelian,
        'order_id': pembelian.order_id,
        'total_harga_formatted': total_harga_formatted,
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

def simulasikan_kirim_email_eticket(pembelian):
    """
    Simulasi pengiriman e-ticket melalui Email. 
    Di produksi, ganti ini dengan integrasi SendGrid yang sebenarnya.
    """
    subject = f"E-Ticket Anda - Order #{pembelian.order_id}"
    body = f"""
    Halo {pembelian.nama_lengkap_pembeli},

    Terima kasih telah membeli tiket di SERVE.TIX!

    Berikut detail E-Ticket Anda untuk Order ID: {pembelian.order_id}.
    Tiket ini akan dikirimkan sebagai lampiran.

    Detail Pembelian:
    - Total Harga: {pembelian.total_harga}
    - Status: Terkonfirmasi
    - Email: {pembelian.email}

    Selamat menikmati pertandingan!

    Salam,
    Tim SERVE.TIX
    """
    
    # Gunakan EmailMessage bawaan Django
    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL, # Pastikan ini diatur di settings.py
        [pembelian.email] # Tujuan
    )
    
    # Lampirkan setiap QR Code (E-Ticket)
    for tiket in pembelian.tikets.all():
        # Asumsi file_qr_code sudah terisi
        if tiket.file_qr_code:
            email.attach_file(tiket.file_qr_code.path) 

    # email.send() # Batalkan komentar ini untuk mengirim email sungguhan
    print(f"SIMULASI: E-Ticket untuk {pembelian.order_id} berhasil 'dikirim' ke {pembelian.email}")
    return True

# --- VIEW UTAMA AJAX UNTUK PEMBAYARAN ---

@require_POST
@csrf_exempt # HARAP HAPUS CSRF_EXEMPT INI DI PROD! Gunakan {% csrf_token %} dan AJAX Header yang benar.
def proses_bayar_ajax(request, order_id):
    """
    Memproses konfirmasi pembayaran, menyimpan bukti transfer, 
    mengubah status, membuat QR code, dan mengirim email.
    """
    pembelian = get_object_or_404(Pembelian, order_id=order_id, status='PENDING')
    
    metode = request.POST.get('metode_pembayaran')
    bukti_transfer = request.FILES.get('bukti_transfer')
    
    if not metode:
        return JsonResponse({'status': 'error', 'message': 'Metode pembayaran wajib diisi.'}, status=400)
        
    # Validasi Bukti Transfer hanya untuk Bank Transfer
    if metode in ['BRI', 'BCA', 'Mandiri'] and not bukti_transfer:
        return JsonResponse({'status': 'error', 'message': 'Bukti transfer wajib untuk metode bank.'}, status=400)

    try:
        # 1. Update Detail Pembelian
        pembelian.metode_pembayaran = metode
        
        # Simpan bukti transfer jika ada
        if bukti_transfer:
            pembelian.bukti_transfer = bukti_transfer
        
        # 2. Ubah Status Menjadi CONFIRMED (Simulasi Konfirmasi Otomatis)
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
            'message': f'Pembayaran {pembelian.order_id} dikonfirmasi. E-Ticket dikirim ke email.',
            'order_id': pembelian.order_id,
            'redirect_url': f'/payment/sukses/{pembelian.order_id}/' # Arahkan ke halaman sukses
        }, status=200)

    except Exception as e:
        # Jika terjadi error saat menyimpan file/QR/email, kembalikan status transaksi
        # Note: Dalam kasus nyata, Anda mungkin ingin me-rollback status pembelian ke PENDING.
        print(f"Processing Error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Pemrosesan pembayaran gagal: {str(e)}'}, status=500)
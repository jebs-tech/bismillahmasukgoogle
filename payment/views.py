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
@csrf_exempt 
@transaction.atomic # WAJIB di atas fungsi
def simpan_pembelian_ajax(request):
    """Endpoint AJAX: Pilih kategori & jumlah, server cari kursi, dan terapkan diskon voucher."""
    
    try:
        data = json.loads(request.body)
        voucher_code = data.get('kode_voucher', '').strip()
        
        # Debug: print data yang diterima (hapus di production)
        print(f"[DEBUG] Data received: {data}")
        
        required_fields = ['nama_lengkap', 'email', 'nomor_telepon', 'match_id', 'kategori_id', 'tickets']
        # 1. Validasi Input Dasar
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JsonResponse({
                'status': 'error', 
                'message': f'Data input tidak lengkap. Field yang kurang: {", ".join(missing_fields)}'
            }, status=400)
        
        # Validasi bahwa field tidak kosong
        nama_lengkap = data['nama_lengkap'].strip() if data['nama_lengkap'] else ''
        email = data['email'].strip() if data['email'] else ''
        nomor_telepon = data['nomor_telepon'].strip() if data['nomor_telepon'] else ''
        
        # Validasi panjang field
        if not nama_lengkap:
            return JsonResponse({'status': 'error', 'message': 'Nama lengkap tidak boleh kosong.'}, status=400)
        if len(nama_lengkap) > 100:
            return JsonResponse({'status': 'error', 'message': 'Nama lengkap terlalu panjang (maksimal 100 karakter).'}, status=400)
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email tidak boleh kosong.'}, status=400)
        if len(email) > 254:
            return JsonResponse({'status': 'error', 'message': 'Email terlalu panjang.'}, status=400)
        if '@' not in email:  # Validasi email sederhana
            return JsonResponse({'status': 'error', 'message': 'Format email tidak valid.'}, status=400)
        if not nomor_telepon:
            return JsonResponse({'status': 'error', 'message': 'Nomor telepon tidak boleh kosong.'}, status=400)
        if len(nomor_telepon) > 20:
            return JsonResponse({'status': 'error', 'message': 'Nomor telepon terlalu panjang (maksimal 20 karakter).'}, status=400)
            
        # Validasi tickets array
        if not isinstance(data['tickets'], list):
            return JsonResponse({'status': 'error', 'message': 'Data tiket tidak valid.'}, status=400)
            
        jumlah_tiket_diminta = len(data['tickets'])
        if jumlah_tiket_diminta <= 0:
            return JsonResponse({'status': 'error', 'message': 'Jumlah tiket tidak valid.'}, status=400)
        if jumlah_tiket_diminta > 10:  # Batasi maksimal tiket per transaksi
            return JsonResponse({'status': 'error', 'message': 'Maksimal 10 tiket per transaksi.'}, status=400)

        # 2. Ambil Objek Match dan Kategori
        try:
            # Validasi match_id dan kategori_id tidak kosong atau None
            match_id_raw = data.get('match_id')
            kategori_id_raw = data.get('kategori_id')
            
            if not match_id_raw or match_id_raw == '' or match_id_raw is None:
                return JsonResponse({'status': 'error', 'message': 'Match ID tidak boleh kosong.'}, status=400)
            if not kategori_id_raw or kategori_id_raw == '' or kategori_id_raw is None:
                return JsonResponse({'status': 'error', 'message': 'Kategori ID tidak boleh kosong. Pastikan Anda sudah memilih kategori kursi.'}, status=400)
            
            # Konversi ke integer untuk memastikan tipe data benar
            try:
                match_id = int(match_id_raw)
                kategori_id = int(kategori_id_raw)
                print(f"[DEBUG] Parsed IDs - match_id: {match_id}, kategori_id: {kategori_id}")
            except (ValueError, TypeError) as e:
                print(f"[DEBUG] Error parsing IDs - match_id_raw: {match_id_raw}, kategori_id_raw: {kategori_id_raw}, error: {e}")
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Format ID tidak valid. Match ID: "{match_id_raw}", Kategori ID: "{kategori_id_raw}". Pastikan keduanya adalah angka.'
                }, status=400)
            
            match = Match.objects.get(id=match_id)
            kategori = SeatCategory.objects.get(id=kategori_id)
            
            # Validasi kategori memiliki price yang valid
            if kategori.price is None or kategori.price < 0:
                return JsonResponse({'status': 'error', 'message': f'Harga kategori {kategori.name} tidak valid.'}, status=400)
            
            print(f"[DEBUG] Found - Match: {match.title}, Kategori: {kategori.name}, Price: {kategori.price}")
        except Match.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Pertandingan dengan ID {match_id} tidak ditemukan.'}, status=404)
        except SeatCategory.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Kategori kursi dengan ID {kategori_id} tidak ditemukan.'}, status=404)

        # 3. Cari Kursi Tersedia (select_for_update untuk mengunci kursi)
        try:
            available_seats = list(Seat.objects.select_for_update().filter(
                match=match,
                category=kategori,
                is_booked=False
            )[:jumlah_tiket_diminta])
        except Exception as e:
            print(f"Error saat mencari kursi: {e}")
            print(traceback.format_exc())
            return JsonResponse({'status': 'error', 'message': f'Error saat mencari kursi: {str(e)}'}, status=500)

        # Cek apakah kursi cukup
        if len(available_seats) < jumlah_tiket_diminta:
            return JsonResponse({'status': 'error', 'message': f'Maaf, hanya tersisa {len(available_seats)} tiket untuk kategori {kategori.name}.'}, status=409)

        # 4. Hitung Total Harga
        try:
            total_harga_dasar = jumlah_tiket_diminta * int(kategori.price)
            if total_harga_dasar < 0:
                return JsonResponse({'status': 'error', 'message': 'Total harga tidak valid.'}, status=400)
            if total_harga_dasar > 999999999:  # Batas maksimal untuk PositiveIntegerField
                return JsonResponse({'status': 'error', 'message': 'Total harga terlalu besar.'}, status=400)
        except (TypeError, ValueError) as e:
            return JsonResponse({'status': 'error', 'message': f'Error menghitung total harga: {str(e)}'}, status=400)
            
        total_harga_final = total_harga_dasar
        discount_amount = 0
        applied_code = ""
        
        # 5. VALIDASI DAN APLIKASI VOUCHER
        if voucher_code:
            try:
                discount_amount, error_message = validate_and_apply_voucher(
                    voucher_code, 
                    request.user if hasattr(request, 'user') else None, 
                    float(total_harga_dasar)
                )
                
                if error_message:
                    # Jika ada error validasi voucher, kembalikan error 400
                    return JsonResponse({'status': 'error', 'message': error_message}, status=400)
                
                if discount_amount > 0:
                    total_harga_final = max(0, total_harga_dasar - discount_amount)  # Pastikan tidak negatif
                    applied_code = voucher_code
            except Exception as e:
                print(f"Error saat validasi voucher: {e}")
                print(traceback.format_exc())
                return JsonResponse({'status': 'error', 'message': f'Error saat validasi voucher: {str(e)}'}, status=400)

        # 6. Buat Objek Pembelian (Simpan HARGA FINAL dan KODE VOUCHER)
        try:
            # Pastikan total_harga_final adalah integer yang valid
            total_price_int = int(round(total_harga_final))
            if total_price_int < 0:
                return JsonResponse({'status': 'error', 'message': 'Total harga tidak boleh negatif.'}, status=400)
            if total_price_int > 2147483647:  # Batas maksimal PositiveIntegerField di beberapa database
                return JsonResponse({'status': 'error', 'message': 'Total harga terlalu besar.'}, status=400)
            
            pembelian = Pembelian.objects.create(
                user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                match=match,
                nama_lengkap_pembeli=nama_lengkap[:100],  # Pastikan tidak melebihi max_length
                email=email[:254],  # Pastikan tidak melebihi max_length
                nomor_telepon=nomor_telepon[:20],  # Pastikan tidak melebihi max_length
                total_price=total_price_int,
                kode_voucher=applied_code[:50] if applied_code else '',  # Pastikan tidak melebihi max_length
                status='PENDING'
            )
        except IntegrityError as e:
            print(f"IntegrityError saat membuat Pembelian: {e}")
            print(traceback.format_exc())
            # Jika ada duplicate order_id, coba lagi (meskipun seharusnya tidak terjadi dengan retry logic di model)
            return JsonResponse({'status': 'error', 'message': 'Error saat membuat pembelian. Silakan coba lagi.'}, status=500)
        except Exception as e:
            print(f"Error saat membuat Pembelian: {e}")
            print(traceback.format_exc())
            return JsonResponse({'status': 'error', 'message': f'Error saat membuat pembelian: {str(e)}'}, status=500)
        
        # 7. Asosiasikan Kursi dan Tandai is_booked=True
        try:
            if available_seats:
                pembelian.seats.set(available_seats)
                seat_ids_to_book = [seat.id for seat in available_seats]
                Seat.objects.filter(id__in=seat_ids_to_book).update(is_booked=True)
        except Exception as e:
            print(f"Error saat mengasosiasikan kursi: {e}")
            print(traceback.format_exc())
            # Jika gagal mengasosiasikan kursi, hapus pembelian yang sudah dibuat
            pembelian.delete()
            return JsonResponse({'status': 'error', 'message': f'Error saat mengasosiasikan kursi: {str(e)}'}, status=500)
        
        # 8. Kirim Response Sukses
        return JsonResponse({
            'status': 'success', 
            'message': 'Booking berhasil disimpan. Lanjut ke pembayaran.', 
            'order_id': pembelian.order_id,
            'total_harga': total_harga_final,
            'discount_amount': discount_amount
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Format data JSON tidak valid.'}, status=400)
    except IntegrityError as e: 
         # IntegrityError bisa terjadi jika ada unique constraint yang dilanggar
         print(f"IntegrityError saat menyimpan pembelian: {e}")
         print(traceback.format_exc())
         return JsonResponse({'status': 'error', 'message': 'Kesalahan integritas data. Coba lagi.'}, status=409)
    except Exception as e:
        # Menangkap error Python lainnya
        error_traceback = traceback.format_exc()
        print(f"Error saat menyimpan pembelian (auto-assign): {e}")
        print(error_traceback)
        # Return error message yang lebih informatif untuk debugging (dalam production, gunakan pesan generic)
        return JsonResponse({
            'status': 'error', 
            'message': f'Terjadi kesalahan di server: {str(e)}'
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
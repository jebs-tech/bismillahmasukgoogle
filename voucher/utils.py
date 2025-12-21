from datetime import datetime
from django.utils import timezone
from .models import Voucher
from django.contrib.auth.models import AnonymousUser

def validate_and_apply_voucher(code, user, total_amount):
    """
    Memeriksa validitas kode voucher dan menghitung nilai diskon yang baru.

    Mengembalikan (diskon_amount, pesan_error)
    """
    
    # 1. Cek Kode Voucher
    try:
        voucher = Voucher.objects.get(code__iexact=code) # Case-insensitive check
    except Voucher.DoesNotExist:
        return 0, "Kode voucher tidak ditemukan."
    
    # 2. Cek Status & Waktu
    if not voucher.is_active or voucher.valid_until < timezone.now() or voucher.valid_from > timezone.now():
        return 0, "Voucher tidak aktif atau sudah kadaluarsa."
    
    # 3. Cek Penggunaan Maksimal Global
    if voucher.max_use_count is not None and voucher.voucherusage_set.count() >= voucher.max_use_count:
        return 0, "Voucher telah mencapai batas maksimal penggunaan."
        
    # 4. Cek Pembelian Minimum
    if total_amount < voucher.min_purchase_amount:
        return 0, f"Pembelian minimum untuk voucher ini adalah Rp {voucher.min_purchase_amount:,}."

    # 5. Cek Penggunaan Per Pengguna (jika user login)
    if user.is_authenticated:
        if voucher.voucherusage_set.filter(user=user).exists():
             return 0, "Anda sudah pernah menggunakan voucher ini."
    
    # 6. Hitung Diskon
    if voucher.discount_type == 'FIXED':
        discount_amount = float(voucher.value)
        # Pastikan diskon tidak melebihi total harga
        discount_amount = min(discount_amount, total_amount) 
    
    elif voucher.discount_type == 'PERCENT':
        discount_amount = total_amount * (float(voucher.value) / 100)
    
    else:
        discount_amount = 0

    return round(discount_amount), None
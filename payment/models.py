# Di dalam payment/models.py

from django.db import models
from django.utils import timezone
from django.conf import settings # Import settings
import random
import string

# Import model yang kita butuhkan dari 'matches'
from matches.models import Match, Seat

# MODEL VENUE DIHAPUS DARI SINI

# Model Pembelian/Transaksi (menggantikan user.Purchase dan matches.Booking)
class Pembelian(models.Model):
    qr_code = models.ImageField(
        upload_to='qrcode/',
        null=True,
        blank=True
    )
    STATUS_CHOICES = (
        ('PENDING', 'Menunggu Pembayaran'),
        ('CONFIRMED', 'Terbayar'),
        ('CANCELLED', 'Dibatalkan'),
    )
    METODE_CHOICES = (
        ('BRI', 'BRI'),
        ('BCA', 'BCA'),
        ('Mandiri', 'Mandiri'),
        ('Gopay', 'Gopay'),
        ('QRIS', 'QRIS'),
    )

    # --- INFORMASI DARI matches.Booking ---
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pembelian_history')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='pembelian_set', null=True)
    seats = models.ManyToManyField(Seat, related_name='pembelian_set')
    total_price = models.PositiveIntegerField(default=0)
    
    # --- INFORMASI DARI payment.Pembelian ---
    order_id = models.CharField(max_length=10, unique=True, editable=False) 
    nama_lengkap_pembeli = models.CharField(max_length=100) # Bisa diambil dari user.profile
    email = models.EmailField() # Bisa diambil dari user.email
    nomor_telepon = models.CharField(max_length=20) # Bisa diambil dari user.profile
    metode_pembayaran = models.CharField(max_length=10, choices=METODE_CHOICES, null=True, blank=True)
    bukti_transfer = models.ImageField(upload_to='bukti_transfer/', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    kode_voucher = models.CharField(max_length=50, blank=True)
    tanggal_pembelian = models.DateTimeField(default=timezone.now)
        


    def save(self, *args, **kwargs):
        if not self.order_id:
            max_attempts = 100
            attempts = 0
            while attempts < max_attempts:
                random_digits = ''.join(random.choices(string.digits, k=6))
                new_order_id = f"AII{random_digits}"
                if not Pembelian.objects.filter(order_id=new_order_id).exists():
                    self.order_id = new_order_id
                    break
                attempts += 1
            else:
                # Fallback: gunakan timestamp jika semua kombinasi sudah digunakan
                import time
                timestamp = str(int(time.time()))[-6:]
                self.order_id = f"AII{timestamp}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pembelian {self.order_id} - {self.status}"

from django.db import models
from django.utils import timezone
import random
import string
from matches.models import Match # IMPOR MODEL DARI APLIKASI PRIYZ

# =======================================================
# HAPUS CLASS Venue DI SINI (KARENA SUDAH ADA DI matches/models.py)
# =======================================================

# Model Pembelian/Transaksi
class Pembelian(models.Model):
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

    order_id = models.CharField(max_length=10, unique=True, editable=False) 
    
    # RELASI KE PERTANDINGAN (Match)
    match = models.ForeignKey(Match, on_delete=models.PROTECT, null=True, blank=True) # Perubahan utama
    
    # Data Pembeli (Kontak)
    nama_lengkap_pembeli = models.CharField(max_length=100)
    email = models.EmailField()
    nomor_telepon = models.CharField(max_length=20)
    
    # Data Transaksi
    total_harga = models.BigIntegerField(default=0)
    metode_pembayaran = models.CharField(max_length=10, choices=METODE_CHOICES, null=True, blank=True)
    bukti_transfer = models.ImageField(upload_to='bukti_transfer/', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    kode_voucher = models.CharField(max_length=50, blank=True)
    
    tanggal_pembelian = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.order_id:
            while True:
                random_digits = ''.join(random.choices(string.digits, k=6))
                new_order_id = f"AII{random_digits}"
                if not Pembelian.objects.filter(order_id=new_order_id).exists():
                    self.order_id = new_order_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pembelian {self.order_id} - {self.status}"


# Model Tiket
class Tiket(models.Model):
    GENDER_CHOICES = (
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    )
    
    # Kategori Choices, disarankan menggunakan list dari SeatCategory yang sebenarnya
    KATEGORI_CHOICES = (
        ('SUPORTER', 'Suporter'),
        ('BRONZE', 'Bronze'),
        ('SILVER', 'Silver'),
        ('GOLD', 'Gold'),
    )

    pembelian = models.ForeignKey(Pembelian, on_delete=models.CASCADE, related_name='tikets')
    nama_pemegang = models.CharField(max_length=100)
    jenis_kelamin = models.CharField(max_length=1, choices=GENDER_CHOICES)
    kategori_kursi = models.CharField(max_length=10, choices=KATEGORI_CHOICES)
    
    # Data E-Ticket
    qr_code_data = models.CharField(max_length=255, unique=True, editable=False)
    file_qr_code = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    
    def __str__(self):
        return f"Tiket {self.id} - {self.nama_pemegang} ({self.kategori_kursi})"
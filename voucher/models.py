from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import random
import string

User = get_user_model()

# --- Fungsi Helper untuk Kode Voucher ---
def generate_voucher_code():
    """Membuat kode voucher acak 8 karakter."""
    characters = string.ascii_uppercase + string.digits
    # Menghindari karakter yang mudah tertukar seperti I, L, O, 0, 1
    # characters = characters.translate(str.maketrans('', '', 'ILO01'))
    return ''.join(random.choices(characters, k=8))
# ----------------------------------------


class Voucher(models.Model):
    DISCOUNT_TYPES = (
        ('PERCENT', 'Persentase (%)'),
        ('FIXED', 'Nilai Tetap (Rp)'),
    )

    code = models.CharField(
        max_length=20, # Dikurangi panjangnya (maks 20 karakter)
        unique=True, 
        default=generate_voucher_code, # Menggunakan fungsi random string
        verbose_name="Kode Voucher"
    )
    
    discount_type = models.CharField(
        max_length=7, 
        choices=DISCOUNT_TYPES, 
        default='FIXED',
        verbose_name="Tipe Diskon"
    )
    
    value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        verbose_name="Nilai Diskon"
    )
    
    min_purchase_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Pembelian Minimum"
    )
    max_use_count = models.PositiveIntegerField(
        default=1, 
        verbose_name="Maksimal Penggunaan"
    )
    
    valid_from = models.DateTimeField(verbose_name="Berlaku Dari")
    valid_until = models.DateTimeField(verbose_name="Berlaku Sampai")
    is_active = models.BooleanField(default=True)
    
    used_by = models.ManyToManyField(
        User, 
        blank=True, 
        through='VoucherUsage',
        verbose_name="Digunakan Oleh"
    )
    
    class Meta:
        verbose_name = "Voucher"
        verbose_name_plural = "Voucher"
        
    def __str__(self):
        return f"{self.code} ({self.discount_type}: {self.value})"

class VoucherUsage(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('voucher', 'user')
        verbose_name = "Pelacakan Penggunaan Voucher"
        verbose_name_plural = "Pelacakan Penggunaan Voucher"
        
    def __str__(self):
        return f"{self.user.username} used {self.voucher.code}"
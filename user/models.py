# Di dalam file models.py aplikasi Anda

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

# Model dasar yang diperlukan (bisa disederhanakan dulu)
class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Event(models.Model):
    name = models.CharField(max_length=255)
    event_date = models.DateTimeField()

    team_a = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='home_events')
    team_b = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='away_events')
    location = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self): return self.name

# --- Model Inti untuk Akun Pengguna ---

# Model Profile untuk menyimpan 'Preferensi Tim'
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    preferred_teams = models.ManyToManyField(Team, blank=True, related_name='fans')
    
    # --- TAMBAHKAN DUA FIELD INI ---
    nama_lengkap = models.CharField(max_length=255, null=True, blank=True)
    nomor_telepon = models.CharField(max_length=20, null=True, blank=True)
    # --------------------------------

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signal untuk membuat Profile secara otomatis saat User baru dibuat
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


# Model Purchase untuk 'Riwayat Pembelian'
class Purchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='purchase_history')
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['-created_at'] # Urutkan riwayat dari yang terbaru

    def __str__(self):
        return f"Purchase {self.id} by {self.user.username}"

# Model Ticket untuk 'Tiket Aktif'
class Ticket(models.Model):
    STATUS_CHOICES = (
        ('active', 'Aktif'),
        ('used', 'Sudah Dipakai'),
        ('expired', 'Kadaluwarsa'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    # Terhubung ke riwayat pembelian
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='tickets')
    # Fitur: Tiket Aktif
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"Ticket for {self.event.name} (User: {self.user.username})"
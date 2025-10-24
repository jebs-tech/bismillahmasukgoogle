# Di dalam user/models.py

from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

# Import Team dari aplikasi 'matches' (atau 'payment' jika Anda pindahkan ke sana)
# Kita asumsikan 'matches' akan memiliki model Team, 
# atau kita bisa hapus 'preferred_teams' untuk sementara jika 'Team' tidak ada lagi.

# Mari kita ASUMSIKAN model 'Team' akan ada di 'matches'
from matches.models import Team 

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    
    # preferred_teams kita arahkan ke model Team yang baru di 'matches'
    preferred_teams = models.ManyToManyField(Team, blank=True, related_name='fans')
    
    nama_lengkap = models.CharField(max_length=255, null=True, blank=True)
    nomor_telepon = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signal untuk membuat Profile secara otomatis saat User baru dibuat
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    # Cek jika profil sudah ada
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # Buat profil jika belum ada (safety check)
        Profile.objects.create(user=instance)

# MODEL Team, Event, Purchase, dan Ticket LAMA DIHAPUS DARI FILE INI
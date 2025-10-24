# Di dalam matches/models.py

from django.db import models
from django.utils import timezone

# Model Team (dipindahkan dari user.models)
class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='team_logos/', null=True, blank=True)
    def __str__(self): return self.name

# Model Venue (INI ADALAH SATU-SATUNYA MODEL VENUE YANG KITA PAKAI)
class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    def __str__(self): return self.name

# Model Match (menggantikan user.Event)
class Match(models.Model):
    title = models.CharField(max_length=255)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    start_time = models.DateTimeField()

    team_a = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='home_matches')
    team_b = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='away_matches')

    description = models.TextField(blank=True)

    price_from = models.PositiveIntegerField(default=0)

    def __str__(self): return f"{self.title} — {self.start_time.date()}"

# Model Kategori Kursi (sudah benar)
class SeatCategory(models.Model):
    name = models.CharField(max_length=50)
    price = models.PositiveIntegerField()
    color = models.CharField(max_length=7, default="#d3a15a")
    def __str__(self): return f"{self.name} (Rp{self.price})"

class Seat(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='seats')
    row = models.CharField(max_length=4)
    col = models.PositiveIntegerField()
    category = models.ForeignKey(SeatCategory, on_delete=models.PROTECT)
    is_booked = models.BooleanField(default=False)

    # --- TAMBAHKAN DUA FIELD INI ---
    qr_code_data = models.CharField(max_length=255, unique=True, editable=False, null=True, blank=True)
    file_qr_code = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    # ---------------------------------

    class Meta: 
        unique_together = (('match', 'row', 'col'),)

    def __str__(self): return f"{self.match.title} - {self.row}{self.col}"

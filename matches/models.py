# Di dalam matches/models.py

from django.db import models
from django.utils import timezone
from django.utils.text import slugify

# Model Team (dipindahkan dari user.models)
class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='team_logos/', null=True, blank=True)
    def __str__(self): return self.name

# Model Venue (INI ADALAH SATU-SATUNYA MODEL VENUE YANG KITA PAKAI)
class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


# Model Match (menggantikan user.Event)
class Match(models.Model):
    
    title = models.CharField(max_length=255, blank=True)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    start_time = models.DateTimeField()

    team_a = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='home_matches')
    team_b = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='away_matches')

    description = models.TextField(blank=True)

    price_from = models.PositiveIntegerField(default=75000, editable=True)

    def __str__(self):
        if self.title:
            try:
                return f"{self.title} — {self.start_time.date()}"
            except Exception:
                return self.title
        return f"Match — {self.start_time.date()}"

    def get_auto_title(self):
        if self.team_a and self.team_b:
            left = self.team_a.name
            right = self.team_b.name
            return f"{left} vs {right}"
        return None

    def save(self, *args, **kwargs):
        auto = self.get_auto_title()
        # If title empty and we can form auto title -> set it.
        if not self.title and auto:
            self.title = auto
        else:
            # If auto available and current title contains " vs " (likely auto), update to keep in-sync.
            if auto and isinstance(self.title, str) and ' vs ' in self.title:
                self.title = auto
        super().save(*args, **kwargs)

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
    
class MatchSeatCapacity(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    category = models.ForeignKey(SeatCategory, on_delete=models.CASCADE)
    capacity = models.IntegerField(default=0)

    class Meta:
        unique_together = ('match', 'category')
        verbose_name = "Kapasitas Kursi Kategori"
        verbose_name_plural = "Kapasitas Kursi Kategori"
    
    def __str__(self): return f"{self.match.title} - {self.category.name}: {self.capacity}"

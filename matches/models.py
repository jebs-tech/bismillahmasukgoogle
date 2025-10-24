from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Team(models.Model):
    """
    Representasi tim/club.
    - name: full name (eg. Persija Jakarta)
    - short_name: optional short name (eg. Persija)
    - slug: url-safe
    - logo: optional ImageField (requires Pillow + MEDIA settings)
    - color: optional hex color used for UI (eg. #ff0000)
    """
    name = models.CharField(max_length=200, unique=True)
    short_name = models.CharField(max_length=50, blank=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    logo = models.ImageField(upload_to='team_logos/', blank=True, null=True)
    color = models.CharField(max_length=7, blank=True, default='')

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:200]
        if not self.short_name:
            self.short_name = ' '.join(self.name.split()[:2])
        super().save(*args, **kwargs)

    def __str__(self):
        return self.short_name or self.name


class Match(models.Model):
    """
    Match with optional relations to Team.
    When both home_team and away_team exist, the title will be set automatically
    to "{home_team.short_name or name} vs {away_team.short_name or name}" if title is empty
    or if title appears to be an auto-generated title (contains ' vs ').
    """
    title = models.CharField(max_length=255, blank=True)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    short_time = models.CharField(max_length=100, blank=True)
    price_from = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    home_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='away_matches')

    def __str__(self):
        if self.title:
            try:
                return f"{self.title} — {self.start_time.date()}"
            except Exception:
                return self.title
        return f"Match — {self.start_time.date()}"

    def get_auto_title(self):
        if self.home_team and self.away_team:
            left = self.home_team.short_name or self.home_team.name
            right = self.away_team.short_name or self.away_team.name
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
    class Meta:
        unique_together = (('match', 'row', 'col'),)
    def __str__(self): return f"{self.match.title} - {self.row}{self.col}"


class Booking(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    seats = models.ManyToManyField(Seat, blank=True)
    buyer_name = models.CharField(max_length=200)
    buyer_email = models.EmailField(blank=True)
    total_price = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    paid = models.BooleanField(default=False)

    # persist passenger details (list of objects)
    passengers = models.JSONField(blank=True, null=True, help_text='List of passenger objects: [{name,email,phone,gender,category}, ...]')

    def __str__(self): return f"Booking #{self.id} - {self.match.title}"

from django.db import models
from django.utils import timezone

class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    def __str__(self): return self.name

class Match(models.Model):
    title = models.CharField(max_length=255)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    short_time = models.CharField(max_length=100, blank=True)
    price_from = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    def __str__(self): return f"{self.title} — {self.start_time.date()}"

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
    class Meta: unique_together = (('match', 'row', 'col'),)
    def __str__(self): return f"{self.match.title} - {self.row}{self.col}"

class Booking(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    seats = models.ManyToManyField(Seat)
    buyer_name = models.CharField(max_length=200)
    buyer_email = models.EmailField()
    total_price = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    paid = models.BooleanField(default=False)
    def __str__(self): return f"Booking #{self.id} - {self.match.title}"
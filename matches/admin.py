from django.contrib import admin
from .models import Venue, Team, Match, SeatCategory, Seat, Booking

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id','title', 'home_team', 'away_team', 'start_time', 'price_from')
    list_filter = ('start_time',)
    search_fields = ('title', 'home_team__name', 'away_team__name')
    raw_id_fields = ('home_team', 'away_team')

@admin.register(SeatCategory)
class SeatCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('match','row','col','category','is_booked')
    list_filter = ('match','category','is_booked')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id','match','buyer_name','total_price','paid','created_at')
    readonly_fields = ('passengers',)
    fieldsets = (
        (None, {'fields': ('match','seats','buyer_name','buyer_email','total_price','paid')}),
        ('Passengers (JSON)', {'fields': ('passengers',)}),
    )

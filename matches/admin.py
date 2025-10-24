from django.contrib import admin
# Pastikan Team diimpor
from .models import Venue, Match, SeatCategory, Seat, Team 

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'capacity') # Tambah capacity

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('title', 'venue', 'start_time', 'price_from', 'team_a', 'team_b') 

    list_filter = ('venue',)


@admin.register(SeatCategory)
class SeatCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'color')

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('match', 'row', 'col', 'category', 'is_booked')
    list_filter = ('match', 'category', 'is_booked')

# --- TAMBAHKAN INI ---
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo')
# ----------------------
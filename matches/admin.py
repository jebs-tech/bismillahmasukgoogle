from django.contrib import admin
# Hapus Booking dari import
from .models import Venue, Team, Match, SeatCategory, Seat, MatchSeatCapacity

# Daftarkan model satu per satu
@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name','address')
    search_fields = ('name',)

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo')
    search_fields = ('name',)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('title', 'venue', 'start_time', 'price_from', 'team_a', 'team_b')
    readonly_fields = ('price_from',)

    fieldsets = (
        (None, {'fields': ('title', 'venue', 'start_time', 'price_from', 'description')}),
        ('Teams', {'fields': ('team_a', 'team_b')}),
    )


@admin.register(SeatCategory)
class SeatCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'color')
    search_fields = ('name',)

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('match', 'row', 'col', 'category', 'is_booked')
    list_filter = ('match', 'category', 'is_booked')
    search_fields = ('match__title', 'row')

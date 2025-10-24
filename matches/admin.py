from django.contrib import admin
from .models import Venue, Match, SeatCategory, Seat, Booking

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name','address')

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('title','venue','start_time','price_from')
    list_filter = ('venue',)

@admin.register(SeatCategory)
class SeatCategoryAdmin(admin.ModelAdmin):
    list_display = ('name','price','color')

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('match','row','col','category','is_booked')
    list_filter = ('match','category','is_booked')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id','match','buyer_name','total_price','paid','created_at')
    list_filter = ('paid','match')
    date_hierarchy = 'created_at'

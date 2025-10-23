from django.contrib import admin
from .models import Team, Venue, Match

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'address']

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['home_team', 'away_team', 'start_time', 'venue']
    list_filter = ['start_time', 'venue']
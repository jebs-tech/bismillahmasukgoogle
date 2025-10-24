from django import forms
from .models import Match

class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['home_team', 'away_team', 'start_time', 'venue']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
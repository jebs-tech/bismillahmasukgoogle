from django import forms
from .models import Match

class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['title', 'venue', 'start_time', 'team_a', 'team_b', 'description', 'price_from']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'title': 'Judul Pertandingan',
            'venue': 'Tempat',
            'start_time': 'Waktu Mulai',
            'team_a': 'Tim A (Tuan Rumah)',
            'team_b': 'Tim B (Tamu)',
            'description': 'Deskripsi',
            'price_from': 'Harga Mulai',
        }

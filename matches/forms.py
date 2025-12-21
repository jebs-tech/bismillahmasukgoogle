from django import forms
from .models import Match

class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = [
            'title', 
            'venue', 
            'start_time', 
            'description', 
            'team_a', 
            'team_b'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            # Anda mungkin perlu mengatur widget untuk datetime-local di sini
            # 'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }

    # --- TAMBAHKAN FUNGSI __init__ INI ---
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
            
        # Tambahkan class CSS Tailwind ke semua field untuk styling konsisten
        for name, field in self.fields.items():
             if name != 'description': # Kecualikan textarea agar tidak bentrok
                field.widget.attrs.update({'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-orange focus:border-brand-orange transition duration-150'})
    # ----------------------------------------
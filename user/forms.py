from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

class ServetixUserCreationForm(UserCreationForm):
    # 1. Tambahkan field baru di sini
    email = forms.EmailField(required=True, help_text="Email akan digunakan sebagai username Anda.")
    nama_lengkap = forms.CharField(max_length=255, required=True)
    nomor_telepon = forms.CharField(max_length=20, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        # Ganti fields bawaan untuk menyertakan email
        fields = ('email', 'nama_lengkap', 'nomor_telepon')

    def save(self, commit=True):
        # 2. Override metode save()
        user = super().save(commit=False)
        
        # 3. Set username = email
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # 4. Buat atau update Profile saat user disimpan
            # Signal kita di models.py akan otomatis membuat Profile.
            # Kita tinggal update field-nya di sini.
            profile = user.profile 
            profile.nama_lengkap = self.cleaned_data['nama_lengkap']
            profile.nomor_telepon = self.cleaned_data['nomor_telepon']
            profile.save()
            
        return user
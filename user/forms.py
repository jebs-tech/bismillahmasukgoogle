from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, Team
from django.contrib.auth import get_user_model

User = get_user_model()

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
    
class ProfileEditForm(forms.ModelForm):
    email = forms.EmailField(
        label="Alamat Email",
        widget=forms.EmailInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-dark-blue'})
    )

    class Meta:
        model = Profile
        fields = ('nama_lengkap', 'nomor_telepon', 'preferred_teams')
        widgets = {
            'preferred_teams': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Isi field email dengan data dari model User
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
        
        # Atur label
        self.fields['nama_lengkap'].label = "Nama Lengkap"
        self.fields['nomor_telepon'].label = "Nomor Telepon"
        self.fields['preferred_teams'].label = "Tim Favorit Saya"
        
        # Pastikan queryset diisi jika Anda ingin menampilkan semua tim
        self.fields['preferred_teams'].queryset = Team.objects.all()

        # Terapkan kelas Tailwind
        base_class = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-dark-blue'
        self.fields['nama_lengkap'].widget.attrs.update({'class': base_class})
        self.fields['nomor_telepon'].widget.attrs.update({
            'class': base_class, 
            'placeholder': 'Contoh: 08123456789'
        })

    def save(self, commit=True):
        # Simpan instance Profile
        profile = super().save(commit=False)
        
        # Simpan email kembali ke model User
        user = profile.user
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            profile.save()
            self.save_m2m()  # Penting untuk menyimpan ManyToMany (preferred_teams)
            
        return profile
# user/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

# 1. Definisikan Profile Inline untuk User
class ProfileInline(admin.StackedInline):
    """
    Menampilkan form Profile di dalam halaman edit User.
    """
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil Pengguna'
    fk_name = 'user'
    
    # Kustomisasi field yang tampil di inline
    fields = ('nama_lengkap', 'nomor_telepon', 'preferred_teams')
    filter_horizontal = ('preferred_teams',) # Agar ManyToManyField lebih mudah digunakan

# 2. Kustomisasi UserAdmin untuk menyertakan ProfileInline
class CustomUserAdmin(BaseUserAdmin):
    """
    Menggabungkan ProfileInline ke dalam UserAdmin bawaan Django.
    """
    inlines = (ProfileInline,)
    
    # Menambahkan nama_lengkap dari Profile ke list_display User
    list_display = ('username', 'email', 'get_nama_lengkap', 'is_staff')
    
    @admin.display(description='Nama Lengkap')
    def get_nama_lengkap(self, obj):
        # Mengambil nama lengkap dari profil terkait
        if hasattr(obj, 'profile'):
            return obj.profile.nama_lengkap
        return '-'

# 3. Kustomisasi ProfileAdmin (Opsional, tapi direkomendasikan)
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Admin view terpisah untuk Model Profile.
    """
    list_display = ('user', 'nama_lengkap', 'nomor_telepon')
    search_fields = ('user__username', 'nama_lengkap', 'nomor_telepon')
    filter_horizontal = ('preferred_teams',)

# 4. Unregister User bawaan dan Register ulang dengan yang kustom
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
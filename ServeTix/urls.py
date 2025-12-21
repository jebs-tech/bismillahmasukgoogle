from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ServeTix/urls.py

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Endpoints untuk Flutter
    # Pastikan ini mengarah ke file api_urls.py yang kita bahas sebelumnya
    path('api/', include('matches.api_urls')), 
    
    # Fitur Aplikasi
    path('forums/', include('forums.urls')), 
    path('payment/', include('payment.urls', namespace='payment')),
    path('notifications/', include('notifications.urls')),
    
    # Perbaikan Warning urls.W005: Namespace 'voucher' harus unik.
    # Pilih salah satu jalur saja untuk menyertakan voucher.urls.
    # Jika Anda butuh 'voucher/' untuk API, gunakan itu saja.
    path('voucher/', include('voucher.urls', namespace='voucher')),
    
    # Jalur Root (Diletakkan di bawah agar tidak menangkap jalur spesifik di atas)
    path('', include('user.urls')),
    path('', include('matches.urls')),
    path('', include('homepage.urls')),
]

# Menangani Media dan Static Files saat Debug
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
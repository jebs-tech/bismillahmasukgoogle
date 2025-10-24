from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.views.generic import RedirectView 
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. PLACEHOLDER UNTUK NAMESPACE 'account' (Untuk link Masuk/Logout di base.html)
    path('accounts/', include(([
        # Menggunakan RedirectView sebagai placeholder agar link {% url 'account:login' %} tidak error
        path('login/', RedirectView.as_view(url='/login-soon/'), name='login'),
        path('profile/', RedirectView.as_view(url='/profile-soon/'), name='profile'),
        path('logout/', RedirectView.as_view(url='/logout-soon/'), name='logout'),
    ], 'user'), namespace='account')), 
    
    # 2. URL Priyz (Aplikasi matches)
    path('matches/', include('matches.urls', namespace='matches')), 
    
    # 3. URL Anda (Aplikasi payment)
    path('payment/', include('payment.urls', namespace='payment')),

    # 4. URL Root (Redirect ke Detail Pembeli Anda)
    path('', RedirectView.as_view(url=reverse_lazy('payment:detail_pembeli')), name='root_redirect'),
]

# Path media untuk development (Wajib agar gambar QR Code muncul)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
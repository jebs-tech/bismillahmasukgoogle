from django.contrib import admin
from django.urls import path, include, reverse_lazy # Import reverse_lazy
from django.views.generic import RedirectView # Import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

# Di ServeTix/urls.py

# Di ServeTix/urls.py

urlpatterns = [
    path('admin/', admin.site.urls),
    path('forums/', include('forums.urls')), 
    path('', include('user.urls')),
    path('', include('matches.urls')),
    path('', include('homepage.urls')),
    path('payment/', include('payment.urls', namespace='payment')),
    path('notifications/', include('notifications.urls')),
    path('vouchers/', include('voucher.urls', namespace='voucher')),
    path('api/payment/', include('payment.api_urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


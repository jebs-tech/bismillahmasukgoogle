"""
URL configuration for ServeTix project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
<<<<<<< HEAD
from django.urls import path, include, reverse_lazy # Import reverse_lazy
from django.views.generic import RedirectView # Import RedirectView
from django.conf import settings
from django.conf.urls.static import static
=======
from django.urls import path, include
>>>>>>> 9907a36664ce69e8cb1bf4ab56a24ded99668587

urlpatterns = [
path('accounts/', include(([
        # Login dan Logout harus memiliki nama 'login' dan 'logout'
        path('login/', RedirectView.as_view(url='/login-soon/'), name='login'),
        path('profile/', RedirectView.as_view(url='/profile-soon/'), name='profile'),
        path('logout/', RedirectView.as_view(url='/logout-soon/'), name='logout'),
    ], 'user'), namespace='account')), # Menggunakan namespace 'account'
    path('', RedirectView.as_view(url=reverse_lazy('payment:detail_pembeli')), name='root_redirect'),
    path('admin/', admin.site.urls),
<<<<<<< HEAD
    path('payment/', include('payment.urls', namespace='payment')),
=======
    path('', include('matches.urls')),
>>>>>>> 9907a36664ce69e8cb1bf4ab56a24ded99668587
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
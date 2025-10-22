from django.urls import path
from . import views

# Ini penting untuk reverse() seperti 'user:login'
app_name = 'user' 

urlpatterns = [
    # URL untuk Register, Login, Logout
    path('register/', views.register, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # URL untuk Profil Pengguna
    path('profile/', views.user_profile_view, name='profile'),
    
    # (Opsional) Buat halaman utama jika perlu
    # path('', views.home_page, name='home'), 
]
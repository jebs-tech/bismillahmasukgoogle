from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

# Ini penting untuk reverse() seperti 'user:login'
app_name = 'user' 

urlpatterns = [
    # URL untuk Register, Login, Logout
    path('register/', views.register, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # URL untuk Profil Pengguna
    path('profile/', views.user_profile_view, name='profile'),
    
    path('password_reset/', 
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html'
        ), 
        name='password_reset'),
    
    # Halaman "Email Terkirim" (konfirmasi)
    path('password_reset/done/', 
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ), 
        name='password_reset_done'),
    
    # Halaman "Reset Password" (klik link dari email, masukkan password baru)
    path('reset/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html'
        ), 
        name='password_reset_confirm'),
    
    # Halaman "Reset Selesai" (konfirmasi password berhasil diubah)
    path('reset/done/', 
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ), 
        name='password_reset_complete'),
    
    # (Opsional) Buat halaman utama jika perlu
    # path('', views.home_page, name='home'), 
]
from django.urls import path, reverse_lazy
from . import views
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

# Ini penting untuk reverse() seperti 'user:login'
app_name = 'user' 

urlpatterns = [
    # URL untuk Register, Login, Logout
    path('register/', views.register, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    
    # URL Dashboard
    path('profile/', views.user_profile_view, name='profile'),

    # URL Parsial HTMX
    path('profile/get-tickets/', views.get_active_tickets, name='get_active_tickets'),
    path('profile/get-tickets-modal/', views.get_active_tickets_modal, name='get_active_tickets_modal'),
    path('profile/get-history/', views.get_purchase_history, name='get_purchase_history'),
    path('profile/get-teams/', views.get_preferred_teams, name='get_preferred_teams'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # URL Detail (ID sekarang merujuk ke Match dan Seat)
    path('profile/purchase-detail/<int:event_id>/', views.purchase_detail, name='purchase_detail'),
    path('profile/ticket-detail/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),

    # URL Hapus Akun
    path('profile/get-delete-form/', views.get_delete_form, name='get_delete_form'),
    path('profile/delete-confirm/', views.delete_account_confirm, name='delete_account_confirm'),
    
    path('password_reset/', 
    auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        html_email_template_name='registration/password_reset_email.html', 
        email_template_name='registration/password_reset_email.txt',
        subject_template_name='registration/password_reset_subject.txt',
        success_url=reverse_lazy('user:password_reset_done')
    ), 
    name='password_reset'),
        
        path('password_reset/done/', 
            auth_views.PasswordResetDoneView.as_view(
                # TAMBAHKAN JUGA DI SINI
                template_name='registration/password_reset_done.html'
            ), 
            name='password_reset_done'),
        
        path('reset/<uidb64>/<token>/', 
            auth_views.PasswordResetConfirmView.as_view(
                # DAN DI SINI
                template_name='registration/password_reset_confirm.html',
                success_url=reverse_lazy('user:password_reset_complete')
            ), 
            name='password_reset_confirm'),
        
        path('reset/done/', 
            auth_views.PasswordResetCompleteView.as_view(
                template_name='registration/password_reset_complete.html'
            ), 
            name='password_reset_complete'),
    ]
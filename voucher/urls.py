from django.urls import path
from . import views


app_name = 'voucher'

urlpatterns = [
    # READ: Tampilan Daftar Voucher (Dashboard)
    path('', views.voucher_dashboard, name='dashboard'),

    # CREATE: Halaman Tambah Voucher Baru
    path('new/', views.voucher_create_update, name='create'),

    # UPDATE: Halaman Edit Voucher
    path('edit/<int:pk>/', views.voucher_create_update, name='update'),

    # DELETE: Halaman Konfirmasi Hapus
    path('delete/<int:pk>/', views.voucher_delete, name='delete'),

    # API untuk Flutter
    path('api/list/', views.api_voucher_list, name='api_list'),
    path('api/redeem/', views.api_redeem_voucher, name='api_redeem'),
]


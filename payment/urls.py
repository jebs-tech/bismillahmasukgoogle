from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    # 1. Halaman Detail Pembeli (GET)
    path('beli-tiket/', views.detail_pembeli_view, name='detail_pembeli'),
    
    # 2. Endpoint AJAX untuk menyimpan data pembeli (POST)
    path('api/simpan-pembelian/', views.simpan_pembelian_ajax, name='simpan_pembelian_ajax'),
    
    # 3. Halaman Detail Pembayaran (GET dengan Order ID)
    path('pembayaran/<str:order_id>/', views.detail_pembayaran_view, name='detail_pembayaran'),
    
    # 4. Endpoint AJAX untuk proses pembayaran, upload bukti, dan konfirmasi
    path('api/proses-bayar/<str:order_id>/', views.proses_bayar_ajax, name='proses_bayar_ajax'),
    path('api/check-voucher/', views.check_voucher_ajax, name='check_voucher_ajax'),
]
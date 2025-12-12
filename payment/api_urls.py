from django.urls import path
from .api_views import CreatePembelianAPI, KonfirmasiPembayaranAPI, DetailETicketAPI

urlpatterns = [
    path('create/', CreatePembelianAPI.as_view()),
    path('pay/<str:order_id>/', KonfirmasiPembayaranAPI.as_view()),
    path('<str:order_id>/', DetailETicketAPI.as_view()),
]

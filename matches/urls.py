from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('', views.index, name='index'),  # <-- homepage: daftar pertandingan
    path('matches/<int:pk>/', views.match_detail, name='match_detail'),
    path('api/matches/<int:pk>/seats/', views.match_seats_api, name='match_seats_api'),
    path('api/book/', views.api_book, name='api_book'),
]
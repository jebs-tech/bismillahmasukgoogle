from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('matches/<int:pk>/', views.match_detail, name='match_detail'),
    path('matches/create/', views.match_create, name='match_create'),
    path('matches/<int:pk>/edit/', views.match_edit, name='match_edit'),
    path('matches/<int:pk>/delete/', views.match_delete, name='match_delete'),
    path('api/matches/<int:pk>/seats/', views.match_seats_api, name='match_seats_api'),
    path('api/book/', views.api_book, name='api_book'),
    path('matches/', views.match_list, name='match_list')
]
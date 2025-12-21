from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('matches/<int:pk>/', views.match_detail, name='match_detail'),
    path('matches/create/', views.match_create, name='match_create'),
    path('matches/<int:pk>/edit/', views.match_edit, name='match_edit'),
    path('matches/<int:pk>/delete/', views.match_delete, name='match_delete'),
    path('matches/', views.match_list, name='match_list'),
    path('json/', views.show_json, name='show_json'),
    path('api/matches/', views.api_match_list, name='api_match_list'),
    path('api/matches/<int:id>/delete/', views.api_match_delete, name='api_match_delete'),
]

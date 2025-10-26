from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('matches/<int:pk>/', views.match_detail, name='match_detail'),
    path('matches/create/', views.match_create_update, name='match_create'),
    path('matches/<int:pk>/edit/', views.match_create_update, name='match_edit'),
    path('matches/<int:pk>/delete/', views.match_delete, name='match_delete'),
    path('matches/', views.match_list, name='match_list'),

]

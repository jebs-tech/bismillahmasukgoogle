from django.urls import path
from . import views

urlpatterns = [
    path('', views.match_list, name='match_list'),
    path('matches/create/', views.match_create, name='match_create'),
    path('matches/<int:pk>/edit/', views.match_edit, name='match_edit'),
    path('matches/<int:pk>/delete/', views.match_delete, name='match_delete'),
]
from django.urls import path
from . import views

urlpatterns = [
    path('', views.match_list, name='match_list'),
    path('matches/create/', views.match_create, name='match_create'),
]
from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/', views.match_detail, name='match_detail'),
    path('api/<int:pk>/seats/', views.match_seats_api, name='match_seats_api'),
    path('api/book/', views.api_book, name='api_book'),
    path('api/book_quantity/', views.api_book_quantity, name='api_book_quantity'),
    path('<int:match_id>/checkout/', views.checkout, name='checkout'),
]

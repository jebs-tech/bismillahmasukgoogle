from django.urls import path
from .api_views import (
    MatchDetailAPI,
    MatchSeatsAPI,
    BookWithSeatsAPI,
    BookByQuantityAPI
)

urlpatterns = [
    path('<int:pk>/', MatchDetailAPI.as_view(), name='match_detail_api'),
    path('<int:match_id>/seats/', MatchSeatsAPI.as_view()),
    path('book/', BookWithSeatsAPI.as_view()),
    path('book-quantity/', BookByQuantityAPI.as_view()),
]

from django.shortcuts import render

from django.shortcuts import render, redirect
from .models import Review, Field

def review_list(request):
    reviews = Review.objects.all()
    return render(request, 'reviews/review_list.html', {'reviews': reviews})

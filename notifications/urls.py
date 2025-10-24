# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('notification/', views.notification_list, name='notification_list'),
    path('api/unread_count/', views.unread_count_api, name='notification_unread_count'),
    path('api/mark_all_read/', views.mark_all_read_api, name='notification_mark_all_read'),
]

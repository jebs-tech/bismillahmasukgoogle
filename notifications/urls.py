# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('notification/', views.notification_list, name='notification_list'),
    path('api/unread_count/', views.unread_count_api, name='notification_unread_count'),
    path('api/mark_all_read/', views.mark_all_read_api, name='notification_mark_all_read'),
    
    # ==== REST API ENDPOINTS FOR FLUTTER ====
    path('api/notifications/', views.api_notification_list, name='api_notification_list'),
    path('api/notifications/unread_count/', views.api_notification_unread_count, name='api_notification_unread_count'),
    path('api/notifications/<int:notification_id>/mark_read/', views.api_notification_mark_read, name='api_notification_mark_read'),
    path('api/notifications/mark_all_read/', views.api_notification_mark_all_read, name='api_notification_mark_all_read'),
]

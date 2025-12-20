from django.urls import path
from . import views

app_name = 'forums'

urlpatterns = [
    path('', views.thread_list, name='thread_list'),

    # ==== THREAD AJAX CRUD ====
    path('ajax/create/', views.create_thread_ajax, name='create_thread_ajax'),
    path('ajax/<int:thread_id>/edit/', views.edit_thread_ajax, name='edit_thread_ajax'),
    path('ajax/<int:thread_id>/delete/', views.delete_thread_ajax, name='delete_thread_ajax'),

    # ==== REPLIES AJAX ====
    path('ajax/<int:thread_id>/reply/', views.reply_ajax, name='reply_ajax'),
    path('ajax/reply/<int:reply_id>/edit/', views.edit_reply_ajax, name='edit_reply_ajax'),
    path('ajax/reply/<int:reply_id>/delete/', views.delete_reply_ajax, name='delete_reply_ajax'),
    path('ajax/<int:thread_id>/vote/', views.vote_thread_ajax, name='vote_thread_ajax'),
    path('ajax/reply/<int:reply_id>/vote/', views.vote_reply_ajax, name='vote_reply_ajax'),

    # ==== REST API ENDPOINTS FOR FLUTTER ====
    path('api/threads/', views.api_thread_list, name='api_thread_list'),
    path('api/threads/<int:thread_id>/', views.api_thread_detail, name='api_thread_detail'),
    path('api/threads/<int:thread_id>/reply/', views.api_thread_reply, name='api_thread_reply'),
    path('api/threads/<int:thread_id>/vote/', views.api_thread_vote, name='api_thread_vote'),
    path('api/replies/<int:reply_id>/', views.api_reply_detail, name='api_reply_detail'),
    path('api/replies/<int:reply_id>/vote/', views.api_reply_vote, name='api_reply_vote'),
    path('api/tags/', views.api_tags_list, name='api_tags_list'),

    # ==== DETAIL THREAD (letakkan paling terakhir) ====
    path('<int:thread_id>/', views.thread_detail, name='thread_detail'),
]

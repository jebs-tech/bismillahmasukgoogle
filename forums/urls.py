from django.urls import path
from . import views

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

    # ==== DETAIL THREAD (letakkan paling terakhir) ====
    path('<int:thread_id>/', views.thread_detail, name='thread_detail'),
]

# notifications/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from .models import Notification

@login_required

def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
def unread_count_api(request):
    """
    Return JSON: { unread_count, html_latest }.
    html_latest is small markup for the toast/dropdown (max 5 items).
    """
    if request.method != 'GET':
        return HttpResponseForbidden()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    latest = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    html_latest = render_to_string('notifications/partials/notification_items.html', {'notifications': latest}, request=request)
    return JsonResponse({'unread_count': unread_count, 'html': html_latest})

@login_required
def mark_all_read_api(request):
    """
    Mark all notifications for current user as read.
    """
    if request.method != 'POST':
        return HttpResponseForbidden()
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})

# notifications/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.timezone import localtime
from .models import Notification

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
def unread_count_api(request):
    if request.method != 'GET':
        return HttpResponseForbidden()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    # Hanya tampilkan notifikasi yang belum dibaca di dropdown
    latest = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5]
    html_latest = render_to_string('notifications/partials/notification_items.html', {'notifications': latest}, request=request)
    return JsonResponse({'unread_count': unread_count, 'html': html_latest})

@login_required
def mark_all_read_api(request):
    if request.method != 'POST':
        return HttpResponseForbidden()
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


# ==================================================
# ===== REST API ENDPOINTS FOR FLUTTER ============
# ==================================================

@csrf_exempt
@require_http_methods(["GET"])
def api_notification_list(request):
    """
    GET: List all notifications for authenticated user
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifications_data = []
    for notification in notifications:
        notifications_data.append({
            'id': notification.id,
            'message': notification.message,
            'created_at': localtime(notification.created_at).isoformat(),
            'is_read': notification.is_read,
        })
    
    return JsonResponse({'success': True, 'notifications': notifications_data}, safe=False)


@csrf_exempt
@require_http_methods(["GET"])
def api_notification_unread_count(request):
    """
    GET: Get unread notification count
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    latest = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5]
    latest_data = []
    for notification in latest:
        latest_data.append({
            'id': notification.id,
            'message': notification.message,
            'created_at': localtime(notification.created_at).isoformat(),
            'is_read': notification.is_read,
        })
    
    return JsonResponse({
        'success': True,
        'unread_count': unread_count,
        'latest': latest_data,
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_notification_mark_read(request, notification_id):
    """
    POST: Mark a specific notification as read
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    notification = Notification.objects.filter(user=request.user, id=notification_id).first()
    if not notification:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)
    
    notification.is_read = True
    notification.save()
    
    return JsonResponse({'success': True, 'message': 'Notification marked as read'})


@csrf_exempt
@require_http_methods(["POST"])
def api_notification_mark_all_read(request):
    """
    POST: Mark all notifications as read
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True, 'message': 'All notifications marked as read'})


@login_required
def delete_all_notifications_api(request):
    """
    POST: Delete all notifications for the authenticated user
    """
    if request.method != 'POST':
        return HttpResponseForbidden()
    Notification.objects.filter(user=request.user).delete()
    return JsonResponse({'success': True, 'message': 'All notifications deleted'})

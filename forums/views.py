from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.timezone import localtime
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Thread, Reply, Tag
from .forms import ThreadForm, ReplyForm


# ===============================
# ==== LIST THREAD ==========
# ===============================
def thread_list(request):
    threads = Thread.objects.select_related('author', 'author__profile').prefetch_related('tags').order_by('-created_at')
    return render(request, 'forums/thread_list.html', {'threads': threads})


# ===============================
# ==== DETAIL THREAD =========
# ===============================
def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread.objects.select_related('author', 'author__profile').prefetch_related('tags'), pk=thread_id)
    replies = thread.replies.select_related('author', 'author__profile').order_by('created_at')
    form = ReplyForm()
    return render(request, 'forums/thread_detail.html', {
        'thread': thread,
        'replies': replies,
        'form': form
    })


# ==================================================
# ===== AJAX endpoints (return JSON) ===============
# ==================================================

# ---- Create thread (AJAX) ----

@login_required
@require_POST
def create_thread_ajax(request):
    form = ThreadForm(request.POST)
    if form.is_valid():
        thread = form.save(commit=False)
        thread.author = request.user
        thread.save()
        form.save_m2m()

        # Refresh thread dengan select_related untuk profile
        thread = Thread.objects.select_related('author', 'author__profile').prefetch_related('tags').get(pk=thread.id)
        html = render_to_string('forums/threads/thread_card.html', {
            'thread': thread,
            'user': request.user
        }, request=request)

        return JsonResponse({'success': True, 'html': html})
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


# ---- Edit thread (AJAX) ----
@login_required
@require_POST
def edit_thread_ajax(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    if thread.author is None or (request.user != thread.author and not request.user.is_superuser):
        return HttpResponseForbidden('Anda tidak mempunyai izin untuk mengedit thread ini.')

        form = ThreadForm(request.POST, instance=thread)
    if form.is_valid():
        form.save()
        # Refresh thread dengan select_related untuk profile
        thread = Thread.objects.select_related('author', 'author__profile').prefetch_related('tags').get(pk=thread.id)
        html = render_to_string('forums/threads/thread_card.html', {
            'thread': thread,
            'user': request.user
        }, request=request)
        return JsonResponse({'success': True, 'html': html})
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


# ---- Delete thread (AJAX) ----
@login_required
@require_POST
def delete_thread_ajax(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    if thread.author is None or (request.user != thread.author and not request.user.is_superuser):
        return HttpResponseForbidden('Anda tidak mempunyai izin untuk menghapus thread ini.')

    thread.delete()
    return JsonResponse({'success': True, 'thread_id': thread_id})


# ---- Reply to thread (AJAX) ----
@login_required
@require_POST
def reply_ajax(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    form = ReplyForm(request.POST)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.thread = thread
        reply.author = request.user
        reply.save()

        # Refresh reply dengan select_related untuk profile
        reply = Reply.objects.select_related('author', 'author__profile').get(pk=reply.id)
        # Render ke template reply_card.html, bukan partials lama
        html = render_to_string(
            'forums/threads/reply_card.html',
            {'reply': reply, 'user': request.user},
            request=request
        )

        return JsonResponse({
            'success': True,
            'reply_id': reply.id,
            'author': reply.author.username,
            'content': reply.content,
            'created_at': localtime(reply.created_at).strftime('%d %b %Y %H:%M'),
            'html': html
        })
    else:
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)


# ---- Edit reply (AJAX) ----
@login_required
@require_POST
def edit_reply_ajax(request, reply_id):
    reply = get_object_or_404(Reply, pk=reply_id)
    if reply.author is None or (request.user != reply.author and not request.user.is_superuser):
        return HttpResponseForbidden('Anda tidak mempunyai izin untuk mengedit balasan ini.')

    form = ReplyForm(request.POST, instance=reply)
    if form.is_valid():
        reply = form.save()
        # Refresh reply dengan select_related untuk profile
        reply = Reply.objects.select_related('author', 'author__profile').get(pk=reply.id)
        html = render_to_string(
            'forums/threads/reply_card.html',
            {'reply': reply, 'user': request.user},
            request=request
        )
        return JsonResponse({
            'success': True,
            'reply_id': reply.id,
            'html': html,
        })
    else:
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)


# ---- Delete reply (AJAX) ----
@login_required
@require_POST
def delete_reply_ajax(request, reply_id):
    reply = get_object_or_404(Reply, pk=reply_id)
    if reply.author is None or (request.user != reply.author and not request.user.is_superuser):
        return HttpResponseForbidden('Anda tidak mempunyai izin untuk menghapus balasan ini.')

    reply.delete()
    return JsonResponse({'success': True, 'reply_id': reply_id})


# ==================================================
# ===== AJAX Voting: Thread & Reply ================
# ==================================================

@login_required
@require_POST
def vote_thread_ajax(request, thread_id):
    """
    Handle upvote/downvote untuk thread.
    User hanya boleh punya 1 jenis vote aktif (upvote atau downvote).
    """
    thread = get_object_or_404(Thread, pk=thread_id)
    action = request.POST.get('action')

    if action == 'upvote':
        if request.user in thread.upvotes.all():
            thread.upvotes.remove(request.user)
        else:
            thread.upvotes.add(request.user)
            thread.downvotes.remove(request.user)
    elif action == 'downvote':
        if request.user in thread.downvotes.all():
            thread.downvotes.remove(request.user)
        else:
            thread.downvotes.add(request.user)
            thread.upvotes.remove(request.user)

    return JsonResponse({
        'success': True,
        'thread_id': thread.id,
        'upvotes': thread.total_upvotes(),
        'downvotes': thread.total_downvotes(),
        'score': thread.score(),
    })


@login_required
@require_POST
def vote_reply_ajax(request, reply_id):
    """
    Handle upvote/downvote untuk reply.
    User hanya boleh punya 1 jenis vote aktif (upvote atau downvote).
    """
    reply = get_object_or_404(Reply, pk=reply_id)
    action = request.POST.get('action')

    if action == 'upvote':
        if request.user in reply.upvotes.all():
            reply.upvotes.remove(request.user)
        else:
            reply.upvotes.add(request.user)
            reply.downvotes.remove(request.user)
    elif action == 'downvote':
        if request.user in reply.downvotes.all():
            reply.downvotes.remove(request.user)
        else:
            reply.downvotes.add(request.user)
            reply.upvotes.remove(request.user)

    return JsonResponse({
        'success': True,
        'reply_id': reply.id,
        'upvotes': reply.total_upvotes(),
        'downvotes': reply.total_downvotes(),
        'score': reply.score(),
    })


# ==================================================
# ===== REST API ENDPOINTS FOR FLUTTER ============
# ==================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_thread_list(request):
    """
    GET: List all threads
    POST: Create new thread (requires authentication)
    """
    if request.method == 'GET':
        threads = Thread.objects.all().select_related('author').prefetch_related('tags', 'upvotes', 'downvotes').order_by('-created_at')
        threads_data = []
        for thread in threads:
            threads_data.append({
                'id': thread.id,
                'title': thread.title,
                'content': thread.content,
                'author': {
                    'id': thread.author.id if thread.author else None,
                    'username': thread.author.username if thread.author else 'Anonymous',
                },
                'tags': [{'id': tag.id, 'name': tag.name} for tag in thread.tags.all()],
                'created_at': localtime(thread.created_at).isoformat(),
                'upvotes': thread.total_upvotes(),
                'downvotes': thread.total_downvotes(),
                'score': thread.score(),
                'reply_count': thread.replies.count(),
                'has_upvoted': request.user.is_authenticated and request.user in thread.upvotes.all(),
                'has_downvoted': request.user.is_authenticated and request.user in thread.downvotes.all(),
            })
        return JsonResponse({'success': True, 'threads': threads_data}, safe=False)
    
    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = request.POST
        
        # Handle tags - convert list of IDs to proper format for form
        if 'tags' in data and isinstance(data['tags'], list):
            # ThreadForm expects tags as a list of tag IDs
            pass  # Already in correct format
        elif 'tags' not in data:
            data['tags'] = []
        
        form = ThreadForm(data)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.author = request.user
            thread.save()
            form.save_m2m()
            
            return JsonResponse({
                'success': True,
                'thread': {
                    'id': thread.id,
                    'title': thread.title,
                    'content': thread.content,
                    'author': {
                        'id': thread.author.id,
                        'username': thread.author.username,
                    },
                    'tags': [{'id': tag.id, 'name': tag.name} for tag in thread.tags.all()],
                    'created_at': localtime(thread.created_at).isoformat(),
                    'upvotes': 0,
                    'downvotes': 0,
                    'score': 0,
                    'reply_count': 0,
                }
            }, status=201)
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def api_thread_detail(request, thread_id):
    """
    GET: Get thread detail with replies
    PUT: Update thread (requires authentication and ownership)
    DELETE: Delete thread (requires authentication and ownership)
    """
    thread = get_object_or_404(Thread, pk=thread_id)
    
    if request.method == 'GET':
        replies = thread.replies.all().select_related('author').prefetch_related('upvotes', 'downvotes').order_by('created_at')
        replies_data = []
        for reply in replies:
            replies_data.append({
                'id': reply.id,
                'content': reply.content,
                'author': {
                    'id': reply.author.id if reply.author else None,
                    'username': reply.author.username if reply.author else 'Anonymous',
                },
                'created_at': localtime(reply.created_at).isoformat(),
                'upvotes': reply.total_upvotes(),
                'downvotes': reply.total_downvotes(),
                'score': reply.score(),
                'has_upvoted': request.user.is_authenticated and request.user in reply.upvotes.all(),
                'has_downvoted': request.user.is_authenticated and request.user in reply.downvotes.all(),
            })
        
        return JsonResponse({
            'success': True,
            'thread': {
                'id': thread.id,
                'title': thread.title,
                'content': thread.content,
                'author': {
                    'id': thread.author.id if thread.author else None,
                    'username': thread.author.username if thread.author else 'Anonymous',
                },
                'tags': [{'id': tag.id, 'name': tag.name} for tag in thread.tags.all()],
                'created_at': localtime(thread.created_at).isoformat(),
                'upvotes': thread.total_upvotes(),
                'downvotes': thread.total_downvotes(),
                'score': thread.score(),
                'reply_count': thread.replies.count(),
                'has_upvoted': request.user.is_authenticated and request.user in thread.upvotes.all(),
                'has_downvoted': request.user.is_authenticated and request.user in thread.downvotes.all(),
                'is_author': request.user.is_authenticated and thread.author is not None and request.user == thread.author,
                'replies': replies_data,
            }
        })
    
    elif request.method == 'PUT':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        
        if thread.author is None or (request.user != thread.author and not request.user.is_superuser):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = request.POST
        
        form = ThreadForm(data, instance=thread)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'thread': {
                    'id': thread.id,
                    'title': thread.title,
                    'content': thread.content,
                    'tags': [{'id': tag.id, 'name': tag.name} for tag in thread.tags.all()],
                }
            })
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    elif request.method == 'DELETE':
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        
        if thread.author is None or (request.user != thread.author and not request.user.is_superuser):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        thread.delete()
        return JsonResponse({'success': True, 'message': 'Thread deleted'})


@csrf_exempt
@require_http_methods(["POST"])
def api_thread_delete(request, thread_id):
    """
    POST: Delete thread (alternative endpoint for Flutter CookieRequest compatibility)
    Requires authentication and ownership
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    thread = get_object_or_404(Thread, pk=thread_id)
    
    if thread.author is None or (request.user != thread.author and not request.user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    thread.delete()
    return JsonResponse({'success': True, 'message': 'Thread deleted'})


@csrf_exempt
@require_http_methods(["POST"])
def api_thread_reply(request, thread_id):
    """
    POST: Create reply to thread (requires authentication)
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    thread = get_object_or_404(Thread, pk=thread_id)
    
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = request.POST
    
    form = ReplyForm(data)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.thread = thread
        reply.author = request.user
        reply.save()
        
        return JsonResponse({
            'success': True,
            'reply': {
                'id': reply.id,
                'content': reply.content,
                'author': {
                    'id': reply.author.id,
                    'username': reply.author.username,
                },
                'created_at': localtime(reply.created_at).isoformat(),
                'upvotes': 0,
                'downvotes': 0,
                'score': 0,
            }
        }, status=201)
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@csrf_exempt
@require_http_methods(["PUT", "DELETE"])
def api_reply_detail(request, reply_id):
    """
    PUT: Update reply (requires authentication and ownership)
    DELETE: Delete reply (requires authentication and ownership)
    """
    reply = get_object_or_404(Reply, pk=reply_id)
    
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    if reply.author is None or (request.user != reply.author and not request.user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'PUT':
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = request.POST
        
        form = ReplyForm(data, instance=reply)
        if form.is_valid():
            reply = form.save()
            return JsonResponse({
                'success': True,
                'reply': {
                    'id': reply.id,
                    'content': reply.content,
                }
            })
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    
    elif request.method == 'DELETE':
        reply.delete()
        return JsonResponse({'success': True, 'message': 'Reply deleted'})


@csrf_exempt
@require_http_methods(["POST"])
def api_thread_vote(request, thread_id):
    """
    POST: Vote on thread (upvote/downvote) - requires authentication
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    thread = get_object_or_404(Thread, pk=thread_id)
    
    try:
        data = json.loads(request.body) if request.body else {}
        action = data.get('action', request.POST.get('action'))
    except json.JSONDecodeError:
        action = request.POST.get('action')
    
    if action == 'upvote':
        if request.user in thread.upvotes.all():
            thread.upvotes.remove(request.user)
        else:
            thread.upvotes.add(request.user)
            thread.downvotes.remove(request.user)
    elif action == 'downvote':
        if request.user in thread.downvotes.all():
            thread.downvotes.remove(request.user)
        else:
            thread.downvotes.add(request.user)
            thread.upvotes.remove(request.user)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
    
    return JsonResponse({
        'success': True,
        'thread_id': thread.id,
        'upvotes': thread.total_upvotes(),
        'downvotes': thread.total_downvotes(),
        'score': thread.score(),
        'has_upvoted': request.user in thread.upvotes.all(),
        'has_downvoted': request.user in thread.downvotes.all(),
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_reply_vote(request, reply_id):
    """
    POST: Vote on reply (upvote/downvote) - requires authentication
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    reply = get_object_or_404(Reply, pk=reply_id)
    
    try:
        data = json.loads(request.body) if request.body else {}
        action = data.get('action', request.POST.get('action'))
    except json.JSONDecodeError:
        action = request.POST.get('action')
    
    if action == 'upvote':
        if request.user in reply.upvotes.all():
            reply.upvotes.remove(request.user)
        else:
            reply.upvotes.add(request.user)
            reply.downvotes.remove(request.user)
    elif action == 'downvote':
        if request.user in reply.downvotes.all():
            reply.downvotes.remove(request.user)
        else:
            reply.downvotes.add(request.user)
            reply.upvotes.remove(request.user)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
    
    return JsonResponse({
        'success': True,
        'reply_id': reply.id,
        'upvotes': reply.total_upvotes(),
        'downvotes': reply.total_downvotes(),
        'score': reply.score(),
        'has_upvoted': request.user in reply.upvotes.all(),
        'has_downvoted': request.user in reply.downvotes.all(),
    })


@require_http_methods(["GET"])
def api_tags_list(request):
    """
    GET: List all available tags
    """
    tags = Tag.objects.all().order_by('name')
    tags_data = [{'id': tag.id, 'name': tag.name} for tag in tags]
    return JsonResponse({'success': True, 'tags': tags_data}, safe=False)

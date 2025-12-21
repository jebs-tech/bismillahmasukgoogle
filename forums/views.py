from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.timezone import localtime

from .models import Thread, Reply
from .forms import ThreadForm, ReplyForm


# ===============================
# ==== LIST THREAD ==========
# ===============================
def thread_list(request):
    threads = Thread.objects.all().order_by('-created_at')
    return render(request, 'forums/thread_list.html', {'threads': threads})


# ===============================
# ==== DETAIL THREAD =========
# ===============================
def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    replies = thread.replies.all().order_by('created_at')
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

from django.shortcuts import render, get_object_or_404, redirect
from .models import Thread
from .forms import ThreadForm, ReplyForm

# ===== LIST THREAD =====
def thread_list(request):
    threads = Thread.objects.all().order_by('-created_at')
    return render(request, 'forums/thread_list.html', {'threads': threads})


# ===== DETAIL THREAD + FORM REPLY (di halaman yang sama) =====
def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    replies = thread.replies.all().order_by('created_at')

    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.thread = thread
            if request.user.is_authenticated:
                reply.author = request.user
            else:
                reply.author = None  # sementara biar gak error saat testing
            reply.save()
            return redirect('thread_detail', thread_id=thread.id)
    else:
        form = ReplyForm()

    return render(request, 'forums/thread_detail.html', {
        'thread': thread,
        'replies': replies,
        'form': form
    })


# ===== BUAT THREAD BARU =====
def create_thread(request):
    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            if request.user.is_authenticated:
                thread.author = request.user
            else:
                thread.author = None  # sementara biar gak error buat testing
            thread.save()
            return redirect('thread_list')
    else:
        form = ThreadForm()
    return render(request, 'forums/thread_form.html', {'form': form})

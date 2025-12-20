from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Reply
from notifications.models import Notification


@receiver(post_save, sender=Reply)
def notify_thread_author_on_reply(sender, instance, created, **kwargs):
    """
    Membuat notifikasi untuk author thread ketika ada user yang membalas thread mereka.
    Hanya kirim notifikasi jika:
    - Reply baru dibuat (created=True)
    - Thread memiliki author (tidak anonymous)
    - Author reply berbeda dengan author thread (tidak reply sendiri)
    """
    if not created:
        return  # Hanya untuk reply baru
    
    thread = instance.thread
    reply_author = instance.author
    
    # Skip jika thread tidak ada author (anonymous) atau reply tidak ada author
    if not thread.author or not reply_author:
        return
    
    # Skip jika user membalas thread sendiri
    if thread.author == reply_author:
        return
    
    # Buat notifikasi untuk thread author
    # Gunakan nama_lengkap jika ada, fallback ke username
    author_display_name = reply_author.profile.nama_lengkap if (hasattr(reply_author, 'profile') and reply_author.profile.nama_lengkap) else reply_author.username
    message = f"{author_display_name} membalas thread Anda: \"{thread.title[:50]}{'...' if len(thread.title) > 50 else ''}\""
    
    # Cek apakah sudah ada notifikasi untuk reply ini hari ini (hindari spam)
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    existing = Notification.objects.filter(
        user=thread.author,
        message=message,
        created_at__gte=today_start
    ).exists()
    
    if not existing:
        Notification.objects.create(
            user=thread.author,
            message=message
        )


from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from matches.models import Match
from .models import Notification

def check_upcoming_matches():
    """
    Mengecek pertandingan yang akan berlangsung besok hari (1 hari lagi)
    dan membuat notifikasi untuk semua user.
    Hanya membuat notifikasi sekali per match per user per hari.
    """
    now = timezone.now()
    tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
    tomorrow_end = tomorrow_start.replace(hour=23, minute=59, second=59)

    matches = Match.objects.filter(start_time__range=(tomorrow_start, tomorrow_end))

    notification_count = 0
    for match in matches:
        # Format nama match
        match_title = match.title or (f"{match.team_a.name if match.team_a else 'Tim A'} vs {match.team_b.name if match.team_b else 'Tim B'}")
        venue_name = match.venue.name if match.venue else 'venue belum ditentukan'
        
        # Format waktu
        match_time = match.start_time.strftime("%d %B %Y pukul %H:%M")
        message = f"Pertandingan {match_title} akan berlangsung besok ({match_time}) di {venue_name}."
        
        users = User.objects.all()
        for user in users:
            # Cek apakah sudah ada notifikasi untuk match ini untuk user ini hari ini
            # Menggunakan prefix message untuk cek duplicate (tanpa waktu yang spesifik)
            message_prefix = f"Pertandingan {match_title} akan berlangsung besok"
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            existing = Notification.objects.filter(
                user=user,
                message__startswith=message_prefix,
                created_at__gte=today_start
            ).exists()
            
            if not existing:
                Notification.objects.create(
                    user=user,
                    message=message
                )
                notification_count += 1
    
    if notification_count > 0:
        print(f"[SCHEDULER] ✅ {notification_count} notifikasi match besok dibuat untuk {tomorrow_start.date()}.")
    else:
        print(f"[SCHEDULER] ℹ️ Tidak ada match baru untuk notifikasi ({tomorrow_start.date()}).")


def start():
    """
    Memulai scheduler saat Django dijalankan.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_upcoming_matches, 'interval', hours=24)
    scheduler.start()
    print("[SCHEDULER] APScheduler dimulai — akan berjalan setiap 24 jam.")

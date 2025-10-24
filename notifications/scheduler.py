from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from matches.models import Match
from .models import Notification

def check_upcoming_matches():
    """
    Mengecek pertandingan yang akan berlangsung 1 hari lagi
    dan membuat notifikasi untuk semua user.
    """
    now = timezone.now()
    tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
    tomorrow_end = tomorrow_start.replace(hour=23, minute=59, second=59)

    matches = Match.objects.filter(start_time__range=(tomorrow_start, tomorrow_end))

    for match in matches:
        users = User.objects.all()
        for user in users:
            Notification.objects.get_or_create(
                user=user,
                message=f"Pertandingan {match.home_team} vs {match.away_team} "
                        f"akan berlangsung besok di {match.venue.name if match.venue else 'venue belum ditentukan'}."
            )
    print(f"[SCHEDULER] Cek pertandingan untuk {tomorrow_start.date()} selesai.")


def start():
    """
    Memulai scheduler saat Django dijalankan.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_upcoming_matches, 'interval', hours=24)
    scheduler.start()
    print("[SCHEDULER] APScheduler dimulai — akan berjalan setiap 24 jam.")

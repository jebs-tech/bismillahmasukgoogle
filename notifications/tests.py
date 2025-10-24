from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from matches.models import Team, Venue, Match
from notifications.models import Notification
from notifications.scheduler import check_upcoming_matches

class NotificationTests(TestCase):

    def setUp(self):
        """Setup tim, venue, dan user untuk notifikasi."""
        self.user = User.objects.create_user(username="fariz", password="12345")
        self.team1 = Team.objects.create(name="Persija")
        self.team2 = Team.objects.create(name="Persib")
        self.venue = Venue.objects.create(name="Stadion Utama GBK")
        self.match = Match.objects.create(
            home_team=self.team1,
            away_team=self.team2,
            start_time=timezone.now() + timedelta(days=1),
            venue=self.venue
        )

    def test_create_notification(self):
        """Pastikan notifikasi bisa dibuat."""
        notif = Notification.objects.create(user=self.user, message="Tes notifikasi pertandingan")
        self.assertEqual(str(notif), "Tes notifikasi pertandingan")
        self.assertFalse(notif.is_read)

    def test_upcoming_match_creates_notification(self):
        """Tes job APScheduler: harus buat notifikasi 1 hari sebelum pertandingan."""
        self.assertEqual(Notification.objects.count(), 0)
        check_upcoming_matches()  # panggil fungsi langsung
        self.assertEqual(Notification.objects.count(), 1)
        notif = Notification.objects.first()
        self.assertIn("Persija vs Persib", notif.message)

    def test_mark_notification_as_read(self):
        """Pastikan notifikasi bisa ditandai sebagai sudah dibaca."""
        notif = Notification.objects.create(user=self.user, message="Baru nih notif")
        notif.mark_as_read()
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_multiple_notifications_for_same_match(self):
        """Pastikan tidak duplikat notifikasi untuk pertandingan sama."""
        check_upcoming_matches()
        check_upcoming_matches()
        self.assertEqual(Notification.objects.count(), 1)

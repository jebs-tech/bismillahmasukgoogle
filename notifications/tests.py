from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from notifications.models import Notification

class NotificationViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='bunga', password='testpass123')
        self.notification1 = Notification.objects.create(
            user=self.user,
            message='Notif 1',
            is_read=False
        )
        self.notification2 = Notification.objects.create(
            user=self.user,
            message='Notif 2',
            is_read=True
        )

    def test_notification_list_requires_login(self):
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_notification_list_authenticated(self):
        self.client.login(username='bunga', password='testpass123')
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'notifications/list.html')
        # Setelah view diakses, semua unread harus jadi read
        self.notification1.refresh_from_db()
        self.assertTrue(self.notification1.is_read)

    def test_unread_count_api_get_success(self):
        self.client.login(username='bunga', password='testpass123')
        # buat notifikasi unread baru
        Notification.objects.create(user=self.user, message='Baru', is_read=False)
        response = self.client.get(reverse('notifications:notification_unread_count'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('unread_count', data)
        self.assertIn('html', data)
        self.assertGreaterEqual(data['unread_count'], 1)

    def test_unread_count_api_rejects_non_get(self):
        self.client.login(username='bunga', password='testpass123')
        response = self.client.post(reverse('notifications:notification_unread_count'))
        self.assertEqual(response.status_code, 403)

    def test_mark_all_read_api_post_success(self):
        self.client.login(username='bunga', password='testpass123')
        Notification.objects.create(user=self.user, message='Unread', is_read=False)
        response = self.client.post(reverse('notifications:notification_mark_all_read'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        unread_left = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread_left, 0)

    def test_mark_all_read_api_rejects_non_post(self):
        self.client.login(username='bunga', password='testpass123')
        response = self.client.get(reverse('notifications:notification_mark_all_read'))
        self.assertEqual(response.status_code, 403)

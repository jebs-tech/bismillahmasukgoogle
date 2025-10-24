from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Thread, Reply

class ForumTests(TestCase):

    def setUp(self):
        """Setup awal: user, client, dan 1 thread dasar."""
        self.client = Client()
        self.user = User.objects.create_user(username="fariz", password="12345")
        self.thread = Thread.objects.create(
            title="Thread Pertama",
            content="Isi dari thread pertama",
            author=self.user
        )
        self.reply = Reply.objects.create(
            thread=self.thread,
            content="Balasan awal",
            author=self.user
        )

    def test_thread_list_view(self):
        """Pastikan halaman daftar thread dapat diakses."""
        response = self.client.get(reverse('thread_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thread Pertama")

    def test_create_thread_ajax(self):
        """Coba buat thread baru via AJAX."""
        self.client.login(username="fariz", password="12345")
        response = self.client.post(reverse('create_thread_ajax'), {
            'title': 'Thread Baru',
            'content': 'Isi thread baru',
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': True, 'html': response.json()['html']})
        self.assertTrue(Thread.objects.filter(title="Thread Baru").exists())

    def test_edit_thread_ajax(self):
        """Edit thread yang sudah ada."""
        self.client.login(username="fariz", password="12345")
        response = self.client.post(reverse('edit_thread_ajax', args=[self.thread.id]), {
            'title': 'Thread Pertama Edit',
            'content': 'Konten sudah diedit',
        })
        self.assertEqual(response.status_code, 200)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.content, 'Konten sudah diedit')

    def test_delete_thread_ajax(self):
        """Hapus thread via AJAX."""
        self.client.login(username="fariz", password="12345")
        response = self.client.post(reverse('delete_thread_ajax', args=[self.thread.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Thread.objects.filter(id=self.thread.id).exists())

    def test_reply_creation(self):
        """Coba tambahkan balasan ke thread."""
        self.client.login(username="fariz", password="12345")
        response = self.client.post(reverse('reply_ajax', args=[self.thread.id]), {
            'content': 'Ini balasan baru'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Reply.objects.filter(content='Ini balasan baru').exists())

    def test_thread_vote_upvote(self):
        """Tes upvote thread."""
        self.client.login(username="fariz", password="12345")
        response = self.client.post(reverse('vote_thread_ajax', args=[self.thread.id]), {'action': 'upvote'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user, self.thread.upvotes.all())

    def test_thread_vote_downvote(self):
        """Tes downvote thread."""
        self.client.login(username="fariz", password="12345")
        response = self.client.post(reverse('vote_thread_ajax', args=[self.thread.id]), {'action': 'downvote'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user, self.thread.downvotes.all())

    def test_reply_vote_upvote(self):
        """Tes upvote reply."""
        self.client.login(username="fariz", password="12345")
        response = self.client.post(reverse('vote_reply_ajax', args=[self.reply.id]), {'action': 'upvote'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user, self.reply.upvotes.all())

    def test_reply_delete(self):
        """Tes delete reply AJAX."""
        self.client.login(username="fariz", password="12345")
        response = self.client.post(reverse('delete_reply_ajax', args=[self.reply.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Reply.objects.filter(id=self.reply.id).exists())

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Profile
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

class UserViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass', email='test@example.com')
        self.profile_url = reverse('user:profile')
        self.login_url = reverse('user:login')
        self.edit_profile_url = reverse('user:edit_profile')

    def test_register_get(self):
        url = reverse('user:register')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

    def test_login_get(self):
        url = reverse('user:login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_profile_view_requires_login(self):
        response = self.client.get(self.profile_url)
        # Pastikan redirect ke login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.login_url in response.url)

    def test_login_post(self):
        response = self.client.post(self.login_url, {'username': 'testuser', 'password': 'testpass'})
        self.assertRedirects(response, reverse('homepage:homepage'))
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_edit_profile_post(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(self.edit_profile_url, {'nama_lengkap': 'Updated Name', 'nomor_telepon': '08123456789'})
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.nama_lengkap, 'Updated Name')

    def test_logout_user(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('user:logout'))
        self.assertRedirects(response, self.login_url)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_password_reset_flow(self):
        url = reverse('user:password_reset')
        response = self.client.post(url, {'email': self.user.email})
        self.assertRedirects(response, reverse('user:password_reset_done'))

        # Generate token manually untuk confirm view
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse('user:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        response = self.client.get(confirm_url)
        self.assertEqual(response.status_code, 200)

    def test_delete_account_confirm(self):
        self.client.login(username='testuser', password='testpass')
        url = reverse('user:delete_account_confirm')
        response = self.client.post(url)
        self.assertFalse(User.objects.filter(username='testuser').exists())
        self.assertEqual(response.status_code, 200)


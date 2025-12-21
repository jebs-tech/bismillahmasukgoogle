from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .models import Voucher

User = get_user_model()

class VoucherViewsTest(TestCase):

    def setUp(self):
        # Buat user staff
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='password123',
            is_staff=True
        )

        # Buat client login
        self.client = Client()
        self.client.login(username='staffuser', password='password123')

        # Buat voucher contoh
        self.voucher = Voucher.objects.create(
            code='TESTVCHR',
            discount_type='FIXED',  # tipe diskon
            value=10000,             # nilai diskon
            min_purchase_amount=0,
            max_use_count=1,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=10)
        )

    def test_dashboard_view(self):
        url = reverse('voucher:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.voucher.code)

    def test_create_voucher_view_get(self):
        url = reverse('voucher:create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')

    def test_create_voucher_view_post(self):
        url = reverse('voucher:create')
        data = {
            'code': 'NEWVCHR1',
            'discount_type': 'PERCENT',
            'value': 20,
            'min_purchase_amount': 5000,
            'max_use_count': 5,
            'valid_from': timezone.now(),
            'valid_until': timezone.now() + timedelta(days=5),
            'is_active': True
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # redirect ke dashboard
        self.assertTrue(Voucher.objects.filter(code='NEWVCHR1').exists())

    def test_update_voucher_view_get(self):
        url = reverse('voucher:update', args=[self.voucher.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form')

    def test_update_voucher_view_post(self):
        url = reverse('voucher:update', args=[self.voucher.pk])
        data = {
            'code': self.voucher.code,
            'discount_type': 'FIXED',
            'value': 20000,  # update value
            'min_purchase_amount': 0,
            'max_use_count': 2,
            'valid_from': timezone.now(),
            'valid_until': timezone.now() + timedelta(days=15),
            'is_active': True
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.voucher.refresh_from_db()
        self.assertEqual(self.voucher.value, 20000)

    def test_delete_voucher_view_post(self):
        url = reverse('voucher:delete', args=[self.voucher.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Voucher.objects.filter(pk=self.voucher.pk).exists())

    def test_non_staff_access_redirect(self):
        # logout staff, login non-staff
        self.client.logout()
        user = User.objects.create_user(
            username='normaluser',
            email='normal@example.com',
            password='password123'
        )
        self.client.login(username='normaluser', password='password123')
        url = reverse('voucher:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # redirect ke login

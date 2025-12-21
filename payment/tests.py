from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from io import BytesIO
import json

from matches.models import Match, SeatCategory, Seat, Team, Venue
from payment.models import Pembelian

class PaymentViewTests(TestCase):
    def setUp(self):
        # Client & user
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='pass1234')
        self.client.login(username='testuser', password='pass1234')

        # Buat teams
        self.team_a = Team.objects.create(name="Team A")
        self.team_b = Team.objects.create(name="Team B")

        # Buat venue
        self.venue = Venue.objects.create(name="Istora Senayan", address="Jl. Gelora Bung Karno")

        # Buat match
        self.match = Match.objects.create(
            venue=self.venue,
            start_time=timezone.now() + timezone.timedelta(days=1),
            team_a=self.team_a,
            team_b=self.team_b
        )

        # Buat kategori kursi
        self.category = SeatCategory.objects.create(name="VIP", price=100000)

        # Buat kursi untuk match
        for i in range(1, 6):
            Seat.objects.create(match=self.match, category=self.category, row="A", col=i, is_booked=False)

    def test_detail_pembeli_view(self):
        url = reverse('payment:detail_pembeli') + f'?match_id={self.match.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.category.name)

    def test_simpan_pembelian_ajax_success(self):
        """Test pembelian sukses - tidak boleh menghasilkan error 500"""
        url = reverse('payment:simpan_pembelian_ajax')
        payload = {
            "nama_lengkap": "Bunga Saragih",
            "email": "bunga@example.com",
            "nomor_telepon": "081234567890",
            "match_id": self.match.id,
            "kategori_id": self.category.id,
            "tickets": [
                {"nama": "Bunga Saragih", "jenis_kelamin": "P"},
                {"nama": "John Doe", "jenis_kelamin": "L"}
            ]
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        # Pastikan tidak ada error 500
        self.assertNotEqual(response.status_code, 500, "Seharusnya tidak ada error 500")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('order_id', data)
        self.assertEqual(Pembelian.objects.count(), 1)
        
        # Pastikan kursi sudah di-book
        pembelian = Pembelian.objects.first()
        self.assertEqual(pembelian.seats.count(), 2)

    def test_simpan_pembelian_ajax_not_enough_seats(self):
        url = reverse('payment:simpan_pembelian_ajax')
        payload = {
            "nama_lengkap": "Bunga Saragih",
            "email": "bunga@example.com",
            "nomor_telepon": "081234567890",
            "match_id": self.match.id,
            "kategori_id": self.category.id,
            "tickets": ["A1","A2","A3","A4","A5","A6"]  # hanya ada 5 kursi
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['status'], 'error')

    def test_detail_pembayaran_view(self):
        pembelian = Pembelian.objects.create(
            user=self.user,
            match=self.match,
            nama_lengkap_pembeli="Bunga",
            email="bunga@example.com",
            nomor_telepon="08123456789",
            total_price=200000,
            status='PENDING'
        )
        url = reverse('payment:detail_pembayaran', args=[pembelian.order_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rp 200000")

    def test_proses_bayar_ajax_success(self):
        pembelian = Pembelian.objects.create(
            user=self.user,
            match=self.match,
            nama_lengkap_pembeli="Bunga",
            email="bunga@example.com",
            nomor_telepon="08123456789",
            total_price=200000,
            status='PENDING'
        )
        pembelian.seats.set(Seat.objects.filter(match=self.match))

        url = reverse('payment:proses_bayar_ajax', args=[pembelian.order_id])
        file_data = BytesIO(b"fake image data")
        file_data.name = 'bukti.png'
        response = self.client.post(url, {'metode_pembayaran': 'BRI', 'bukti_transfer': file_data})
        self.assertEqual(response.status_code, 200)
        pembelian.refresh_from_db()
        self.assertEqual(pembelian.status, 'CONFIRMED')

    def test_check_voucher_ajax_invalid_code(self):
        url = reverse('payment:check_voucher_ajax')
        payload = {
            "code": "",
            "total": 100000
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')

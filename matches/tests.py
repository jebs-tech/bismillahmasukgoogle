# matches/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from matches.models import Team, Venue, Match, SeatCategory, Seat, MatchSeatCapacity
from matches.forms import MatchForm
import json

# =========================================================
# TEST MODEL MATCHES
# =========================================================

class MatchesModelTest(TestCase):
    def setUp(self):
        self.team_a = Team.objects.create(name='Garuda United')
        self.team_b = Team.objects.create(name='Macan Asia')
        self.venue = Venue.objects.create(name='Stadion Gelora Raya', address='Jakarta')
        self.category_gold = SeatCategory.objects.create(name='GOLD', price=250000)
        
        # Match di masa depan
        self.future_time = timezone.now() + timedelta(days=7)
        self.match = Match.objects.create(
            venue=self.venue,
            start_time=self.future_time,
            team_a=self.team_a,
            team_b=self.team_b
        )
        
        # Match dengan judul kustom
        self.match_custom = Match.objects.create(
            title='Konser Amal',
            venue=self.venue,
            start_time=self.future_time,
            team_a=None,
            team_b=None
        )

    def test_team_creation(self):
        """Memastikan objek Team dibuat dengan benar."""
        self.assertEqual(self.team_a.name, 'Garuda United')
        self.assertEqual(str(self.team_a), 'Garuda United')

    def test_seat_category_creation(self):
        """Memastikan objek SeatCategory dibuat dengan benar."""
        self.assertEqual(self.category_gold.price, 250000)
        self.assertIn('GOLD', str(self.category_gold))

    def test_match_auto_title_generation(self):
        """Menguji Match membuat judul otomatis dari Team A vs Team B."""
        expected_title = 'Garuda United vs Macan Asia'
        self.assertEqual(self.match.title, expected_title)
        self.assertEqual(self.match.get_auto_title(), expected_title)
        self.assertIn('Garuda United', str(self.match))
        
    def test_match_custom_title_preservation(self):
        """Menguji Match mempertahankan judul kustom."""
        self.assertEqual(self.match_custom.title, 'Konser Amal')
        
    def test_match_title_update_if_teams_change(self):
        """Menguji judul match otomatis diperbarui jika tim berubah."""
        team_c = Team.objects.create(name='Elang Hitam')
        self.match.team_b = team_c
        self.match.save()
        self.assertEqual(self.match.title, 'Garuda United vs Elang Hitam')
        
    def test_seat_creation_and_uniqueness(self):
        """Menguji objek Seat dibuat dan constraint uniqueness."""
        seat = Seat.objects.create(
            match=self.match,
            row='A',
            col=10,
            category=self.category_gold,
            is_booked=False
        )
        self.assertEqual(str(seat), f"{self.match.title} - A10")
        
        with self.assertRaises(Exception) as context:
            Seat.objects.create(
                match=self.match,
                row='A',
                col=10,
                category=self.category_gold
            )
        
        # PERBAIKAN: Mencari pesan error database yang spesifik
        self.assertIn('UNIQUE constraint failed', str(context.exception))
        
# =========================================================
# TEST FORMS
# =========================================================

class MatchFormTest(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(name='Test Venue')
        self.team_a = Team.objects.create(name='Home')
        self.team_b = Team.objects.create(name='Away')
        self.valid_data = {
            'venue': self.venue.pk,
            'start_time': (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'team_a': self.team_a.pk,
            'team_b': self.team_b.pk,
            'description': 'Laga uji coba'
        }

    def test_match_form_valid(self):
        """Memastikan MatchForm valid dengan data yang benar."""
        form = MatchForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_match_form_invalid_missing_venue(self):
        """Memastikan MatchForm tidak valid jika venue kosong."""
        invalid_data = self.valid_data.copy()
        del invalid_data['venue']
        form = MatchForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('venue', form.errors)


# =========================================================
# TEST VIEWS MATCHES (CRUD & Staff Protection)
# =========================================================

class MatchViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(username='staff', password='staffpass', is_staff=True)
        self.regular_user = User.objects.create_user(username='regular', password='regularpass', is_staff=False)
        
        self.venue = Venue.objects.create(name='Test Arena')
        self.team_home = Team.objects.create(name='Home Team')
        self.team_away = Team.objects.create(name='Away Team')
        self.future_time = timezone.now() + timedelta(days=10)
        
        self.match = Match.objects.create(
            venue=self.venue,
            start_time=self.future_time,
            team_a=self.team_home,
            team_b=self.team_away
        )
        
        self.list_url = reverse('matches:match_list')
        self.detail_url = reverse('matches:match_detail', args=[self.match.pk])
        self.create_url = reverse('matches:match_create') 
        self.edit_url = reverse('matches:match_edit', args=[self.match.pk]) 
        self.delete_url = reverse('matches:match_delete', args=[self.match.pk])
        
        self.valid_form_data = {
            'venue': self.venue.pk,
            'start_time': (self.future_time + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'team_a': self.team_home.pk,
            'team_b': self.team_away.pk,
            'description': 'New Match'
        }

    # --- Test General Views ---
    
    def test_match_list_view(self):
        """Memastikan match_list merender status 200 dan konten."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        
        # PERBAIKAN: Memeriksa template dan konten secara terpisah
        self.assertTemplateUsed(response, 'match_list.html')
        self.assertContains(response, 'Home Team')
        self.assertContains(response, 'Away Team')
        self.assertContains(response, 'Pertandingan')
        
    def test_match_detail_view(self):
        """Memastikan match_detail merender match yang benar."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Home Team vs Away Team')
        self.assertTemplateUsed(response, 'matches/match_detail.html')

    # --- Test CRUD Staff Protection ---
    
    def test_match_create_access_denied_to_regular_user(self):
        """Memastikan user non-staff tidak bisa mengakses create view."""
        self.client.login(username='regular', password='regularpass')
        response = self.client.get(self.create_url)
        self.assertNotEqual(response.status_code, 200) 

    # --- TES BARU: Menguji request GET (Render Form) ---
    
    def test_match_create_get_view_by_staff_user(self):
        """TES BARU: Memastikan staff bisa me-load halaman create form (GET)."""
        self.client.login(username='staff', password='staffpass')
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'matches/match_form.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['is_edit']) # Memastikan ini mode create

    def test_match_edit_get_view_by_staff_user(self):
        """TES BARU: Memastikan staff bisa me-load halaman edit form (GET)."""
        self.client.login(username='staff', password='staffpass')
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'matches/match_form.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['is_edit']) # Memastikan ini mode edit

    # --- Tes Operasi POST (Non-AJAX) ---
        
    def test_match_create_post_success_by_staff_user(self):
        """Memastikan staff user bisa membuat match (POST non-AJAX)."""
        self.client.login(username='staff', password='staffpass')
        response = self.client.post(self.create_url, self.valid_form_data)
        
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertRedirects(response, self.list_url)
        self.assertTrue(Match.objects.filter(description='New Match').exists())

    def test_match_edit_post_success_by_staff_user(self):
        """Memastikan staff user bisa mengedit match (POST non-AJAX)."""
        self.client.login(username='staff', password='staffpass')
        
        updated_data = self.valid_form_data.copy()
        updated_data['description'] = 'Updated Description'
        
        response = self.client.post(self.edit_url, updated_data)
        
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertRedirects(response, self.list_url)
        self.match.refresh_from_db()
        self.assertEqual(self.match.description, 'Updated Description')

    def test_match_delete_post_success_by_staff_user(self):
        """Memastikan staff user bisa menghapus match (POST non-AJAX)."""
        self.client.login(username='staff', password='staffpass')
        
        response = self.client.post(self.delete_url)
        
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertRedirects(response, self.list_url)
        self.assertFalse(Match.objects.filter(pk=self.match.pk).exists())

    # --- TES BARU: Menguji Form Tidak Valid (Invalid Path) ---

    def test_match_create_post_invalid_form(self):
        """TES BARU: Menguji create POST dengan form tidak valid (Non-AJAX)."""
        self.client.login(username='staff', password='staffpass')
        invalid_data = self.valid_form_data.copy()
        del invalid_data['venue'] # Membuat form tidak valid
        
        response = self.client.post(self.create_url, invalid_data)
        
        self.assertEqual(response.status_code, 200) # Harus render ulang form
        self.assertTemplateUsed(response, 'matches/match_form.html')
        self.assertIn('venue', response.context['form'].errors)

    def test_match_edit_post_invalid_form(self):
        """TES BARU: Menguji edit POST dengan form tidak valid (Non-AJAX)."""
        self.client.login(username='staff', password='staffpass')
        invalid_data = self.valid_form_data.copy()
        invalid_data['start_time'] = '' # Membuat form tidak valid
        
        response = self.client.post(self.edit_url, invalid_data)
        
        self.assertEqual(response.status_code, 200) # Harus render ulang form
        self.assertTemplateUsed(response, 'matches/match_form.html')
        self.assertIn('start_time', response.context['form'].errors)

    # --- TES BARU: Menguji Operasi AJAX ---

    def test_match_create_ajax_success(self):
        """TES BARU: Memastikan staff bisa create via AJAX."""
        self.client.login(username='staff', password='staffpass')
        response = self.client.post(
            self.create_url, 
            self.valid_form_data, 
            HTTP_X_REQUESTED_WITH='XMLHttpRequest' # Header AJAX
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(Match.objects.filter(description='New Match').exists())

    def test_match_edit_ajax_success(self):
        """TES BARU: Memastikan staff bisa edit via AJAX."""
        self.client.login(username='staff', password='staffpass')
        
        updated_data = self.valid_form_data.copy()
        updated_data['description'] = 'Updated Via AJAX'
        
        response = self.client.post(
            self.edit_url, 
            updated_data, 
            HTTP_X_REQUESTED_WITH='XMLHttpRequest' # Header AJAX
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.match.refresh_from_db()
        self.assertEqual(self.match.description, 'Updated Via AJAX')

    def test_match_delete_ajax_success(self):
        """TES BARU: Memastikan staff bisa delete via AJAX."""
        self.client.login(username='staff', password='staffpass')
        
        response = self.client.post(
            self.delete_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest' # Header AJAX
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(Match.objects.filter(pk=self.match.pk).exists())
        
    def test_match_create_ajax_invalid_form(self):
        """TES BARU: Menguji create POST via AJAX dengan form tidak valid."""
        self.client.login(username='staff', password='staffpass')
        invalid_data = self.valid_form_data.copy()
        del invalid_data['venue'] # Membuat form tidak valid
        
        response = self.client.post(
            self.create_url, 
            invalid_data, 
            HTTP_X_REQUESTED_WITH='XMLHttpRequest' # Header AJAX
        )
        
        self.assertEqual(response.status_code, 400) # Bad Request
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('venue', data['errors'])
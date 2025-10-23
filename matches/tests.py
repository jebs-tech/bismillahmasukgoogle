from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import datetime
from .models import Team, Venue, Match

class SimpleTests(TestCase):
    def setUp(self):
        a = Team.objects.create(name='A')
        b = Team.objects.create(name='B')
        v = Venue.objects.create(name='V1')
        Match.objects.create(home_team=a, away_team=b, venue=v, start_time=timezone.make_aware(datetime(2025,10,10,18,0)))

    def test_search_oct(self):
        url = reverse('servetix:match_search_json') + '?month=10&year=2025'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('matches', data)

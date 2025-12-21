from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.timezone import now

from .models import Match, Player
from .forms import MatchForm

class MatchesFullTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username="alice", password="pw123")
        self.user2 = User.objects.create_user(username="bob", password="pw456")
        self.client.login(username="alice", password="pw123")

        # Players
        self.player1 = Player.objects.create(user=self.user1)
        self.player2 = Player.objects.create(user=self.user2)

        # Match normal
        self.match = Match.objects.create(
            player1=self.player1,
            player2=self.player2,
            score1=10,
            score2=5
        )

        # Match tanpa player2 (edge case)
        self.match_no_player2 = Match.objects.create(
            player1=self.player1,
            player2=None,
            score1=0,
            score2=0
        )

    # =======================
    # MODELS EDGE CASES
    # =======================
    def test_match_str_and_winner(self):
        # __str__ normal
        self.assertIn(self.match.player1.user.username, str(self.match))
        self.assertIn(self.match.player2.user.username, str(self.match))
        # __str__ edge case player2=None
        self.assertIn(self.match_no_player2.player1.user.username, str(self.match_no_player2))

        # winner method
        self.assertEqual(self.match.winner(), self.player1)
        self.match.score1 = 3
        self.match.score2 = 5
        self.match.save()
        self.assertEqual(self.match.winner(), self.player2)
        # seri
        self.match.score1 = 4
        self.match.score2 = 4
        self.match.save()
        self.assertIsNone(self.match.winner())
        # edge player2=None
        self.assertEqual(self.match_no_player2.winner(), self.player1)

    # =======================
    # FORMS VALID / INVALID
    # =======================
    def test_match_form_valid_invalid(self):
        # valid
        form = MatchForm(data={'player1': self.player1.id, 'player2': self.player2.id, 'score1': 1, 'score2': 2})
        self.assertTrue(form.is_valid())

        # invalid empty
        form = MatchForm(data={'player1': '', 'player2': '', 'score1': '', 'score2': ''})
        self.assertFalse(form.is_valid())

        # invalid type
        form = MatchForm(data={'player1': 'x', 'player2': 'y', 'score1': 'abc', 'score2': 'def'})
        self.assertFalse(form.is_valid())

    # =======================
    # VIEWS CRUD / AJAX
    # =======================
    def test_create_match_ajax(self):
        url = reverse('matches:create_match_ajax')

        # valid
        response = self.client.post(url, {
            'player1': self.player1.id,
            'player2': self.player2.id,
            'score1': 7,
            'score2': 3
        })
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data['success'])
        self.assertTrue(Match.objects.filter(score1=7, score2=3).exists())

        # invalid form
        response = self.client.post(url, {'player1': '', 'player2': '', 'score1': '', 'score2': ''})
        self.assertEqual(response.status_code, 400)
        json_data = response.json()
        self.assertFalse(json_data['success'])

        # unauthenticated
        self.client.logout()
        response = self.client.post(url, {'player1': self.player1.id, 'player2': self.player2.id, 'score1':1,'score2':2})
        self.assertIn(response.status_code, [302, 403])

    def test_edit_match_ajax(self):
        url = reverse('matches:edit_match_ajax', args=[self.match.id])

        # valid
        response = self.client.post(url, {'score1': 8, 'score2': 2})
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data['success'])
        self.match.refresh_from_db()
        self.assertEqual(self.match.score1, 8)

        # invalid
        response = self.client.post(url, {'score1': '', 'score2': ''})
        self.assertEqual(response.status_code, 400)
        json_data = response.json()
        self.assertFalse(json_data['success'])

        # forbidden
        self.client.logout()
        self.client.login(username="bob", password="pw456")
        response = self.client.post(url, {'score1':10,'score2':0})
        self.assertEqual(response.status_code, 403)

        # edge case: match_no_player2 edit
        self.client.logout()
        self.client.login(username="alice", password="pw123")
        url2 = reverse('matches:edit_match_ajax', args=[self.match_no_player2.id])
        response = self.client.post(url2, {'score1':5,'score2':1})
        self.assertEqual(response.status_code, 200)
        self.match_no_player2.refresh_from_db()
        self.assertEqual(self.match_no_player2.score2, 1)

    def test_delete_match_ajax(self):
        url = reverse('matches:delete_match_ajax', args=[self.match.id])

        # forbidden
        self.client.logout()
        self.client.login(username="bob", password="pw456")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        # delete by owner
        self.client.logout()
        self.client.login(username="alice", password="pw123")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data['success'])
        self.assertFalse(Match.objects.filter(id=self.match.id).exists())

        # unauthenticated
        self.client.logout()
        response = self.client.post(url)
        self.assertIn(response.status_code, [302, 403])

    # =======================
    # SIGNALS TRIGGER
    # =======================
    def test_match_signal_on_save_delete(self):
        # create triggers signal
        match = Match.objects.create(player1=self.player1, player2=self.player2, score1=1, score2=2)
        match.score1 = 5
        match.save()  # update triggers signal

        match_id = match.id
        match.delete()  # delete triggers signal
        self.assertFalse(Match.objects.filter(id=match_id).exists())

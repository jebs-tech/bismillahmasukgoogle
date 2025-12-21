from django.test import TestCase
from django.urls import reverse

class HomepageViewTests(TestCase):
    def test_homepage_url_exists(self):
        """Pastikan URL utama '/' bisa diakses"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_homepage_url_name(self):
        """Pastikan URL dengan name 'homepage:homepage' bisa diakses"""
        url = reverse('homepage:homepage')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_homepage_uses_correct_template(self):
        """Pastikan view menggunakan template 'homepage.html'"""
        response = self.client.get(reverse('homepage:homepage'))
        self.assertTemplateUsed(response, 'homepage.html')

    def test_homepage_contains_main_content(self):
        """Pastikan konten utama muncul di halaman"""
        response = self.client.get(reverse('homepage:homepage'))
        self.assertContains(response, "Dukung Tim Favoritmu")
        self.assertContains(response, "Pesan Tiket Sekarang")
        self.assertContains(response, "Layanan Utama Kami")

    def test_homepage_links_work(self):
        """Pastikan link ke halaman lain ada"""
        response = self.client.get(reverse('homepage:homepage'))
        self.assertContains(response, reverse('matches:match_list'))
        self.assertContains(response, reverse('forums:thread_list'))
        self.assertContains(response, reverse('user:profile'))

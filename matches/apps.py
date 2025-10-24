from django.apps import AppConfig

class MatchesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matches'
    verbose_name = 'Matches (Pertandingan)'
    
    def ready(self):
        print("🔥 MatchesConfig loaded")
        import matches.signals

class HomepageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matches'
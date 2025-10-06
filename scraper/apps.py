from django.apps import AppConfig


class ScraperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scraper'
    verbose_name = 'Job Scraper'
    
    def ready(self):
        """Import signal handlers when the app is ready"""
        pass
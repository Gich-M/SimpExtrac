"""
Django models for scraper app
"""
from django.db import models
from django.core.validators import URLValidator
import json


class ScraperConfiguration(models.Model):
    """Model to store scraper configuration settings"""
    
    name = models.CharField(max_length=100, unique=True, help_text="Configuration name")
    source = models.CharField(max_length=50, help_text="Scraper source (indeed, glassdoor, etc.)")
    
    # Configuration settings as JSON
    settings = models.JSONField(
        default=dict, 
        help_text="JSON configuration for the scraper"
    )
    
    # Rate limiting
    requests_per_minute = models.PositiveIntegerField(default=10)
    delay_between_requests = models.FloatField(default=2.0, help_text="Seconds to wait between requests")
    
    # Scraper behavior
    use_selenium = models.BooleanField(default=False)
    fetch_descriptions = models.BooleanField(default=True)
    max_retries = models.PositiveIntegerField(default=3)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(auto_now=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['source', 'name']
        verbose_name = "Scraper Configuration"
        verbose_name_plural = "Scraper Configurations"
    
    def __str__(self):
        return f"{self.source.title()} - {self.name}"


class ScraperStats(models.Model):
    """Model to track scraper performance and statistics"""
    
    source = models.CharField(max_length=50)
    date = models.DateField()
    
    # Success metrics
    requests_made = models.PositiveIntegerField(default=0)
    successful_requests = models.PositiveIntegerField(default=0)
    failed_requests = models.PositiveIntegerField(default=0)
    
    # Job metrics
    jobs_found = models.PositiveIntegerField(default=0)
    jobs_saved = models.PositiveIntegerField(default=0)
    duplicates_skipped = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    average_response_time = models.FloatField(default=0.0, help_text="Average response time in seconds")
    total_scraping_time = models.FloatField(default=0.0, help_text="Total time spent scraping in seconds")
    
    # Error tracking
    error_details = models.JSONField(default=list, help_text="List of errors encountered")
    
    class Meta:
        unique_together = ['source', 'date']
        ordering = ['-date', 'source']
        verbose_name = "Scraper Statistics"
        verbose_name_plural = "Scraper Statistics"
    
    def __str__(self):
        return f"{self.source.title()} - {self.date}"
    
    @property
    def success_rate(self):
        """Calculate success rate as percentage"""
        if self.requests_made == 0:
            return 0
        return round((self.successful_requests / self.requests_made) * 100, 2)
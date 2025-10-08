"""
Django models for scraper app
"""
from django.db import models


class ScraperStats(models.Model):
    """
    Scraper statistics for URL-based scraping
    """
    
    source = models.CharField(max_length=50, help_text="Source: indeed, glassdoor, linkedin")
    date = models.DateField()
    
    # Job metrics
    jobs_requested = models.PositiveIntegerField(default=0, help_text="Number of jobs user requested")
    jobs_found = models.PositiveIntegerField(default=0, help_text="Number of jobs found on page")
    jobs_saved = models.PositiveIntegerField(default=0, help_text="Number of jobs successfully saved")
    duplicates_skipped = models.PositiveIntegerField(default=0, help_text="Number of duplicate jobs skipped")
    
    # Enhancement metrics
    company_enhancements_success = models.PositiveIntegerField(default=0, help_text="Jobs enhanced with company info")
    company_enhancements_failed = models.PositiveIntegerField(default=0, help_text="Jobs that failed enhancement")
    
    # Performance metrics
    total_scraping_time = models.FloatField(default=0.0, help_text="Total time in seconds")
    
    # Debugging info
    last_url_used = models.URLField(blank=True, help_text="Last URL scraped for debugging")
    
    class Meta:
        unique_together = ['source', 'date']
        ordering = ['-date', 'source']
        verbose_name = "Scraper Statistics"
        verbose_name_plural = "Scraper Statistics"
    
    def __str__(self):
        return f"{self.source.title()} - {self.date} ({self.jobs_saved}/{self.jobs_requested} jobs)"
    
    @property
    def success_rate(self):
        """Calculate job scraping success rate"""
        if self.jobs_requested == 0:
            return 0
        return (self.jobs_saved / self.jobs_requested) * 100
    
    @property
    def enhancement_rate(self):
        """Calculate company enhancement success rate"""
        total_attempts = self.company_enhancements_success + self.company_enhancements_failed
        if total_attempts == 0:
            return 0
        return (self.company_enhancements_success / total_attempts) * 100
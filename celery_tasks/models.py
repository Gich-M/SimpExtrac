"""
Models for Celery task management and scheduling
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class ScheduledScrapeJob(models.Model):
    """Model for storing scheduled scraping job configurations"""
    
    SCHEDULE_TYPES = [
        ('hourly', 'Every Hour'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('custom', 'Custom Cron'),
    ]
    
    name = models.CharField(max_length=200, help_text="Name for this scheduled job")
    description = models.TextField(blank=True, help_text="Description of what this job does")
    
    # Search criteria (stored as JSON)
    job_title = models.CharField(max_length=200, help_text="Job title to search for")
    location = models.CharField(max_length=200, blank=True, help_text="Location to search in")
    sources = models.JSONField(default=list, help_text="List of sources to scrape (indeed, glassdoor, etc.)")
    max_jobs = models.PositiveIntegerField(default=25, validators=[MinValueValidator(1), MaxValueValidator(500)])
    
    # Schedule configuration
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPES, default='daily')
    cron_expression = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Custom cron expression (only for custom schedule type)"
    )
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Job management
    is_active = models.BooleanField(default=True, help_text="Whether this job should run")
    last_run = models.DateTimeField(null=True, blank=True, help_text="When this job last ran")
    next_run = models.DateTimeField(null=True, blank=True, help_text="When this job will run next")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_jobs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Scheduled Scrape Job"
        verbose_name_plural = "Scheduled Scrape Jobs"
    
    def __str__(self):
        return f"{self.name} ({self.get_schedule_type_display()})"
    
    @property
    def search_criteria(self):
        """Return search criteria as a dictionary"""
        return {
            'job_title': self.job_title,
            'location': self.location,
            'sources': self.sources,
            'max_jobs': self.max_jobs,
        }


class ScrapeJobRun(models.Model):
    """Model for tracking individual scrape job executions"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Job reference
    scheduled_job = models.ForeignKey(
        ScheduledScrapeJob, 
        on_delete=models.CASCADE, 
        related_name='runs',
        null=True,
        blank=True,
        help_text="Reference to scheduled job (null for manual runs)"
    )
    
    # Task tracking
    celery_task_id = models.CharField(max_length=100, unique=True, help_text="Celery task ID")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Search parameters (snapshot at time of execution)
    search_criteria = models.JSONField(help_text="Search parameters used for this run")
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    jobs_found = models.PositiveIntegerField(default=0)
    companies_found = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, help_text="List of errors encountered")
    result_summary = models.JSONField(default=dict, help_text="Detailed results and metrics")
    
    # Manual run tracking
    triggered_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="User who triggered this run (for manual runs)"
    )
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = "Scrape Job Run"
        verbose_name_plural = "Scrape Job Runs"
    
    def __str__(self):
        job_name = self.scheduled_job.name if self.scheduled_job else "Manual Run"
        return f"{job_name} - {self.get_status_display()} ({self.started_at})"
    
    @property
    def duration(self):
        """Calculate duration of the job run"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_running(self):
        """Check if the job is currently running"""
        return self.status in ['pending', 'running']
    
    @property
    def success_rate(self):
        """Calculate success rate based on jobs found vs. expected"""
        if 'expected_jobs' in self.result_summary and self.result_summary['expected_jobs'] > 0:
            return (self.jobs_found / self.result_summary['expected_jobs']) * 100
        return 100 if self.jobs_found > 0 else 0


class TaskProgress(models.Model):
    """Model for tracking real-time task progress"""
    
    task_id = models.CharField(max_length=100, unique=True, db_index=True)
    current_step = models.CharField(max_length=200, default="Starting...")
    progress_percentage = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)])
    
    # Progress details
    total_sources = models.PositiveIntegerField(default=0)
    completed_sources = models.PositiveIntegerField(default=0)
    current_source = models.CharField(max_length=50, blank=True)
    
    # Results so far
    jobs_scraped = models.PositiveIntegerField(default=0)
    companies_found = models.PositiveIntegerField(default=0)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Task Progress"
        verbose_name_plural = "Task Progress"
    
    def __str__(self):
        return f"Task {self.task_id} - {self.progress_percentage}%"
    
    def update_progress(self, step=None, percentage=None, **kwargs):
        """Update progress information"""
        if step:
            self.current_step = step
        if percentage is not None:
            self.progress_percentage = min(100, max(0, percentage))
        
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
        
        self.save(update_fields=['current_step', 'progress_percentage', 'updated_at'] + list(kwargs.keys()))

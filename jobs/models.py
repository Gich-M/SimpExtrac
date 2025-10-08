from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=200, unique=True)
    company_website = models.URLField(blank=True, null=True)  # Requirement 8
    company_email = models.EmailField(blank=True, null=True)  # Requirement 9
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Job(models.Model):
    title = models.CharField(max_length=200)  # Job title
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')  # Company name
    location = models.CharField(max_length=200)  # Job location
    url = models.URLField()  # Source URL
    description = models.TextField(blank=True)  # Job description
    source = models.CharField(max_length=50)  # Source website
    scraped_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.company.name}"

    class Meta:
        ordering = ['-created_at']

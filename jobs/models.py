from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=200, unique=True)
    company_website = models.URLField(blank=True, null=True)
    company_email = models.EmailField(blank=True, null=True)
    description = models.TextField(blank=True)
    employee_count = models.IntegerField(blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Job(models.Model):
    title = models.CharField(max_length=200)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    location = models.CharField(max_length=200)
    url = models.URLField()
    description = models.TextField(blank=True)
    salary = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=50)  # 'Indeed', 'Glassdoor', etc.
    scraped_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.company.name}"

    class Meta:
        ordering = ['-created_at']

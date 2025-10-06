from rest_framework import serializers
from .models import Company, Job

class CompanySerializer(serializers.ModelSerializer):
    jobs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'company_website', 'company_email', 
            'description', 'employee_count', 'industry', 
            'created_at', 'jobs_count'
        ]
    
    def get_jobs_count(self, obj):
        return obj.jobs.count()

class JobListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_website = serializers.CharField(source='company.company_website', read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company_name', 'company_website',
            'location', 'salary', 'source', 'url', 'scraped_at'
        ]

class JobDetailSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'location', 'url',
            'description', 'salary', 'source', 'scraped_at',
            'created_at', 'updated_at'
        ]
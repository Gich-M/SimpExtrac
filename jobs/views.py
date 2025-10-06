from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count
from .models import Company, Job
from .serializers import CompanySerializer, JobListSerializer, JobDetailSerializer

class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Company.objects.all().annotate(jobs_count=Count('jobs'))
    serializer_class = CompanySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['industry']
    search_fields = ['name', 'company_website', 'company_email']
    ordering_fields = ['name', 'created_at', 'jobs_count']
    ordering = ['-created_at']

    @action(detail=True, methods=['get'])
    def jobs(self, request, pk=None):
        """Get all jobs for a specific company"""
        company = self.get_object()
        jobs = Job.objects.filter(company=company)
        serializer = JobListSerializer(jobs, many=True)
        return Response(serializer.data)

class JobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Job.objects.select_related('company').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source', 'location', 'company__name']
    search_fields = ['title', 'description', 'company__name', 'location']
    ordering_fields = ['title', 'scraped_at', 'created_at']
    ordering = ['-scraped_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return JobDetailSerializer
        return JobListSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get job statistics"""
        total_jobs = Job.objects.count()
        total_companies = Company.objects.count()
        
        # Jobs by source
        jobs_by_source = dict(Job.objects.values_list('source').annotate(Count('id')))
        
        # Top locations
        top_locations = list(
            Job.objects.values('location')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        # Recent jobs (last 7 days)
        from django.utils import timezone
        from datetime import timedelta
        week_ago = timezone.now() - timedelta(days=7)
        recent_jobs = Job.objects.filter(scraped_at__gte=week_ago).count()
        
        return Response({
            'total_jobs': total_jobs,
            'total_companies': total_companies,
            'jobs_by_source': jobs_by_source,
            'top_locations': top_locations,
            'recent_jobs_7_days': recent_jobs,
        })

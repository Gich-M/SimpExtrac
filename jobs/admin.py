from django.contrib import admin
from .models import Company, Job

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'company_website', 'company_email', 'created_at']
    list_filter = ['created_at', 'industry']
    search_fields = ['name', 'company_website', 'company_email']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'location', 'source', 'salary', 'scraped_at']
    list_filter = ['source', 'location', 'scraped_at', 'created_at']
    search_fields = ['title', 'company__name', 'location', 'description']
    readonly_fields = ['created_at', 'updated_at', 'scraped_at']
    ordering = ['-scraped_at']
    
    # Show jobs grouped by company
    list_select_related = ['company']
    
    # Add filters in sidebar
    date_hierarchy = 'scraped_at'
    
    # Customize the form layout
    fieldsets = (
        ('Job Information', {
            'fields': ('title', 'company', 'location', 'url')
        }),
        ('Job Details', {
            'fields': ('description', 'salary', 'source')
        }),
        ('Timestamps', {
            'fields': ('scraped_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

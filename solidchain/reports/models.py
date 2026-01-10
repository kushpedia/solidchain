from django.db import models
from django.contrib.auth.models import User
from core.models import Member, Payment, ContributionMonth
from django.utils import timezone

class ReportLog(models.Model):
    """Track report generation for audit purposes"""
    REPORT_TYPES = [
        ('monthly', 'Monthly Collection Report'),
        ('member', 'Member Statement'),
        ('outstanding', 'Outstanding Payments'),
        ('fines', 'Fines Summary'),
        ('custom', 'Custom Report'),
    ]
    
    FORMAT_TYPES = [
        ('html', 'HTML'),
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ]
    
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    format = models.CharField(max_length=10, choices=FORMAT_TYPES, default='html')
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(default=timezone.now)
    parameters = models.JSONField(default=dict, blank=True)  # Store filter parameters
    file_path = models.CharField(max_length=500, blank=True, null=True)
    
    class Meta:
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
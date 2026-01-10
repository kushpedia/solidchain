from django.contrib import admin
from .models import ReportLog

@admin.register(ReportLog)
class ReportLogAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'format', 'generated_by', 'generated_at')
    list_filter = ('report_type', 'format', 'generated_at')
    search_fields = ('generated_by__username', 'parameters')
    readonly_fields = ('generated_at', 'parameters')
    
    def has_add_permission(self, request):
        return False  # Reports should only be created via the app
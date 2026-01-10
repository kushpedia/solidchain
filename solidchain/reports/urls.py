from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard
    path('', views.reports_dashboard, name='dashboard'),
    
    # Report forms
    path('monthly/', views.monthly_collection_report, name='monthly_report'),
    path('member/', views.member_statement, name='member_statement'),
    path('outstanding/', views.outstanding_payments_report, name='outstanding_payments'),
    path('fines/', views.fines_summary_report, name='fines_summary'),
    
    # Quick access reports
    path('monthly/<int:month_id>/', views.quick_monthly_report, name='quick_monthly'),
    path('member/<int:member_id>/', views.quick_member_statement, name='quick_member'),
    
    # History
    path('history/', views.report_history, name='history'),
]
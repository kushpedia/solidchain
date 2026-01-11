from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.db import models
from datetime import datetime, date, timedelta
import json
from io import BytesIO

from .forms import (
    MonthlyReportForm, 
    MemberStatementForm, 
    OutstandingPaymentsForm, 
    FinesReportForm
)
from core.models import Member, Payment, ContributionMonth
from .models import ReportLog

# Helper functions
def calculate_monthly_stats(month):
    """Calculate statistics for a specific month"""
    payments = Payment.objects.filter(month=month).select_related('member__user')
    
    # Get all active members
    all_active_members = Member.objects.filter(is_active=True).select_related('user')
    
    # Get member IDs who have paid for this month
    paid_member_ids = payments.values_list('member_id', flat=True)
    
    # Get pending members (active members who haven't paid)
    pending_members = all_active_members.exclude(id__in=paid_member_ids)
    
    total_members = all_active_members.count()
    paid_members = payments.count()
    on_time_count = payments.filter(status='On Time').count()
    
    # Calculate percentages
    if paid_members > 0:
        on_time_percentage = (on_time_count / paid_members) * 100
        collection_rate = (paid_members / total_members) * 100 if total_members > 0 else 0
    else:
        on_time_percentage = 0
        collection_rate = 0
    
    stats = {
        'month': month,
        'total_members': total_members,
        'paid_members': paid_members,
        'pending_members': pending_members.count(),
        'pending_members_list': pending_members,  # Add this
        'paid_member_ids': list(paid_member_ids),  # Add this for template checks
        'total_collected': payments.aggregate(total=Sum('amount_paid'))['total'] or 0,
        'total_fines': payments.aggregate(total=Sum('fine_amount'))['total'] or 0,
        'on_time_count': on_time_count,
        'late_count': payments.filter(status='Late').count(),
        'average_fine': payments.aggregate(avg=Avg('fine_amount'))['avg'] or 0,
        'collection_rate': collection_rate,
        'on_time_percentage': on_time_percentage,
        'payments': payments,
        'all_active_members': all_active_members,  # Add this
    }
    
    return stats


def get_member_statement(member, start_date=None, end_date=None):
    """Get payment history for a specific member"""
    payments = Payment.objects.filter(member=member).select_related('month')
    
    if start_date:
        payments = payments.filter(month__month__gte=start_date)
    if end_date:
        payments = payments.filter(month__month__lte=end_date)
    
    payments = payments.order_by('-month__month')
    
    total_payments = payments.count()
    on_time_count = payments.filter(status='On Time').count()
    late_count = payments.filter(status='Late').count()
    
    # Calculate percentages
    if total_payments > 0:
        on_time_percentage = (on_time_count / total_payments) * 100
        late_percentage = (late_count / total_payments) * 100
    else:
        on_time_percentage = 0
        late_percentage = 0
    
    summary = {
        'member': member,
        'total_payments': total_payments,
        'total_contributions': payments.aggregate(total=Sum('amount_paid'))['total'] or 0,
        'total_fines': payments.aggregate(total=Sum('fine_amount'))['total'] or 0,
        'on_time_count': on_time_count,
        'late_count': late_count,
        'on_time_percentage': on_time_percentage,
        'late_percentage': late_percentage,  # Add this
        'payments': payments,
        'period_start': start_date,
        'period_end': end_date,
    }
    
    return summary


def get_outstanding_payments(month):
    """Get list of members who haven't paid for a specific month"""
    paid_member_ids = Payment.objects.filter(month=month).values_list('member_id', flat=True)
    outstanding_members = Member.objects.filter(
        is_active=True
    ).exclude(
        id__in=paid_member_ids
    ).select_related('user').order_by('user__first_name')
    
    paid_count = Payment.objects.filter(month=month).count()
    total_members = Member.objects.filter(is_active=True).count()
    outstanding_count = outstanding_members.count()
    
    # Calculate collection rate
    if total_members > 0:
        collection_rate = (paid_count / total_members) * 100
    else:
        collection_rate = 0
    
    return {
        'month': month,
        'outstanding_members': outstanding_members,
        'count': outstanding_count,
        'paid_count': paid_count,  # Add this
        'total_members': total_members,  # Add this
        'collection_rate': collection_rate,  # Add this
        'total_amount': outstanding_count * 2500,  # Monthly contribution
    }


def get_fines_summary(start_date=None, end_date=None, group_by_month=True):
    """Get fines summary with optional grouping"""
    payments = Payment.objects.filter(fine_amount__gt=0).select_related('member__user', 'month')
    
    if start_date:
        payments = payments.filter(month__month__gte=start_date)
    if end_date:
        payments = payments.filter(month__month__lte=end_date)
    
    total_fines = payments.aggregate(total=Sum('fine_amount'))['total'] or 0
    total_fine_payments = payments.count()
    
    if group_by_month:
        # Group fines by month
        monthly_fines = payments.values(
            'month__month', 
            'month__month__year', 
            'month__month__month'
        ).annotate(
            total_fines=Sum('fine_amount'),
            count=Count('id'),
            avg_fine=Avg('fine_amount')
        ).order_by('-month__month')
        
        return {
            'total_fines': total_fines,
            'total_fine_payments': total_fine_payments,
            'monthly_fines': monthly_fines,
            'payments': payments.order_by('-month__month'),
            'average_fine': total_fines / total_fine_payments if total_fine_payments > 0 else 0,
            'start_date': start_date,
            'end_date': end_date,
        }
    else:
        return {
            'total_fines': total_fines,
            'total_fine_payments': total_fine_payments,
            'payments': payments.order_by('-month__month'),
            'average_fine': total_fines / total_fine_payments if total_fine_payments > 0 else 0,
            'start_date': start_date,
            'end_date': end_date,
        }
# Main views
@staff_member_required
def reports_dashboard(request):
    """Main reports dashboard"""
    # Get some quick stats for the dashboard
    current_month = timezone.now().date().replace(day=1)
    
    try:
        current_contribution_month = ContributionMonth.objects.get(month=current_month)
        current_stats = calculate_monthly_stats(current_contribution_month)
    except ContributionMonth.DoesNotExist:
        current_stats = None
    
    # Recent report logs
    recent_reports = ReportLog.objects.filter(
        generated_by=request.user
    ).order_by('-generated_at')[:5]
    
    context = {
        'current_stats': current_stats,
        'recent_reports': recent_reports,
        'total_members': Member.objects.filter(is_active=True).count(),
        'total_payments': Payment.objects.count(),
        'total_fines_collected': Payment.objects.aggregate(total=Sum('fine_amount'))['total'] or 0,
    }
    
    return render(request, 'reports/dashboard.html', context)


@staff_member_required
def monthly_collection_report(request):
    """Generate monthly collection report"""
    if request.method == 'POST':
        form = MonthlyReportForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data['month']
            include_pending = form.cleaned_data['include_pending']
            show_fine_details = form.cleaned_data['show_fine_details']
            format_type = form.cleaned_data['format']
            
            # Get statistics for the month
            stats = calculate_monthly_stats(month)
            
            # Log the report generation
            ReportLog.objects.create(
                report_type='monthly',
                format=format_type,
                generated_by=request.user,
                parameters={
                    'month': month.id,
                    'month_name': str(month),
                    'include_pending': include_pending,
                    'show_fine_details': show_fine_details,
                }
            )
            
            # Prepare context
            context = {
                'stats': stats,
                'month': month,
                'include_pending': include_pending,
                'show_fine_details': show_fine_details,
                'generated_at': timezone.now(),
                'generated_by': request.user,
                'report_title': f'Monthly Collection Report - {month.month.strftime("%B %Y")}',
            }
            
            # Handle different formats
            if format_type == 'pdf':
                return generate_pdf_report('reports/monthly_pdf.html', context, f'monthly_report_{month.month.strftime("%Y_%m")}')
            elif format_type == 'excel':
                return generate_excel_monthly_report(stats, month)
            else:
                # HTML format - render template
                return render(request, 'reports/monthly_report.html', context)
    else:
        form = MonthlyReportForm()
    
    # Get recent months for quick links
    recent_months = ContributionMonth.objects.all().order_by('-month')[:6]
    
    context = {
        'form': form,
        'recent_months': recent_months,
        'report_type': 'Monthly Collection',
    }
    return render(request, 'reports/report_form.html', context)


@staff_member_required
def member_statement(request):
    """Generate member statement report"""
    if request.method == 'POST':
        form = MemberStatementForm(request.POST)
        if form.is_valid():
            member = form.cleaned_data['member']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            include_summary = form.cleaned_data['include_summary']
            format_type = form.cleaned_data['format']
            
            # Get member statement
            statement = get_member_statement(member, start_date, end_date)
            
            # Log the report generation
            ReportLog.objects.create(
                report_type='member',
                format=format_type,
                generated_by=request.user,
                parameters={
                    'member_id': member.id,
                    'member_name': str(member),
                    'start_date': str(start_date) if start_date else None,
                    'end_date': str(end_date) if end_date else None,
                }
            )
            
            # Prepare context
            context = {
                'statement': statement,
                'member': member,
                'start_date': start_date,
                'end_date': end_date,
                'include_summary': include_summary,
                'generated_at': timezone.now(),
                'generated_by': request.user,
                'report_title': f'Member Statement - {member.user.get_full_name()}',
            }
            
            # Handle different formats
            if format_type == 'pdf':
                return generate_pdf_report('reports/member_pdf.html', context, f'member_statement_{member.id}_{datetime.now().strftime("%Y%m%d")}')
            elif format_type == 'excel':
                return generate_excel_member_report(statement, member)
            else:
                # HTML format - render template
                return render(request, 'reports/member_statement.html', context)
    else:
        form = MemberStatementForm()
    
    # Get active members for quick links
    active_members = Member.objects.filter(is_active=True).select_related('user').order_by('user__first_name')[:10]
    
    context = {
        'form': form,
        'active_members': active_members,
        'report_type': 'Member Statement',
    }
    return render(request, 'reports/report_form.html', context)


@staff_member_required
def outstanding_payments_report(request):
    """Generate outstanding payments report"""
    if request.method == 'POST':
        form = OutstandingPaymentsForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data['month']
            send_reminders = form.cleaned_data['send_reminders']
            format_type = form.cleaned_data['format']
            
            # Get outstanding payments
            outstanding_data = get_outstanding_payments(month)
            
            # Log the report generation
            ReportLog.objects.create(
                report_type='outstanding',
                format=format_type,
                generated_by=request.user,
                parameters={
                    'month': month.id,
                    'month_name': str(month),
                    'send_reminders': send_reminders,
                }
            )
            
            # Send reminders if requested
            if send_reminders:
                # This would integrate with your notification system
                messages.info(request, f'Reminder notes prepared for {outstanding_data["count"]} members.')
            
            # Prepare context
            context = {
                'outstanding_data': outstanding_data,
                'month': month,
                'send_reminders': send_reminders,
                'generated_at': timezone.now(),
                'generated_by': request.user,
                'report_title': f'Outstanding Payments - {month.month.strftime("%B %Y")}',
            }
            
            # Handle different formats
            if format_type == 'pdf':
                return generate_pdf_report('reports/outstanding_pdf.html', context, f'outstanding_payments_{month.month.strftime("%Y_%m")}')
            elif format_type == 'excel':
                return generate_excel_outstanding_report(outstanding_data, month)
            else:
                # HTML format - render template
                return render(request, 'reports/outstanding_payments.html', context)
    else:
        form = OutstandingPaymentsForm()
    
    # Get current month for default
    current_month = timezone.now().date().replace(day=1)
    try:
        default_month = ContributionMonth.objects.get(month=current_month)
    except ContributionMonth.DoesNotExist:
        default_month = None
    
    context = {
        'form': form,
        'default_month': default_month,
        'report_type': 'Outstanding Payments',
    }
    return render(request, 'reports/report_form.html', context)


@staff_member_required
def fines_summary_report(request):
    """Generate fines summary report"""
    if request.method == 'POST':
        form = FinesReportForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            group_by_month = form.cleaned_data['group_by_month']
            format_type = form.cleaned_data['format']
            
            # Get fines summary
            fines_data = get_fines_summary(start_date, end_date, group_by_month)
            
            # Log the report generation
            ReportLog.objects.create(
                report_type='fines',
                format=format_type,
                generated_by=request.user,
                parameters={
                    'start_date': str(start_date) if start_date else None,
                    'end_date': str(end_date) if end_date else None,
                    'group_by_month': group_by_month,
                }
            )
            
            # Prepare context
            context = {
                'fines_data': fines_data,
                'start_date': start_date,
                'end_date': end_date,
                'group_by_month': group_by_month,
                'generated_at': timezone.now(),
                'generated_by': request.user,
                'report_title': 'Fines Summary Report',
            }
            
            if start_date and end_date:
                context['report_title'] = f'Fines Summary ({start_date.strftime("%d/%m/%Y")} to {end_date.strftime("%d/%m/%Y")})'
            
            # Handle different formats
            if format_type == 'pdf':
                return generate_pdf_report('reports/fines_pdf.html', context, f'fines_summary_{datetime.now().strftime("%Y%m%d")}')
            elif format_type == 'excel':
                return generate_excel_fines_report(fines_data)
            else:
                # HTML format - render template
                return render(request, 'reports/fines_summary.html', context)
    else:
        # Set default dates (last 6 months)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=180)
        
        form = FinesReportForm(initial={
            'start_date': start_date,
            'end_date': end_date,
            'group_by_month': True,
        })
    
    context = {
        'form': form,
        'report_type': 'Fines Summary',
    }
    return render(request, 'reports/report_form.html', context)


@staff_member_required
def report_history(request):
    """View report generation history"""
    reports = ReportLog.objects.filter(generated_by=request.user).order_by('-generated_at')
    
    # Stats
    total_reports = reports.count()
    reports_today = reports.filter(generated_at__date=timezone.now().date()).count()
    
    context = {
        'reports': reports,
        'total_reports': total_reports,
        'reports_today': reports_today,
    }
    
    return render(request, 'reports/history.html', context)


# Export functions (simplified versions - you'll need to implement full versions)
def generate_pdf_report(template_name, context, filename):
    """Generate PDF report - placeholder function"""
    # You'll need to install reportlab or weasyprint for this
    messages.warning(request, 'PDF export is not yet implemented. Please use HTML or Excel format.')
    return redirect('reports:dashboard')


def generate_excel_monthly_report(stats, month):
    """Generate Excel monthly report - placeholder function"""
    # You'll need to install pandas/openpyxl for this
    messages.warning(request, 'Excel export is not yet implemented. Please use HTML format.')
    return redirect('reports:monthly_report')


def generate_excel_member_report(statement, member):
    """Generate Excel member report - placeholder function"""
    messages.warning(request, 'Excel export is not yet implemented. Please use HTML format.')
    return redirect('reports:member_statement')


def generate_excel_outstanding_report(outstanding_data, month):
    """Generate Excel outstanding report - placeholder function"""
    messages.warning(request, 'Excel export is not yet implemented. Please use HTML format.')
    return redirect('reports:outstanding_payments')


def generate_excel_fines_report(fines_data):
    """Generate Excel fines report - placeholder function"""
    messages.warning(request, 'Excel export is not yet implemented. Please use HTML format.')
    return redirect('reports:fines_summary')


@staff_member_required
def quick_monthly_report(request, month_id):
    """Quick access to monthly report for a specific month"""
    month = get_object_or_404(ContributionMonth, id=month_id)
    stats = calculate_monthly_stats(month)
    
    context = {
        'stats': stats,
        'month': month,
        'include_pending': True,
        'show_fine_details': True,
        'generated_at': timezone.now(),
        'generated_by': request.user,
        'report_title': f'Monthly Collection Report - {month.month.strftime("%B %Y")}',
        'is_quick_view': True,
    }
    
    return render(request, 'reports/monthly_report.html', context)


@staff_member_required 
def quick_member_statement(request, member_id):
    """Quick access to member statement"""
    member = get_object_or_404(Member, id=member_id)
    statement = get_member_statement(member)
    
    context = {
        'statement': statement,
        'member': member,
        'include_summary': True,
        'generated_at': timezone.now(),
        'generated_by': request.user,
        'report_title': f'Member Statement - {member.user.get_full_name()}',
        'is_quick_view': True,
    }
    
    return render(request, 'reports/member_statement.html', context)
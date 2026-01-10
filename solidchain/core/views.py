
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from datetime import date
from .models import Member, Payment, ContributionMonth
from django.template.defaulttags import register
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout as auth_logout
from django.contrib.admin.views.decorators import staff_member_required
from django import forms
from .forms import PaymentEntryForm
from django.db import models
from django.http import JsonResponse
@csrf_exempt
@register.filter
def filter_by_status(payments, status):
    return [p for p in payments if p.status == status]

@csrf_exempt
@login_required
def profile_view(request):
    """
    Member profile view
    """
    member = request.user.member
    
    # Get statistics from payments
    payments = Payment.objects.filter(member=member)
    total_payments = payments.count()
    on_time_count = payments.filter(status='On Time').count()
    late_count = total_payments - on_time_count
    print(total_payments)
    # Calculate on-time percentage
    if total_payments > 0:
        on_time_percentage = (on_time_count / total_payments) * 100
    else:
        on_time_percentage = 0
    if on_time_percentage:
        print(on_time_percentage)
    else:
        print("No payments yet")
    context = {
        'member': member,
        'total_payments': total_payments,
        'on_time_count': on_time_count,
        'late_count': late_count,
        'on_time_percentage': on_time_percentage, 
        'member_since': member.joined_date.strftime('%B %Y'),
    }
    
    return render(request, 'core/profile.html', context)

@csrf_exempt
def custom_logout(request):
    """
    Custom logout with message
    """
    # Store message before logout
    messages.success(request, 'You have been logged out successfully.')
    
    # Perform logout
    auth_logout(request)
    
    # Redirect to login page
    return redirect('userauths:login')



@login_required
def dashboard(request):
    """
    Member's main dashboard - shows current status and recent payments
    """
    try:
        member = request.user.member
    except Member.DoesNotExist:
        messages.error(request, "Please complete your member profile.")
        return redirect('admin:index')
    
    # Get current month
    today = timezone.now().date()
    current_month = today.replace(day=1)
    
    # Try to get current month's payment
    current_payment = None
    try:
        current_contribution_month = ContributionMonth.objects.get(month=current_month)
        current_payment = Payment.objects.filter(
            member=member,
            month=current_contribution_month
        ).first()
    except ContributionMonth.DoesNotExist:
        current_contribution_month = None
    
    # Get recent payments (last 5)
    recent_payments = Payment.objects.filter(
        member=member
    ).select_related('month').order_by('-month__month')[:5]
    
    # Calculate totals
    all_payments = Payment.objects.filter(member=member)
    total_contributions = sum(p.amount_paid for p in all_payments)
    total_fines = sum(p.fine_amount for p in all_payments)
    
    # Count on-time vs late payments
    total_count = all_payments.count()
    on_time_count = all_payments.filter(status='On Time').count()
    late_count = all_payments.filter(status='Late').count()
    
    # Calculate percentage
    if total_count > 0:
        on_time_percentage = (on_time_count / total_count) * 100
    else:
        on_time_percentage = 0
    
    context = {
        'member': member,
        'current_payment': current_payment,
        'current_month': current_month.strftime('%B %Y'),
        'recent_payments': recent_payments,
        'total_contributions': total_contributions,
        'total_fines': total_fines,
        'total_payments': total_count,  
        'on_time_count': on_time_count,
        'late_count': late_count,
        'on_time_percentage': on_time_percentage,  
        'today': today,
    }
    
    return render(request, 'core/dashboard.html', context)

@csrf_exempt
@login_required
def contribution_history(request):
    """
    View all contributions with optional filtering
    """
    member = request.user.member
    
    # Get all payments
    payments = Payment.objects.filter(member=member).select_related('month').order_by('-month__month')
    
    # Calculate totals
    total_amount = sum(p.amount_paid for p in payments)
    total_fines = sum(p.fine_amount for p in payments)
    
    # Count statistics
    total_count = payments.count()
    on_time_count = payments.filter(status='On Time').count()
    late_count = payments.filter(status='Late').count()
    
    context = {
        'member': member,
        'payments': payments,
        'total_amount': total_amount,
        'total_fines': total_fines,
        'total_count': total_count,
        'on_time_count': on_time_count,
        'late_count': late_count,
        'on_time_percentage': (on_time_count / total_count * 100) if total_count > 0 else 0,
    }
    
    return render(request, 'core/history.html', context)

@csrf_exempt
@staff_member_required
def payment_entry(request):
    """
    Treasurer-only view to record payments
    """
    if request.method == 'POST':
        form = PaymentEntryForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.recorded_by = request.user
            payment.save()
            
            messages.success(
                request, 
                f"Payment recorded for {payment.member.user.get_full_name()} - {payment.month}"
            )
            return redirect('core:payment_entry')
    else:
        form = PaymentEntryForm()
    
    # Get recent payments for context
    recent_payments = Payment.objects.select_related(
        'member__user', 'month'
    ).order_by('-recorded_at')[:10]
    
    context = {
        'form': form,
        'recent_payments': recent_payments,
    }
    return render(request, 'core/payment_entry.html', context)

@staff_member_required 
@csrf_exempt
def treasurer_dashboard(request):
    """
    Treasurer overview dashboard
    """
    # Get current month
    today = timezone.now().date()
    current_month = today.replace(day=1)
    
    try:
        current_contribution_month = ContributionMonth.objects.get(month=current_month)
    except ContributionMonth.DoesNotExist:
        current_contribution_month = None
    
    # Get statistics
    total_members = Member.objects.filter(is_active=True).count()
    total_payments = Payment.objects.count()
    
    # Current month stats
    if current_contribution_month:
        current_payments = Payment.objects.filter(month=current_contribution_month)
        paid_count = current_payments.count()
        pending_count = total_members - paid_count
        current_fines = current_payments.aggregate(total=models.Sum('fine_amount'))['total'] or 0
    else:
        paid_count = 0
        pending_count = total_members
        current_fines = 0
    
    context = {
        'total_members': total_members,
        'total_payments': total_payments,
        'current_month': current_month.strftime('%B %Y'),
        'paid_count': paid_count,
        'pending_count': pending_count,
        'current_fines': current_fines,
        'collection_rate': (paid_count / total_members * 100) if total_members > 0 else 0,
    }
    
    return render(request, 'core/treasurer_dashboard.html', context)

@csrf_exempt
def get_month_due_date(request, month_id):
    """
    API endpoint to get due date for a month
    """
    month = get_object_or_404(ContributionMonth, id=month_id)
    
    return JsonResponse({
        'due_date': month.due_date.isoformat(),
        'month_name': month.month.strftime("%B %Y"),
    })    
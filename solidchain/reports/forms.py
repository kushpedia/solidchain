from django import forms
from django.utils import timezone
from datetime import datetime
from core.models import ContributionMonth, Member

class MonthlyReportForm(forms.Form):
    """Form for generating monthly reports"""
    month = forms.ModelChoiceField(
        queryset=ContributionMonth.objects.all().order_by('-month'),
        label="Select Month",
        empty_label="Select a month",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    include_pending = forms.BooleanField(
        required=False,
        initial=True,
        label="Include Pending Members",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    show_fine_details = forms.BooleanField(
        required=False,
        initial=True,
        label="Show Fine Details",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    format = forms.ChoiceField(
        choices=[('html', 'HTML'), ('pdf', 'PDF'), ('excel', 'Excel')],
        initial='html',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )


class MemberStatementForm(forms.Form):
    """Form for generating member statements"""
    member = forms.ModelChoiceField(
        queryset=Member.objects.filter(is_active=True).order_by('user__first_name'),
        label="Select Member",
        empty_label="Select a member",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    start_date = forms.DateField(
        label="Start Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    end_date = forms.DateField(
        label="End Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    include_summary = forms.BooleanField(
        required=False,
        initial=True,
        label="Include Summary",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    format = forms.ChoiceField(
        choices=[('html', 'HTML'), ('pdf', 'PDF'), ('excel', 'Excel')],
        initial='html',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )


class OutstandingPaymentsForm(forms.Form):
    """Form for outstanding payments report"""
    month = forms.ModelChoiceField(
        queryset=ContributionMonth.objects.all().order_by('-month'),
        label="Select Month",
        empty_label="Select a month",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    send_reminders = forms.BooleanField(
        required=False,
        initial=False,
        label="Send Reminder Notes",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    format = forms.ChoiceField(
        choices=[('html', 'HTML'), ('pdf', 'PDF'), ('excel', 'Excel')],
        initial='html',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )


class FinesReportForm(forms.Form):
    """Form for fines summary report"""
    start_date = forms.DateField(
        label="Start Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    end_date = forms.DateField(
        label="End Date",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    group_by_month = forms.BooleanField(
        required=False,
        initial=True,
        label="Group by Month",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    format = forms.ChoiceField(
        choices=[('html', 'HTML'), ('pdf', 'PDF'), ('excel', 'Excel')],
        initial='html',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
# core/forms.py
from django import forms
from .models import Payment, Member, ContributionMonth
from django.utils import timezone

class PaymentEntryForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['member', 'month', 'amount_paid', 'paid_date']
        widgets = {
            'paid_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'value': 2500}),
            'member': forms.Select(attrs={'class': 'form-control'}),
            'month': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active members
        self.fields['member'].queryset = Member.objects.filter(is_active=True)
        # Only show unlocked months
        self.fields['month'].queryset = ContributionMonth.objects.filter(is_locked=False)
        
        # Set default paid date to today
        if not self.instance.pk:
            self.fields['paid_date'].initial = timezone.now().date()
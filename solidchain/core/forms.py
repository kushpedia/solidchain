# core/forms.py
from django import forms
from .models import Payment, Member, ContributionMonth
from django.utils import timezone

class PaymentEntryForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['member', 'month', 'amount_paid', 'paid_date']
        widgets = {
            'paid_date': forms.DateInput(
                attrs={
                    'type': 'date', 
                    'class': 'form-control',
                    'max': timezone.now().date().isoformat()  # Prevent future dates
                }
            ),
            'amount_paid': forms.NumberInput(
                attrs={
                    'class': 'form-control', 
                    'value': 2500,
                    'min': 0  # Prevent negative amounts
                }
            ),
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
    
    def clean(self):
        cleaned_data = super().clean()
        member = cleaned_data.get('member')
        month = cleaned_data.get('month')
        paid_date = cleaned_data.get('paid_date')
        
        # Check for duplicate payment
        if member and month:
            duplicate = Payment.objects.filter(member=member, month=month)
            if self.instance.pk:  # Exclude current instance when editing
                duplicate = duplicate.exclude(pk=self.instance.pk)
            
            if duplicate.exists():
                raise forms.ValidationError(
                    f"{member} already has a payment recorded for {month}"
                )
        
        # Validate paid_date is not before the contribution month
        if month and paid_date:
            if paid_date < month.month:  # month.month is the DateField
                raise forms.ValidationError(
                    f"Payment date cannot be before the contribution month ({month.month.strftime('%B %Y')})"
                )
        
        return cleaned_data
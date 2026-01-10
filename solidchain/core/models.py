from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date  # Add this import

class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='member')
    phone = models.CharField(max_length=15)
    joined_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['user__first_name']
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username

class ContributionMonth(models.Model):
    month = models.DateField()  # First day of month
    due_date = models.DateField()  # 5th of same month
    is_locked = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-month']
        unique_together = ['month']
    
    def __str__(self):
        return self.month.strftime("%B %Y")
    
    def save(self, *args, **kwargs):
        # Auto-set due_date to 5th of the month if not provided
        if not self.due_date:
            self.due_date = self.month.replace(day=5)
        super().save(*args, **kwargs)

class Payment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('On Time', 'On Time'),
        ('Late', 'Late'),
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='payments')
    month = models.ForeignKey(ContributionMonth, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=2500)
    paid_date = models.DateField()
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['member', 'month']
        ordering = ['-month', 'member']
    
    def __str__(self):
        return f"{self.member} - {self.month}"
    
    def calculate_fine(self):
        """
        Calculate fine based on payment date vs due date
        Rules:
        - 6th-10th: KSh 100 per day (days 1-5 late)
        - 11th to next month 5th: KSh 15 per day (days 6+ late)
        - Stops fining on 5th of following month
        """
        due_date = self.month.due_date
        days_late = (self.paid_date - due_date).days
        
        if days_late <= 0:
            return 0  # No fine if paid on or before due date
        
        # Calculate next month's 5th (when fines stop)
        # Get the month after the payment month
        month_year = self.month.month.year
        month_month = self.month.month.month
        
        if month_month == 12:  # December
            next_month_year = month_year + 1
            next_month_month = 1  # January
        else:
            next_month_year = month_year
            next_month_month = month_month + 1
        
        next_month_5th = date(next_month_year, next_month_month, 5)
        
        # If paid after next month's 5th, calculate only up to next month's 5th
        if self.paid_date > next_month_5th:
            days_late = (next_month_5th - due_date).days
        
        # Now calculate fine based on corrected days_late
        if days_late <= 5:
            # Days 1-5 late (6th-10th of month): 100 per day
            return days_late * 100
        else:
            # Days 6+ late (11th+ of month): 500 for first 5 days + 25 for each additional day
            return (5 * 100) + ((days_late - 5) * 25)
    
    def determine_status(self):
        """Determine if payment is On Time or Late"""
        due_date = self.month.due_date
        days_late = (self.paid_date - due_date).days
        
        if days_late <= 0:
            return 'On Time'
        else:
            return 'Late'
    
    def save(self, *args, **kwargs):
        """
        Automatically calculate fine and status before saving
        """
        # Calculate fine if paid_date is set
        if self.paid_date:
            self.fine_amount = self.calculate_fine()
            self.status = self.determine_status()
        
        super().save(*args, **kwargs)


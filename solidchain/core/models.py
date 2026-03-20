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
    # Auto-set due_date to 5th of the FOLLOWING month if not provided
        if not self.due_date:
            # Get the month after self.month
            month_year = self.month.year
            month_month = self.month.month
            
            if month_month == 12:  # December
                due_year = month_year + 1
                due_month = 1  # January
            else:
                due_year = month_year
                due_month = month_month + 1
            
            # Set due_date to 5th of the following month
            self.due_date = date(due_year, due_month, 5)
        
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
        - Fine starts the day after due date (due date is 5th of following month)
        - Days 1-5 late: KSh 100 per day
        - Days 6+ late: KSh 25 per day
        - Stops fining on 5th of month after due date month
        """
        due_date = self.month.due_date  # Should be 5th of following month
        days_late = (self.paid_date - due_date).days
        
        if days_late <= 0:
            return 0  # No fine if paid on or before due date
        
        # Calculate stop date (5th of month after due date month)
        due_year = due_date.year
        due_month = due_date.month
        
        # Get month after due date month
        if due_month == 12:  # December
            stop_year = due_year + 1
            stop_month = 1  # January
        else:
            stop_year = due_year
            stop_month = due_month + 1
        
        stop_date = date(stop_year, stop_month, 5)  # 5th of month after due date
        
        # If paid after stop date, calculate only up to stop date
        if self.paid_date > stop_date:
            days_late = (stop_date - due_date).days
        
        # Calculate fine based on days_late
        if days_late <= 5:
            # Days 1-5 late: 100 per day
            return days_late * 100
        else:
            # Days 6+ late: 500 for first 5 days + 25 for each additional day
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


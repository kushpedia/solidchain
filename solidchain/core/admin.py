from django.contrib import admin

from .models import Member, ContributionMonth, Payment


admin.site.register(Member)
admin.site.register(ContributionMonth)
admin.site.register(Payment)
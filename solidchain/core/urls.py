# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('history/', views.contribution_history, name='history'),
    path('profile/', views.profile_view, name='profile'),
	path('logout/', views.custom_logout, name='logout'),
	
    # Treasurer/admin routes
    path('treasurer/', views.treasurer_dashboard, name='treasurer_dashboard'),
    path('treasurer/payment-entry/', views.payment_entry, name='payment_entry'),
	path('api/month/<int:month_id>/due-date/', views.get_month_due_date, name='month_due_date'),
]

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'userauths'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='userauths:login'), name='logout'),
]
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='core:dashboard', permanent=False)),
    path('dashboard/', include('core.urls')),
    path('auth/', include('userauths.urls')),
	path('reports/', include('reports.urls')),
]
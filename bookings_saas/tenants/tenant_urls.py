"""
Montado en: /api/tenants/
"""
from django.urls import path
from . import views

urlpatterns = [
    path('me/',                 views.TenantMeView.as_view(), name='tenant-me'),
    path('<slug:slug>/public/', views.tenant_public,          name='tenant-public'),
]

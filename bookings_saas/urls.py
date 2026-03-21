from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from bookings_saas.tenants import admin_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Auth ──────────────────────────────────────────────
    path('api/auth/', include('bookings_saas.tenants.urls')),

    # ── Tenant ────────────────────────────────────────────
    path('api/tenants/', include('bookings_saas.tenants.tenant_urls')),

    # ── Recursos ─────────────────────────────────────────
    path('api/services/',   include('bookings_saas.services.urls')),
    path('api/staff/',      include('bookings_saas.services.staff_urls')),
    path('api/scheduling/', include('bookings_saas.scheduling.urls')),
    path('api/bookings/',   include('bookings_saas.bookings.urls')),

    # ── Super Admin ───────────────────────────────────────
    path('api/admin/stats/',                     admin_views.admin_stats,          name='admin-stats'),
    path('api/admin/tenants/',                   admin_views.admin_tenants,        name='admin-tenants'),
    path('api/admin/tenants/<uuid:tenant_id>/toggle/', admin_views.admin_tenant_toggle, name='admin-tenant-toggle'),
    path('api/admin/tenants/<uuid:tenant_id>/',  admin_views.admin_tenant_delete,  name='admin-tenant-delete'),
    path('api/admin/bookings/',                  admin_views.admin_bookings,       name='admin-bookings'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

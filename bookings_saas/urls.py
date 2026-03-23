from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from bookings_saas.tenants import admin_views
from bookings_saas.scheduling.views import public_blocked_days
from bookings_saas.bookings import rating_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Auth ──────────────────────────────────────────────
    path('api/auth/', include('bookings_saas.tenants.urls')),

    # ── Tenant ────────────────────────────────────────────
    path('api/tenants/', include('bookings_saas.tenants.tenant_urls')),

    # ── Tenant público: días bloqueados ───────────────────
    path('api/tenants/<slug:slug>/blocked-days/', public_blocked_days, name='public-blocked-days'),

    # ── Tenant público: rating ────────────────────────────
    path('api/tenants/<slug:slug>/rating/', rating_views.tenant_rating, name='tenant-rating'),

    # ── Valoraciones (público) ────────────────────────────
    path('api/ratings/', rating_views.create_rating, name='create-rating'),

    # ── Recursos ─────────────────────────────────────────
    path('api/services/',   include('bookings_saas.services.urls')),
    path('api/staff/',      include('bookings_saas.services.staff_urls')),
    path('api/scheduling/', include('bookings_saas.scheduling.urls')),
    path('api/bookings/',   include('bookings_saas.bookings.urls')),

    # ── Super Admin ───────────────────────────────────────
    path('api/admin/stats/',                                    admin_views.admin_stats,             name='admin-stats'),
    path('api/admin/tenants/',                                  admin_views.admin_tenants,           name='admin-tenants'),
    path('api/admin/tenants/<uuid:tenant_id>/toggle/',          admin_views.admin_tenant_toggle,     name='admin-tenant-toggle'),
    path('api/admin/tenants/<uuid:tenant_id>/extend/',          admin_views.admin_tenant_extend,     name='admin-tenant-extend'),
    path('api/admin/tenants/<uuid:tenant_id>/detail/',          admin_views.admin_tenant_detail,     name='admin-tenant-detail'),
    path('api/admin/tenants/<uuid:tenant_id>/notes/',           admin_views.admin_tenant_add_note,   name='admin-tenant-notes'),
    path('api/admin/tenants/<uuid:tenant_id>/',                 admin_views.admin_tenant_delete,     name='admin-tenant-delete'),
    path('api/admin/payments/summary/',                         admin_views.admin_payments_summary,  name='admin-payments-summary'),
    path('api/admin/payments/<int:payment_id>/',                admin_views.admin_payment_delete,    name='admin-payment-delete'),
    path('api/admin/payments/',                                 admin_views.admin_payments,          name='admin-payments'),
    path('api/admin/notes/<int:note_id>/',                      admin_views.admin_note_delete,       name='admin-note-delete'),
    path('api/admin/bookings/',                                 admin_views.admin_bookings,          name='admin-bookings'),
    path('api/admin/config/',                                   admin_views.admin_config,            name='admin-config'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

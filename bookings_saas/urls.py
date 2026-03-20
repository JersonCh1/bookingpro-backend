from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

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

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

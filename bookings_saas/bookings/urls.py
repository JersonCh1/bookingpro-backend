from django.urls import path
from . import views, rating_views

# Montado en /api/bookings/
urlpatterns = [
    # POST (público, sin auth) + GET (dashboard, con auth)
    path('',                             views.BookingListCreateView.as_view(), name='booking-list-create'),

    # Dashboard (autenticado)
    path('<uuid:pk>/',                   views.BookingDetailView.as_view(),     name='booking-detail'),
    path('<uuid:pk>/status/',            views.booking_status,                  name='booking-status'),
    path('today/',                       views.bookings_today,                  name='booking-today'),
    path('stats/',                       views.bookings_stats,                  name='booking-stats'),
    path('customers/',                   views.customers_list,                  name='customers-list'),
    path('analytics/',                   views.bookings_analytics,              name='booking-analytics'),

    # Público — portal del cliente
    path('by-phone/',                    views.bookings_by_phone,               name='bookings-by-phone'),
    path('<uuid:pk>/cancel-by-phone/',   views.cancel_by_phone,                 name='cancel-by-phone'),
    path('cancel-token/<str:token>/',    views.booking_by_cancel_token,         name='booking-by-token'),

    # Valoraciones (dashboard)
    path('ratings/mine/',                rating_views.my_tenant_rating,         name='ratings-mine'),
]

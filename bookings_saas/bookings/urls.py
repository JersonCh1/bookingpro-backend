from django.urls import path
from . import views

# Montado en /api/bookings/
urlpatterns = [
    # POST (público, sin auth) + GET (dashboard, con auth)
    path('',                  views.BookingListCreateView.as_view(), name='booking-list-create'),

    # Dashboard
    path('<uuid:pk>/',        views.BookingDetailView.as_view(),     name='booking-detail'),
    path('<uuid:pk>/status/', views.booking_status,                  name='booking-status'),
    path('today/',            views.bookings_today,                  name='booking-today'),
    path('stats/',            views.bookings_stats,                  name='booking-stats'),
    path('customers/',        views.customers_list,                  name='customers-list'),
]

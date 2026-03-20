from django.urls import path
from . import views

# Montado en /api/staff/
urlpatterns = [
    path('',                        views.StaffListCreateView.as_view(), name='staff-list'),
    path('<int:pk>/',               views.StaffDetailView.as_view(),     name='staff-detail'),
    path('public/<slug:slug>/',     views.public_staff,                  name='staff-public'),
]

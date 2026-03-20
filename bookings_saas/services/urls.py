from django.urls import path
from . import views

# Montado en /api/services/
urlpatterns = [
    path('',                        views.ServiceListCreateView.as_view(), name='service-list'),
    path('<int:pk>/',               views.ServiceDetailView.as_view(),     name='service-detail'),
    path('public/<slug:slug>/',     views.public_services,                 name='service-public'),
]

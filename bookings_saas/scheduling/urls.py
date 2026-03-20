from django.urls import path
from . import views

# Montado en /api/scheduling/
urlpatterns = [
    # Horarios semanales
    path('',              views.ScheduleListCreateView.as_view(), name='schedule-list'),
    path('<int:pk>/',     views.ScheduleDetailView.as_view(),     name='schedule-detail'),

    # Slots bloqueados
    path('blocked/',          views.BlockedSlotListCreateView.as_view(), name='blocked-list'),
    path('blocked/<int:pk>/', views.BlockedSlotDetailView.as_view(),     name='blocked-detail'),

    # Disponibilidad (público)
    path('available-slots/', views.available_slots, name='available-slots'),
    path('available-days/',  views.available_days,  name='available-days'),
]

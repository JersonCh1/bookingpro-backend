"""
Montado en: /api/auth/
"""
from django.urls import path
from . import views

urlpatterns = [
    path('register/',        views.register,         name='auth-register'),
    path('login/',           views.login,             name='auth-login'),
    path('logout/',          views.logout,            name='auth-logout'),
    path('me/',              views.me,                name='auth-me'),
    path('refresh/',         views.token_refresh,     name='auth-refresh'),
    path('change-password/', views.change_password,   name='auth-change-password'),
]

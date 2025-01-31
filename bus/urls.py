from django.urls import path
from . import views
urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('passenger/dashboard/', views.dashboard, name='passenger_dashboard'),
    path('administrator/dashboard/', views.dashboard, name='admin_dashboard'),
    path('',views.home, name='project-home'),
    path('book/<int:bus_number>/', views.book_bus, name='book_bus'),
    path('summary/', views.booking_summary, name='booking_summary'),
    path('edit-booking/<int:booking_id>/', views.edit_booking, name='edit_booking'),
    path('edit-bus/<int:bus_number>/', views.edit_bus, name='edit_bus'),
    path('bus-list/', views.admin_bus_list, name='bus_list'),
    path('about/', views.about, name='about'),
]
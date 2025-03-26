from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
#from allauth.socialaccount.providers.oauth2.views import OAuth2Callback, OAuth2Login
#from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter

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
    path('verify_bus_otp/', views.verif_bus_otp, name='verif_bus_otp'),
    path('verify_edit_booking_otp/', views.verif_bus_otp, name='edit_booking_otp'),
    path('export/', views.export_buses_to_excel, name='export_buses'),
    path('add-bus/', views.add_bus, name='add_bus'),
    path('delete-bus/<int:bus_number>/', views.delete_bus, name='delete_bus'),
    path('verify_delete_bus_otp/', views.verif_del_bus_otp, name='verify_del_bus_otp'),
    path('bookings/<int:bus_number>/', views.bus_bookings, name='bus_bookings'),
    path('add-route/', views.add_route, name='add_route'),
    path('add-stop/', views.add_stop, name='add_stop'),
    path('add-class/', views.add_class, name='add_class'),
    path('stops/',views.view_stops, name='view_stops'),
    path('add-seatclass/', views.add_seat_class, name='add_seat_class'),
    path('routes/', views.view_routes, name='view_routes'),
    path('ticket/<int:booking_id>/', views.display_ticket, name='ticket'),
#    path('accounts/google/login/callback/', views.CustomGoogleOAuth2CallbackView.as_view(), name='google_callback'),
#    path('accounts/google/login/callback/', OAuth2Callback.as_view(adapter=GoogleOAuth2Adapter), name='google_callback'),
#    path('accounts/google/login/', OAuth2Login.as_view(adapter=GoogleOAuth2Adapter), name='google_login'),'''
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


#from django.urls import path, include
#from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
#from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView
#from .views import CustomGoogleOAuth2CallbackView
#
#urlpatterns += [
#    path(
#        "accounts/google/login/",
#        OAuth2LoginView.as_view(adapter=GoogleOAuth2Adapter),
#        name="google_login",
#    ),
#    path(
#        "accounts/google/login/callback/",
#        CustomGoogleOAuth2CallbackView.as_view(),
#        name="google_callback",
#    ),
#]
from django.urls import path

from . import views


app_name = "resorts"

urlpatterns = [
    path("", views.tour_list, name="tour_list"),
    path("tours/<int:pk>/", views.tour_detail, name="tour_detail"),
    path("tours/<int:pk>/book/", views.booking_create, name="booking_create"),
    path("my/bookings/", views.my_bookings, name="my_bookings"),
    path("my/bookings/<int:pk>/edit/", views.booking_update, name="booking_update"),
    path("my/bookings/<int:pk>/delete/", views.booking_delete, name="booking_delete"),
    path("signup/", views.signup, name="signup"),
]


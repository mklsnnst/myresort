from django.urls import path

from . import views


app_name = "resorts"

urlpatterns = [
    path("", views.home, name="home"),
    path("tours/catalog/", views.tour_list, name="tour_list"),
    
    #path("tours/manage/", views.tour_manage_list, name="tour_manage_list"),
    path("tours/manage/create/", views.tour_create, name="tour_create"),
    path("tours/manage/<int:pk>/edit/", views.tour_update, name="tour_update"),
    path("tours/manage/<int:pk>/delete/", views.tour_delete, name="tour_delete"),
    path("tours/search/", views.tour_search, name="tour_search"),
    path("tours/popular/", views.tour_popular_list, name="tour_popular_list"),
    path("tours/soon/", views.tour_soon_list, name="tour_soon_list"),
    path("tours/upcoming/", views.tour_upcoming_list, name="tour_upcoming_list"),
    path("tours/<int:pk>/", views.tour_detail, name="tour_detail"),
    path("tours/<int:pk>/book/", views.booking_create, name="booking_create"),
    path("my/bookings/", views.my_bookings, name="my_bookings"),
    path("my/bookings/<int:pk>/edit/", views.booking_update, name="booking_update"),
    path("my/bookings/<int:pk>/delete/", views.booking_delete, name="booking_delete"),
    path("signup/", views.signup, name="signup"),
]


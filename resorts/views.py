from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BookingCreateForm, BookingUpdateForm, SignupForm
from .models import Booking, Tour


def tour_list(request):
    qs = (
        Tour.objects.upcoming()
        .filter(title__icontains=request.GET.get("q", "").strip()) 
        .filter(location__icontains=request.GET.get("location", "").strip())
    )

    difficulty = request.GET.get("difficulty", "").strip()
    if difficulty:
        qs = qs.filter(difficulty_level=difficulty)

    qs = qs.exclude(reviews__moderation_status="rejected")

    sort = request.GET.get("sort", "date")
    if sort == "price":
        qs = qs.order_by("price", "-start_date")
    else:
        qs = qs.order_by("-start_date", "-id")

    qs = qs.annotate(
        approved_reviews=Count(
            "reviews",
            filter=Q(reviews__moderation_status="approved"),
            distinct=True,
        )
    )

    paginator = Paginator(qs, 6)
    page = request.GET.get("page", 1)
    try:
        tours_page = paginator.page(page)
    except PageNotAnInteger:
        tours_page = paginator.page(1)
    except EmptyPage:
        tours_page = paginator.page(paginator.num_pages)

    return render(
        request,
        "resorts/tour_list.html",
        {
            "tours_page": tours_page,
            "difficulty_choices": Tour.DIFFICULTY_CHOICES,
            "now": timezone.now(),
            "today": timezone.localdate(),
        },
    )


def tour_detail(request, pk: int):
    tour = get_object_or_404(
        Tour.objects.prefetch_related("images", "services", "reviews__user"),
        pk=pk,
    )
    approved_reviews = tour.reviews.filter(moderation_status="approved").order_by("-created_at")

    # Агрегирование (пример): средняя оценка
    rating_avg = approved_reviews.aggregate(avg=Avg("rating")).get("avg")

    return render(
        request,
        "resorts/tour_detail.html",
        {
            "tour": tour,
            "approved_reviews": approved_reviews,
            "rating_avg": rating_avg,
        },
    )


@login_required
def booking_create(request, pk: int):
    tour = get_object_or_404(Tour, pk=pk)

    if request.method == "POST":
        form = BookingCreateForm(request.POST, tour=tour)
        if form.is_valid():
            booking: Booking = form.save(commit=False)
            booking.user = request.user
            booking.tour = tour
            booking.status = "new"
            booking.full_clean()
            booking.save()

            form.instance = booking
            form.save_m2m()

            return redirect("resorts:my_bookings")
    else:
        form = BookingCreateForm(tour=tour)

    return render(
        request,
        "resorts/booking_form.html",
        {"tour": tour, "form": form},
    )


@login_required
def my_bookings(request):
    bookings = (
        Booking.objects.filter(user=request.user)
       # .select_related("tour")
        .prefetch_related("booking_services__service")
        .order_by("-created_at")
    )
    return render(request, "resorts/my_bookings.html", {"bookings": bookings})


@login_required
def booking_update(request, pk: int):
    booking = get_object_or_404(
        Booking.objects.select_related("tour", "user").prefetch_related("booking_services__service"),
        pk=pk,
        user=request.user,
    )
    if booking.status == "cancelled":
        messages.error(request, "Нельзя редактировать отмененное бронирование.")
        return redirect("resorts:my_bookings")

    if request.method == "POST":
        form = BookingUpdateForm(request.POST, instance=booking, tour=booking.tour)
        if form.is_valid():
            updated_booking = form.save(commit=False)
            updated_booking.full_clean()
            updated_booking.save()
            form.instance = updated_booking
            form.save_m2m()
            messages.success(request, "Бронирование обновлено.")
            return redirect("resorts:my_bookings")
    else:
        selected_services = booking.booking_services.values_list("service_id", flat=True)
        form = BookingUpdateForm(
            instance=booking,
            tour=booking.tour,
            initial={"services": selected_services},
        )

    return render(
        request,
        "resorts/booking_form.html",
        {"tour": booking.tour, "form": form, "booking": booking},
    )


@login_required
def booking_delete(request, pk: int):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    if request.method == "POST":
        booking.delete()
        messages.success(request, "Бронирование удалено.")
        return redirect("resorts:my_bookings")
    return render(request, "resorts/booking_confirm_delete.html", {"booking": booking})


def signup(request):
    if request.user.is_authenticated:
        return redirect("resorts:tour_list")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("resorts:tour_list")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})

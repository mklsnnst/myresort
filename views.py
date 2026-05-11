import hashlib

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import (
    BookingCreateForm,
    BookingUpdateForm,
    SignupForm,
    TourManageForm,
    TourSearchForm,
)
from .models import Booking, Tour
from .tour_queries import annotate_widget_stats, apply_catalog_text_filters, search_tours_by_title_or_location


def _pick_tour_of_day(upcoming_qs):
    """Один «тур дня» из предстоящих, детерминированно от даты (обновляется раз в сутки)."""
    qs = annotate_widget_stats(upcoming_qs).order_by("id")
    candidates = list(qs)
    if not candidates:
        return None
    day_key = timezone.localdate().isoformat()
    h = int(hashlib.sha256(day_key.encode()).hexdigest(), 16)
    return candidates[h % len(candidates)]


def home(request):
    upcoming = Tour.objects.upcoming()
    popular_tours = annotate_widget_stats(upcoming).order_by(
        "-booking_count", "-start_date", "-id"
    )[:5]
    soon_tours = annotate_widget_stats(upcoming).order_by("start_date", "id")[:5]
    tour_of_day = _pick_tour_of_day(upcoming)
    search_form = TourSearchForm()

    return render(
        request,
        "resorts/home.html",
        {
            "popular_tours": popular_tours,
            "soon_tours": soon_tours,
            "tour_of_day": tour_of_day,
            "search_form": search_form,
            "today": timezone.localdate(),
        },
    )


def tour_popular_list(request):
    upcoming = Tour.objects.upcoming()
    tours = annotate_widget_stats(upcoming).order_by(
        "-booking_count", "-start_date", "-id"
    )
    return render(
        request,
        "resorts/tour_popular_list.html",
        {"tours": tours, "page_title": "Популярные туры"},
    )


def tour_soon_list(request):
    upcoming = Tour.objects.upcoming()
    tours = annotate_widget_stats(upcoming).order_by("start_date", "id")
    return render(
        request,
        "resorts/tour_soon_list.html",
        {"tours": tours, "page_title": "Скоро начнутся"},
    )


def tour_upcoming_list(request):
    """Все предстоящие (для ссылки «все туры» у блока «Тур дня»)."""
    upcoming = Tour.objects.upcoming()
    tours = annotate_widget_stats(upcoming).order_by("start_date", "id")
    return render(
        request,
        "resorts/tour_upcoming_list.html",
        {"tours": tours, "page_title": "Все предстоящие туры"},
    )


def tour_search(request):
    form = TourSearchForm(request.GET or None)
    results = []
    if form.is_valid():
        term = (form.cleaned_data.get("query") or "").strip()
        if term:
            results = list(
                annotate_widget_stats(
                    search_tours_by_title_or_location(term)
                ).order_by("start_date", "id")
            )
    return render(
        request,
        "resorts/tour_search_results.html",
        {
            "form": form,
            "results": results,
            "has_query": form.is_valid() and (form.cleaned_data.get("query") or "").strip(),
        },
    )


def tour_list(request):
    if not request.session.get('visited', False):
        request.session['visited'] = True
        request.session['visit_count'] = 1
    else:
        request.session['visit_count'] += 1
    qs = Tour.objects.all()
    qs = apply_catalog_text_filters(
        qs,
        q=request.GET.get("q", ""),
        location=request.GET.get("location", ""),
        description=request.GET.get("description_contains", ""),
    )
    difficulty = request.GET.get("difficulty", "").strip()
    if difficulty:
        qs = qs.filter(difficulty_level=difficulty)

    qs = qs.exclude(reviews__moderation_status="rejected").distinct()

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
        Tour.objects.prefetch_related("images", "services", "reviews__user", "bookings__user"),
        pk=pk,
    )
    approved_reviews = tour.reviews.filter(moderation_status="approved").order_by("-created_at")
    services = tour.services.order_by("price", "id")
    gallery_images = tour.images.order_by("-uploaded_at")
    recent_bookings = tour.bookings.select_related("user").order_by("-created_at")[:5]
    bookings_count = tour.bookings.exclude(status="cancelled").count()

    # Агрегирование (пример): средняя оценка
    rating_avg = approved_reviews.aggregate(avg=Avg("rating")).get("avg")

    return render(
        request,
        "resorts/tour_detail.html",
        {
            "tour": tour,
            "approved_reviews": approved_reviews,
            "rating_avg": rating_avg,
            "services": services,
            "gallery_images": gallery_images,
            "recent_bookings": recent_bookings,
            "bookings_count": bookings_count,
        },
    )


def tour_manage_list(request):
    tours = (
        Tour.objects.all()
        .annotate(bookings_count=Count("bookings", filter=~Q(bookings__status="cancelled")))
        .order_by("-start_date", "-id")
    )
    return render(
        request,
        "resorts/tour_manage_list.html",
        {
            "tours": tours,
            "tours_count": tours.count(),
            "demo_recommended_min": 8,
        },
    )


def tour_create(request):
    if request.method == "POST":
        form = TourManageForm(request.POST, request.FILES)
        if form.is_valid():
            tour = form.save(commit=False)
            if request.user.is_authenticated:
                tour.created_by = request.user
            tour.save()
            messages.success(request, f"Тур «{tour.title}» добавлен.")
            return redirect("resorts:tour_detail", pk=tour.pk)
    else:
        form = TourManageForm()
    return render(
        request,
        "resorts/tour_manage_form.html",
        {"form": form, "mode": "create"},
    )


def tour_update(request, pk: int):
    tour = get_object_or_404(Tour, pk=pk)
    if request.method == "POST":
        form = TourManageForm(request.POST, request.FILES, instance=tour)
        if form.is_valid():
            tour = form.save()
            messages.success(request, f"Тур «{tour.title}» обновлён.")
            return redirect("resorts:tour_detail", pk=tour.pk)
    else:
        form = TourManageForm(instance=tour)
    return render(
        request,
        "resorts/tour_manage_form.html",
        {"form": form, "mode": "update", "tour": tour},
    )


def tour_delete(request, pk: int):
    tour = get_object_or_404(Tour, pk=pk)
    if request.method == "POST":
        title = tour.title
        deleted_count, _ = Tour.objects.filter(pk=tour.pk).delete()
        messages.success(
            request,
            f"Тур «{title}» удалён (записей: {deleted_count}).",
        )
        return redirect("resorts:tour_list")
    return render(
        request,
        "resorts/tour_manage_confirm_delete.html",
        {"tour": tour},
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
    bookings_qs = (
        Booking.objects.filter(user=request.user)
        .select_related("tour")
        .prefetch_related("booking_services__service")
        .order_by("-created_at")
    )
    has_confirmed = bookings_qs.filter(status="confirmed").exists()
    bookings_count = bookings_qs.count()
    service_summary = list(
        bookings_qs.filter(services__isnull=False)
        .values("services__name")
        .annotate(total=Count("services"))
        .order_by("-total")[:5]
    )
    bookings = bookings_qs[:30]
    return render(
        request,
        "resorts/my_bookings.html",
        {
            "bookings": bookings,
            "has_confirmed": has_confirmed,
            "bookings_count": bookings_count,
            "service_summary": service_summary,
        },
    )


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
        deleted_count, _ = Booking.objects.filter(pk=booking.pk, user=request.user).delete()
        messages.success(request, f"Бронирование удалено (записей: {deleted_count}).")
        return redirect("resorts:my_bookings")
    return render(request, "resorts/booking_confirm_delete.html", {"booking": booking})


def signup(request):
    if request.user.is_authenticated:
        return redirect("resorts:home")

    if request.method == "POST":
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            cleaned = form.cleaned_data
            bio = cleaned.get("bio", "").strip()
            uploaded_file = cleaned.get("profile_file")
            user = form.save()
            login(request, user)
            if bio:
                request.session["signup_bio"] = bio
            if uploaded_file:
                request.session["signup_file_name"] = uploaded_file.name
            return HttpResponseRedirect(reverse("resorts:home"))
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})

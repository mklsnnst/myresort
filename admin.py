from django.contrib import admin
from django import forms
from django.db.models import Count
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from pathlib import Path

from .models import Booking, BookingService, Review, Service, Tour, TourImage

ARIAL_FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    fields = ["name", "price", "included_in_price", "available_from", "available_to"]
    raw_id_fields = ["tour"]


class TourImageInline(admin.TabularInline):
    model = TourImage
    extra = 1
    fields = ["image", "caption", "image_preview", "uploaded_at"]
    readonly_fields = ["image_preview", "uploaded_at"]

    @admin.display(description="Превью")
    def image_preview(self, obj):
        if getattr(obj, "image", None):
            return format_html(
                '<img src="{}" style="max-height: 100px;"/>',
                obj.image.url,
            )
        return "—"


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "location",
        "difficulty_level",
        "capacity",
        "booked_people_display",
        "free_places_display",
        "period_display",
        "price",
        "main_image_thumb",
        "bookings_count_display",
        "start_date",
    ]
    list_display_links = ["title"]
    list_filter = ["difficulty_level", "start_date", "created_at"]
    search_fields = ["title", "description", "location"]
    readonly_fields = ["created_at", "updated_at", "main_image_preview"]
    raw_id_fields = ["created_by"]
    date_hierarchy = "start_date"
    save_on_top = True

    fieldsets = (
        (
            "Тур",
            {
                "fields": (
                    "title",
                    "description",
                    "location",
                    "difficulty_level",
                    "start_date",
                    "end_date",
                    "price",
                )
            },
        ),
        (
            "Изображение",
            {"fields": ("main_image", "main_image_preview"), "classes": ("collapse",)},
        ),
        (
            "Дополнительно",
            {
                "fields": (
                    "brochure",
                    "official_url",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Метаданные",
            {"fields": ("created_by", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    inlines = [TourImageInline, ServiceInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_bookings_count=Count("bookings", distinct=True))

    @admin.display(description="Период")
    def period_display(self, obj):
        return f"{obj.start_date} — {obj.end_date}"

    @admin.display(description="Главное фото")
    def main_image_thumb(self, obj):
        if obj.main_image:
            return format_html(
                '<img src="{}" style="max-height: 48px;"/>',
                obj.main_image.url,
            )
        return "—"

    @admin.display(description="Превью главного фото")
    def main_image_preview(self, obj):
        if obj.main_image:
            return format_html(
                '<img src="{}" style="max-height: 220px;"/>',
                obj.main_image.url,
            )
        return "Нет изображения"

    @admin.display(description="Броней", ordering="_bookings_count")
    def bookings_count_display(self, obj):
        return getattr(obj, "_bookings_count", obj.bookings.count())

    @admin.display(description="Занято мест")
    def booked_people_display(self, obj):
        return obj.booked_people

    @admin.display(description="Свободно мест")
    def free_places_display(self, obj):
        return obj.free_places


class BookingServiceInline(admin.TabularInline):
    model = BookingService
    extra = 1
    fields = ["service", "quantity"]
    raw_id_fields = ["service"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "service":
            tour_id = getattr(request, "_booking_admin_tour_id", None)
            if not tour_id:
                parent_obj = getattr(request, "_booking_admin_parent_obj", None)
                tour_id = getattr(parent_obj, "tour_id", None)
            if tour_id:
                kwargs["queryset"] = Service.objects.filter(tour_id=tour_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "tour",
        "price",
        "included_in_price",
        "period_display",
    ]
    list_display_links = ["name"]
    list_filter = ["included_in_price", "available_from", "available_to"]
    search_fields = ["name", "tour__title"]
    raw_id_fields = ["tour"]
    date_hierarchy = "available_from"

    fieldsets = (
        (
            "Услуга",
            {
                "fields": (
                    "tour",
                    "name",
                    "price",
                    "included_in_price",
                    "available_from",
                    "available_to",
                )
            },
        ),
    )

    @admin.display(description="Период доступности")
    def period_display(self, obj):
        a, b = obj.available_from, obj.available_to
        if a or b:
            return f"{a or '—'} — {b or '—'}"
        return "—"

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "tour",
        "booking_date",
        "people_count",
        "status",
        "total_price",
        "created_at",
    ]
    list_display_links = ["id", "tour"]
    list_filter = ["status", "booking_date", "created_at", "tour"]
    search_fields = ["user__username", "user__email", "tour__title"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["user", "tour"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "user",
                    "tour",
                    "booking_date",
                    "people_count",
                    "status",
                    "total_price",
                )
            },
        ),
        (
            "Метаданные",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    inlines = [BookingServiceInline]

    actions = ["confirm_bookings", "cancel_bookings", "export_bookings_to_pdf"]

    @admin.action(description="Подтвердить выбранные бронирования")
    def confirm_bookings(self, request, queryset):
        updated = queryset.update(status="confirmed")
        self.message_user(request, f"Подтверждено {updated} бронирований.")

    @admin.action(description="Отменить выбранные бронирования")
    def cancel_bookings(self, request, queryset):
        updated = queryset.update(status="cancelled")
        self.message_user(request, f"Отменено {updated} бронирований.")

    @admin.action(description="Скачать выбранные бронирования в PDF")
    def export_bookings_to_pdf(self, request, queryset):
        response = HttpResponse(content_type="application/pdf")
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        response["Content-Disposition"] = (
            f'attachment; filename="bookings_{timestamp}.pdf"'
        )

        pdf = canvas.Canvas(response, pagesize=A4)
        _, height = A4
        y = height - 40

        font_regular = "Helvetica"
        font_bold = "Helvetica-Bold"
        if ARIAL_FONT_PATH.exists():
            pdfmetrics.registerFont(TTFont("Arial", str(ARIAL_FONT_PATH)))
            font_regular = "Arial"
            font_bold = "Arial"

        pdf.setFont(font_bold, 14)
        pdf.drawString(40, y, "Список бронирований")
        y -= 30

        pdf.setFont(font_regular, 10)
        for booking in queryset.select_related("user", "tour").order_by("id"):
            line = (
                f"#{booking.id} | {booking.user.username} | {booking.tour.title} | "
                f"{booking.booking_date} | {booking.people_count} чел. | "
                f"{booking.status} | {booking.total_price} руб."
            )
            pdf.drawString(40, y, line[:120])
            y -= 18

            if y < 50:
                pdf.showPage()
                y = height - 40
                pdf.setFont(font_regular, 10)

        pdf.save()
        return response

    def get_form(self, request, obj=None, **kwargs):
        request._booking_admin_parent_obj = obj
        tour_id = None
        if obj and obj.tour_id:
            tour_id = obj.tour_id
        elif request.method == "GET":
            tour_id = request.GET.get("tour") or None
        elif request.method == "POST":
            tour_id = request.POST.get("tour") or None
        request._booking_admin_tour_id = int(tour_id) if tour_id else None
        return super().get_form(request, obj, **kwargs)

    def get_formsets_with_inlines(self, request, obj=None):
        tour_id = None
        if obj and obj.tour_id:
            tour_id = obj.tour_id
        elif request.method == "GET":
            tour_id = request.GET.get("tour") or None
        elif request.method == "POST":
            tour_id = request.POST.get("tour") or None
        request._booking_admin_tour_id = int(tour_id) if tour_id else None
        yield from super().get_formsets_with_inlines(request, obj)

    class Media:
        js = ("resorts/admin/booking_services_filter.js",)


class ReviewAdminForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "rating" in self.fields:
            self.fields["rating"].min_value = 1
            self.fields["rating"].max_value = 5


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    form = ReviewAdminForm
    list_display = [
        "id",
        "user",
        "tour",
        "rating",
        "short_comment",
        "moderation_status",
        "created_at",
    ]
    list_display_links = ["user", "tour"]
    list_filter = ["moderation_status", "rating", "tour", "created_at"]
    search_fields = ["user__username", "tour__title", "comment"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["user", "tour"]
    date_hierarchy = "created_at"

    fieldsets = (
        ("Отзыв", {"fields": ("user", "tour", "rating", "comment", "moderation_status")}),
        ("Метаданные", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    actions = ["approve_reviews", "reject_reviews"]

    @admin.display(description="Комментарий")
    def short_comment(self, obj):
        text = obj.comment or ""
        return text[:50] + "..." if len(text) > 50 else text

    @admin.action(description="Одобрить выбранные отзывы")
    def approve_reviews(self, request, queryset):
        updated = queryset.update(moderation_status="approved")
        self.message_user(request, f"Одобрено {updated} отзывов.")

    @admin.action(description="Отклонить выбранные отзывы")
    def reject_reviews(self, request, queryset):
        updated = queryset.update(moderation_status="rejected")
        self.message_user(request, f"Отклонено {updated} отзывов.")


@admin.register(BookingService)
class BookingServiceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "booking",
        "booking_tour_display",
        "service",
        "quantity",
        "booking_created_display",
    ]
    list_display_links = ["booking", "service"]
    list_filter = ["booking__status", "service__tour", "booking__tour"]
    search_fields = ["booking__id", "service__name", "booking__tour__title"]
    raw_id_fields = ["booking", "service"]
    readonly_fields = ["booking_created_display", "booking_tour_readonly"]
    date_hierarchy = "booking__created_at"

    fieldsets = (
        (
            "Связь",
            {
                "fields": (
                    "booking",
                    "booking_tour_readonly",
                    "service",
                    "quantity",
                    "booking_created_display",
                )
            },
        ),
    )

    @admin.display(description="Тур брони")
    def booking_tour_display(self, obj):
        return obj.booking.tour.title

    @admin.display(description="Тур (бронирование)")
    def booking_tour_readonly(self, obj):
        if obj.booking_id:
            t = obj.booking.tour
            url = reverse("admin:resorts_tour_change", args=[t.pk])
            return format_html('<a href="{}">{}</a>', url, t.title)
        return "—"

    @admin.display(description="Дата создания брони")
    def booking_created_display(self, obj):
        if obj.booking_id:
            return obj.booking.created_at
        return "—"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("booking__tour", "service")
        )
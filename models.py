from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q
from django.db.models.functions import Coalesce


class TourQuerySet(models.QuerySet):
    def upcoming(self):
        return self.filter(end_date__gte=timezone.localdate())

    def in_location(self, q: str):
        if not q:
            return self
        return self.filter(location__icontains=q)

    def with_free_places(self):
        # Пример "__" с обращением к связанной таблице (bookings__status).
        booked = models.Sum(
            "bookings__people_count",
            filter=~Q(bookings__status="cancelled"),
        )
        return (
            self.annotate(_booked_people=Coalesce(booked, 0))
            .filter(capacity__gt=models.F("_booked_people"))
            .order_by("-start_date", "-id")
        )


class TourManager(models.Manager):
    def get_queryset(self):
        return TourQuerySet(self.model, using=self._db)

    def upcoming(self):
        return self.get_queryset().upcoming()

    def in_location(self, q: str):
        return self.get_queryset().in_location(q)


class Tour(models.Model):
    DIFFICULTY_CHOICES = [
        ("beginner", "Начинающий"),
        ("intermediate", "Средний"),
        ("advanced", "Продвинутый"),
        ("expert", "Эксперт"),
    ]

    title = models.CharField(max_length=200, verbose_name="Название тура")
    description = models.TextField(verbose_name="Описание", blank=True)
    location = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Локация/направление",
    )
    difficulty_level = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default="intermediate",
        verbose_name="Уровень сложности",
    )
    start_date = models.DateField(verbose_name="Дата начала")
    end_date = models.DateField(verbose_name="Дата окончания")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Стоимость тура (руб.)",
    )
    capacity = models.PositiveIntegerField(
        default=20,
        verbose_name="Максимальное количество человек",
    )
    main_image = models.ImageField(
        upload_to="tours/",
        null=True,
        blank=True,
        verbose_name="Главное изображение",
    )
    brochure = models.FileField(
        upload_to="tours/brochures/",
        null=True,
        blank=True,
        verbose_name="Файл тура (PDF/документ)",
    )
    official_url = models.URLField(
        blank=True,
        verbose_name="Официальная ссылка",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tours",
        verbose_name="Кто создал",
    )

    objects = TourManager()

    class Meta:
        verbose_name = "Тур"
        verbose_name_plural = "Туры"
        ordering = ["-start_date", "-id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("resorts:tour_detail", kwargs={"pk": self.pk})

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "Дата окончания не может быть раньше даты начала."}
            )

    @property
    def booked_people(self) -> int:
        # Считаем занятые места по всем бронированиям, кроме отменённых.
        return (
            self.bookings.exclude(status="cancelled")
            .aggregate(total=models.Sum("people_count"))
            .get("total")
            or 0
        )

    @property
    def free_places(self) -> int:
        return max(0, int(self.capacity) - int(self.booked_people))


class TourImage(models.Model):
    tour = models.ForeignKey(
        Tour,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Тур",
    )
    image = models.ImageField(upload_to="tours/gallery/", verbose_name="Изображение")
    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Подпись",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Изображение тура"
        verbose_name_plural = "Изображения туров"
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"Фото к туру «{self.tour.title}»"


class Service(models.Model):
    tour = models.ForeignKey(
        Tour,
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name="Тур",
    )
    name = models.CharField(max_length=100, verbose_name="Название услуги")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    available_from = models.DateField(
        verbose_name="Доступно с", null=True, blank=True
    )
    available_to = models.DateField(
        verbose_name="Доступно по", null=True, blank=True
    )
    included_in_price = models.BooleanField(
        default=False,
        verbose_name="Включено в стоимость тура",
    )

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ["tour", "price"]

    def __str__(self):
        return f"{self.name} — {self.price} руб."


class Booking(models.Model):
    STATUS_CHOICES = [
        ("new", "Новое"),
        ("confirmed", "Подтверждено"),
        ("cancelled", "Отменено"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="Пользователь",
    )
    tour = models.ForeignKey(
        Tour,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="Тур",
    )
    people_count = models.PositiveIntegerField(
        default=1,
        verbose_name="Количество человек",
    )
    services = models.ManyToManyField(
        Service,
        through="BookingService",
        verbose_name="Дополнительные услуги",
    )
    booking_date = models.DateField(verbose_name="Дата бронирования")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
        verbose_name="Статус",
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Итого")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Бронь #{self.pk} — {self.user.username} — {self.tour.title}"

    def save(self, *args, **kwargs):
        if self.booking_date is None:
            self.booking_date = timezone.localdate()
        if not self.status:
            self.status = "new"
        super().save(*args, **kwargs)
        services_total = (
            self.booking_services.select_related("service")
            .filter(service__included_in_price=False)
            .aggregate(
                total=models.Sum(
                    models.ExpressionWrapper(
                        models.F("quantity") * models.F("service__price"),
                        output_field=models.DecimalField(max_digits=12, decimal_places=2),
                    )
                )
            )
            .get("total")
            or 0
        )
        calculated_total = (self.tour.price * self.people_count) + services_total
        if self.total_price != calculated_total:
            Booking.objects.filter(pk=self.pk).update(total_price=calculated_total)
            self.total_price = calculated_total

    def clean(self):
        super().clean()
        if self.people_count < 1:
            raise ValidationError({"people_count": "Количество человек должно быть >= 1."})

        if not self.tour_id:
            return
        qs = self.tour.bookings.exclude(status="cancelled")
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        already = qs.aggregate(total=models.Sum("people_count")).get("total") or 0
        if already + int(self.people_count) > int(self.tour.capacity):
            free = int(self.tour.capacity) - int(already)
            raise ValidationError(
                {
                    "people_count": (
                        f"Недостаточно мест: свободно {max(0, free)}. "
                        f"Вы пытаетесь забронировать {self.people_count}."
                    )
                }
            )


class BookingService(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        verbose_name="Бронирование",
        related_name="booking_services",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        verbose_name="Услуга",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")

    class Meta:
        verbose_name = "Услуга в бронировании"
        verbose_name_plural = "Услуги в бронированиях"

    def __str__(self):
        return f"{self.booking} — {self.service} ×{self.quantity}"

    def clean(self):
        super().clean()
        if self.booking_id and self.service_id:
            if self.service.tour_id != self.booking.tour_id:
                raise ValidationError(
                    {
                        "service": "Услуга должна относиться к выбранному туру.",
                    }
                )


class Review(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Пользователь",
    )
    tour = models.ForeignKey(
        Tour,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Тур",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Оценка",
    )
    comment = models.TextField(verbose_name="Комментарий", blank=True)
    moderation_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "На модерации"),
            ("approved", "Одобрено"),
            ("rejected", "Отклонено"),
        ],
        default="pending",
        verbose_name="Статус модерации",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]
        unique_together = [["user", "tour"]]

    def __str__(self):
        return (
            f"Отзыв от {self.user.username} на {self.tour.title} — {self.rating}★"
        )

    def clean(self):
        super().clean()
        if not self.user_id or not self.tour_id:
            return

        # Отзыв разрешён только после участия в туре:
        # нужна подтверждённая бронь и тур должен завершиться.
        if self.tour.end_date >= timezone.localdate():
            raise ValidationError(
                {"tour": "Нельзя оставить отзыв до завершения тура."}
            )

        has_confirmed_booking = Booking.objects.filter(
            user_id=self.user_id,
            tour_id=self.tour_id,
            status="confirmed",
        ).exists()
        if not has_confirmed_booking:
            raise ValidationError(
                {"tour": "Отзыв можно оставить только после подтверждённого бронирования тура."}
            )
    
# Generated manually for Tour model, booking.tour, removal of ResortImage

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def forwards_booking_tour(apps, schema_editor):
    Booking = apps.get_model("resorts", "Booking")
    Tour = apps.get_model("resorts", "Tour")
    Resort = apps.get_model("resorts", "Resort")
    for booking in Booking.objects.all():
        resort = Resort.objects.get(pk=booking.resort_id)
        tour = Tour.objects.filter(resort_id=resort.pk).order_by("pk").first()
        if tour is None:
            tour = Tour.objects.create(
                resort_id=resort.pk,
                title=f"Перенос: {resort.name}",
                description="",
                start_date=booking.booking_date,
                end_date=booking.booking_date,
                price=booking.total_price,
            )
        booking.tour_id = tour.pk
        booking.save(update_fields=["tour_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("resorts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.DeleteModel(
            name="ResortImage",
        ),
        migrations.RemoveField(
            model_name="resort",
            name="main_image",
        ),
        migrations.CreateModel(
            name="Tour",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=200, verbose_name="Название тура")),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Описание"),
                ),
                ("start_date", models.DateField(verbose_name="Дата начала")),
                ("end_date", models.DateField(verbose_name="Дата окончания")),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        verbose_name="Стоимость тура (руб.)",
                    ),
                ),
                (
                    "main_image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="tours/",
                        verbose_name="Главное изображение",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Дата создания"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Дата обновления"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_tours",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Кто создал",
                    ),
                ),
                (
                    "resort",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tours",
                        to="resorts.resort",
                        verbose_name="Курорт",
                    ),
                ),
            ],
            options={
                "verbose_name": "Тур",
                "verbose_name_plural": "Туры",
                "ordering": ["-start_date", "-id"],
            },
        ),
        migrations.AddField(
            model_name="tour",
            name="included_services",
            field=models.ManyToManyField(
                blank=True,
                related_name="included_in_tours",
                to="resorts.service",
                verbose_name="Услуги, включённые в стоимость тура",
            ),
        ),
        migrations.CreateModel(
            name="TourImage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "image",
                    models.ImageField(upload_to="tours/gallery/", verbose_name="Изображение"),
                ),
                (
                    "caption",
                    models.CharField(blank=True, max_length=200, verbose_name="Подпись"),
                ),
                (
                    "uploaded_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки"),
                ),
                (
                    "tour",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="resorts.tour",
                        verbose_name="Тур",
                    ),
                ),
            ],
            options={
                "verbose_name": "Изображение тура",
                "verbose_name_plural": "Изображения туров",
                "ordering": ["uploaded_at"],
            },
        ),
        migrations.AddField(
            model_name="booking",
            name="tour",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bookings",
                to="resorts.tour",
                verbose_name="Тур",
            ),
        ),
        migrations.RunPython(forwards_booking_tour, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="booking",
            name="resort",
        ),
        migrations.AlterField(
            model_name="booking",
            name="tour",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bookings",
                to="resorts.tour",
                verbose_name="Тур",
            ),
        ),
        migrations.AlterField(
            model_name="booking",
            name="services",
            field=models.ManyToManyField(
                through="resorts.BookingService",
                to="resorts.service",
                verbose_name="Дополнительные услуги",
            ),
        ),
        migrations.AlterField(
            model_name="bookingservice",
            name="booking",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="booking_services",
                to="resorts.booking",
                verbose_name="Бронирование",
            ),
        ),
    ]

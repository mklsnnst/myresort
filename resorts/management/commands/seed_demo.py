import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from resorts.models import Booking, BookingService, Review, Service, Tour


class Command(BaseCommand):
    help = "Seed demo data (tours/services/bookings/reviews) into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tours",
            type=int,
            default=15,
            help="How many tours to create (default: 15).",
        )
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Delete existing demo objects before seeding.",
        )

    def handle(self, *args, **options):
        tours_count: int = options["tours"]
        wipe: bool = options["wipe"]

        if wipe:
            BookingService.objects.all().delete()
            Booking.objects.all().delete()
            Review.objects.all().delete()
            Service.objects.all().delete()
            Tour.objects.all().delete()

        admin_user, _ = User.objects.get_or_create(
            username="demo_admin",
            defaults={"email": "demo_admin@example.com", "is_staff": True, "is_superuser": True},
        )
        if not admin_user.is_staff or not admin_user.is_superuser:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save(update_fields=["is_staff", "is_superuser"])

        demo_users = [admin_user]
        for i in range(1, 6):
            u, _ = User.objects.get_or_create(
                username=f"demo_user_{i}",
                defaults={"email": f"demo_user_{i}@example.com"},
            )
            demo_users.append(u)

        locations = [
            "Кавказ",
            "Домбай",
            "Шерегеш",
            "Красная Поляна",
            "Алтай",
            "Байкал",
            "Карелия",
            "Камчатка",
        ]
        difficulties = ["beginner", "intermediate", "advanced", "expert"]
        title_templates = [
            "Тур выходного дня: {loc}",
            "Активный тур: {loc}",
            "Зимний тур: {loc}",
            "Экспедиция: {loc}",
            "Комфорт-тур: {loc}",
        ]
        service_names = [
            "Трансфер",
            "Аренда снаряжения",
            "Инструктор",
            "Питание",
            "Экскурсия",
            "Страховка",
            "SPA/баня",
        ]

        created_tours = 0
        created_services = 0
        created_bookings = 0
        created_reviews = 0

        # Часть туров создаём в прошлом, чтобы можно было оставлять отзывы
        # по правилу "после завершённого/подтверждённого бронирования".
        base = date.today() - timedelta(days=max(1, tours_count // 2) * 3)

        for idx in range(tours_count):
            loc = random.choice(locations)
            title = random.choice(title_templates).format(loc=loc)
            difficulty = random.choice(difficulties)
            start = base + timedelta(days=idx * 3)
            duration = random.randint(2, 7)
            end = start + timedelta(days=duration - 1)
            price = random.choice([15990, 24990, 34990, 49990, 64990, 89990])

            tour = Tour.objects.create(
                title=f"{title} #{idx + 1}",
                description="Демо-тур для заполнения базы данных.",
                location=loc,
                difficulty_level=difficulty,
                start_date=start,
                end_date=end,
                price=f"{price:.2f}",
                created_by=admin_user,
            )
            created_tours += 1

            # Services
            services_for_tour = []
            for _ in range(random.randint(3, 6)):
                name = random.choice(service_names)
                included = random.random() < 0.25
                s_price = 0 if included else random.choice([500, 1200, 2500, 3500, 6000])
                services_for_tour.append(
                    Service(
                        tour=tour,
                        name=name,
                        price=f"{s_price:.2f}",
                        included_in_price=included,
                        available_from=start,
                        available_to=end,
                    )
                )
            Service.objects.bulk_create(services_for_tour)
            created_services += len(services_for_tour)

            # Bookings
            tour_services = list(tour.services.all())
            for _ in range(random.randint(0, 3)):
                user = random.choice(demo_users)
                status = random.choice(["new", "confirmed", "cancelled"])
                booking = Booking.objects.create(
                    user=user,
                    tour=tour,
                    booking_date=start,
                    status=status,
                    total_price=tour.price,
                )
                created_bookings += 1

                # Add 0-3 extra services to booking (only those not included in price)
                candidates = [s for s in tour_services if not s.included_in_price]
                random.shuffle(candidates)
                for s in candidates[: random.randint(0, min(3, len(candidates)))]:
                    BookingService.objects.create(
                        booking=booking,
                        service=s,
                        quantity=random.randint(1, 3),
                    )

            # Reviews
            if end < date.today():
                confirmed_users = list(
                    Booking.objects.filter(tour=tour, status="confirmed")
                    .values_list("user_id", flat=True)
                    .distinct()
                )
                random.shuffle(confirmed_users)
                for user_id in confirmed_users[: random.randint(0, min(2, len(confirmed_users)))]:
                    if Review.objects.filter(user_id=user_id, tour=tour).exists():
                        continue
                    rating = random.randint(3, 5)
                    moderation_status = random.choice(["pending", "approved", "rejected"])
                    Review.objects.create(
                        user_id=user_id,
                        tour=tour,
                        rating=rating,
                        comment="Демо-отзыв для заполнения базы данных.",
                        moderation_status=moderation_status,
                    )
                    created_reviews += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seed complete: "
                f"tours={created_tours}, services={created_services}, "
                f"bookings={created_bookings}, reviews={created_reviews}"
            )
        )


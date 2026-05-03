"""Вспомогательные QuerySet для туров (главная, поиск, каталог)."""

from django.db.models import Count, Q

from .models import Tour


def annotate_widget_stats(qs):
    return qs.annotate(
        booking_count=Count("bookings", filter=~Q(bookings__status="cancelled")),
        gallery_count=Count("images", distinct=True),
    )


def _icontains_casefold_q(field: str, raw: str) -> Q | None:
    """
    Регистронезависимый подстрочный поиск для SQLite + кириллицы.
    В SQLite LOWER(поле) не нормализует русские буквы, поэтому нельзя сравнивать
    только с lower(term) из Python. Берём несколько вариантов регистра строки
    запроса и объединяем через __icontains (LIKE).
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    variants = {raw, raw.lower(), raw.upper(), raw.capitalize()}
    q = Q()
    for v in variants:
        if v:
            q |= Q(**{f"{field}__icontains": v})
    return q


def apply_catalog_text_filters(qs, q="", location="", description=""):
    """Фильтры каталога по подстроке в названии, локации, описании."""
    q = (q or "").strip()
    location = (location or "").strip()
    description = (description or "").strip()

    tq = _icontains_casefold_q("title", q)
    if tq is not None:
        qs = qs.filter(tq)

    lq = _icontains_casefold_q("location", location)
    if lq is not None:
        qs = qs.filter(lq)

    dq = _icontains_casefold_q("description", description)
    if dq is not None:
        qs = qs.filter(dq)

    return qs


def search_tours_by_title_or_location(term: str):
    """
    Поиск по названию или локации.
    По всем турам (не только upcoming), см. комментарий в views.tour_list.
    """
    term = (term or "").strip()
    if not term:
        return Tour.objects.none()

    tq = _icontains_casefold_q("title", term)
    lq = _icontains_casefold_q("location", term)
    if tq is None and lq is None:
        return Tour.objects.none()
    combined = Q()
    if tq is not None:
        combined |= tq
    if lq is not None:
        combined |= lq
    return Tour.objects.filter(combined).distinct()

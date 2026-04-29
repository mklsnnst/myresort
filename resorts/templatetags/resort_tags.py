from django import template
from django.utils import timezone
import random
from resorts.models import Tour

register = template.Library()


@register.simple_tag
def current_year():
    return timezone.localdate().year


@register.inclusion_tag("resorts/_tour_of_day.html", takes_context=True)
def tour_of_day(context):
    today = context.get("today", timezone.localdate())
    upcoming_tours = list(Tour.objects.upcoming())
    if upcoming_tours:
        random_tour = random.choice(upcoming_tours)
    else:
        random_tour = None
    return {
        "tour_of_day": random_tour,
        "today": today, 
        "from_context": "today" in context 
    }

@register.simple_tag
def featured_tours(limit=3):
    return Tour.objects.upcoming().order_by("price", "-start_date")[: int(limit)]


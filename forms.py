from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Booking, Service


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=False)
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Кратко расскажите о себе",
            }
        ),
        label="О себе",
        help_text="Необязательное поле.",
    )
    profile_file = forms.FileField(
        required=False,
        label="Файл профиля",
        help_text="Можно прикрепить файл.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Логин"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com"}),
        }
        labels = {
            "username": "Имя пользователя",
            "email": "Email",
        }
        help_texts = {
            "email": "Можно оставить пустым.",
        }
        error_messages = {
            "username": {
                "required": "Введите имя пользователя.",
            },
            "email": {
                "invalid": "Введите корректный email адрес.",
            },
        }


class BookingCreateForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Дополнительные услуги",
    )

    class Meta:
        model = Booking
        fields = ("people_count", "services")
        widgets = {
            "people_count": forms.NumberInput(
                attrs={
                    "min": 1,
                    "placeholder": "Например: 2",
                }
            ),
        }

    def __init__(self, *args, tour=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tour = tour
        if tour is not None:
            self.fields["services"].queryset = Service.objects.filter(tour=tour).order_by("price")

    def clean_people_count(self):
        people_count = self.cleaned_data["people_count"]
        if people_count < 1:
            raise forms.ValidationError("Количество человек должно быть не меньше 1.")
        return people_count

    def save(self, commit=True):
        obj: Booking = super().save(commit=False)
        if obj.booking_date is None:
            obj.booking_date = timezone.localdate()
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class BookingUpdateForm(BookingCreateForm):
    class Meta(BookingCreateForm.Meta):
        exclude = (
            "user",
            "tour",
            "booking_date",
            "status",
            "total_price",
            "created_at",
            "updated_at",
            "services",
        )


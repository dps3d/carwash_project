"""Роль «API» (+ базова валідація доступу та обмежень від ролі «Доступ»).

================================================================================
ПОСЛАННЯ ДЛЯ РОЗРОБНИКА РОЛІ «API» ВІД РОЛІ «ДОСТУП» — БУДЬ ЛАСКА, ПРОЧИТАЙ:
================================================================================
Цей файл уже містить захисну базу під моделі WashSlot і Booking (із гілки
`models-wash-slot`), щоб закрити рядки 11–17, 20 та захист від падінь SQLite (500):

1. НЕ ВИДАЛЯЙ `read_only_fields = ("id", "owner", "status")` у `BookingSerializer` —
   це захищає від підміни `owner` і `status` у тілі запиту (рядки 11 і 12).
2. НЕ ВИДАЛЯЙ `BookingValidationMixin`, `quantity` обмеження (`MIN_QUANTITY..MAX_QUANTITY`),
   `to_internal_value()` та `validate()` — вони відбивають `-5`, `0`,
   `99999999999999999999`, булеві значення, гігантський `slot` ID та перевищення
   залишку кодом `400` замість `500` (рядки 13–17), і при цьому дозволяють створити
   кілька `draft`-заявок по 1 шт. для Гонки Б (рядок 22).
3. Можеш вільно додавати додаткові поля для відображення (наприклад, nested info
   чи `read_only` поля), якщо не послаблюєш ці перевірки.
================================================================================
"""

from collections.abc import Mapping

from rest_framework import serializers

from . import models as api_models
from .permissions import (
    MAX_QUANTITY,
    MIN_QUANTITY,
    SQLITE_MAX_INT,
    validate_booking_quantity,
)

WashSlot = getattr(api_models, "WashSlot", None)
Booking = getattr(api_models, "Booking", None)


class BookingValidationMixin:
    """Міксин валідації вхідних даних заявки (рядки 13–17, захист від SQLite overflow)."""

    def validate_quantity(self, value):
        return validate_booking_quantity(value)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            if "quantity" in data and isinstance(data["quantity"], (bool, float)):
                raise serializers.ValidationError(
                    {"quantity": "Кількість має бути цілим числом."}
                )

            if "slot" in data:
                raw_slot = data["slot"]
                if isinstance(raw_slot, (bool, float)):
                    raise serializers.ValidationError(
                        {"slot": "ID слота має бути цілим числом."}
                    )
                if isinstance(raw_slot, int) and abs(raw_slot) > SQLITE_MAX_INT:
                    raise serializers.ValidationError({"slot": "Некоректний ID слота."})
                if isinstance(raw_slot, str):
                    stripped = raw_slot.strip()
                    if len(stripped) > 20 or not stripped.isascii():
                        raise serializers.ValidationError({"slot": "Некоректний ID слота."})
                    try:
                        if abs(int(stripped)) > SQLITE_MAX_INT:
                            raise serializers.ValidationError({"slot": "Некоректний ID слота."})
                    except ValueError:
                        raise serializers.ValidationError({"slot": "ID слота має бути цілим числом."})

        return super().to_internal_value(data)

    def validate(self, attrs):
        return super().validate(attrs)


if WashSlot is not None:

    class WashSlotSerializer(serializers.ModelSerializer):
        class Meta:
            model = WashSlot
            fields = ("id", "date", "start_time", "end_time", "available")
            read_only_fields = ("id",)


if Booking is not None:

    class BookingSerializer(BookingValidationMixin, serializers.ModelSerializer):
        quantity = serializers.IntegerField(
            min_value=MIN_QUANTITY,
            max_value=MAX_QUANTITY,
            validators=[validate_booking_quantity],
        )

        class Meta:
            model = Booking
            fields = ("id", "owner", "slot", "quantity", "status")
            read_only_fields = ("id", "owner", "status")

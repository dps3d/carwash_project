from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError

from .models import Booking, WashSlot
from .permissions import ConflictError as Conflict  # DRF сам віддає 409


def confirm(booking):
    with transaction.atomic():
        # 1) стан: draft → confirmed, атомарно в базі
        moved = Booking.objects.filter(pk=booking.pk, status="draft") \
                               .update(status="confirmed")
        if not moved:
            raise Conflict("Заявка не в стані draft")
        # 2) ресурс: списати, лише якщо вистачає
        taken = WashSlot.objects.filter(pk=booking.slot_id,
                                        available__gte=booking.quantity) \
                                .update(available=F("available") - booking.quantity)
        if not taken:
            # виняток ВСЕРЕДИНІ atomic: перший UPDATE відкотиться
            raise ValidationError("Недостатньо вільних вікон")  # 400, рядок 17


def cancel(booking):
    with transaction.atomic():
        # confirmed → cancelled: ресурс повертаємо
        if Booking.objects.filter(pk=booking.pk, status="confirmed") \
                          .update(status="cancelled"):
            WashSlot.objects.filter(pk=booking.slot_id) \
                            .update(available=F("available") + booking.quantity)
            return
        # draft → cancelled: ресурс не займали, нічого не повертаємо
        if Booking.objects.filter(pk=booking.pk, status="draft") \
                          .update(status="cancelled"):
            return
        raise Conflict("Заявка вже скасована")  # cancelled → cancelled = 409
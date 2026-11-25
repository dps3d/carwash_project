from django.conf import settings
from django.db import models


class WashSlot(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    available = models.PositiveIntegerField()

    class Meta:
        ordering = ("date", "start_time")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(available__gte=0),
                name="washslot_available_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.date} {self.start_time:%H:%M}–{self.end_time:%H:%M}"


class Booking(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    slot = models.ForeignKey(
        WashSlot,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ("-pk",)
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="booking_quantity_positive"),
            models.CheckConstraint(
                condition=models.Q(status__in=("draft", "confirmed", "cancelled")),
                name="booking_status_valid",
            ),
        ]

    def __str__(self):
        return f"Booking {self.pk} ({self.status})"

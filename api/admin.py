from django.contrib import admin

from .models import Booking, WashSlot


@admin.register(WashSlot)
class WashSlotAdmin(admin.ModelAdmin):
    list_display = ("date", "start_time", "end_time", "available")
    list_filter = ("date",)
    ordering = ("date", "start_time")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "slot", "quantity", "status")
    list_filter = ("status", "slot__date")
    search_fields = ("owner__username",)
    ordering = ("-id",)

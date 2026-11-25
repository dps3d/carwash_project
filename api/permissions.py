"""Роль «Доступ». Класи прав, перевірка власника, коди відповідей і захист від переповнення.

Покриває вимоги карти атаки (рядки 1–4, 7–16, 20) та інваріант закритої частини:
- Каталог (`IsCatalogReadOnlyOrAdmin`): читання відкрите всім (200), зміни — лише адміну (401/403).
- Заявки (`IsOwner`): без токена доступ заборонено (401); деталі та дії доступні
  виключно власнику (403); `PUT`/`PATCH`/`DELETE` для заявки не в стані `draft`
  блокується з кодом `409 Conflict` (захист інваріанта).
- `OwnerSafeViewSetMixin`: ізолює список заявок (`get_queryset`), захищає від
  SQLite OverflowError (500) у URL та примусово виставляє `owner` і `status="draft"`
  на сервері (`perform_create`).
- `ConflictError` та `custom_exception_handler`: стандартизують 400 / 409 замість 500.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

MIN_QUANTITY = 1
MAX_QUANTITY = 1_000_000
SQLITE_MAX_INT = 9_223_372_036_854_775_807


def validate_sqlite_int(value, field_name="value"):
    """Перевіряє, що ціле число не перевищує межі 64-бітного signed int у SQLite."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise serializers.ValidationError(f"Поле '{field_name}' має бути цілим числом.")
    if abs(value) > SQLITE_MAX_INT:
        raise serializers.ValidationError(
            f"Значення '{field_name}' виходить за допустимі межі цілого числа."
        )
    return value


def validate_booking_quantity(value):
    """Валідатор кількості для заявки (рядки 13–15: -5, 0, 99999999999999999999 -> 400)."""
    validate_sqlite_int(value, field_name="quantity")
    if value < MIN_QUANTITY:
        raise serializers.ValidationError(
            f"Кількість має бути не меншою за {MIN_QUANTITY}."
        )
    if value > MAX_QUANTITY:
        raise serializers.ValidationError(
            f"Кількість не може перевищувати {MAX_QUANTITY}."
        )
    return value


class ConflictError(APIException):
    """HTTP 409 Conflict для заборонених переходів станів та порушень інваріанта."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Недопустимий перехід стану або конфлікт стану заявки."
    default_code = "conflict"


def custom_exception_handler(exc, context):
    """Перетворює необроблені винятки Django/SQLite на осмислені 400 / 409 замість 500."""
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, OverflowError):
        return Response(
            {"detail": "Числове значення виходить за допустимі межі."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError):
        return Response(
            {"detail": "Конфлікт цілісності даних або стану ресурсу."},
            status=status.HTTP_409_CONFLICT,
        )

    return None


class IsCatalogReadOnlyOrAdmin(permissions.BasePermission):
    """Каталог вікон автомийки: читають усі (200), змінює лише адмін/staff (401/403)."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwner(permissions.BasePermission):
    """Права на заявки: лише з токеном (401) і лише для власника (403).

    Для заявок не в стані `draft` забороняє `PUT`/`PATCH`/`DELETE` з кодом `409`,
    щоб не можна було змінити кількість чи видалити підтверджену заявку в обхід `cancel`.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Сувора перевірка власника без винятків навіть для is_staff
        owner_id = getattr(obj, "owner_id", None)
        user_id = getattr(request.user, "id", None)
        if owner_id is not None and user_id is not None:
            is_owner = owner_id == user_id
        else:
            owner = getattr(obj, "owner", None)
            if owner is None:
                owner = getattr(obj, "user", None)
            is_owner = owner is not None and owner == request.user

        if not is_owner:
            return False

        # Захист інваріанта: редагувати або видаляти можна лише чернетку (draft)
        if request.method in ("PUT", "PATCH", "DELETE"):
            if getattr(obj, "status", "draft") != "draft":
                raise ConflictError(
                    "Змінювати або видаляти можна лише заявку в стані 'draft'."
                )

        return True


class OwnerSafeViewSetMixin:
    """Базовий міксин безпеки для ViewSet заявок.

    У `views.py` успадковуйте першим:
        class BookingViewSet(OwnerSafeViewSetMixin, viewsets.ModelViewSet):
    """

    permission_classes = [IsOwner]
    owner_field = "owner"

    def dispatch(self, request, *args, **kwargs):
        if request.method not in permissions.SAFE_METHODS and kwargs:
            with transaction.atomic():
                response = super().dispatch(request, *args, **kwargs)
                if response.status_code >= 400:
                    transaction.set_rollback(True)
                return response
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return qs.none()
        return qs.filter(**{self.owner_field: user})

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        raw_val = self.kwargs.get(lookup_url_kwarg)
        if raw_val is not None:
            try:
                if abs(int(raw_val)) > SQLITE_MAX_INT:
                    raise Http404
            except (TypeError, ValueError):
                pass
        return super().get_object()

    def perform_create(self, serializer):
        serializer.save(**{self.owner_field: self.request.user, "status": "draft"})

    def perform_update(self, serializer):
        instance = serializer.instance
        with transaction.atomic():
            is_still_draft = (
                type(instance).objects.filter(pk=instance.pk, status="draft").exists()
            )
            if not is_still_draft:
                raise ConflictError(
                    "Змінювати або видаляти можна лише заявку в стані 'draft'."
                )
            serializer.save(**{self.owner_field: self.request.user, "status": "draft"})

    def perform_destroy(self, instance):
        with transaction.atomic():
            deleted, _ = (
                type(instance).objects.filter(pk=instance.pk, status="draft").delete()
            )
            if not deleted:
                raise ConflictError(
                    "Змінювати або видаляти можна лише заявку в стані 'draft'."
                )


# Зручні аліаси для сумісності
IsBookingOwner = IsOwner
IsOrderOwner = IsOwner

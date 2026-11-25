"""Роль «API». ViewSet-и каталогу і заявок; @action confirm / cancel
викликають функції з services.py і нічого не рахують самі."""

from rest_framework import viewsets  # noqa: F401

from .permissions import (  # noqa: F401
    ConflictError,
    IsCatalogReadOnlyOrAdmin,
    IsOwner,
    OwnerSafeViewSetMixin,
)

# === ПОСЛАННЯ ДЛЯ РОЗРОБНИКА РОЛІ «API» ВІД РОЛІ «ДОСТУП» ===
# Права доступу, ізоляція власника та захист станів уже готові в `api/permissions.py`
# і підключені імпортами вище. Будь ласка, НЕ переписуй і НЕ вимикай їх:
#
# 1. Для каталогу (`WashSlotViewSet` — ReadOnlyModelViewSet або ModelViewSet):
#        permission_classes = [IsCatalogReadOnlyOrAdmin]
#    (Відкритий GET без токена = 200; зміна каталогу звичайним юзером = 403).
#
# 2. Для заявок (`BookingViewSet`): став `OwnerSafeViewSetMixin` ПЕРШИМ у спадкуванні:
#        class BookingViewSet(OwnerSafeViewSetMixin, viewsets.ModelViewSet):
#            queryset = Booking.objects.all()
#            serializer_class = BookingSerializer
#    Не перевизначай `permission_classes`, `get_queryset()` або `perform_create()`
#    без виклику `super()`, бо міксин уже забезпечує:
#    - 401 без токена (рядки 2, 3, 4);
#    - видимість і дії лише для власника (рядки 7–10);
#    - захист від підміни `owner` / `status` (рядки 11–12);
#    - 409 Conflict при спробі PATCH / PUT / DELETE заявки не в стані `draft`;
#    - 404 замість 500 при гігантських ID в URL.
#
# 3. У `@action(detail=True, methods=["post"])` для `confirm` і `cancel`:
#    Обов'язково ПЕРШИМ рядком викликай `booking = self.get_object()`, щоб спрацювали
#    перевірки 401/403/404 перед викликом `services.py`!
#    Пам'ятай про коди відповідей:
#    - недопустимий перехід стану (confirmed->confirmed, cancelled->*) -> 409 (можеш кидати `ConflictError`)
#    - нестача залишку при confirm -> 400
#
# 4. (Опціонально) Для повної страховки від 500 у `config/settings.py` в `REST_FRAMEWORK`
#    можна додати: `"EXCEPTION_HANDLER": "api.permissions.custom_exception_handler"`

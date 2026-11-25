"""Роль «Доступ». Власні класи прав та перевірок доступу.

Захищає рядки 1–4, 7–10 карти атаки:
- Каталог відкритий для читання будь-кому (GET/HEAD/OPTIONS без токена => 200).
- Заявки доступні ТІЛЬКИ автентифікованим користувачам (без токена => 401).
- Будь-які дії над конкретною заявкою (GET, PATCH, DELETE, confirm, cancel)
  дозволені виключно її власнику (чужий користувач => 403 Forbidden).

УВАГА: `has_object_permission` спрацьовує лише для детальних операцій (retrieve, update,
destroy, custom @actions). Для списку (list) обов'язково фільтрувати у `get_queryset()`:
    queryset = queryset.filter(owner=self.request.user)
"""

from rest_framework import permissions


class IsCatalogReadOnlyOrAdmin(permissions.BasePermission):
    """Каталог (послуги / бокси / слоти мийки).

    Відповідає за Рядок 1 карти атаки:
    - Будь-хто (навіть анонімний клієнт без токена) має право читати каталог (SAFE_METHODS).
    - Змінювати каталог через API звичайним клієнтам заборонено (тільки admin/staff).
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class IsOwner(permissions.BasePermission):
    """Захист заявок (бронювань на автомийку).

    Відповідає за Рядки 2, 3, 4, 8, 9, 10 карти атаки:
    - Без валідного токена доступ повністю блокується (DRF поверне 401).
    - Окрему заявку (detail view, confirm, cancel) бачить і змінює ТІЛЬКИ її власник.
      Спроба доступу чужого користувача повертає 403 Forbidden.
    """

    def has_permission(self, request, view):
        # Обов'язкова наявність автентифікованого користувача (якщо нема -> 401 Unauthorized)
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Якщо запит від адміна/staff — дозволяємо
        if request.user and request.user.is_staff:
            return True

        # Визначаємо поле власника (підтримуємо як 'owner', так і 'user')
        owner = getattr(obj, "owner", None)
        if owner is None:
            owner = getattr(obj, "user", None)

        # Безпечна перевірка: об'єкт належить поточному користувачу
        return owner == request.user


# Зручний аліас для сумісності
IsOrderOwner = IsOwner
IsBookingOwner = IsOwner

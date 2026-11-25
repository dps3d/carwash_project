from rest_framework.routers import DefaultRouter

from .views import BookingViewSet, WashSlotViewSet

router = DefaultRouter()
router.register("slots", WashSlotViewSet, basename="slot")
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = router.urls

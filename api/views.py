from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import Booking, WashSlot
from .permissions import IsCatalogReadOnlyOrAdmin, OwnerSafeViewSetMixin
from .serializers import BookingSerializer, WashSlotSerializer


class WashSlotViewSet(viewsets.ModelViewSet):
    queryset = WashSlot.objects.all()
    serializer_class = WashSlotSerializer
    permission_classes = [IsCatalogReadOnlyOrAdmin]


class BookingViewSet(OwnerSafeViewSetMixin, viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        try:
            services.confirm(booking)
        except services.Conflict as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        booking.refresh_from_db()
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        try:
            services.cancel(booking)
        except services.Conflict as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        booking.refresh_from_db()
        return Response(self.get_serializer(booking).data)

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("", lambda request: redirect("/api/v1/slots/")),
    path("admin/", admin.site.urls),
    # Вхід: POST {"username": ..., "password": ...} → {"access": ..., "refresh": ...}
    path("api/v1/auth/token/", TokenObtainPairView.as_view()),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view()),
    path("api/v1/", include("api.urls")),
]

from django.contrib import admin
from django.urls import include, path

from .testapp import views as testapp_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("payments/", include("payments.urls")),
    path(
        "payment-details/<int:payment_id>",
        testapp_views.payment_details,
        name="payment-details",
    ),
]

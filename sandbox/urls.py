"""sandbox URL Configuration"""
from django.contrib import admin
from django.urls import include, path
from example_app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("payments/", include("payments.urls")),
    path(
        "payment-failure/<int:payment_id>",
        views.payment_failure,
        name="payment-failure",
    ),
    path(
        "payment-success/<int:payment_id>",
        views.payment_success,
        name="payment-success",
    ),
    path(
        "payment-details/<int:payment_id>",
        views.payment_details,
        name="payment-details",
    ),
    path("create-payment/", views.create_payment),
]

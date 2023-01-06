import logging
from decimal import Decimal

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from payments import RedirectNeeded, get_payment_model

Payment = get_payment_model()


def payment_details(request, payment_id):
    payment = get_object_or_404(get_payment_model(), id=payment_id)

    try:
        form = payment.get_form(data=request.POST or None)
    except RedirectNeeded as redirect_to:
        return redirect(str(redirect_to))

    return TemplateResponse(
        request,
        "payment.html",
        {"form": form, "payment": payment},
    )


def payment_start(request):
    """Create a new payment (for manual testing)"""
    if "create" not in request.GET.keys():
        return HttpResponse(f"<a href='{request.path}?create'>Create new payment</a>")
    else:
        payment = Payment.objects.create(
            variant="mollie",
            description="Book purchase",
            total=Decimal(120),
            currency="EUR",
        )

        logging.warning(f"New payment created with id '{payment.id}', now redirecting")
        return redirect(reverse("payment-details", kwargs={"payment_id": payment.id}))


def payment_success(request, payment_id):
    """Display a successful payment (for manual testing)"""
    payment = Payment.objects.get(id=payment_id)
    return HttpResponse(
        f"Payment successful: status={payment.status}, amount={payment.captured_amount}"
    )


def payment_failure(request, payment_id):
    """Display a failed payment (for manual testing)"""
    payment = Payment.objects.get(id=payment_id)
    return HttpResponse(
        f"Payment failed: status={payment.status} message={payment.message}"
    )

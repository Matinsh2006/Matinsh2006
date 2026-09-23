"""تست‌های چرخه‌ی پرداخت بیعانه."""
from __future__ import annotations

import datetime as dt

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment, WorkingHour
from appointments.scheduling import available_slots, working_hour_for
from core.models import SiteSettings
from payments.gateways import SandboxGateway, ZarinPalGateway, get_gateway
from payments.models import Payment
from services.models import Service

User = get_user_model()


@override_settings(PAYMENT_GATEWAY="payments.gateways.SandboxGateway")
class DepositPaymentTests(TestCase):
    def setUp(self):
        WorkingHour.ensure_defaults()
        self.service = Service.objects.create(title="صافکاری", duration_minutes=60, deposit_amount=200000)
        self.user = User.objects.create_user("09121112233")
        self.client.force_login(self.user, backend="accounts.backends.PhoneBackend")

        day = timezone.localdate() + dt.timedelta(days=1)
        while working_hour_for(day) is None:
            day += dt.timedelta(days=1)
        self.appointment = Appointment.objects.create(
            user=self.user, service=self.service, date=day,
            start_time=available_slots(day, self.service)[0], description="تست",
        )

    def test_gateway_is_loaded_from_settings(self):
        self.assertIsInstance(get_gateway(), SandboxGateway)

    @override_settings(PAYMENT_GATEWAY="zarinpal")
    def test_gateway_alias_resolves(self):
        self.assertIsInstance(get_gateway(), ZarinPalGateway)

    def test_start_payment_creates_transaction(self):
        response = self.client.get(reverse("payments:start", args=[self.appointment.tracking_code]))
        payment = Payment.objects.get(appointment=self.appointment)
        self.assertEqual(payment.amount, 200000)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertRedirects(response, reverse("payments:sandbox", args=[payment.invoice_number]))

    def test_successful_payment_confirms_appointment(self):
        self.client.get(reverse("payments:start", args=[self.appointment.tracking_code]))
        payment = Payment.objects.get(appointment=self.appointment)

        self.client.post(reverse("payments:sandbox", args=[payment.invoice_number]), {"action": "pay"}, follow=True)
        payment.refresh_from_db()
        self.appointment.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.PAID)
        self.assertTrue(payment.ref_id)
        self.assertIsNotNone(payment.paid_at)
        self.assertTrue(self.appointment.is_deposit_paid)
        self.assertEqual(self.appointment.status, Appointment.Status.CONFIRMED)

    def test_cancelled_payment_leaves_appointment_pending(self):
        self.client.get(reverse("payments:start", args=[self.appointment.tracking_code]))
        payment = Payment.objects.get(appointment=self.appointment)

        self.client.post(reverse("payments:sandbox", args=[payment.invoice_number]), {"action": "cancel"}, follow=True)
        payment.refresh_from_db()
        self.appointment.refresh_from_db()

        self.assertEqual(payment.status, Payment.Status.CANCELLED)
        self.assertFalse(self.appointment.is_deposit_paid)
        self.assertEqual(self.appointment.status, Appointment.Status.PENDING)

    def test_paid_deposit_cannot_be_paid_twice(self):
        self.client.get(reverse("payments:start", args=[self.appointment.tracking_code]))
        payment = Payment.objects.get(appointment=self.appointment)
        self.client.post(reverse("payments:sandbox", args=[payment.invoice_number]), {"action": "pay"}, follow=True)

        response = self.client.get(reverse("payments:start", args=[self.appointment.tracking_code]), follow=True)
        self.assertEqual(Payment.objects.filter(appointment=self.appointment).count(), 1)
        self.assertContains(response, "قبلاً پرداخت شده")

    def test_online_payment_can_be_disabled(self):
        site = SiteSettings.load()
        site.online_payment_enabled = False
        site.save()
        response = self.client.get(reverse("payments:start", args=[self.appointment.tracking_code]), follow=True)
        self.assertFalse(Payment.objects.exists())
        self.assertContains(response, "غیرفعال")

    def test_other_user_cannot_start_payment(self):
        self.client.logout()
        intruder = User.objects.create_user("09355556677")
        self.client.force_login(intruder, backend="accounts.backends.PhoneBackend")
        response = self.client.get(reverse("payments:start", args=[self.appointment.tracking_code]))
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_open_receipt(self):
        self.client.get(reverse("payments:start", args=[self.appointment.tracking_code]))
        payment = Payment.objects.get(appointment=self.appointment)
        self.client.logout()
        intruder = User.objects.create_user("09355556677")
        self.client.force_login(intruder, backend="accounts.backends.PhoneBackend")
        response = self.client.get(reverse("payments:receipt", args=[payment.invoice_number]))
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_invoice_numbers_are_unique(self):
        numbers = {Payment.generate_invoice_number() for _ in range(40)}
        self.assertEqual(len(numbers), 40)

    def test_amount_conversion_to_rial(self):
        payment = Payment(amount=200000, user=self.user)
        self.assertEqual(payment.amount_rial, 2000000)

    @override_settings(ZARINPAL_MERCHANT_ID="")
    def test_zarinpal_without_merchant_id_fails_gracefully(self):
        payment = Payment.objects.create(user=self.user, amount=1000, gateway="zarinpal")
        result = ZarinPalGateway().request_payment(payment, "https://example.com/callback/")
        self.assertFalse(result.ok)
        self.assertIn("مرچنت‌کد", result.error)

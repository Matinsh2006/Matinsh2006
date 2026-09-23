"""
ساخت حساب کارفرما (مدیر سایت).

    python manage.py create_owner --phone 09121234567

اگر رمز عبور داده نشود، به صورت تعاملی پرسیده می‌شود.
"""
from __future__ import annotations

from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from core.validators import normalize_phone, validate_iran_mobile

User = get_user_model()


class Command(BaseCommand):
    help = "ساخت یا به‌روزرسانی حساب کارفرما با دسترسی کامل"

    def add_arguments(self, parser):
        parser.add_argument("--phone", required=True, help="شماره موبایل کارفرما، مثال: 09121234567")
        parser.add_argument("--name", default="", help="نام و نام خانوادگی")
        parser.add_argument("--password", default="", help="رمز عبور (در صورت خالی بودن پرسیده می‌شود)")

    def handle(self, *args, **options):
        phone = normalize_phone(options["phone"])
        try:
            validate_iran_mobile(phone)
        except ValidationError as exc:
            raise CommandError(exc.messages[0]) from exc

        password = options["password"] or getpass("رمز عبور: ")
        if not password:
            raise CommandError("رمز عبور نمی‌تواند خالی باشد.")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(" / ".join(exc.messages)) from exc

        user, created = User.objects.get_or_create(phone=phone)
        user.full_name = options["name"] or user.full_name
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.is_phone_verified = True
        user.set_password(password)
        user.save()

        action = "ساخته شد" if created else "به‌روزرسانی شد"
        self.stdout.write(self.style.SUCCESS(f"حساب کارفرما با شماره {phone} {action}."))
        self.stdout.write("ورود به پنل: /panel/  —  ورود پیشرفته: /admin/")

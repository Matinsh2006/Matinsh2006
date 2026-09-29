"""Small factories shared by the test suites."""
import itertools

from apps.accounts.models import Address, User
from apps.catalog.models import Brand, Category, Product

_counter = itertools.count(1)


def make_user(phone=None, **extra):
    phone = phone or f"0912{next(_counter):07d}"
    return User.objects.create_user(phone=phone, **extra)


def make_category(name="مراقبت از پوست", **extra):
    return Category.objects.create(name=name, **extra)


def make_brand(name=None, **extra):
    name = name or f"برند {next(_counter)}"
    return Brand.objects.create(name=name, **extra)


def make_product(name=None, price=100000, stock=10, **extra):
    name = name or f"محصول {next(_counter)}"
    return Product.objects.create(name=name, price=price, stock=stock, **extra)


def make_address(user, **extra):
    data = {
        "receiver_name": "سارا محمدی",
        "receiver_phone": "09121112233",
        "province": "تهران",
        "city": "تهران",
        "full_address": "خیابان آزادی، پلاک ۱",
        "postal_code": "1234567890",
    }
    data.update(extra)
    return Address.objects.create(user=user, **data)

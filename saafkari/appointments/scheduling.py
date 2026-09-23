"""محاسبه‌ی نوبت‌های خالی بر اساس ساعت کاری، تعطیلات و نوبت‌های ثبت‌شده."""
from __future__ import annotations

import datetime as dt

from django.utils import timezone

from core.jalali import jalali_weekday

from .models import Appointment, Holiday, WorkingHour

#: حداکثر روزهای پیش‌رو که مشتری می‌تواند نوبت بگیرد
BOOKING_WINDOW_DAYS = 60


def is_holiday(date: dt.date) -> bool:
    return Holiday.objects.filter(date=date).exists()


def working_hour_for(date: dt.date) -> WorkingHour | None:
    """ساعت کاری روز موردنظر؛ در صورت تعطیل بودن، ‎None‎."""
    if is_holiday(date):
        return None
    hour = WorkingHour.objects.filter(weekday=jalali_weekday(date)).first()
    if hour is None or not hour.is_open:
        return None
    return hour


def _overlaps(start_a, end_a, start_b, end_b) -> bool:
    return start_a < end_b and start_b < end_a


def available_slots(date: dt.date, service=None, exclude_pk: int | None = None) -> list[dt.time]:
    """
    فهرست ساعت‌های خالی یک روز.

    مدت هر نوبت از روی مدت خدمت محاسبه می‌شود و نوبت‌های رزروشده‌ی هم‌پوشان
    (با احتساب ظرفیت هم‌زمان مغازه) کنار گذاشته می‌شوند.
    """
    if date is None:
        return []
    hour = working_hour_for(date)
    if hour is None:
        return []

    duration = (service.duration_minutes if service and service.duration_minutes else hour.slot_minutes) or 60
    step = dt.timedelta(minutes=hour.slot_minutes or 60)
    day_start = dt.datetime.combine(date, hour.open_time)
    day_end = dt.datetime.combine(date, hour.close_time)
    now = timezone.localtime()

    booked = list(
        Appointment.objects.filter(date=date, status__in=Appointment.BLOCKING_STATUSES)
        .exclude(pk=exclude_pk)
        .values_list("start_time", "end_time")
    )

    slots: list[dt.time] = []
    cursor = day_start
    while cursor + dt.timedelta(minutes=duration) <= day_end:
        slot_start = cursor
        slot_end = cursor + dt.timedelta(minutes=duration)
        # نوبت‌های گذشته‌ی امروز نمایش داده نمی‌شوند
        if date > now.date() or slot_start.time() > now.time():
            taken = 0
            for booked_start, booked_end in booked:
                booked_start_dt = dt.datetime.combine(date, booked_start)
                booked_end_dt = dt.datetime.combine(date, booked_end or booked_start)
                if _overlaps(slot_start, slot_end, booked_start_dt, booked_end_dt):
                    taken += 1
            if taken < hour.capacity:
                slots.append(slot_start.time())
        cursor += step
    return slots


def is_slot_available(date: dt.date, start_time: dt.time, service=None, exclude_pk: int | None = None) -> bool:
    """بررسی اینکه ساعت انتخابی مشتری هنوز خالی است."""
    return start_time in available_slots(date, service=service, exclude_pk=exclude_pk)


def booking_window() -> tuple[dt.date, dt.date]:
    """بازه‌ی مجاز رزرو: از امروز تا ‎BOOKING_WINDOW_DAYS‎ روز بعد."""
    today = timezone.localdate()
    return today, today + dt.timedelta(days=BOOKING_WINDOW_DAYS)


def open_weekdays() -> list[int]:
    """روزهای هفته‌ای که مغازه باز است (شنبه=۰)."""
    return list(WorkingHour.objects.filter(is_open=True).values_list("weekday", flat=True))


def upcoming_holidays(limit: int = 60) -> list[str]:
    """تاریخ تعطیلات پیش‌رو به صورت ‎YYYY-MM-DD‎ میلادی برای تقویم جاوااسکریپتی."""
    start, end = booking_window()
    return [
        holiday.date.isoformat()
        for holiday in Holiday.objects.filter(date__range=(start, end)).order_by("date")[:limit]
    ]

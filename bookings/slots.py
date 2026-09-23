import datetime

from salon.models import SalonProfile

from .models import Appointment


def get_available_slots(service, date_value):
    """Available start times (datetime.time) for booking `service` on the
    given Gregorian `date_value`, based on the salon's working hours/days and
    any existing (non-cancelled) appointments that would overlap."""
    if date_value < datetime.date.today():
        return []

    salon = SalonProfile.get_solo()
    if not salon.is_open_on(date_value):
        return []

    duration = datetime.timedelta(minutes=service.duration_minutes)
    step_minutes = salon.slot_duration_minutes or 30
    step = datetime.timedelta(minutes=step_minutes)

    day_start = datetime.datetime.combine(date_value, salon.opening_time)
    day_end = datetime.datetime.combine(date_value, salon.closing_time)

    busy_ranges = [
        (
            datetime.datetime.combine(date_value, appt.start_time),
            datetime.datetime.combine(date_value, appt.end_time),
        )
        for appt in Appointment.objects.filter(date=date_value).exclude(
            status=Appointment.STATUS_CANCELLED
        )
    ]

    now = datetime.datetime.now()
    is_today = date_value == datetime.date.today()

    slots = []
    cursor = day_start
    while cursor + duration <= day_end:
        slot_end = cursor + duration
        if not (is_today and cursor <= now):
            overlaps = any(
                cursor < busy_end and slot_end > busy_start
                for busy_start, busy_end in busy_ranges
            )
            if not overlaps:
                slots.append(cursor.time())
        cursor += step

    return slots

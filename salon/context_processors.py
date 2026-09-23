from .models import SalonProfile


def salon_profile(request):
    return {"salon_profile": SalonProfile.get_solo()}

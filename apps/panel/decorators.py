from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def staff_required(view_func):
    @wraps(view_func)
    @login_required(login_url="panel:login")
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            logout(request)
            messages.error(request, "Sizda panelga kirish huquqi yo'q.")
            return redirect("panel:login")
        return view_func(request, *args, **kwargs)

    return wrapper


def superuser_required(view_func):
    @staff_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "Bu bo'lim faqat super admin uchun.")
            return redirect("panel:dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.bookings.models import Booking, Match
from apps.stadiums.models import Stadium
from apps.wallet import services
from apps.wallet.models import TopUpRequest, Wallet

from .decorators import staff_required, superuser_required

User = get_user_model()


def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("panel:dashboard")

    error = None
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=phone, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect("panel:dashboard")
        error = "Telefon raqam yoki parol noto'g'ri, yoki sizda ruxsat yo'q."

    return render(request, "panel/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("panel:login")


@staff_required
def dashboard(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    stats = {
        "total_users": User.objects.count(),
        "new_today": User.objects.filter(created_at__gte=today_start).count(),
        "new_week": User.objects.filter(created_at__gte=week_start).count(),
        "new_month": User.objects.filter(created_at__gte=month_start).count(),
        "total_stadiums": Stadium.objects.filter(is_active=True).count(),
        "total_matches": Match.objects.count(),
        "matches_waiting": Match.objects.filter(status=Match.Status.WAITING).count(),
        "matches_confirmed": Match.objects.filter(status=Match.Status.CONFIRMED).count(),
        "matches_finished": Match.objects.filter(status=Match.Status.FINISHED).count(),
        "total_bookings": Booking.objects.count(),
        "paid_revenue": Booking.objects.filter(payment_status=Booking.PaymentStatus.PAID).aggregate(
            s=Sum("amount_charged")
        )["s"]
        or 0,
        "wallet_total": Wallet.objects.aggregate(s=Sum("balance_usd"))["s"] or 0,
        "topup_pending": TopUpRequest.objects.filter(status=TopUpRequest.Status.PENDING).count(),
        "topup_month_total": TopUpRequest.objects.filter(
            status=TopUpRequest.Status.APPROVED, created_at__gte=month_start
        ).aggregate(s=Sum("amount"))["s"]
        or 0,
    }

    pending_topups = (
        TopUpRequest.objects.select_related("user", "payment_method")
        .filter(status=TopUpRequest.Status.PENDING)
        .order_by("-created_at")[:8]
    )
    recent_users = User.objects.order_by("-created_at")[:8]
    top_stadiums = Stadium.objects.annotate(match_count=Count("matches")).order_by("-match_count")[:5]

    signup_series = []
    max_count = 1
    for i in range(13, -1, -1):
        day = today_start - timedelta(days=i)
        next_day = day + timedelta(days=1)
        count = User.objects.filter(created_at__gte=day, created_at__lt=next_day).count()
        max_count = max(max_count, count)
        signup_series.append({"label": day.strftime("%d/%m"), "count": count})
    for point in signup_series:
        point["pct"] = round(point["count"] / max_count * 100)

    return render(
        request,
        "panel/dashboard.html",
        {
            "stats": stats,
            "pending_topups": pending_topups,
            "recent_users": recent_users,
            "top_stadiums": top_stadiums,
            "signup_series": signup_series,
        },
    )


@staff_required
def users_list(request):
    q = request.GET.get("q", "").strip()
    qs = User.objects.order_by("-created_at")
    if q:
        filters = Q(phone__icontains=q) | Q(full_name__icontains=q) | Q(telegram_username__icontains=q)
        if q.isdigit():
            filters |= Q(telegram_id=q)
        qs = qs.filter(filters)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "panel/users_list.html", {"page_obj": page_obj, "q": q})


@staff_required
def user_detail(request, pk):
    target = get_object_or_404(User, pk=pk)
    wallet, _ = Wallet.objects.get_or_create(user=target)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "topup":
            try:
                amount = Decimal(request.POST.get("amount", "0"))
            except InvalidOperation:
                amount = Decimal("0")
            note = request.POST.get("note", "").strip() or f"Admin top-up by {request.user}"
            if amount > 0:
                services.credit(target, amount, title="Admin top-up", subtitle=note)
                messages.success(request, f"${amount} hisobga qo'shildi.")
            else:
                messages.error(request, "Summani to'g'ri kiriting.")
        elif action == "toggle_active":
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
            messages.success(request, "Foydalanuvchi holati yangilandi.")
        return redirect("panel:user_detail", pk=pk)

    transactions = wallet.transactions.order_by("-created_at")[:20]
    bookings = target.bookings.select_related("match", "match__stadium").order_by("-created_at")[:20]
    badges = target.badges.select_related("badge")

    return render(
        request,
        "panel/user_detail.html",
        {
            "target": target,
            "wallet": wallet,
            "transactions": transactions,
            "bookings": bookings,
            "badges": badges,
        },
    )


@superuser_required
def admins_list(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")

        if not phone or not password:
            messages.error(request, "Telefon raqam va parol majburiy.")
        elif User.objects.filter(phone=phone).exists():
            messages.error(request, "Bu telefon raqam bilan foydalanuvchi mavjud.")
        elif len(password) < 6:
            messages.error(request, "Parol kamida 6 belgidan iborat bo'lsin.")
        else:
            User.objects.create_user(
                phone=phone,
                password=password,
                full_name=full_name,
                is_staff=True,
                is_onboarded=True,
            )
            messages.success(request, "Yangi admin qo'shildi.")
        return redirect("panel:admins")

    admins = User.objects.filter(is_staff=True).order_by("-is_superuser", "-created_at")
    return render(request, "panel/admins_list.html", {"admins": admins})

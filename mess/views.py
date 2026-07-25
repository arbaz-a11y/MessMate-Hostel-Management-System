from __future__ import annotations

from datetime import date

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET

from .forms import (
    AdminAuthenticationForm,
    AdminStaffCreateForm,
    AdminStudentCreateForm,
    AdminStudentEditForm,
    LeaveRequestForm,
    MealAbsenceForm,
    USNAuthenticationForm,
)
from .models import LeaveRequest, MealAbsence, StudentProfile, StudentUser


def _get_student_profile(user: StudentUser) -> StudentProfile | None:
    try:
        return user.profile
    except StudentProfile.DoesNotExist:
        return None


def _today() -> date:
    return timezone.localdate()


def _homepage_stats():
    """Lightweight aggregates for marketing-style stats on the landing page."""

    today = _today()

    absentees_today_union = MealAbsence.objects.filter(date=today).values_list(
        "student_id", flat=True
    )
    leave_student_ids_today = LeaveRequest.objects.filter(
        from_date__lte=today, to_date__gte=today
    ).values_list("student_id", flat=True)

    # Unique students flagged absent for any meal via absence or leave today (approx.).
    flagged_today_ids = set(absentees_today_union) | set(leave_student_ids_today)

    return {
        "stat_students": StudentProfile.objects.count(),
        "stat_meals_marked_absent_today": MealAbsence.objects.filter(date=today).count(),
        "stat_students_impacted_today": len(flagged_today_ids),
    }


def home(request):
    ctx = _homepage_stats()
    return render(request, "mess/home.html", ctx)


def signup(request):
    """Public self-registration is disabled; only staff may create accounts."""
    messages.info(
        request,
        "Student accounts are created by hostel administrators. Please contact your mess admin.",
    )
    return redirect("login")


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("admin_dashboard")
        return redirect("student_dashboard")

    if request.method == "POST":
        form = USNAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_staff:
                messages.error(
                    request,
                    "Staff accounts must use Admin Login with username and password.",
                )
                return redirect("admin_login")
            login(request, user)
            messages.success(request, "Logged in successfully.")
            return redirect("student_dashboard")
    else:
        form = USNAuthenticationForm(request)

    return render(request, "mess/login.html", {"form": form})


def admin_login(request):
    """
    Staff entry point branded as Mess Admin login.
    Grants access only when the authenticated user has is_staff.
    """

    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("admin_dashboard")
        messages.warning(
            request,
            "You're signed in as a student. Mess admin login is only for staff accounts.",
        )
        return redirect("student_dashboard")

    if request.method == "POST":
        form = AdminAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_staff:
                messages.error(request, "This login is restricted to hostel mess admins.")
                return render(request, "mess/admin_login.html", {"form": form})

            login(request, user)
            messages.success(request, "Signed in as mess admin.")
            return redirect("admin_dashboard")
    else:
        form = AdminAuthenticationForm(request)

    return render(request, "mess/admin_login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


@login_required
def student_dashboard(request):
    profile = _get_student_profile(request.user)
    if profile is None:
        messages.error(request, "Student profile not found. Please contact admin.")
        return redirect("home")

    today = _today()

    # A student is absent if they submitted a single-meal absence OR have an active leave covering today.
    leave_active_today = LeaveRequest.objects.filter(
        student=profile, from_date__lte=today, to_date__gte=today
    ).exists()

    absent_breakfast = leave_active_today or MealAbsence.objects.filter(
        student=profile, date=today, meal_type=MealAbsence.MealType.BREAKFAST
    ).exists()
    absent_lunch = leave_active_today or MealAbsence.objects.filter(
        student=profile, date=today, meal_type=MealAbsence.MealType.LUNCH
    ).exists()
    absent_dinner = leave_active_today or MealAbsence.objects.filter(
        student=profile, date=today, meal_type=MealAbsence.MealType.DINNER
    ).exists()

    upcoming_meal_absences = MealAbsence.objects.filter(
        student=profile, date__gte=today
    ).order_by("date", "meal_type")
    upcoming_leave_requests = LeaveRequest.objects.filter(
        student=profile, to_date__gte=today
    ).order_by("from_date")

    meal_history = MealAbsence.objects.filter(student=profile, date__lt=today).order_by("-date")[
        :25
    ]

    # Simple dashboard notifications (not the staff "unseen" system).
    dashboard_notifications: list[str] = []
    if leave_active_today:
        dashboard_notifications.append(
            "You have an approved leave window that covers today — all meals are treated as absent."
        )
    if not upcoming_meal_absences.exists() and not upcoming_leave_requests.exists():
        dashboard_notifications.append(
            "No upcoming absences scheduled. Submit early to help the mess reduce wastage."
        )
    elif upcoming_meal_absences.exists():
        dashboard_notifications.append(
            "Tip: Cancel or adjust absences before the meal day if your plans change."
        )

    return render(
        request,
        "mess/student_dashboard.html",
        {
            "profile": profile,
            "today": today,
            "absent_breakfast": absent_breakfast,
            "absent_lunch": absent_lunch,
            "absent_dinner": absent_dinner,
            "upcoming_meal_absences": upcoming_meal_absences,
            "upcoming_leave_requests": upcoming_leave_requests,
            "meal_history": meal_history,
            "dashboard_notifications": dashboard_notifications,
        },
    )


@login_required
def meal_absence_create(request):
    profile = _get_student_profile(request.user)
    if profile is None:
        messages.error(request, "Student profile not found.")
        return redirect("home")

    if request.method == "POST":
        form = MealAbsenceForm(request.POST, student=profile)
        if form.is_valid():
            obj: MealAbsence = form.save(commit=False)
            obj.student = profile
            obj.is_seen = False
            obj.save()
            messages.success(request, "Meal absence submitted successfully.")
            return redirect("request_history")
    else:
        form = MealAbsenceForm()

    return render(request, "mess/meal_absence_form.html", {"form": form})


@login_required
def leave_request_create(request):
    profile = _get_student_profile(request.user)
    if profile is None:
        messages.error(request, "Student profile not found.")
        return redirect("home")

    if request.method == "POST":
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            obj: LeaveRequest = form.save(commit=False)
            obj.student = profile
            obj.is_seen = False
            obj.save()
            messages.success(request, "Leave request submitted successfully.")
            return redirect("request_history")
    else:
        form = LeaveRequestForm()

    return render(request, "mess/leave_request_form.html", {"form": form})


@login_required
def request_history(request):
    profile = _get_student_profile(request.user)
    if profile is None:
        messages.error(request, "Student profile not found.")
        return redirect("home")

    today = _today()

    meal_absences = MealAbsence.objects.filter(student=profile)
    leave_requests = LeaveRequest.objects.filter(student=profile)

    return render(
        request,
        "mess/request_history.html",
        {
            "today": today,
            "meal_absences": meal_absences,
            "leave_requests": leave_requests,
        },
    )


@login_required
def cancel_meal_absence(request, pk: int):
    profile = _get_student_profile(request.user)
    if profile is None:
        messages.error(request, "Student profile not found.")
        return redirect("home")

    obj = get_object_or_404(MealAbsence, pk=pk, student=profile)
    today = _today()

    if request.method == "POST":
        if obj.date < today:
            messages.error(request, "You cannot cancel past meal requests.")
        else:
            obj.delete()
            messages.success(request, "Meal absence request cancelled.")
    else:
        messages.error(request, "Invalid request.")

    return redirect("request_history")


@login_required
def cancel_leave_request(request, pk: int):
    profile = _get_student_profile(request.user)
    if profile is None:
        messages.error(request, "Student profile not found.")
        return redirect("home")

    obj = get_object_or_404(LeaveRequest, pk=pk, student=profile)
    today = _today()

    if request.method == "POST":
        if obj.to_date < today:
            messages.error(request, "You cannot cancel past leave requests.")
        else:
            obj.delete()
            messages.success(request, "Leave request cancelled.")
    else:
        messages.error(request, "Invalid request.")

    return redirect("request_history")


def _parse_date_param(date_str: str | None) -> date | None:
    if not date_str:
        return None
    parsed = parse_date(date_str)
    return parsed


def _student_search_q(queryset, q: str):
    if not q:
        return queryset
    return queryset.filter(
        Q(student__full_name__icontains=q)
        | Q(student__usn__icontains=q)
        | Q(student__email__icontains=q)
    )


def _profile_list_search(queryset, q: str):
    if not q:
        return queryset
    return queryset.filter(
        Q(full_name__icontains=q) | Q(usn__icontains=q) | Q(email__icontains=q)
    )


def _student_management_stats() -> dict[str, int]:
    total = StudentProfile.objects.count()
    active = StudentProfile.objects.filter(user__is_active=True).count()
    return {
        "students_count": total,
        "active_students_count": active,
    }


def _absent_student_ids_for_meal(filter_date: date, meal_type: str) -> set[int]:
    single = set(
        MealAbsence.objects.filter(date=filter_date, meal_type=meal_type).values_list(
            "student_id", flat=True
        )
    )
    leave = set(
        LeaveRequest.objects.filter(
            from_date__lte=filter_date, to_date__gte=filter_date
        ).values_list("student_id", flat=True)
    )
    return single | leave


@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    today = _today()

    requested_date = _parse_date_param(request.GET.get("date"))
    explicit_date_requested = requested_date is not None
    # Operational “kitchen day” defaults to today, but admins can pivot to another date.
    filter_date = requested_date or today
    q = (request.GET.get("q") or "").strip()

    students_count = StudentProfile.objects.count()
    active_leave_requests = LeaveRequest.objects.filter(to_date__gte=today).count()

    absent_breakfast_ids = _absent_student_ids_for_meal(today, MealAbsence.MealType.BREAKFAST)
    absent_lunch_ids = _absent_student_ids_for_meal(today, MealAbsence.MealType.LUNCH)
    absent_dinner_ids = _absent_student_ids_for_meal(today, MealAbsence.MealType.DINNER)

    absent_breakfast_count = len(absent_breakfast_ids)
    absent_lunch_count = len(absent_lunch_ids)
    absent_dinner_count = len(absent_dinner_ids)

    # Meal “units” flagged absent today (same metric as previous admin dashboard).
    estimated_meal_reduction_today = (
        absent_breakfast_count + absent_lunch_count + absent_dinner_count
    )

    meals_q = MealAbsence.objects.select_related("student").order_by("-created_at")
    leaves_q = LeaveRequest.objects.select_related("student").order_by("-created_at")

    meals_q = _student_search_q(meals_q, q)
    leaves_q = _student_search_q(leaves_q, q)

    # Recent tables show global freshest submissions unless staff explicitly selects a lens date.
    if explicit_date_requested:
        meals_q = meals_q.filter(date=filter_date)
        leaves_q = leaves_q.filter(from_date__lte=filter_date, to_date__gte=filter_date)

    recent_meal_absences = meals_q[:40]
    recent_leave_requests = leaves_q[:40]

    # Also keep the date-scoped operational lists (useful for kitchen planning).
    meal_absences_for_day = MealAbsence.objects.select_related("student").filter(date=filter_date)
    leave_requests_for_day = LeaveRequest.objects.select_related("student").filter(
        from_date__lte=filter_date, to_date__gte=filter_date
    )

    if q:
        meal_absences_for_day = meal_absences_for_day.filter(
            Q(student__full_name__icontains=q)
            | Q(student__usn__icontains=q)
            | Q(student__email__icontains=q)
        )
        leave_requests_for_day = leave_requests_for_day.filter(
            Q(student__full_name__icontains=q)
            | Q(student__usn__icontains=q)
            | Q(student__email__icontains=q)
        )

    unseen_meal_count = MealAbsence.objects.filter(is_seen=False).count()
    unseen_leave_count = LeaveRequest.objects.filter(is_seen=False).count()

    return render(
        request,
        "mess/admin_dashboard.html",
        {
            "today": today,
            "filter_date": filter_date,
            "explicit_date_requested": explicit_date_requested,
            "q": q,
            "students_count": students_count,
            "active_leave_requests": active_leave_requests,
            "absent_breakfast_count": absent_breakfast_count,
            "absent_lunch_count": absent_lunch_count,
            "absent_dinner_count": absent_dinner_count,
            "estimated_meal_reduction_today": estimated_meal_reduction_today,
            "recent_meal_absences": recent_meal_absences,
            "recent_leave_requests": recent_leave_requests,
            "meal_absences_for_day": meal_absences_for_day,
            "leave_requests_for_day": leave_requests_for_day,
            "unseen_meal_count": unseen_meal_count,
            "unseen_leave_count": unseen_leave_count,
        },
    )


@user_passes_test(lambda u: u.is_staff)
@require_GET
def admin_notifications(request):
    """
    Staff notification inbox — marks unseen rows as seen after rendering (clears badges).
    """

    unseen_meals_before = MealAbsence.objects.filter(is_seen=False).count()
    unseen_leaves_before = LeaveRequest.objects.filter(is_seen=False).count()

    unseen_meals = list(
        MealAbsence.objects.filter(is_seen=False)
        .select_related("student")
        .order_by("-created_at")[:200]
    )
    unseen_leaves = list(
        LeaveRequest.objects.filter(is_seen=False)
        .select_related("student")
        .order_by("-created_at")[:200]
    )

    MealAbsence.objects.filter(is_seen=False).update(is_seen=True)
    LeaveRequest.objects.filter(is_seen=False).update(is_seen=True)

    return render(
        request,
        "mess/admin_notifications.html",
        {
            "cleared_meal_count": unseen_meals_before,
            "cleared_leave_count": unseen_leaves_before,
            "cleared_meals": unseen_meals,
            "cleared_leaves": unseen_leaves,
        },
    )


@user_passes_test(lambda u: u.is_staff)
def admin_student_records(request):
    q = (request.GET.get("q") or "").strip()
    students = StudentProfile.objects.select_related("user").order_by("usn")
    students = _profile_list_search(students, q)
    stats = _student_management_stats()

    return render(
        request,
        "mess/admin_student_records.html",
        {
            "students": students,
            "q": q,
            **stats,
        },
    )


@user_passes_test(lambda u: u.is_staff)
def admin_student_create(request):
    if request.method == "POST":
        form = AdminStudentCreateForm(request.POST)
        if form.is_valid():
            usn = form.cleaned_data["usn"]
            full_name = form.cleaned_data["full_name"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = StudentUser.objects.create_user(
                username=usn,
                email=email,
                password=password,
                first_name=full_name,
            )

            StudentProfile.objects.create(
                user=user,
                full_name=full_name,
                usn=usn,
                email=email,
                room_number="—",
            )

            messages.success(request, f"Student account created for {full_name} ({usn}).")
            return redirect("admin_student_detail", pk=user.profile.pk)
    else:
        form = AdminStudentCreateForm()

    return render(
        request,
        "mess/admin_student_form.html",
        {
            "form": form,
            "form_title": "Add student",
            "form_submit_label": "Create student",
            **_student_management_stats(),
        },
    )


@user_passes_test(lambda u: u.is_staff)
def admin_student_detail(request, pk: int):
    profile = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)
    meal_absences = MealAbsence.objects.filter(student=profile).order_by("-date", "-created_at")[
        :50
    ]
    leave_requests = LeaveRequest.objects.filter(student=profile).order_by(
        "-from_date", "-created_at"
    )[:50]

    return render(
        request,
        "mess/admin_student_detail.html",
        {
            "profile": profile,
            "meal_absences": meal_absences,
            "leave_requests": leave_requests,
            **_student_management_stats(),
        },
    )


@user_passes_test(lambda u: u.is_staff)
def admin_student_edit(request, pk: int):
    profile = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)

    if request.method == "POST":
        form = AdminStudentEditForm(request.POST, profile=profile)
        if form.is_valid():
            usn = form.cleaned_data["usn"]
            full_name = form.cleaned_data["full_name"]
            email = form.cleaned_data["email"]
            room_number = (form.cleaned_data.get("room_number") or "").strip() or "—"
            password = form.cleaned_data.get("password")
            is_active = form.cleaned_data.get("is_active", False)

            user = profile.user
            user.username = usn
            user.email = email
            user.first_name = full_name
            user.is_active = is_active
            if password:
                user.set_password(password)
            user.save()

            profile.full_name = full_name
            profile.usn = usn
            profile.email = email
            profile.room_number = room_number
            profile.save()

            messages.success(request, "Student details updated.")
            return redirect("admin_student_detail", pk=profile.pk)
    else:
        form = AdminStudentEditForm(
            initial={
                "full_name": profile.full_name,
                "usn": profile.usn,
                "email": profile.email,
                "room_number": profile.room_number if profile.room_number != "—" else "",
            },
            profile=profile,
        )

    return render(
        request,
        "mess/admin_student_form.html",
        {
            "form": form,
            "profile": profile,
            "form_title": "Edit student",
            "form_submit_label": "Save changes",
            **_student_management_stats(),
        },
    )


@user_passes_test(lambda u: u.is_staff)
def admin_student_delete(request, pk: int):
    profile = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)

    if request.method == "POST":
        label = f"{profile.full_name} ({profile.usn})"
        profile.user.delete()
        messages.success(request, f"Deleted student account for {label}.")
        return redirect("admin_student_records")

    return render(
        request,
        "mess/admin_student_confirm_delete.html",
        {
            "profile": profile,
            **_student_management_stats(),
        },
    )


@user_passes_test(lambda u: u.is_staff)
def admin_delete_meal_absence(request, pk: int):
    obj = get_object_or_404(MealAbsence, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Meal absence request deleted.")
    else:
        messages.error(request, "Invalid request.")
    return redirect("admin_dashboard")


@user_passes_test(lambda u: u.is_staff)
def admin_delete_leave_request(request, pk: int):
    obj = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Leave request deleted.")
    else:
        messages.error(request, "Invalid request.")
    return redirect("admin_dashboard")


# ---------------------------------------------------------------------------
# Staff / Admin management
# ---------------------------------------------------------------------------

def _staff_management_stats() -> dict[str, int]:
    total = StudentUser.objects.filter(is_staff=True).count()
    active = StudentUser.objects.filter(is_staff=True, is_active=True).count()
    return {
        "staff_count": total,
        "active_staff_count": active,
    }


def _staff_user_search(queryset, q: str):
    if not q:
        return queryset
    return queryset.filter(
        Q(username__icontains=q)
        | Q(first_name__icontains=q)
        | Q(email__icontains=q)
    )


@user_passes_test(lambda u: u.is_staff)
def admin_staff_records(request):
    q = (request.GET.get("q") or "").strip()
    staff_users = StudentUser.objects.filter(is_staff=True).order_by("username")
    staff_users = _staff_user_search(staff_users, q)

    return render(
        request,
        "mess/admin_staff_records.html",
        {
            "staff_users": staff_users,
            "q": q,
            **_staff_management_stats(),
        },
    )


@user_passes_test(lambda u: u.is_staff)
def admin_staff_create(request):
    if request.method == "POST":
        form = AdminStaffCreateForm(request.POST)
        if form.is_valid():
            user = StudentUser.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["full_name"],
                is_staff=True,
            )
            messages.success(
                request,
                f"Staff account created for {user.first_name} ({user.username}).",
            )
            return redirect("admin_staff_records")
    else:
        form = AdminStaffCreateForm()

    return render(
        request,
        "mess/admin_staff_form.html",
        {
            "form": form,
            "form_title": "Add staff member",
            "form_submit_label": "Create staff account",
            **_staff_management_stats(),
        },
    )


@user_passes_test(lambda u: u.is_staff)
def admin_staff_edit(request, pk: int):
    staff_user = get_object_or_404(StudentUser, pk=pk, is_staff=True)

    if request.method == "POST":
        full_name = (request.POST.get("full_name") or "").strip()
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        is_active = request.POST.get("is_active") == "on"

        errors: list[str] = []
        if not full_name:
            errors.append("Full name is required.")
        if not username:
            errors.append("Username is required.")
        elif (
            StudentUser.objects.filter(username=username).exclude(pk=staff_user.pk).exists()
        ):
            errors.append("This username is already taken.")
        if not email:
            errors.append("Email is required.")

        if errors:
            return render(
                request,
                "mess/admin_staff_form.html",
                {
                    "form_data": request.POST,
                    "errors": errors,
                    "form_title": "Edit staff member",
                    "form_submit_label": "Save changes",
                    "editing_user": staff_user,
                    **_staff_management_stats(),
                },
            )

        staff_user.username = username
        staff_user.email = email
        staff_user.first_name = full_name
        staff_user.is_active = is_active
        if password:
            staff_user.set_password(password)
        staff_user.save()

        messages.success(request, "Staff account updated.")
        return redirect("admin_staff_records")

    return render(
        request,
        "mess/admin_staff_form.html",
        {
            "form_data": {
                "full_name": staff_user.first_name,
                "username": staff_user.username,
                "email": staff_user.email,
            },
            "is_active": staff_user.is_active,
            "errors": [],
            "form_title": "Edit staff member",
            "form_submit_label": "Save changes",
            "editing_user": staff_user,
            **_staff_management_stats(),
        },
    )


@user_passes_test(lambda u: u.is_staff)
def admin_staff_delete(request, pk: int):
    staff_user = get_object_or_404(StudentUser, pk=pk, is_staff=True)

    # Prevent admins from deleting themselves
    if staff_user.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect("admin_staff_records")

    if request.method == "POST":
        label = f"{staff_user.first_name or staff_user.username} ({staff_user.username})"
        staff_user.delete()
        messages.success(request, f"Deleted staff account for {label}.")
        return redirect("admin_staff_records")

    return render(
        request,
        "mess/admin_staff_confirm_delete.html",
        {
            "staff_user": staff_user,
            **_staff_management_stats(),
        },
    )

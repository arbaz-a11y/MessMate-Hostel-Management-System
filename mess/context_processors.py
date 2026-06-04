from __future__ import annotations

from .models import LeaveRequest, MealAbsence


def mess_notifications(request):
    """
    Badge counts for staff: unseen meal-absence submissions and leave requests.
    """

    ctx = {"unseen_meal_count": 0, "unseen_leave_count": 0}

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or not user.is_staff:
        return ctx

    ctx["unseen_meal_count"] = MealAbsence.objects.filter(is_seen=False).count()
    ctx["unseen_leave_count"] = LeaveRequest.objects.filter(is_seen=False).count()
    return ctx

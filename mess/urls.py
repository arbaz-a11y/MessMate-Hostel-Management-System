from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.student_dashboard, name="student_dashboard"),
    path("absence/new/", views.meal_absence_create, name="meal_absence_create"),
    path("leave/new/", views.leave_request_create, name="leave_request_create"),
    path("requests/", views.request_history, name="request_history"),
    path(
        "requests/meal/<int:pk>/cancel/",
        views.cancel_meal_absence,
        name="cancel_meal_absence",
    ),
    path(
        "requests/leave/<int:pk>/cancel/",
        views.cancel_leave_request,
        name="cancel_leave_request",
    ),
    path("mess-admin/login/", views.admin_login, name="admin_login"),
    path("mess-admin/notifications/", views.admin_notifications, name="admin_notifications"),
    path("mess-admin/students/", views.admin_student_records, name="admin_student_records"),
    path("mess-admin/students/add/", views.admin_student_create, name="admin_student_create"),
    path(
        "mess-admin/students/<int:pk>/",
        views.admin_student_detail,
        name="admin_student_detail",
    ),
    path(
        "mess-admin/students/<int:pk>/edit/",
        views.admin_student_edit,
        name="admin_student_edit",
    ),
    path(
        "mess-admin/students/<int:pk>/delete/",
        views.admin_student_delete,
        name="admin_student_delete",
    ),
    path("mess-admin/", views.admin_dashboard, name="admin_dashboard"),
    path(
        "mess-admin/meal-absence/<int:pk>/delete/",
        views.admin_delete_meal_absence,
        name="admin_delete_meal_absence",
    ),
    path(
        "mess-admin/leave/<int:pk>/delete/",
        views.admin_delete_leave_request,
        name="admin_delete_leave_request",
    ),
    # Preserve older routes used by bookmarks / external links.
    path(
        "admin-panel/",
        RedirectView.as_view(pattern_name="admin_dashboard", query_string=True, permanent=False),
    ),
    path(
        "admin-panel/meal-absence/<int:pk>/delete/",
        views.admin_delete_meal_absence,
    ),
    path(
        "admin-panel/leave/<int:pk>/delete/",
        views.admin_delete_leave_request,
    ),
    # Staff / admin management
    path("mess-admin/staff/", views.admin_staff_records, name="admin_staff_records"),
    path("mess-admin/staff/add/", views.admin_staff_create, name="admin_staff_create"),
    path(
        "mess-admin/staff/<int:pk>/edit/",
        views.admin_staff_edit,
        name="admin_staff_edit",
    ),
    path(
        "mess-admin/staff/<int:pk>/delete/",
        views.admin_staff_delete,
        name="admin_staff_delete",
    ),
]

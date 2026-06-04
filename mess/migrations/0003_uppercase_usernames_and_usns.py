from __future__ import annotations

from django.apps.registry import Apps
from django.db import migrations


def forwards(apps: Apps, schema_editor) -> None:
    StudentProfile = apps.get_model("mess", "StudentProfile")
    StudentUser = apps.get_model("mess", "StudentUser")

    for profile in StudentProfile.objects.all().iterator():
        usn_upper = profile.usn.upper()
        changed = False

        if profile.usn != usn_upper:
            profile.usn = usn_upper
            changed = True

        user = getattr(profile, "user", None)
        if user is not None and user.username != usn_upper:
            user.username = usn_upper
            user.save(update_fields=["username"])

        if changed:
            profile.save(update_fields=["usn"])


def backwards(apps: Apps, schema_editor) -> None:
    # No-op: we cannot reliably restore pre-uppercase values.
    del apps
    del schema_editor


class Migration(migrations.Migration):

    dependencies = [
        ("mess", "0002_seen_flags_and_usn_validation"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

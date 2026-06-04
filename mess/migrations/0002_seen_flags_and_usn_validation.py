# Generated manually for unseen notification flags + USN field constraints.

import django.core.validators
from django.db import migrations, models


USN_VALIDATOR = django.core.validators.RegexValidator(
    regex=r"^2AB[a-zA-Z0-9]{7}$",
    message=(
        "USN must start with '2AB', contain exactly 10 characters, "
        "and include only letters and numbers."
    ),
)


class Migration(migrations.Migration):

    dependencies = [
        ("mess", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="mealabsence",
            name="is_seen",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leaverequest",
            name="is_seen",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="studentprofile",
            name="usn",
            field=models.CharField(max_length=10, unique=True, validators=[USN_VALIDATOR]),
        ),
    ]

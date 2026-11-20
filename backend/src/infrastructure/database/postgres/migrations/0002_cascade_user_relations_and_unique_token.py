# Generated manually to clean up orphans and enforce CASCADE + OneToOneField.

import django.db.models.deletion
from django.db import migrations, models


def _cleanup_orphans_and_duplicate_tokens(apps, schema_editor):
    UserPermissionModel = apps.get_model("postgres_db", "UserPermissionModel")
    UserTokenModel = apps.get_model("postgres_db", "UserTokenModel")
    UserPermissionModel.objects.filter(user__isnull=True).delete()
    UserTokenModel.objects.filter(user__isnull=True).delete()

    seen_user_ids: set[int] = set()
    duplicate_ids: list[int] = []
    for token_id, uid in UserTokenModel.objects.order_by("-id").values_list("id", "user_id"):
        if uid in seen_user_ids:
            duplicate_ids.append(token_id)
        else:
            seen_user_ids.add(uid)
    if duplicate_ids:
        UserTokenModel.objects.filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("postgres_db", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            _cleanup_orphans_and_duplicate_tokens,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="userpermissionmodel",
            name="user",
            field=models.ForeignKey(
                db_column="user_id",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="permissions",
                to="postgres_db.usermodel",
            ),
        ),
        migrations.AlterField(
            model_name="usertokenmodel",
            name="user",
            field=models.OneToOneField(
                db_column="user_id",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="token",
                to="postgres_db.usermodel",
            ),
        ),
    ]

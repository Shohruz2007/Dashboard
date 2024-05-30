# Generated by Django 4.2.3 on 2024-05-28 09:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0014_comments'),
    ]

    operations = [
        migrations.AddField(
            model_name='comments',
            name='receiver',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='comments',
            name='comment_owner',
            field=models.IntegerField(),
        ),
    ]
# Generated by Django 4.2.3 on 2024-03-27 16:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0017_order_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentmethod',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]

# Generated by Django 4.2.3 on 2024-03-10 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0011_remove_product_rate_percentage'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentmethod',
            name='extra_payment',
            field=models.FloatField(default=0),
        ),
    ]

# Generated by Django 4.2.3 on 2024-03-10 00:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0009_order_is_finished_alter_product_source'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='source',
            field=models.FileField(blank=True, null=True, upload_to='course_videos'),
        ),
    ]

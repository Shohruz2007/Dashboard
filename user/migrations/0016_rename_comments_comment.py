# Generated by Django 4.2.3 on 2024-05-28 10:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0015_comments_receiver_alter_comments_comment_owner'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Comments',
            new_name='Comment',
        ),
    ]

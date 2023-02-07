# Generated by Django 4.1.4 on 2023-02-07 21:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_operation_addition_datetime'),
    ]

    operations = [
        migrations.CreateModel(
            name='GlobusTokens',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tokens', models.JSONField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='globus_tokens', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
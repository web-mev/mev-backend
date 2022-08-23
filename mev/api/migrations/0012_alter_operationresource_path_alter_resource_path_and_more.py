# Generated by Django 4.0.6 on 2022-08-23 01:58

import api.models.operation_resource
import api.models.resource
import api.models.simple_resource
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_simpleresource_delete_testresource'),
    ]

    operations = [
        migrations.AlterField(
            model_name='operationresource',
            name='path',
            field=models.FileField(upload_to=api.models.operation_resource.upload_base),
        ),
        migrations.AlterField(
            model_name='resource',
            name='path',
            field=models.FileField(upload_to=api.models.resource.upload_base),
        ),
        migrations.AlterField(
            model_name='simpleresource',
            name='path',
            field=models.FileField(upload_to=api.models.simple_resource.upload_to),
        ),
    ]

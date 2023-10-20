# Generated by Django 4.0.10 on 2023-04-01 15:07

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='password_reset_key',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.CreateModel(
            name='ResetPasswordOTP',
            fields=[
                ('datetime_created', models.DateTimeField(auto_created=True)),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('signed_pin', models.CharField(max_length=1000)),
                ('is_active', models.BooleanField(default=True)),
                ('is_expired', models.BooleanField(default=False)),
                ('duration_in_minutes', models.IntegerField(default=10)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]

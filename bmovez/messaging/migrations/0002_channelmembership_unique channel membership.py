# Generated by Django 4.0.10 on 2023-04-04 23:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0001_initial'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='channelmembership',
            constraint=models.UniqueConstraint(fields=('channel', 'user'), name='unique channel membership'),
        ),
    ]

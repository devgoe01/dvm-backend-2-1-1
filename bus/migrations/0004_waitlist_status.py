# Generated by Django 4.2.18 on 2025-02-20 00:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bus', '0003_alter_booking_seat_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='waitlist',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Fulfilled', 'Fulfilled')], default='Pending', max_length=20),
        ),
    ]

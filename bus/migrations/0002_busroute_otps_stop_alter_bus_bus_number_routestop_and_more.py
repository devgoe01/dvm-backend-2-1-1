# Generated by Django 4.2.18 on 2025-02-24 11:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bus', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BusRoute',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Otps',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('otp_code', models.PositiveIntegerField(max_length=6)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('otp_resend_attempts', models.PositiveIntegerField(default=0)),
                ('email', models.EmailField(max_length=254)),
                ('is_verified', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Stop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.AlterField(
            model_name='bus',
            name='bus_number',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.CreateModel(
            name='RouteStop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField()),
                ('bus_route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bus.busroute')),
                ('stop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bus.stop')),
            ],
            options={
                'ordering': ['bus_route', 'order'],
                'unique_together': {('bus_route', 'stop', 'order')},
            },
        ),
        migrations.AddField(
            model_name='busroute',
            name='stops',
            field=models.ManyToManyField(related_name='bus_routes', through='bus.RouteStop', to='bus.stop'),
        ),
        migrations.AlterField(
            model_name='bus',
            name='route',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buses', to='bus.busroute'),
        ),
        migrations.DeleteModel(
            name='Route',
        ),
    ]

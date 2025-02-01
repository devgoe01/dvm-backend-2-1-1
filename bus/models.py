from django.db import models
from django.contrib.auth.models import AbstractUser,Group,Permission
from django.conf import settings
class User(AbstractUser):
    ROLE_CHOICES = (('passenger', 'Passenger'),('admin', 'Administrator'),)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='passenger')
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    can_change_buses = models.ManyToManyField('Bus',related_name='editable_by', blank=True)# defined later,
    email = models.EmailField(unique=True)
    def is_passenger(self):
        return self.role == 'passenger'

    def is_admin(self):
        return self.role == 'admin'

class Route(models.Model):
    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    duration = models.DurationField()

    def __str__(self):
        return f"{self.source} to {self.destination}"

class Bus(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    bus_number = models.PositiveIntegerField(unique=True)
    total_seats = models.PositiveIntegerField()
    available_seats = models.PositiveIntegerField()
    departure_time = models.DateTimeField()
    fare = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"By {self.bus_number} from {self.route.source} to {self.route.destination}"

class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seats_booked = models.PositiveIntegerField(default=0)
    booking_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Confirmed', 'Confirmed'), ('Cancelled', 'Cancelled')], default='Confirmed')

    def __str__(self):
        return f"Booking {self.id} by {self.user.username}"

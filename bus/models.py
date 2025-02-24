from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from datetime import timedelta,datetime


class User(AbstractUser):
    ROLE_CHOICES = (('passenger', 'Passenger'), ('admin', 'Administrator'))
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='passenger')
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    can_change_buses = models.ManyToManyField('Bus', related_name='editable_by', blank=True)
    email = models.EmailField(unique=True)

    def is_passenger(self):
        return self.role == 'passenger'

    def is_admin(self):
        return self.role == 'admin'



class Stop(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

class BusRoute(models.Model):
    name = models.CharField(max_length=100, unique=True)
    stops = models.ManyToManyField(Stop, through='RouteStop', related_name='bus_routes')
    def __str__(self):
        return self.name
    def get_ordered_stops(self):
        return self.routestop_set.order_by('order')

class RouteStop(models.Model):
    bus_route = models.ForeignKey(BusRoute, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    class Meta:
        unique_together = ('bus_route', 'stop', 'order')
        ordering = ['bus_route', 'order']
    def __str__(self):
        return f"{self.bus_route.name} - {self.stop.name} (Order: {self.order})"

class Bus(models.Model):
    bus_number = models.AutoField(primary_key=True)
    route = models.ForeignKey(BusRoute, on_delete=models.CASCADE, related_name="buses")
    departure_time = models.DateTimeField()
    base_fare_per_hour = models.DecimalField(max_digits=6, decimal_places=2)

    def calculate_fare(self, seat_class_multiplier, start_stop, end_stop):
        
        ordered_stops = self.route.get_ordered_stops()
        stop_names = [route_stop.stop.name for route_stop in ordered_stops]
        start_index = stop_names.index(start_stop)
        end_index = stop_names.index(end_stop)

        if start_index >= end_index:
            raise ValueError("End stop must come after start stop.")

        total_duration_hours = (end_index - start_index)  
        total_fare_per_seat = float(self.base_fare_per_hour) * total_duration_hours * float(seat_class_multiplier)
        return round(total_fare_per_seat, 2)

    def __str__(self):
        return f"Bus {self.bus_number} on Route {self.route.name}"



class Seatclass(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="seat_classes")
    name = models.CharField(max_length=50)
    total_seats = models.PositiveIntegerField()
    seats_available = models.PositiveIntegerField()
    fare_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    seating_arrangement = models.JSONField(default=dict)

    class Meta:
        unique_together = ("bus", "name")

    def __str__(self):
        return f"{self.bus.bus_number} - {self.name}: {self.seats_available}/{self.total_seats} available"



class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="bookings")
    seat_class = models.ForeignKey(Seatclass, on_delete=models.CASCADE)
    seat_number = models.TextField()
    seats_booked = models.PositiveIntegerField()
    booking_time = models.DateTimeField(auto_now_add=True)
    start_stop = models.CharField(max_length=100)
    end_stop = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=[('Confirmed', 'Confirmed'), ('Cancelled', 'Cancelled')],
        default='Confirmed'
    )

    def calculate_fare(self):
        return self.bus.calculate_fare(self.seat_class.fare_multiplier, self.start_stop, self.end_stop)

    def save(self, *args, **kwargs):
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.id} by {self.user.username}"



class Waitlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seat_class = models.ForeignKey(Seatclass, on_delete=models.CASCADE)
    seats_requested = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Fulfilled', 'Fulfilled')],
        default='Pending'
    )

    def __str__(self):
        return f"Waitlist Entry: {self.user.username} for Bus {self.bus.bus_number} class {self.seat_class.name}"

class Otps(models.Model):
    otp_code = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    otp_resend_attempts = models.PositiveIntegerField(default=0)
    max_resend_attempts = 5
    email=models.EmailField()
    is_verified=models.BooleanField(default=False)

    def save(self, *args, **kwargs):
#        if not self.expires_at:
        self.expires_at = datetime.now().isoformat() + timedelta(minutes=2)
        self.created_at = datetime.now().isoformat()
        super().save(*args, **kwargs)

    def is_expired(self):
        return datetime.now() > self.expires_at+timedelta(minutes=2)

    def can_resend(self):
        return self.otp_resend_attempts < self.max_resend_attempts

    def resend_otp(self,otp_code):
        self.otp_code = otp_code
        self.otp_resend_attempts += 1
        self.save()

    def __str__(self):
        return f"OTP for {self.user.username} created at {self.created_at}"
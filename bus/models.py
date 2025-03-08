from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from datetime import timedelta,datetime, timezone
#from fernet_fields import EncryptedIntegerField

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
    
    def get_stops_names(self):
        return [route_stop.stop.name for route_stop in self.get_ordered_stops()]


class RouteStop(models.Model):
    bus_route = models.ForeignKey(BusRoute, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()   
    duration_to_next_stop = models.DurationField(null=True, blank=True)

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

    def calculate_fare(self, start_stop, end_stop, seat_class_multiplier,num_seats):
        ordered_stops = self.route.get_ordered_stops()
        start_index = (start_stop.order)
        end_index = (end_stop.order)

        total_duration = timedelta()
        for i in range(start_index, end_index):
            total_duration += ordered_stops[i].duration_to_next_stop

        total_hours = total_duration.total_seconds() / 3600
        return round(total_hours *num_seats* float(self.base_fare_per_hour) * float(seat_class_multiplier), 2)

    def __str__(self):
        return f"Bus {self.bus_number} on Route {self.route.name}"
    

    def get_all_available_seats(self, start_stop, end_stop,seat_class=None):
        all_seats = self.seats.values_list('id', flat=True)
        booked_seats = Booking.objects.filter(
            bus=self,
            start_stop__order__lt=end_stop.order,
            end_stop__order__gt=start_stop.order,
            status='Confirmed'
        ).values_list('seats__id', flat=True)
        available_seats_ids = set(all_seats) - set(booked_seats)
        if seat_class:
            return self.seats.filter(id__in=available_seats_ids, seat_class=seat_class)
        return self.seats.filter(id__in=available_seats_ids)

    def initialize_seats(self):
        for seat_class in self.seat_classes.all():
            for i in range(1,seat_class.total_seats+1):
                Seat.objects.get_or_create(bus=self, seat_number=f"{seat_class.name[:1]}-{i}",seat_class=seat_class)

    def are_seats_available(self,num_seats,start_stop,end_stop,seat_class):
        all_seats_in_class=self.seats.filter(seat_class=seat_class).values_list('id',flat=True)
        booked_seats = Booking.objects.filter(
            bus=self,
            seats__seat_class=seat_class,
            start_stop__order__lt=end_stop.order,
            end_stop__order__gt=start_stop.order,
            status='Confirmed'
        ).values_list('seats__id', flat=True)
        available_seats = set(all_seats_in_class) - set(booked_seats)
        
        return len(available_seats) >= num_seats

class Seatclass(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="seat_classes")
    name = models.CharField(max_length=50)
    total_seats = models.PositiveIntegerField()
    fare_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    
    class Meta:
        unique_together = ("bus", "name")

    def __str__(self):
        return f"{self.bus.bus_number} - {self.name} Total:{self.total_seats} "

class Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="seats")
    seat_number = models.CharField(max_length=10)
    seat_class=models.ForeignKey(Seatclass,on_delete=models.CASCADE)
    class Meta:
        unique_together = ("bus", "seat_number")

    def __str__(self):
        return f"Seat {self.seat_number} {self.seat_class.name} on Bus {self.bus.bus_number}"

    def get_seat_class(self):
        return self.seat_class.name

    def is_booked(self, start_stop, end_stop):
        overlapping_bookings = Booking.objects.filter(
            seats=self,
            start_stop__order__lt=end_stop.order,
            end_stop__order__gt=start_stop.order,
            bus=self.bus,
            status='Confirmed'
        )
        return overlapping_bookings.exists()

    @staticmethod
    def are_seats_booked(bus, seat_numbers, start_stop, end_stop, seat_class=None):
        booked_seats_query = Booking.objects.filter(
            bus=bus,
            start_stop__order__lt=end_stop.order,
            end_stop__order__gt=start_stop.order,
            status='Confirmed'
        )
        if seat_class:
            booked_seats_query = booked_seats_query.filter(seats__seat_class=seat_class) 
        booked_seat_numbers = booked_seats_query.values_list('seats__seat_number', flat=True)
        booked_seats_in_requested = set(seat_numbers).intersection(set(booked_seat_numbers))
        return bool(booked_seats_in_requested), list(booked_seats_in_requested)


class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="bookings")
    seats = models.ManyToManyField(Seat,blank=True)
    booking_time = models.DateTimeField(auto_now_add=True)
    start_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name="booking_start")
    end_stop = models.ForeignKey(RouteStop, on_delete=models.CASCADE, related_name="booking_end")
    status = models.CharField(
        max_length=20,
        choices=[('Confirmed', 'Confirmed'), ('Cancelled', 'Cancelled')],
        default='Confirmed'
    )
    
    def __str__(self):
        return f"Booking {self.id} by {self.user.username}"
    def get_booked_seats(self):
        return self.seats.all()




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
#    otp_code = models.EncyptedIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    otp_resend_attempts = models.PositiveIntegerField(default=0)
    max_resend_attempts = 5
    email=models.EmailField()
    is_verified=models.BooleanField(default=False)

    def save(self, *args, **kwargs):
#        if not self.expires_at:
        self.expires_at = datetime.now() + timedelta(minutes=2)
        self.created_at = datetime.now().isoformat()
        super().save(*args, **kwargs)

    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at

    def can_resend(self):
        return self.otp_resend_attempts < self.max_resend_attempts

    def resend_otp(self,otp_code):
        self.otp_code = otp_code
        self.otp_resend_attempts += 1
        self.save()

    def __str__(self):
        return f"OTP for {self.email} created at {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
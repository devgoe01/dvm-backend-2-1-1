from django.db import models
from django.contrib.auth.models import AbstractUser,Group,Permission
from django.conf import settings


def initialize_bus_seats(bus):
    seat_classes=bus.seat_classes
    general, sleeper, luxury = map(int, seat_classes.split('-'))
    seat_ranges = {
        'General': (1, general),
        'Sleeper': (general + 1, sleeper+general),
        'Luxury': (sleeper+general+1, sleeper+general+luxury)
    }
    seats_to_create = []
    for seat_class, (start, end) in seat_ranges.items():
        for seat_num in range(start, end + 1):
            seats_to_create.append(
                Seat(
                    bus=bus,
                    seat_number=seat_num,
                    seat_class=seat_class,
                    is_available=True
                )
            )
    Seat.objects.bulk_create(seats_to_create)

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
        return f"{self.source} --> {self.destination}"

class Bus(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    bus_number = models.PositiveIntegerField(unique=True)
    total_seats = models.PositiveIntegerField(blank=True, null=True)
    available_seats = models.CharField(max_length=11,help_text="Available Seat counts for General, Sleeper, and Luxury classes, separated by hyphens. Example: '50-30-10'")
    departure_time = models.DateTimeField()
    fare = models.DecimalField(max_digits=6, decimal_places=2)
    seat_classes = models.CharField(max_length=11,default='50-30-10',help_text="Seat counts for General, Sleeper, and Luxury classes, separated by hyphens. Example: '50-30-10'")

    def __str__(self):        
        return f"By {self.bus_number} from {self.route.source} to {self.route.destination}"
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.seats.exists():
            initialize_bus_seats(self)

class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seats_booked = models.CharField(default=2-2-2,max_length=11,help_text="Booked Seat counts for General, Sleeper, and Luxury classes, separated by hyphens. Example: '50-30-10'")
    booking_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Confirmed', 'Confirmed'), ('Cancelled', 'Cancelled')], default='Confirmed')
    seats = models.ManyToManyField('Seat')
    selected_seats = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Comma-separated seat numbers"
    )

    def __str__(self):
        return f"Booking {self.id} by {self.user.username}"
    def auto_assign_seats(self, num_seats):
        available_seats = self.bus.seats.filter(is_available=True).order_by('seat_number')[:num_seats]

        if available_seats.count() < num_seats:
            raise ValueError("Not enough available seats.")
        for seat in available_seats:
            seat.is_available = False
            seat.save()
        self.seats.add(*available_seats)
        self.selected_seats = ','.join(str(seat.seat_number) for seat in available_seats)
        self.save()




class Waitlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seats_requested = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Waitlist entry for {self.user.username} on bus {self.bus.bus_number}"

class Seat(models.Model):
    SEAT_CLASS_CHOICES = [
        ('General', 'General'),
        ('Sleeper', 'Sleeper'),
        ('Luxury', 'Luxury')
    ]

    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.PositiveIntegerField()
    seat_class = models.CharField(max_length=10, choices=SEAT_CLASS_CHOICES)
    is_available = models.BooleanField(default=True)
    class Meta:
        unique_together = ('bus', 'seat_number')
    def __str__(self):
        return f"Seat {self.seat_number} ({self.seat_class}) - Bus {self.bus.bus_number}"
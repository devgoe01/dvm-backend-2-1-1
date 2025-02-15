from django.db import models
from django.contrib.auth.models import AbstractUser 
from django.conf import settings
from django.utils.timezone import now
import json
from datetime import timedelta,datetime
class User(AbstractUser):
    ROLE_CHOICES = (('passenger', 'Passenger'),('admin', 'Administrator'),)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='passenger')
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    can_change_buses = models.ManyToManyField('Bus', related_name='editable_by', blank=True)
    email = models.EmailField(unique=True)

    def is_passenger(self):
        return self.role == 'passenger'

    def is_admin(self):
        return self.role == 'admin'


class Route(models.Model):
    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    intermediate_stops = models.JSONField(default=list,blank=True,null=True)
    stop_durations=models.JSONField(default=dict)

    def get_duration_between_stops(self,start_stop,end_stop):
        stops=[self.source]+self.intermediate_stops+[self.destination]
        total_duration=timedelta()
        start_index=stops.index(start_stop)
        end_index=stops.index(end_stop)
        for i in range(start_index,end_index):
            stop_pair=f"{stops[i]}-{stops[i+1]}"
            total_duration+=timedelta(seconds=self.stop_durations.get(stop_pair,0))
        return total_duration

    def __str__(self):
        stops = " → ".join([self.source] + [self.destination])
        return f"Route: {stops}"


class Bus(models.Model):
    route = models.OneToOneField(Route, on_delete=models.CASCADE)
    bus_number = models.PositiveIntegerField(unique=True, primary_key=True,auto_created=True)
    departure_time = models.TimeField()
    base_fare_per_hour = models.DecimalField(max_digits=6, decimal_places=2)
    operating_days = models.JSONField(default=list)

    def calculate_fare(self, seat_class_multiplier,start_stop,end_stop):
        total_hours=self.route.get_duration_between_stops(start_stop,end_stop).total_seconds()/3600
        total_fare_per_seat = float(self.base_fare_per_hour) *(total_hours) *float(seat_class_multiplier)
        return round(total_fare_per_seat, 2)

    def __str__(self):
        return f"Bus {self.bus_number} from {self.route.source} to {self.route.destination}"

class BusInstance(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="instances")
    travel_date = models.DateField()

    def __str__(self):
        return f"{self.bus.bus_number} on {self.travel_date}"
    def initialize_seat_classes(self):
        for seat_class in self.bus.seat_classes.all():
            Seatclass.objects.create(
                bus_instance=self,
                name=seat_class.name,
                total_seats=seat_class.total_seats,
                seats_available=seat_class.total_seats,
                fare_multiplier=seat_class.fare_multiplier,
                seating_arrangement={f"Seat-{i+1}": True for i in range(seat_class.total_seats)},
            )

class Seatclass(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="seat_classes")
    name = models.CharField(max_length=50) 
    total_seats = models.PositiveIntegerField()
    seats_available = models.PositiveIntegerField()
    fare_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    seating_arrangement = models.JSONField(default=dict)

    class Meta:
        unique_together = ("bus", "name")

    def initialize_seats(self):
        if not self.seating_arrangement:
            self.seating_arrangement = {f"Seat-{i+1}": True for i in range(self.total_seats)}
            self.save()

    def __str__(self):
        return f"{self.bus.bus_number} - {self.name}: {self.seats_available}/{self.total_seats} available"


class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seat_class = models.ForeignKey(Seatclass, on_delete=models.CASCADE)
    seat_number = models.CharField(max_length=50)
    seats_booked = models.PositiveIntegerField()
    booking_time = models.DateTimeField(auto_now_add=True)
    start_stop = models.CharField(max_length=100)
    end_stop = models.CharField(max_length=100)
    travel_date = models.DateField(default=now().date())
    status = models.CharField(
        max_length=20,
        choices=[('Confirmed', 'Confirmed'), ('Cancelled', 'Cancelled')],
        default='Confirmed'
    )
    def calculate_fare(self):
        return self.bus.calculate_fare(self.seat_class.fare_multiplier,self.start_stop,self.end_stop)

    def save(self, *args, **kwargs):
        if self.pk:
            previous_booking = Booking.objects.get(pk=self.pk)
            if previous_booking.status == 'Confirmed' and self.status == 'Cancelled':
                self.release_seats(previous_booking)
            elif previous_booking.seats_booked < self.seats_booked:
                additional_seats_needed = self.seats_booked - previous_booking.seats_booked
                self.assign_additional_seats(additional_seats_needed)
            elif previous_booking.seats_booked > self.seats_booked:
                self.release_excess_seats(previous_booking)

        if not self.pk or (self.status == 'Confirmed' and not kwargs.get('skip_assign', False)):
            self.assign_seats()
        super().save(*args, **kwargs)
        try:
            assert False,locals()
        except: pass
    def release_seats(self, booking):
        seating_arrangement = booking.seat_class.seating_arrangement.copy()
        print("Before release:", json.dumps(seating_arrangement, indent=2))
        if booking.seat_number:
            for seat in booking.seat_number.split(', '):
                seating_arrangement[seat] = True
                booking.seat_class.seats_available+=1
        print("After release:", json.dumps(seating_arrangement, indent=2))
        booking.seat_class.seating_arrangement = dict(seating_arrangement)
        booking.seat_class.save(update_fields=['seating_arrangement', 'seats_available'])
        booking.seat_class.refresh_from_db()
        print("Database after save:", json.dumps(booking.seat_class.seating_arrangement, indent=2))

    def release_excess_seats(self, previous_booking):
        seating_arrangement = previous_booking.seat_class.seating_arrangement
        current_seat_numbers = previous_booking.seat_number.split(', ')
        excess_seats_count = len(current_seat_numbers) - self.seats_booked

        if excess_seats_count > 0:
            for seat in current_seat_numbers[-excess_seats_count:]:
                seating_arrangement[seat] = True
                previous_booking.seat_class.seats_available += 1

            self.seat_number = ', '.join(current_seat_numbers[:-excess_seats_count])

        previous_booking.seat_class.seating_arrangement = seating_arrangement
        previous_booking.seat_class.save()

    def assign_additional_seats(self, additional_seats_needed):
        seating_arrangement = self.seat_class.seating_arrangement
        assigned_seats = []

        for seat, available in seating_arrangement.items():
            if available and len(assigned_seats) < additional_seats_needed:
                seating_arrangement[seat] = False
                assigned_seats.append(seat)

        if len(assigned_seats) < additional_seats_needed:
            raise ValueError("Not enough seats available to fulfill the updated booking.")

        current_seat_numbers = self.seat_number.split(', ') if self.seat_number else []
        self.seat_number = ', '.join(current_seat_numbers + assigned_seats)

        self.seat_class.seats_available -= len(assigned_seats)
        self.seat_class.seating_arrangement = seating_arrangement
        self.seat_class.save()

    def assign_seats(self):
        seating_arrangement = self.seat_class.seating_arrangement

        if self.pk and self.status == 'Cancelled':
            return
        if len(self.seat_number)!=0:
            for seat in self.seat_number.split(', '):
                self.seat_class.seating_arrangement[seat] = False
                self.seat_class.save()
        else:
            assigned_seats = []
            del self.seat_number
            for seat, available in seating_arrangement.items():
                if available and len(assigned_seats) < self.seats_booked:
                    seating_arrangement[seat] = False
                    assigned_seats.append(seat)
                    self.seat_number = ', '.join(assigned_seats)
        self.seat_class.seating_arrangement = seating_arrangement
        self.seat_class.seats_available -= self.seats_booked
        self.seat_class.save()

    def __str__(self):
        return f"Booking {self.id} by {self.user.username}"

class Waitlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    seat_class = models.ForeignKey(Seatclass, on_delete=models.CASCADE)
    seats_requested= models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Waitlist Entry: {self.user.username} for Bus {self.bus.bus_number} class {self.seat_class.name}"
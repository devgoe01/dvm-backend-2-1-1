# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AccountEmailaddress(models.Model):
    email = models.CharField(unique=True, max_length=254)
    verified = models.BooleanField()
    primary = models.BooleanField()
    user = models.ForeignKey('BusUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'account_emailaddress'
        unique_together = (('user', 'email'), ('user', 'primary'),)


class AccountEmailconfirmation(models.Model):
    created = models.DateTimeField()
    sent = models.DateTimeField(blank=True, null=True)
    key = models.CharField(unique=True, max_length=64)
    email_address = models.ForeignKey(AccountEmailaddress, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'account_emailconfirmation'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class BusBooking(models.Model):
    id = models.BigAutoField(primary_key=True)
    seats_booked = models.CharField(max_length=11)
    booking_time = models.DateTimeField()
    status = models.CharField(max_length=20)
    bus = models.ForeignKey('BusBus', models.DO_NOTHING)
    user = models.ForeignKey('BusUser', models.DO_NOTHING)
    selected_seats = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bus_booking'


class BusBookingSeats(models.Model):
    id = models.BigAutoField(primary_key=True)
    booking = models.ForeignKey(BusBooking, models.DO_NOTHING)
    seat = models.ForeignKey('BusSeat', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'bus_booking_seats'
        unique_together = (('booking', 'seat'),)


class BusBus(models.Model):
    id = models.BigAutoField(primary_key=True)
    bus_number = models.IntegerField(unique=True)
    total_seats = models.IntegerField(blank=True, null=True)
    available_seats = models.CharField(max_length=11)
    departure_time = models.DateTimeField()
    fare = models.DecimalField(max_digits=6, decimal_places=2)
    route = models.ForeignKey('BusRoute', models.DO_NOTHING)
    seat_classes = models.CharField(max_length=11)

    class Meta:
        managed = False
        db_table = 'bus_bus'


class BusRoute(models.Model):
    id = models.BigAutoField(primary_key=True)
    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    duration = models.DurationField()

    class Meta:
        managed = False
        db_table = 'bus_route'


class BusSeat(models.Model):
    id = models.BigAutoField(primary_key=True)
    seat_number = models.IntegerField()
    seat_class = models.CharField(max_length=10)
    is_available = models.BooleanField()
    bus = models.ForeignKey(BusBus, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'bus_seat'
        unique_together = (('bus', 'seat_number'),)


class BusUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()
    role = models.CharField(max_length=10)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2)
    email = models.CharField(unique=True, max_length=254)

    class Meta:
        managed = False
        db_table = 'bus_user'


class BusUserCanChangeBuses(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(BusUser, models.DO_NOTHING)
    bus = models.ForeignKey(BusBus, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'bus_user_can_change_buses'
        unique_together = (('user', 'bus'),)


class BusUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(BusUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'bus_user_groups'
        unique_together = (('user', 'group'),)


class BusUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(BusUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'bus_user_user_permissions'
        unique_together = (('user', 'permission'),)


class BusWaitlist(models.Model):
    id = models.BigAutoField(primary_key=True)
    seats_requested = models.IntegerField()
    created_at = models.DateTimeField()
    bus = models.ForeignKey(BusBus, models.DO_NOTHING)
    user = models.ForeignKey(BusUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'bus_waitlist'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(BusUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class SocialaccountSocialaccount(models.Model):
    provider = models.CharField(max_length=200)
    uid = models.CharField(max_length=191)
    last_login = models.DateTimeField()
    date_joined = models.DateTimeField()
    extra_data = models.JSONField()
    user = models.ForeignKey(BusUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'socialaccount_socialaccount'
        unique_together = (('provider', 'uid'),)


class SocialaccountSocialapp(models.Model):
    provider = models.CharField(max_length=30)
    name = models.CharField(max_length=40)
    client_id = models.CharField(max_length=191)
    secret = models.CharField(max_length=191)
    key = models.CharField(max_length=191)
    provider_id = models.CharField(max_length=200)
    settings = models.JSONField()

    class Meta:
        managed = False
        db_table = 'socialaccount_socialapp'


class SocialaccountSocialtoken(models.Model):
    token = models.TextField()
    token_secret = models.TextField()
    expires_at = models.DateTimeField(blank=True, null=True)
    account = models.ForeignKey(SocialaccountSocialaccount, models.DO_NOTHING)
    app = models.ForeignKey(SocialaccountSocialapp, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'socialaccount_socialtoken'
        unique_together = (('app', 'account'),)


class UsersProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    image = models.CharField(max_length=100)
    user = models.OneToOneField(BusUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'users_profile'

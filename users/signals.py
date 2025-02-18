from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile
from django.conf import settings
#from bus.models import Bus
#from .utils import create_bus_instances_for_next_month

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()



################################
"""@receiver(post_save, sender=Bus)
def create_initial_bus_instances(sender, instance, created, **kwargs):
    if created:  
        create_bus_instances_for_next_month(instance)"""
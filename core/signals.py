import os

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SecurityProfile


@receiver(post_save, sender=User)
def create_security_profile(sender, instance, created, **kwargs):
    if created:
        SecurityProfile.objects.get_or_create(
            user=instance,
            defaults={'role': SecurityProfile.ROLE_ADMIN if instance.is_superuser else SecurityProfile.ROLE_USER},
        )

    temporary_username = os.getenv('BOOTSTRAP_TEMP_USERNAME', 'bootstrap_admin')
    if instance.is_superuser and instance.username != temporary_username:
        User.objects.filter(username=temporary_username, is_superuser=True).delete()
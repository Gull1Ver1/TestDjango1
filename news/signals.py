from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, ActivationCode
import secrets
from django.core.mail import send_mail
from django.conf import settings

@receiver(post_save, sender=User)
def create_activation_code(sender, instance, created, **kwargs):
    if created and not instance.is_active:
        code = secrets.token_urlsafe(16)
        ActivationCode.objects.create(user=instance, code=code)
        send_mail(
            'Activate your account',
            f'Hello {instance.email},\nActivation code: {code}',
            settings.DEFAULT_FROM_EMAIL,
            [instance.email],
        )
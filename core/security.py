from datetime import timedelta

from django.utils import timezone

from .models import LoginAttempt

MAX_LOGIN_FAILURES = 5
LOCKOUT_MINUTES = 15


def client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    return (forwarded_for.split(',')[0].strip() if forwarded_for else request.META.get('REMOTE_ADDR', '0.0.0.0'))


def is_login_locked(identifier, ip_address):
    attempt = LoginAttempt.objects.filter(identifier=identifier, ip_address=ip_address).first()
    return bool(attempt and attempt.is_locked())


def register_login_failure(identifier, ip_address):
    attempt, _ = LoginAttempt.objects.get_or_create(identifier=identifier, ip_address=ip_address)
    attempt.failed_count += 1
    if attempt.failed_count >= MAX_LOGIN_FAILURES:
        attempt.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_MINUTES)
    attempt.save(update_fields=['failed_count', 'locked_until', 'updated_at'])


def clear_login_failures(identifier, ip_address):
    LoginAttempt.objects.filter(identifier=identifier, ip_address=ip_address).delete()
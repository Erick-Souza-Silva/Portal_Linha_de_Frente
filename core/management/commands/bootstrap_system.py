import logging
import os
import secrets

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand


logger = logging.getLogger('django.security')


class Command(BaseCommand):
    help = 'Cria o administrador temporário inicial ou o usuário de teste controlado.'

    def handle(self, *args, **options):
        if User.objects.exists():
            self.stdout.write('Bootstrap ignorado: já existem usuários cadastrados.')
            return

        username = os.getenv('BOOTSTRAP_TEMP_USERNAME', 'bootstrap_admin')
        password = secrets.token_urlsafe(18)
        user = User.objects.create_superuser(username=username, password=password, email='')
        logger.warning('Admin temporário criado. username=%s password=%s', username, password)
        self.stdout.write(self.style.WARNING(f'Admin temporário criado: {username}'))

        if os.getenv('NODE_ENV', '').lower() == 'test':
            test_admin, _ = User.objects.get_or_create(username='test_admin')
            test_admin.set_unusable_password()
            test_admin.is_staff = True
            test_admin.is_superuser = False
            test_admin.save(update_fields=['password', 'is_staff', 'is_superuser'])
            group, _ = Group.objects.get_or_create(name='Test Admin')
            permissions = Permission.objects.filter(codename__startswith='view_')
            group.permissions.set(permissions)
            test_admin.groups.add(group)
            self.stdout.write('Usuário test_admin criado com permissões somente de visualização.')
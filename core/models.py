import secrets
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class SecurityProfile(models.Model):
	ROLE_USER = 'user'
	ROLE_MODERATOR = 'moderator'
	ROLE_ADMIN = 'admin'
	ROLE_CHOICES = (
		(ROLE_USER, 'Usuário'),
		(ROLE_MODERATOR, 'Moderador'),
		(ROLE_ADMIN, 'Administrador'),
	)

	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='security_profile')
	role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)
	is_banned = models.BooleanField(default=False)
	mfa_enabled = models.BooleanField(default=False)
	mfa_secret = models.CharField(max_length=32, blank=True)
	email_verified = models.BooleanField(default=False)
	session_version = models.PositiveIntegerField(default=1)
	created_at = models.DateTimeField(auto_now_add=True)

	def revoke_sessions(self):
		self.session_version = models.F('session_version') + 1
		self.save(update_fields=['session_version'])
		self.refresh_from_db(fields=['session_version'])

	def enable_mfa(self):
		self.mfa_secret = self.mfa_secret or secrets.token_hex(10).upper()
		self.mfa_enabled = True
		self.save(update_fields=['mfa_secret', 'mfa_enabled'])


class ContentBase(models.Model):
	title = models.CharField(max_length=180)
	slug = models.SlugField(max_length=200, unique=True)
	body = models.TextField()
	cover_image = models.URLField(blank=True)
	video_url = models.URLField(blank=True)
	audio_url = models.URLField(blank=True)
	is_published = models.BooleanField(default=False)
	published_at = models.DateTimeField(null=True, blank=True)
	author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='%(class)s_items')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True
		ordering = ('-published_at', '-created_at')

	def publish(self):
		self.is_published = True
		self.published_at = self.published_at or timezone.now()
		self.save(update_fields=['is_published', 'published_at', 'updated_at'])


class Post(ContentBase):
	category = models.CharField(max_length=80, default='Esportes')

	def __str__(self):
		return self.title


class Page(ContentBase):
	class Meta:
		ordering = ('title',)

	def __str__(self):
		return self.title


class Comment(models.Model):
	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
	author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
	parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
	body = models.TextField(max_length=2000)
	is_visible = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('created_at',)


class Rating(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings')
	content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
	object_id = models.PositiveBigIntegerField()
	content_object = GenericForeignKey('content_type', 'object_id')
	value = models.PositiveSmallIntegerField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['user', 'content_type', 'object_id'], name='unique_user_rating'),
			models.CheckConstraint(condition=models.Q(value__gte=1, value__lte=5), name='rating_between_one_five'),
		]


class Favorite(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
	content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
	object_id = models.PositiveBigIntegerField()
	content_object = GenericForeignKey('content_type', 'object_id')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=['user', 'content_type', 'object_id'], name='unique_user_favorite')]


class BrowsingHistory(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='browsing_history')
	content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
	object_id = models.PositiveBigIntegerField()
	content_object = GenericForeignKey('content_type', 'object_id')
	visited_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ('-visited_at',)


class AccessLog(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
	path = models.CharField(max_length=255)
	method = models.CharField(max_length=10)
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	status_code = models.PositiveSmallIntegerField()
	created_at = models.DateTimeField(auto_now_add=True)


class LoginAttempt(models.Model):
	identifier = models.CharField(max_length=180)
	ip_address = models.GenericIPAddressField()
	failed_count = models.PositiveSmallIntegerField(default=0)
	locked_until = models.DateTimeField(null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=['identifier', 'ip_address'], name='unique_login_attempt')]

	def is_locked(self):
		return bool(self.locked_until and self.locked_until > timezone.now())


class EmailVerificationToken(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_tokens')
	token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	expires_at = models.DateTimeField()
	used_at = models.DateTimeField(null=True, blank=True)

	def is_valid(self):
		return self.used_at is None and self.expires_at > timezone.now()

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import (
    AccessLog,
    BrowsingHistory,
    Comment,
    EmailVerificationToken,
    Favorite,
    LoginAttempt,
    Page,
    Post,
    Rating,
    SecurityProfile,
)


admin.site.unregister(User)


@admin.register(User)
class PortalUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email')


@admin.action(description='Publicar itens selecionados')
def publish_items(modeladmin, request, queryset):
    for item in queryset:
        item.publish()


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'is_published', 'published_at', 'updated_at')
    list_filter = ('category', 'is_published')
    search_fields = ('title', 'body', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    actions = (publish_items,)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_published', 'published_at', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'body', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    actions = (publish_items,)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'is_visible', 'created_at')
    list_filter = ('is_visible', 'created_at')
    search_fields = ('body', 'author__username', 'post__title')
    actions = ('show_comments', 'hide_comments')

    @admin.action(description='Exibir comentários selecionados')
    def show_comments(self, request, queryset):
        queryset.update(is_visible=True)

    @admin.action(description='Ocultar comentários selecionados')
    def hide_comments(self, request, queryset):
        queryset.update(is_visible=False)


@admin.register(SecurityProfile)
class SecurityProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_banned', 'mfa_enabled', 'email_verified', 'session_version')
    list_filter = ('role', 'is_banned', 'mfa_enabled', 'email_verified')
    search_fields = ('user__username', 'user__email')
    actions = ('ban_users', 'unban_users')

    @admin.action(description='Banir e revogar sessões')
    def ban_users(self, request, queryset):
        for profile in queryset:
            profile.is_banned = True
            profile.revoke_sessions()
            profile.user.is_active = False
            profile.user.save(update_fields=['is_active'])

    @admin.action(description='Reativar usuários')
    def unban_users(self, request, queryset):
        queryset.update(is_banned=False)
        User.objects.filter(security_profile__in=queryset).update(is_active=True)


admin.site.register(Rating)
admin.site.register(Favorite)
admin.site.register(BrowsingHistory)
admin.site.register(AccessLog)
admin.site.register(LoginAttempt)
admin.site.register(EmailVerificationToken)

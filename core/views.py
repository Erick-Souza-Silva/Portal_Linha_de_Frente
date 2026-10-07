from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone

from .forms import CommentForm, MFAForm, PostForm, RegistrationForm
from .models import AccessLog, BrowsingHistory, Category, Comment, EmailVerificationToken, Favorite, Post, SecurityProfile
from .security import clear_login_failures, client_ip, is_login_locked, register_login_failure
from .sports import fetch_scoreboard

MFA_PENDING_USER_SESSION_KEY = 'mfa_pending_user_id'


def home(request):
    posts = Post.objects.filter(is_published=True).select_related('author', 'category')
    category_slug = request.GET.get('categoria', '').strip()
    if category_slug:
        posts = posts.filter(category__slug=category_slug)
    recent_posts = list(posts[:6])
    return render(request, 'pages/main.html', {
        'recent_posts': recent_posts,
        'featured_post': recent_posts[0] if recent_posts else None,
        'active_category': category_slug,
        'scoreboard': fetch_scoreboard(),
    })


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comentário publicado com sucesso.')
            return redirect('noticia', slug=post.slug)
    else:
        comment_form = CommentForm()

    content_type = ContentType.objects.get_for_model(Post)
    if request.user.is_authenticated:
        BrowsingHistory.objects.update_or_create(
            user=request.user,
            content_type=content_type,
            object_id=post.pk,
        )
        is_favorite = Favorite.objects.filter(
            user=request.user,
            content_type=content_type,
            object_id=post.pk,
        ).exists()
    else:
        is_favorite = False

    return render(request, 'pages/notica.html', {
        'post': post,
        'comments': post.comments.filter(is_visible=True).select_related('author'),
        'comment_form': comment_form,
        'is_favorite': is_favorite,
    })


def post_pdf(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    if not post.pdf_file:
        raise Http404
    try:
        pdf_file = post.pdf_file.open('rb')
    except FileNotFoundError:
        raise Http404
    return FileResponse(pdf_file, content_type='application/pdf')


def _is_admin_portal_user(user):
    try:
        profile = user.security_profile
    except SecurityProfile.DoesNotExist:
        profile = None
    portal_permissions = (
        'core.view_post',
        'core.add_post',
        'core.change_post',
        'core.delete_post',
        'core.publish_post',
    )
    return user.is_authenticated and (user.is_staff or user.is_superuser or any(user.has_perm(permission) for permission in portal_permissions) or getattr(profile, 'role', None) in (
        SecurityProfile.ROLE_ADMIN,
        SecurityProfile.ROLE_MODERATOR,
    ))


def _can_publish_posts(user):
    return user.is_staff or user.is_superuser or user.has_perm('core.publish_post')


def _can_add_posts(user):
    try:
        profile = user.security_profile
        role_allows_creation = profile.role in (SecurityProfile.ROLE_ADMIN, SecurityProfile.ROLE_MODERATOR)
    except SecurityProfile.DoesNotExist:
        role_allows_creation = False
    return user.is_staff or user.is_superuser or user.has_perm('core.add_post') or role_allows_creation


@login_required
def profile_view(request):
    return render(request, 'prefil/prefil.html', {
        'favorite_count': request.user.favorites.count(),
        'history_count': request.user.browsing_history.count(),
        'can_add_post': _can_add_posts(request.user),
    })


@login_required
def history_view(request):
    history = request.user.browsing_history.select_related('content_type')[:50]
    return render(request, 'prefil/historico.html', {'history': history})


@login_required
def favorites_view(request):
    favorites = request.user.favorites.select_related('content_type')
    return render(request, 'prefil/favorito.html', {'favorites': favorites})


@login_required
def clear_history(request):
    if request.method == 'POST':
        request.user.browsing_history.all().delete()
    return redirect('historico')


@login_required
@require_POST
def toggle_favorite(request, post_id):
    post = get_object_or_404(Post, pk=post_id, is_published=True)
    content_type = ContentType.objects.get_for_model(Post)
    favorite, created = Favorite.objects.get_or_create(
        user=request.user, content_type=content_type, object_id=post.pk,
    )
    if not created:
        favorite.delete()
    return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or 'home')


@user_passes_test(_is_admin_portal_user, login_url='login')
def admin_dashboard(request):
    from django.contrib.auth.models import User

    post_form = PostForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and post_form.is_valid():
        if not request.user.has_perm('core.add_post') and not request.user.is_staff and not request.user.is_superuser:
            raise PermissionDenied
        post = post_form.save(commit=False)
        if post.is_published and not _can_publish_posts(request.user):
            post_form.add_error('is_published', 'Seu grupo pode criar rascunhos, mas não pode publicar notícias.')
            return render(request, 'admin/desboord.html', {
                'user_count': User.objects.count(),
                'post_count': Post.objects.count(),
                'published_count': Post.objects.filter(is_published=True).count(),
                'comment_count': Comment.objects.count(),
                'access_count': AccessLog.objects.count(),
                'recent_posts': Post.objects.select_related('author')[:6],
                'post_form': post_form,
            })
        post.author = request.user
        base_slug = slugify(post.title) or 'noticia'
        post.slug = base_slug
        suffix = 2
        while Post.objects.filter(slug=post.slug).exists():
            post.slug = f'{base_slug}-{suffix}'
            suffix += 1
        if post.is_published:
            post.published_at = timezone.now()
        post.save()
        messages.success(request, 'Notícia criada com sucesso.')
        return redirect('noticia', slug=post.slug)

    return render(request, 'admin/desboord.html', {
        'user_count': User.objects.count(),
        'post_count': Post.objects.count(),
        'published_count': Post.objects.filter(is_published=True).count(),
        'comment_count': Comment.objects.count(),
        'access_count': AccessLog.objects.count(),
        'recent_posts': Post.objects.select_related('author')[:6],
        'post_form': post_form,
    })


@user_passes_test(_can_add_posts, login_url='login')
def create_post_view(request):
    post_form = PostForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and post_form.is_valid():
        post = post_form.save(commit=False)
        if post.is_published and not _can_publish_posts(request.user):
            post_form.add_error('is_published', 'Seu grupo pode criar rascunhos, mas não pode publicar notícias.')
        else:
            post.author = request.user
            base_slug = slugify(post.title) or 'noticia'
            post.slug = base_slug
            suffix = 2
            while Post.objects.filter(slug=post.slug).exists():
                post.slug = f'{base_slug}-{suffix}'
                suffix += 1
            if post.is_published:
                post.published_at = timezone.now()
            post.save()
            messages.success(request, 'Notícia criada com sucesso.')
            return redirect('noticia', slug=post.slug)

    return render(request, 'admin/post_create.html', {
        'post_form': post_form,
        'can_publish': _can_publish_posts(request.user),
    })


def login_view(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip().lower()
        ip_address = client_ip(request)
        if is_login_locked(identifier, ip_address):
            form.add_error(None, 'Muitas tentativas. Aguarde 15 minutos e tente novamente.')
        elif form.is_valid():
            clear_login_failures(identifier, ip_address)
            user = form.get_user()
            profile = user.security_profile
            if profile.mfa_enabled:
                request.session[MFA_PENDING_USER_SESSION_KEY] = user.pk
                request.session.set_expiry(300)
                return redirect('mfa-verify')
            auth_login(request, user)
            request.session['security_session_version'] = profile.session_version
            return redirect(request.POST.get('next') or 'home')
        else:
            register_login_failure(identifier, ip_address)
    return render(request, 'Login/login.html', {'form': form})


def mfa_verify(request):
    user_id = request.session.get(MFA_PENDING_USER_SESSION_KEY)
    if not user_id:
        return redirect('login')

    form = MFAForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = get_object_or_404(User, pk=user_id, is_active=True)
        profile = user.security_profile
        if profile.mfa_enabled and profile.mfa_secret and pyotp.TOTP(profile.mfa_secret).verify(
            form.cleaned_data['code'],
            valid_window=1,
        ):
            request.session.pop(MFA_PENDING_USER_SESSION_KEY, None)
            auth_login(request, user)
            request.session['security_session_version'] = profile.session_version
            return redirect('home')
        form.add_error('code', 'Código inválido ou expirado.')

    return render(request, 'auth/auth.html', {'form': form})


@login_required
def mfa_setup(request):
    profile = request.user.security_profile
    if profile.mfa_enabled:
        return render(request, 'Login/mfa_setup.html', {'enabled': True})

    if not profile.mfa_secret:
        profile.mfa_secret = pyotp.random_base32()
        profile.save(update_fields=['mfa_secret'])

    form = MFAForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if pyotp.TOTP(profile.mfa_secret).verify(form.cleaned_data['code'], valid_window=1):
            profile.mfa_enabled = True
            profile.save(update_fields=['mfa_enabled'])
            messages.success(request, 'A autenticação em dois fatores foi ativada.')
            return redirect('perfil')
        form.add_error('code', 'Código inválido ou expirado.')

    provisioning_uri = pyotp.TOTP(profile.mfa_secret).provisioning_uri(
        name=request.user.email or request.user.username,
        issuer_name='Linha de Frente',
    )
    return render(request, 'Login/mfa_setup.html', {
        'form': form,
        'secret': profile.mfa_secret,
        'provisioning_uri': provisioning_uri,
        'enabled': False,
    })


def cadastro(request):
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.is_active = False
        user.save()
        verification = EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        verification_url = request.build_absolute_uri(reverse('verify-email', args=[verification.token]))
        send_mail(
            'Confirme seu e-mail | Linha de Frente',
            f'Confirme sua conta acessando: {verification_url}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        messages.success(request, 'Conta criada. Confira seu e-mail para ativá-la.')
        return redirect('login')
    return render(request, 'Login/cadastro.html', {'form': form})


def verify_email(request, token):
    verification = get_object_or_404(EmailVerificationToken, token=token)
    if not verification.is_valid():
        messages.error(request, 'Este link de verificação expirou ou já foi utilizado.')
        return redirect('login')
    verification.user.is_active = True
    verification.user.save(update_fields=['is_active'])
    SecurityProfile.objects.update_or_create(
        user=verification.user,
        defaults={'email_verified': True},
    )
    verification.used_at = timezone.now()
    verification.save(update_fields=['used_at'])
    messages.success(request, 'E-mail confirmado. Agora você já pode entrar.')
    return redirect('login')


def logout_view(request):
    request.session.pop(MFA_PENDING_USER_SESSION_KEY, None)
    auth_logout(request)
    return redirect('home')

def health_check(request):
    return JsonResponse({'status': 'ok'})

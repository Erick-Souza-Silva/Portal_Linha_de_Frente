from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone

from .forms import PostForm, RegistrationForm
from .models import AccessLog, BrowsingHistory, Comment, EmailVerificationToken, Favorite, Post, SecurityProfile
from .security import clear_login_failures, client_ip, is_login_locked, register_login_failure
from .sports import fetch_scoreboard


def home(request):
    return render(request, 'pages/main.html', {
        'recent_posts': Post.objects.filter(is_published=True).select_related('author')[:6],
        'scoreboard': fetch_scoreboard(),
    })


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    return render(request, 'pages/notica.html', {'post': post})


def _is_admin_portal_user(user):
    try:
        profile = user.security_profile
    except SecurityProfile.DoesNotExist:
        profile = None
    return user.is_authenticated and (user.is_staff or user.is_superuser or getattr(profile, 'role', None) in (
        SecurityProfile.ROLE_ADMIN,
        SecurityProfile.ROLE_MODERATOR,
    ))


@login_required
def profile_view(request):
    return render(request, 'prefil/prefil.html', {
        'favorite_count': request.user.favorites.count(),
        'history_count': request.user.browsing_history.count(),
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

    post_form = PostForm(request.POST or None)
    if request.method == 'POST' and post_form.is_valid():
        post = post_form.save(commit=False)
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


def login_view(request):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip().lower()
        ip_address = client_ip(request)
        if is_login_locked(identifier, ip_address):
            form.add_error(None, 'Muitas tentativas. Aguarde 15 minutos e tente novamente.')
        elif form.is_valid():
            clear_login_failures(identifier, ip_address)
            auth_login(request, form.get_user())
            request.session['security_session_version'] = form.get_user().security_profile.session_version
            return redirect('home')
        else:
            register_login_failure(identifier, ip_address)
    return render(request, 'Login/login.html', {'form': form})


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
            None,
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
    verification.used_at = timezone.now()
    verification.save(update_fields=['used_at'])
    messages.success(request, 'E-mail confirmado. Agora você já pode entrar.')
    return redirect('login')


def logout_view(request):
    auth_logout(request)
    return redirect('home')

def health_check(request):
    return JsonResponse({'status': 'ok'})
from django.shortcuts import render

# Create your views here.

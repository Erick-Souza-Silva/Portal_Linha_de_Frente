from datetime import timedelta

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
import pyotp

from .models import EmailVerificationToken, Post


class HealthCheckTests(TestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get('/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Uma rodada para mudar tudo')


class AuthenticationTests(TestCase):
    def test_login_page_is_available(self):
        response = self.client.get('/login/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Entrar na sua conta')

    def test_user_can_create_account_and_verify_email(self):
        response = self.client.post('/cadastro/', {
            'username': 'torcedor',
            'email': 'torcedor@example.com',
            'password1': 'UmaSenhaForte123!',
            'password2': 'UmaSenhaForte123!',
        })

        self.assertRedirects(response, '/login/')
        self.assertTrue(User.objects.filter(username='torcedor').exists())
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertFalse(User.objects.get(username='torcedor').is_active)

        token = EmailVerificationToken.objects.get(user__username='torcedor')
        verify_response = self.client.get(f'/verificar-email/{token.token}/')

        self.assertRedirects(verify_response, '/login/')
        self.assertTrue(User.objects.get(username='torcedor').is_active)
        self.assertTrue(User.objects.get(username='torcedor').security_profile.email_verified)

    def test_expired_email_verification_token_does_not_activate_user(self):
        user = User.objects.create_user(
            username='expirado',
            email='expirado@example.com',
            password='UmaSenhaForte123!',
            is_active=False,
        )
        token = EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.get(f'/verificar-email/{token.token}/')

        self.assertRedirects(response, '/login/')
        user.refresh_from_db()
        token.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertIsNone(token.used_at)

    def test_email_verification_token_cannot_be_reused(self):
        user = User.objects.create_user(
            username='unico',
            email='unico@example.com',
            password='UmaSenhaForte123!',
            is_active=False,
        )
        token = EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=1),
        )

        first_response = self.client.get(f'/verificar-email/{token.token}/')
        second_response = self.client.get(f'/verificar-email/{token.token}/')

        self.assertRedirects(first_response, '/login/')
        self.assertRedirects(second_response, '/login/')
        user.refresh_from_db()
        token.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNotNone(token.used_at)

    def test_mfa_is_required_and_accepts_valid_code(self):
        user = User.objects.create_user(username='mfa-user', password='UmaSenhaForte123!')
        profile = user.security_profile
        profile.mfa_secret = pyotp.random_base32()
        profile.mfa_enabled = True
        profile.save(update_fields=['mfa_secret', 'mfa_enabled'])

        login_response = self.client.post('/login/', {
            'username': 'mfa-user',
            'password': 'UmaSenhaForte123!',
        })
        self.assertRedirects(login_response, '/seguranca/mfa/verificar/')
        self.assertFalse(login_response.wsgi_request.user.is_authenticated)

        verify_response = self.client.post('/seguranca/mfa/verificar/', {
            'code': pyotp.TOTP(profile.mfa_secret).now(),
        })
        self.assertRedirects(verify_response, '/')
        self.assertTrue(verify_response.wsgi_request.user.is_authenticated)

    def test_user_can_logout(self):
        user = User.objects.create_user(username='leitor', password='UmaSenhaForte123!')
        self.client.force_login(user)

        response = self.client.get('/sair/')

        self.assertRedirects(response, '/')
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_is_locked_after_five_failures(self):
        for _ in range(5):
            response = self.client.post('/login/', {'username': 'unknown', 'password': 'wrong'})
            self.assertEqual(response.status_code, 200)

        response = self.client.post('/login/', {'username': 'unknown', 'password': 'wrong'})

        self.assertContains(response, 'Aguarde 15 minutos')


class UserAreaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='leitor-area', password='UmaSenhaForte123!')

    def test_user_can_access_profile_history_and_favorites(self):
        self.client.force_login(self.user)

        self.assertEqual(self.client.get('/perfil/').status_code, 200)
        self.assertEqual(self.client.get('/perfil/historico/').status_code, 200)
        self.assertEqual(self.client.get('/perfil/favoritos/').status_code, 200)

    def test_authenticated_user_can_comment_favorite_and_create_history(self):
        post = Post.objects.create(
            title='Notícia para interação',
            slug='noticia-para-interacao',
            body='Conteúdo da notícia.',
            author=self.user,
            is_published=True,
            published_at=timezone.now(),
        )
        self.client.force_login(self.user)

        response = self.client.get(f'/noticia/{post.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.browsing_history.count(), 1)

        comment_response = self.client.post(f'/noticia/{post.slug}/', {
            'body': 'Minha opinião sobre a notícia.',
        })
        self.assertRedirects(comment_response, f'/noticia/{post.slug}/')
        self.assertEqual(post.comments.count(), 1)
        self.assertEqual(post.comments.get().author, self.user)

        favorite_response = self.client.post(f'/perfil/favoritos/post/{post.pk}/', {
            'next': f'/noticia/{post.slug}/',
        })
        self.assertRedirects(favorite_response, f'/noticia/{post.slug}/')
        self.assertEqual(self.user.favorites.count(), 1)

    def test_anonymous_user_cannot_comment(self):
        post = Post.objects.create(
            title='Notícia pública',
            slug='noticia-publica',
            body='Conteúdo público.',
            author=self.user,
            is_published=True,
            published_at=timezone.now(),
        )

        response = self.client.post(f'/noticia/{post.slug}/', {'body': 'Comentário anônimo.'})

        self.assertRedirects(response, f'/login/?next=/noticia/{post.slug}/')
        self.assertEqual(post.comments.count(), 0)

    def test_anonymous_user_is_redirected_from_user_area(self):
        response = self.client.get('/perfil/historico/')

        self.assertRedirects(response, '/login/?next=/perfil/historico/')

    def test_only_staff_can_access_admin_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get('/painel/')

        self.assertRedirects(response, '/login/?next=/painel/')

        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.assertEqual(self.client.get('/painel/').status_code, 200)

    def test_staff_can_publish_post_and_open_news_page(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)

        response = self.client.post('/painel/', {
            'title': 'Novo destaque do campeonato',
            'category': 'Futebol',
            'body': 'Texto completo da notícia publicada pelo painel.',
            'cover_image': '',
            'is_published': 'on',
        })

        post = Post.objects.get(title='Novo destaque do campeonato')
        self.assertRedirects(response, f'/noticia/{post.slug}/')
        self.assertEqual(post.author, self.user)
        self.assertTrue(post.is_published)
        self.assertContains(self.client.get(f'/noticia/{post.slug}/'), post.body)

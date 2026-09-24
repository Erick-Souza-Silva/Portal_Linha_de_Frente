from django.test import TestCase
from django.contrib.auth.models import User

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

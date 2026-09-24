from django.urls import path

from .views import (
    admin_dashboard,
    cadastro,
    clear_history,
    favorites_view,
    health_check,
    history_view,
    home,
    login_view,
    logout_view,
    post_detail,
    profile_view,
    toggle_favorite,
    verify_email,
)

urlpatterns = [
    path('', home, name='home'),
    path('noticia/<slug:slug>/', post_detail, name='noticia'),
    path('health/', health_check, name='health-check'),
    path('login/', login_view, name='login'),
    path('cadastro/', cadastro, name='cadastro'),
    path('verificar-email/<uuid:token>/', verify_email, name='verify-email'),
    path('sair/', logout_view, name='logout'),
    path('perfil/', profile_view, name='perfil'),
    path('prefil/', profile_view, name='perfil-legacy'),
    path('perfil/historico/', history_view, name='historico'),
    path('perfil/historico/limpar/', clear_history, name='limpar-historico'),
    path('perfil/favoritos/', favorites_view, name='favorito'),
    path('perfil/favoritos/post/<int:post_id>/', toggle_favorite, name='alternar-favorito'),
    path('prefil/historico/', history_view, name='historico-legacy'),
    path('prefil/historico/limpar/', clear_history, name='limpar-historico-legacy'),
    path('prefil/favoritos/', favorites_view, name='favorito-legacy'),
    path('prefil/favoritos/post/<int:post_id>/', toggle_favorite, name='alternar-favorito-legacy'),
    path('painel/', admin_dashboard, name='admin-dashboard'),
]
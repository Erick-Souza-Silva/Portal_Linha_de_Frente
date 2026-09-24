from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Post


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label='E-mail')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'category', 'body', 'cover_image', 'is_published')
        labels = {
            'title': 'Título',
            'category': 'Categoria',
            'body': 'Texto da notícia',
            'cover_image': 'Imagem de capa (URL)',
            'is_published': 'Publicar agora',
        }
        widgets = {
            'body': forms.Textarea(attrs={'rows': 8}),
        }
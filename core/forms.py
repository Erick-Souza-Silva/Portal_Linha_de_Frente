from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Category, Comment, Post


class CategoryChoiceField(forms.ModelChoiceField):
    def to_python(self, value):
        if isinstance(value, str) and value.strip() and not value.isdigit():
            category, _ = Category.objects.get_or_create(name=value.strip())
            return category
        return super().to_python(value)


class MFAForm(forms.Form):
    code = forms.CharField(
        label='Código de autenticação',
        min_length=6,
        max_length=6,
        strip=True,
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'one-time-code'}),
    )

    def clean_code(self):
        code = self.cleaned_data['code']
        if not code.isdigit():
            raise forms.ValidationError('Informe os 6 números do seu aplicativo autenticador.')
        return code


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label='E-mail')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('body',)
        labels = {'body': 'Seu comentário'}
        widgets = {
            'body': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Compartilhe sua opinião sobre esta notícia',
            }),
        }


class PostForm(forms.ModelForm):
    category = CategoryChoiceField(queryset=Category.objects.filter(is_active=True), label='Categoria')
    pdf_file = forms.FileField(
        required=False,
        label='Anexo PDF',
        help_text='Opcional. Envie somente arquivos PDF de até 10 MB.',
    )

    class Meta:
        model = Post
        fields = ('title', 'category', 'body', 'cover_image', 'pdf_file', 'pdf_description', 'is_published')
        labels = {
            'title': 'Título',
            'category': 'Categoria',
            'body': 'Texto da notícia',
            'cover_image': 'Imagem de capa (URL)',
            'pdf_description': 'Descrição do PDF',
            'is_published': 'Publicar agora',
        }
        widgets = {
            'body': forms.Textarea(attrs={'rows': 8}),
        }

    def clean_pdf_file(self):
        pdf_file = self.cleaned_data.get('pdf_file')
        if not pdf_file:
            return pdf_file
        if not pdf_file.name.lower().endswith('.pdf'):
            raise forms.ValidationError('O anexo precisa estar no formato PDF.')
        if pdf_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('O PDF não pode ultrapassar 10 MB.')
        return pdf_file
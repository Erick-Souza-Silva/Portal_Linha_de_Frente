from .models import Category


def navigation_categories(request):
	return {'categories': Category.objects.filter(is_active=True)}
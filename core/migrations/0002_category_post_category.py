from django.db import migrations, models
import django.db.models.deletion


def copy_post_categories(apps, schema_editor):
	Category = apps.get_model('core', 'Category')
	Post = apps.get_model('core', 'Post')

	category_ids = {}
	for post in Post.objects.all().only('id', 'category'):
		name = post.category or 'Esportes'
		if name not in category_ids:
			category, _ = Category.objects.get_or_create(name=name)
			category_ids[name] = category.pk
		Post.objects.filter(pk=post.pk).update(category_relation_id=category_ids[name])


class Migration(migrations.Migration):

	dependencies = [
		('core', '0001_initial'),
	]

	operations = [
		migrations.CreateModel(
			name='Category',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('name', models.CharField(max_length=80, unique=True)),
				('slug', models.SlugField(blank=True, max_length=90, unique=True)),
				('is_active', models.BooleanField(default=True)),
				('order', models.PositiveIntegerField(default=0)),
			],
			options={
				'ordering': ('order', 'name'),
				'verbose_name': 'categoria',
				'verbose_name_plural': 'categorias',
			},
		),
		migrations.AddField(
			model_name='post',
			name='category_relation',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='legacy_posts', to='core.category'),
		),
		migrations.RunPython(copy_post_categories, migrations.RunPython.noop),
		migrations.RemoveField(
			model_name='post',
			name='category',
		),
		migrations.RenameField(
			model_name='post',
			old_name='category_relation',
			new_name='category',
		),
		migrations.AlterField(
			model_name='post',
			name='category',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='posts', to='core.category'),
		),
	]
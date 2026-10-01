from django.db import migrations


class Migration(migrations.Migration):

	dependencies = [
		('core', '0002_category_post_category'),
	]

	operations = [
		migrations.AlterModelOptions(
			name='post',
			options={
				'ordering': ('-published_at', '-created_at'),
				'permissions': (('publish_post', 'Pode publicar notícias'),),
			},
		),
	]
from django.db import migrations


class Migration(migrations.Migration):

	dependencies = [
		('core', '0003_post_publish_permission'),
	]

	operations = [
		migrations.AlterModelOptions(
			name='post',
			options={
				'permissions': (('publish_post', 'Pode publicar notícias'),),
			},
		),
	]
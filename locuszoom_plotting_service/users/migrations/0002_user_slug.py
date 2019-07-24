# Generated by Django 2.0.13 on 2019-07-23 19:03

from django.db import migrations, models
import locuszoom_plotting_service.base.util


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='slug',
            field=models.SlugField(default=locuszoom_plotting_service.base.util._generate_slug, editable=False, help_text='The external facing identifier for this record', max_length=6, unique=True),
        ),
    ]
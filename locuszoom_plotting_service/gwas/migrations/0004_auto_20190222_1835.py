# Generated by Django 2.0.10 on 2019-02-22 18:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gwas', '0003_auto_20190220_1759'),
    ]

    operations = [
        migrations.RenameField(
            model_name='gwas',
            old_name='user',
            new_name='owner',
        ),
        migrations.AddField(
            model_name='gwas',
            name='is_public',
            field=models.BooleanField(default=False, help_text='Is this study visible to everyone?'),
        ),
    ]

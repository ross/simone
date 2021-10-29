# Generated by Django 3.2.8 on 2021-10-27 21:50

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Fact',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('user_id', models.CharField(max_length=32)),
                ('value', models.CharField(max_length=255)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ('user_id', 'created_at'),
                'unique_together': {('user_id', 'value')},
                'index_together': {('user_id', 'created_at')},
            },
        )
    ]
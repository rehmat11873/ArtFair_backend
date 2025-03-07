# Generated by Django 5.1.3 on 2024-12-13 18:37

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('training_data', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='License',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('terms', models.TextField()),
                ('status', models.CharField(max_length=50)),
                ('licensee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='received_licenses', to=settings.AUTH_USER_MODEL)),
                ('rights_owner', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='issued_licenses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='LicensedContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('access_type', models.CharField(max_length=50)),
                ('restrictions', models.JSONField(default=dict)),
                ('license', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='licensed_content', to='licensing.license')),
                ('media_file', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='licenses', to='training_data.mediafile')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]

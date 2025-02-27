# Generated by Django 5.1.5 on 2025-02-18 17:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training_data', '0002_remove_mediafile_deleted_at_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='videofile',
            name='mediafile_ptr',
        ),
        migrations.AlterField(
            model_name='audiosegment',
            name='source_video',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audio_segments', to='training_data.mediafile'),
        ),
        migrations.AddField(
            model_name='mediafile',
            name='linked_video_file',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='captions_media', to='training_data.mediafile'),
        ),
        migrations.AlterField(
            model_name='mediafile',
            name='S3URL',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='mediafile',
            name='file_type',
            field=models.CharField(blank=True, choices=[('video', 'Video'), ('audio', 'Audio'), ('subtitle', 'Subtitle'), ('csv', 'CSV'), ('ass', 'Caption')], max_length=50, null=True),
        ),
        migrations.DeleteModel(
            name='Caption',
        ),
        migrations.DeleteModel(
            name='VideoFile',
        ),
    ]

# training_data/models.py
import os
import hashlib
from django.db import models
from django.core.files.storage import default_storage
from apps.core.models import SoftDeleteBaseModel
from django.conf import settings

def get_upload_path(instance, filename):
    """Generate upload path based on client and file type"""
    return f"uploads/{instance.owner.id}/{instance._meta.model_name}/{filename}" if instance and instance.owner else  f"uploads/{instance._meta.model_name}/{filename}"


class MediaFile(models.Model):
    """Base model for all uploaded media files"""
    FILE_TYPES = [
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('subtitle', 'Subtitle'),
        ('csv', 'CSV'),
        ('ass', 'Caption')
    ]

    # client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='media_files')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='media_files')
    linked_video_file = models.ForeignKey(
        'training_data.MediaFile',
        on_delete=models.CASCADE,
        related_name='captions_media',
        null=True,
        blank=True
    )
    file = models.FileField(upload_to=get_upload_path, blank=True, null=True)
    file_type = models.CharField(max_length=50, choices=FILE_TYPES, blank=True, null=True)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.BigIntegerField(editable=False, null=True)
    md5_hash = models.CharField(max_length=32, editable=False, null=True)
    processing_status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    metadata = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    S3URL = models.CharField(max_length=255, default="", blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            self.original_filename = self.file.name

            # Calculate MD5 hash
            md5 = hashlib.md5()
            for chunk in self.file.chunks():
                md5.update(chunk)
            self.md5_hash = md5.hexdigest()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.owner.email} - {self.original_filename}"
    def delete(self, *args, **kwargs):
        # Delete the actual file when the model is deleted
        if self.file:
            default_storage.delete(self.file.name)
        super().delete(*args, **kwargs)

# class VideoFile(MediaFile):
#     """Video specific attributes"""
#     duration = models.FloatField(null=True, blank=True)  # Allow null for initial upload
#     resolution = models.CharField(max_length=20, blank=True)
#     fps = models.FloatField(null=True, blank=True)
#
#     def clean(self):
#         super().clean()
#         if self.file and not self.file_type in ['mp4', 'mov', 'avi', 'mkv']:
#             from django.core.exceptions import ValidationError
#             raise ValidationError('Invalid video file format')

class AudioSegment(MediaFile):
    """Processed audio segments from videos"""
    source_video = models.ForeignKey(MediaFile, on_delete=models.CASCADE, related_name='audio_segments')
    start_time = models.FloatField()
    end_time = models.FloatField()
    sampling_rate = models.IntegerField()
    transcription = models.TextField(blank=True)
    speaker_id = models.CharField(max_length=100, blank=True)

    def clean(self):
        super().clean()
        if self.file and not self.file_type in ['mp3', 'wav', 'aac']:
            from django.core.exceptions import ValidationError
            raise ValidationError('Invalid audio file format')
#
# class Caption(SoftDeleteBaseModel):
#     """Caption/subtitle entries"""
#     video = models.ForeignKey(VideoFile, on_delete=models.CASCADE, related_name='captions', null=True, blank=True)
#     media = models.ForeignKey(MediaFile, on_delete=models.CASCADE,related_name='captions_media', null=True)
#     start_time = models.FloatField(null=True, blank=True)
#     end_time = models.FloatField(null=True, blank=True)
#     text = models.TextField(null=True, blank=True)
#     language = models.CharField(
#         max_length=10,
#         choices=[('en', 'English'), ('es', 'Spanish'), ('fr', 'French')]  # Add more as needed
#     )
#     speaker_id = models.CharField(max_length=100, blank=True)
#     file = models.FileField(upload_to=get_upload_path, blank=True, null=True)

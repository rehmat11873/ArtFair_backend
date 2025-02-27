from django.contrib import admin
from django.contrib import messages
from .models import MediaFile, AudioSegment
from django.utils import timezone
from django.urls import path
from django.shortcuts import render
from .tasks import process_and_upload
from django.contrib.auth import get_user_model
from django.conf import settings


User = get_user_model()


def queue_for_processing(modeladmin, request, queryset):
    """
    Generic action to queue items for processing
    """
    try:
        # Update status to 'processing' for selected items
        count = queryset.update(
            processing_status='processing',
            updated_at=timezone.now()
        )

        # Here you would typically queue items in your task system
        # e.g., celery, django-q, etc.

        modeladmin.message_user(
            request,
            f'{count} items have been queued for processing.',
            messages.SUCCESS
        )
    except Exception as e:
        modeladmin.message_user(
            request,
            f'Error queueing items: {str(e)}',
            messages.ERROR
        )


queue_for_processing.short_description = "Queue selected items for processing"


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'file_type', 'file_size', 'processing_status', 'created_at', 'linked_video_file')
    list_editable = ('linked_video_file',)
    list_filter = ('file_type', 'processing_status')
    search_fields = ('file_path', 'owner__email', 'md5_hash', 'original_filename')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('owner',)


    def get_queryset(self, request):
        return MediaFile.objects.all()

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('custom-page/', admin.site.admin_view(self.custom_page_view), name="custom_page"),
            path('<int:pk>/process_video/', admin.site.admin_view(self.process_video_view), name="process_video")
        ]
        return custom_urls + urls

    
    def custom_page_view(self, request):
        users = User.objects.all().values("id", "email", "first_name", "last_name")
        return render(request, "admin/custom_page.html", {"users": users})

    def process_video_view(self, request, pk):
        if request.method == 'POST':
            selected_caption = request.POST.get('caption_file')
            try:
                process_and_upload(pk, selected_caption)
                self.message_user(request, f"caption id: {request.POST.get('caption_file')}, vid id: {pk}")
            except Exception as e:
                messages.error(request, f"Error processing video: {str(e)}")
        video = MediaFile.objects.get(id=pk)
        caption_files = MediaFile.objects.filter(file_type='subtitle')
        return render(request, 'admin/process_video.html',
                      {'caption_files': caption_files, 'video_name': video.original_filename})

    def process_video(self, request, pk):
        obj = self.get_object(request, pk)
        # ... do something with obj ...
        self.message_user(request, "Custom action performed successfully.")

    actions = [queue_for_processing, process_video]


@admin.register(AudioSegment)
class AudioSegmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_video', 'start_time', 'end_time', 'sampling_rate', 'speaker_id')
    list_filter = ('sampling_rate', 'processing_status')
    search_fields = ('transcription', 'speaker_id', 'source_video__file_path')
    raw_id_fields = ('source_video', 'owner')
    actions = [queue_for_processing]

    def queue_transcription(self, request, queryset):
        try:
            # Update status for selected audio segments
            count = queryset.update(
                processing_status='processing',
                updated_at=timezone.now()
            )

            # Mock: Here you would queue transcription tasks
            self.message_user(
                request,
                f'{count} audio segments have been queued for transcription.',
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(
                request,
                f'Error queueing transcription: {str(e)}',
                messages.ERROR
            )

    queue_transcription.short_description = "Queue audio for transcription"

    # Add audio-specific action
    actions = [queue_for_processing, queue_transcription]

    def get_queryset(self, request):
        return AudioSegment.objects.all()

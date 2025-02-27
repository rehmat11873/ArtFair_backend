# tasks.py
from celery import shared_task
import os
from apps.users.models import CustomUser
from .models import MediaFile
from .utils import (
    convert_video_to_audio,
    convert_aac_to_wav,
    create_audio_clips,
    compile_dataset,
    upload_to_huggingface
)

@shared_task
def process_video_file(video_file_id):
    """Process video file - convert to audio"""
    video_file = MediaFile.objects.get(id=video_file_id)
    video_file.processing_status = 'processing'
    video_file.save()

    try:
        audio_file = convert_video_to_audio(video_file)
        video_file.processing_status = 'completed'
        video_file.metadata['audio_file_id'] = audio_file.id
        video_file.save()
        return audio_file.id
    except Exception as e:
        video_file.processing_status = 'failed'
        video_file.metadata['error'] = str(e)
        video_file.save()
        raise


@shared_task
def process_audio_file(audio_file_id):
    """Process video file - convert to audio"""
    audio_file = MediaFile.objects.get(id=audio_file_id)
    audio_file.processing_status = 'processing'
    audio_file.save()
    try:
        _, ext = os.path.splitext(audio_file.file.name)
        is_aac = ext.lower() == '.aac'
        if is_aac:
            convert_aac_to_wav(audio_file)
        audio_file.processing_status = 'completed'
        audio_file.metadata['audio_file_id'] = audio_file.id
        audio_file.save()
    except Exception as e:
        audio_file.processing_status = 'failed'
        audio_file.metadata['error'] = str(e)
        audio_file.save()
        raise

@shared_task
def process_audio_clips(audio_file_id, csv_file_id):
    """Process video file - convert to audio"""
    audio_file = MediaFile.objects.get(id=audio_file_id)
    csv_file = MediaFile.objects.get(id=csv_file_id)
    audio_file.processing_status = 'processing'
    audio_file.save()
    try:
        create_audio_clips(audio_file, csv_file)
        audio_file.processing_status = 'completed'
        audio_file.save()
    except Exception as e:
        audio_file.processing_status = 'failed'
        audio_file.metadata['error'] = str(e)
        audio_file.save()
        raise

@shared_task
def process_subtitle_file(subtitle_file_id):
    """Process subtitle file - convert to CSV and clean"""
    subtitle_file = MediaFile.objects.get(id=subtitle_file_id)
    subtitle_file.processing_status = 'processing'
    subtitle_file.save()

    try:
        # metadata_file = convert_subtitles_to_metadata(subtitle_file)
        metadata_file = None
        metadata_file.processing_status = 'completed'
        subtitle_file.processing_status = 'completed'
        subtitle_file.metadata['csv_file_id'] = metadata_file.id
        subtitle_file.save()
        metadata_file.save()
        return metadata_file
    except Exception as e:
        subtitle_file.processing_status = 'failed'
        subtitle_file.metadata['error'] = str(e)
        subtitle_file.save()
        raise


@shared_task
def compile_training_dataset(channel_id):
    """Compile and upload training dataset"""
    channel = CustomUser.objects.get(id=channel_id)
    csv_files = MediaFile.objects.filter(
        owner=channel,
        file_type='csv',
        processing_status='completed'
    )
    try:
        dataset = compile_dataset(list(csv_files))
        upload_to_huggingface(dataset, channel.id)
        return True
    except Exception as e:
        raise


# This is a test function used in the temporary admin dashboard page 
# to trigger the processing pipeline for a specific audio file. In the future
# the processing steps will happen separately from the compile_training_dataset step.
def process_and_upload(video_file_id, subtitle_file_id):
    audio_file_id = process_video_file(video_file_id)
    process_audio_file(audio_file_id)
    processed_csv_file = process_subtitle_file(subtitle_file_id)
    process_audio_clips(audio_file_id, processed_csv_file.id)
    compile_training_dataset(processed_csv_file.owner.id)

import os
from io import BytesIO
from ..models import MediaFile
from pydub import AudioSegment as PydubAudioSegment  # Renamed to avoid conflict


def convert_video_to_audio(video_file):
    """Convert video to audio using pydub"""
    try:
        # Create audio file instance
        audio_file = MediaFile.objects.create(
            owner=video_file.owner,
            file_type='audio',
            original_filename=f"{os.path.splitext(video_file.original_filename)[0]}.wav"
        )

        # Download video file to temp storage
        video_file.file.seek(0)
        video_data = video_file.file.read()
        video_temp = BytesIO(video_data)

        # Convert to audio using pydub
        video = PydubAudioSegment.from_file(video_temp)  # Using renamed import
        audio = video.set_frame_rate(16000)  # Set to 16kHz for Whisper compatibility

        # Save to temp buffer
        audio_buffer = BytesIO()
        audio.export(audio_buffer, format='wav')
        audio_buffer.seek(0)  # Reset buffer position to start

        # Save to MediaFile
        audio_file.file.save(
            f"{audio_file.original_filename}",
            audio_buffer,
            save=True
        )

        return audio_file

    except Exception as e:
        raise Exception(f"Error converting video to audio: {str(e)}")


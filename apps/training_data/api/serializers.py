from rest_framework import serializers
from apps.training_data.models import MediaFile 


class FileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(write_only=True)
    s3_url = serializers.CharField(write_only=True)
    original_filename = serializers.CharField(max_length=255)

    class Meta:
        model = MediaFile
        fields = ["user_email", "s3_url", "original_filename"]

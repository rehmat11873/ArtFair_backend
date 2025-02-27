from django.urls import path 
from .api.views import (
    generate_s3_presigned_url, 
    create_file_upload,
    create_s3_multipart,
    s3_multipart_listParts,
    s3_multipart_signPart,
    s3_multipart_abort,
    s3_multipart_complete,
    upload_media
)

urlpatterns = [
    path('generate-s3-presigned-url/',generate_s3_presigned_url, name='generate_s3_presigned_url'),
    path('create/', create_file_upload, name='create_file_upload'),
    path('create_s3_multipart/', create_s3_multipart, name='create_s3_multipart'),
    path('s3_multipart_listParts/<str:uploadId>/', s3_multipart_listParts, name='s3_multipart_listParts'),
    path('s3_multipart_signPart/<str:uploadId>/<int:partNumber>/', s3_multipart_signPart, name='s3_multipart_signPart'),
    path('s3_multipart_abort/<str:uploadId>/', s3_multipart_abort, name='s3_multipart_abort'),
    path('s3_multipart_complete/<str:uploadId>/', s3_multipart_complete, name='s3_multipart_complete'),
    # local configutations
    path("media/upload/", upload_media, name="upload_media"),
]
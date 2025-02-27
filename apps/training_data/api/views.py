import boto3
from botocore.exceptions import NoCredentialsError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.decorators import api_view
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from apps.users.models import CustomUser
from apps.training_data.models import MediaFile
from .serializers import FileSerializer
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


@api_view(['POST'])
def create_file_upload(request):
    serializer = FileSerializer(data=request.data, many=True)
    # Handling multiple entries in one request using bulk_create
    media_files = []
    if serializer.is_valid():
        prev_user = None
        for file_meta in request.data:
            user_email = file_meta["user_email"]
            try:
                user = prev_user
                # Only query CustomUser table when current file_meta user is different from the previous user.
                if user == None or user_email != user.email:
                    user = CustomUser.objects.get(email=user_email)
                file_meta_data = MediaFile(
                    owner=user,
                    original_filename=file_meta["original_filename"],
                    S3URL=file_meta["s3_url"]
                )
                media_files.append(file_meta_data)
                prev_user = user
            except CustomUser.DoesNotExist:
                raise NotFound(detail="User with the provided email does not exist.", code=status.HTTP_400_BAD_REQUEST)
        new_file_metadata = MediaFile.objects.bulk_create(media_files)
        return Response(FileSerializer(new_file_metadata, many=True).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



s3_client = boto3.client(
    's3',
    region_name=settings.AWS_S3_REGION,
)


@csrf_exempt
def generate_s3_presigned_url(request):
    data = json.loads(request.body)
    file_name = data.get('file_name')
    file_type = data.get('file_type')

    try:
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': file_name,
                'ContentType': file_type
            },
            ExpiresIn=3600
        )
        return JsonResponse(
            {
                'url': presigned_url,
                'fields': {
                    'key': file_name,
                    'content-type': file_type
                },
                "method": "PUT",
                "headers": {
                    'content-type': file_type
                }
            }
        )
    except (NoCredentialsError, Exception) as e:
        return JsonResponse({'error': str(e)}, status=403)
    
@csrf_exempt
@api_view(['POST'])
def create_s3_multipart(request):
    data = request.data
    file_type = data["type"]
    file_name = data["file_name"]
    try:
        res = s3_client.create_multipart_upload(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file_name,
            ContentType=file_type
        )
        return JsonResponse(
            {
                "uploadId": res["UploadId"],
                "key": res["Key"]
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
@api_view(['POST'])
def s3_multipart_listParts(request, uploadId):
    data = request.data
    try:
        res = s3_client.list_parts(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            UploadId=uploadId,
            Key=data["key"]
        )
        return JsonResponse({
            "parts": res["Parts"]
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
@api_view(['POST'])
def s3_multipart_signPart(request, uploadId, partNumber):
    data = request.data
    try:
        url = s3_client.generate_presigned_url("upload_part",
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': data["key"],
                "UploadId":uploadId,
                "PartNumber":partNumber
            },
            ExpiresIn=3600
        )
        return JsonResponse({
            "url": url
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
@api_view(['DELETE'])
def s3_multipart_abort(request, uploadId):
    data = request.data
    try:
        s3_client.abort_multipart_upload(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=data["key"],
            UploadId=uploadId
        )
        return JsonResponse({})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
@api_view(['POST'])
def s3_multipart_complete(request, uploadId):
    data = request.data
    parts = data.get("parts")
    file_key = data.get("key")
    try:
        res = s3_client.complete_multipart_upload(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file_key,
            UploadId=uploadId,
            MultipartUpload={"Parts": parts}
        )
        return JsonResponse({
                'message': 'Multipart upload completed successfully',
                'name': res.get('Key'),
                "S3URL": res.get("Location")
            })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)




@csrf_exempt
def upload_media(request):
    if request.method == "POST" and request.FILES.get("file"):
        try:
            file = request.FILES["file"]
            user = request.user if request.user.is_authenticated else None
            user_id = request.POST.get("user_id")  # Get user from form data

            # Save file
            file_path = default_storage.save(f"media/{file.name}", ContentFile(file.read()))
            
            # Manually construct the full URL
            base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
            file_url = f"{base_url}{settings.MEDIA_URL}{(file_path)}"

            # file_url = default_storage.url(file_path)

            # Create MediaFile entry
            media_file = MediaFile.objects.create(
                owner=user,
                original_filename=file.name,
                S3URL=file_url,
            )

            return JsonResponse({
                "success": True,
                "file_url": file_url,
                "url": file_url,
                "original_filename": file.name,
                "media_id": media_file.id
            })
            
            
            

        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)

    return JsonResponse({
        "success": False,
        "error": "Invalid request"
    }, status=400)


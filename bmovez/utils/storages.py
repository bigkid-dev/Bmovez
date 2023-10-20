from storages.backends.s3boto3 import S3Boto3Storage


class StaticRootS3Boto3Storage(S3Boto3Storage):
    location = "static"
    default_acl = "public-read"


class MediaRootS3Boto3Storage(S3Boto3Storage):
    location = "media"
    file_overwrite = False


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT /<user_id>/<filename>
    return f"uploads/{instance.created_by.id}/{filename}"

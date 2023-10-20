import uuid

from django.contrib.auth.models import AbstractUser
from django.core import signing
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Default custom user model for BMovez."""

    first_name = None  # type: ignore
    last_name = None  # type: ignore

    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )
    name = models.CharField(_("Name of User"), max_length=255)
    profile_picture = models.ImageField(
        upload_to="media/profiles/", null=True, blank=True, max_length=300
    )
    phone_number = models.CharField(max_length=255, unique=True)

    password_reset_key = models.CharField(max_length=100, blank=True, null=True)


class ResetPasswordOTP(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    signed_pin = models.CharField(max_length=1000)
    is_active = models.BooleanField(default=True)
    is_expired = models.BooleanField(default=False)
    duration_in_minutes = models.IntegerField(default=10)
    datetime_created = models.DateTimeField(auto_now_add=True)


# NOTE: This model should not be here but lets leave it here for now
class FreePBXOauth2Access(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )
    token_type = models.CharField(max_length=100)
    expires_in = models.DateTimeField()
    expired = models.BooleanField(default=False)
    signed_access_token = models.TextField()
    datetime_created = models.DateTimeField(auto_now_add=True)

    def get_unsigned_access_token(self) -> str:
        """Returns unsigned access token."""
        signer = signing.Signer()
        return signer.unsign(self.signed_access_token)

    @staticmethod
    def sign_access_token(token: str):
        signer = signing.Signer()
        return signer.sign(value=token)


class FreepbxExtentionProfile(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    extention_id = models.PositiveIntegerField(unique=True, primary_key=False)
    caller_id = models.CharField(max_length=200)
    extention_password = models.TextField()
    datetime_created = models.DateTimeField(auto_now_add=True)

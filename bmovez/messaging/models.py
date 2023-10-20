import uuid

from django.db import models

from bmovez.users.models import User
from bmovez.utils.storages import user_directory_path


class Channel(models.Model):
    CHANNEL_TYPE_DM = "DM"
    CHANNEL_TYPE_GROUP = "GROUP"

    CHANNEL_TYPES = (
        (CHANNEL_TYPE_DM, "DM"),
        (CHANNEL_TYPE_GROUP, "GROUP"),
    )

    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )
    users = models.ManyToManyField(
        User, through="messaging.ChannelMembership", through_fields=("channel", "user")
    )
    created_by = models.ForeignKey(
        User, related_name="my_channels", null=True, on_delete=models.CASCADE
    )
    type = models.CharField(choices=CHANNEL_TYPES, max_length=50)
    title = models.CharField(blank=True, null=True, max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(
        upload_to="channels/icons/", null=True, blank=True, max_length=300
    )
    is_active = models.BooleanField(default=True)
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)


class ChannelMembership(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )
    channel = models.ForeignKey(Channel, null=True, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    added_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_memberships", null=True
    )
    is_admin = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=True)
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(
                fields=["channel", "user"], name="unique channel membership"
            )
        ]


class File(models.Model):
    FILE_TYPE_IMAGE = "IMG"
    FILE_TYPE_DOCUMENT = "DOC"

    FILE_TYPES = (
        (FILE_TYPE_IMAGE, "IMAGE"),
        (FILE_TYPE_DOCUMENT, "DOCUMENT"),
    )

    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=255, choices=FILE_TYPES)
    file = models.FileField(upload_to=user_directory_path, max_length=300)
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)


class Message(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    files = models.ManyToManyField(File, null=True)
    tagged_users = models.ManyToManyField(
        User, related_name="tagged_message_set", null=True
    )
    text = models.TextField(max_length=3000)
    edited = models.BooleanField(default=False)
    replying = models.ForeignKey(
        "messaging.Message", on_delete=models.DO_NOTHING, null=True
    )
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)


class Reaction(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )
    emoji = models.CharField(max_length=50)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)

import logging
from typing import Any

from rest_framework import serializers

from bmovez.messaging.api.v1.utils import assign_members_to_channel
from bmovez.messaging.models import Channel, ChannelMembership, File, Message, Reaction
from bmovez.users.api.v1.serializers import UserSerializer
from bmovez.users.models import User

logger = logging.getLogger()


class ChannelSerializer(serializers.ModelSerializer):
    users = UserSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Channel
        fields = [
            "title",
            "type",
            "description",
            "users",
            "icon",
            "id",
            "created_by",
            "datetime_updated",
        ]

        read_only_fields = ["id", "created_by", "datetime_updated", "type"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate channel data."""
        data = super().validate(attrs)
        return data

    def create(self, validated_data: dict[str, Any]) -> Channel:
        """Create a group channel."""

        user = self.context["request"].user

        # we only allow API creation of GROUP channels
        validated_data["type"] = Channel.CHANNEL_TYPE_GROUP
        validated_data["created_by"] = user
        channel = super().create(validated_data)

        ChannelMembership.objects.create(
            channel=channel, user=user, added_by=user, is_admin=True
        )

        return channel

    def dm_channel_representation(self, instance: Channel) -> dict[str, Any]:
        """Construct channel representaion for DM channels."""

        context_user = instance.users.exclude(
            id=self.context["request"].user.id
        ).first()
        if not context_user:
            logger.error(
                "bmovez::messaging::api::v1::serializer::ChannelSerializer::dm_channel_representation"
                " context_user is None. DM is missing a second user",
                extra={"dm_id": str(instance.id)},
            )
            context_user = self.context["request"].user

        data = {
            "id": str(instance.id),
            "users": [
                {**UserSerializer(instance=context_user).data, "membership_data": None}
            ],
            "type": instance.type,
            "title": context_user.name,
            "description": "",
            "icon": context_user.profile_picture
            if (context_user.profile_picture)
            else None,
            "is_active": instance.is_active,
            "datetime_updated": instance.datetime_updated,
        }

        return data

    def group_channel_representation(self, instance: Channel) -> dict[str, Any]:
        """Construct channel representation for group channels."""

        members = ChannelMembership.objects.filter(channel=instance)

        data = {
            "id": str(instance.id),
            "users": [
                {
                    **UserSerializer(instance=membership.user).data,
                    "membership_data": {
                        "added_by": str(membership.added_by.id)
                        if (membership.added_by)
                        else "",
                        "is_admin": membership.is_admin,
                        "datetime_created": membership.datetime_created.isoformat(),
                        "datetime_updated": membership.datetime_updated.isoformat(),
                    },
                }
                for membership in members
            ],
            "created_by": str(instance.created_by.id),
            "type": instance.type,
            "title": instance.title,
            "description": instance.description,
            "icon": instance.icon if (instance.icon) else None,
            "is_active": instance.is_active,
            "datetime_updated": instance.datetime_updated,
        }

        return data

    def to_representation(self, instance: Channel) -> dict[str, Any]:
        if instance.type == Channel.CHANNEL_TYPE_GROUP:
            return self.group_channel_representation(instance)
        else:
            return self.dm_channel_representation(instance)


class ChannelMemberSerializer(serializers.ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(
        many=True, allow_empty=False, queryset=User._default_manager
    )

    class Meta:
        model = Channel
        fields = ["users"]

    def update(self, instance: Channel, validated_data: dict[str, Any]) -> Channel:
        """Assign members to channel."""
        user = self.context["request"].user

        assign_members_to_channel(
            channel=instance, users=validated_data["users"], initiator=user
        )

        return self.instance


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = "__all__"
        read_only_fields = ["id", "created_by", "datetime_created", "datetime_updated"]

    def update(self, instance: File, validated_data: dict[str, Any]) -> None:
        """Overide this method."""


class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = "__all__"
        read_only_fields = [
            "datetime_created",
            "datetime_updated",
            "created_by",
        ]

    def update(self, instance: Reaction, validated_data: dict[str, Any]) -> Reaction:
        # important we dont want message field to be updated
        validated_data.pop("message", "")
        return super().update(instance, validated_data)

    def to_representation(self, instance: Reaction) -> dict[str, Any]:
        data = {
            "id": str(instance.id),
            "emoji": instance.emoji,
            "created_by": UserSerializer(instance=instance.created_by).data,
            "message": MessageSerializer(instance=instance.message).data,
            "datetime_created": instance.datetime_created.isoformat(),
            "datetime_updated": instance.datetime_created.isoformat(),
        }

        return data


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_by",
            "edited",
            "datetime_created",
            "datetime_updated",
            "channel",
        ]
        extra_kwargs = {
            "files": {"required": False, "allow_null": True, "allow_empty": True},
            "tagged_users": {
                "required": False,
                "allow_null": True,
                "allow_empty": True,
            },
        }

    def to_representation(self, instance: Message) -> dict[str, Any]:
        message_data = {
            "id": str(instance.id),
            "text": instance.text,
            "edited": instance.edited,
            "created_by": UserSerializer(instance=instance.created_by).data,
            "channel": str(instance.channel.id),
            "replying": str(instance.replying.id) if instance.replying else None,
            "files": FileSerializer(instance=instance.files, many=True).data,
            "tagged_users": UserSerializer(
                instance=instance.tagged_users, many=True
            ).data,
            "reactions": [
                {
                    "id": str(reaction.id),
                    "created_by": UserSerializer(instance=reaction.created_by).data,
                    "emoji": reaction.emoji,
                    "datetime_created": reaction.datetime_created.isoformat(),
                }
                for reaction in instance.reaction_set.all()
            ],
            "datetime_created": instance.datetime_created.isoformat(),
            "datetime_updated": instance.datetime_created.isoformat(),
        }

        return message_data

    def update(self, instance: Message, validated_data: dict[str, Any]) -> Message:
        # important we dont want replying to be updated
        validated_data.pop("replying", "")
        # important we dont want replying to be updated
        validated_data.pop("files", "")
        return super().update(instance, validated_data)

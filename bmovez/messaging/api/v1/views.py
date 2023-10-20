import uuid

from django.db.models import Count, F, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response

from bmovez.messaging.api.v1 import constants
from bmovez.messaging.api.v1.permissions import (
    IsChannelAdminOrReadOnly,
    IsChannelMember,
    IsObjectCreator,
)
from bmovez.messaging.api.v1.serializers import (
    ChannelMemberSerializer,
    ChannelSerializer,
    FileSerializer,
    MessageSerializer,
    ReactionSerializer,
)
from bmovez.messaging.api.v1.utils import CentWrapper
from bmovez.messaging.models import Channel, ChannelMembership, File, Message, Reaction
from bmovez.users.models import User


class ChannelAPIView(generics.ListCreateAPIView):
    serializer_class = ChannelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["datetime_updated", "datetime_created"]
    ordering = ["-datetime_updated"]
    search_fields = ["username", "name"]

    def get_queryset(self) -> QuerySet[Channel]:
        return self.request.user.channel_set.all().order_by("-datetime_updated")


class RetrieveUpdateChannelAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = ChannelSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsChannelMember,
        IsChannelAdminOrReadOnly,
    ]

    lookup_field = "id"

    def get_queryset(self) -> QuerySet[Channel]:
        return self.request.user.channel_set.all().order_by("-datetime_updated")


class AddChannelMemeberAPIView(generics.GenericAPIView):
    serializer_class = ChannelMemberSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsChannelAdminOrReadOnly,
    ]

    def get_object(self) -> Channel:
        channel = get_object_or_404(
            Channel, id=self.kwargs["channel_id"], type=Channel.CHANNEL_TYPE_GROUP
        )
        return channel

    def post(self, request: Request, channel_id: uuid.uuid4) -> Response:
        """Add members to a channel"""
        channel = get_object_or_404(
            Channel, id=channel_id, type=Channel.CHANNEL_TYPE_GROUP
        )
        serializer = self.get_serializer(data=request.data, instance=channel)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)


class RemoveChannelMemberAPIView(generics.GenericAPIView):
    serializer_class = ChannelMemberSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsChannelAdminOrReadOnly,
    ]

    def get_object(self) -> Channel:
        channel = get_object_or_404(
            Channel, id=self.kwargs["channel_id"], type=Channel.CHANNEL_TYPE_GROUP
        )
        return channel

    def post(self, request: Request, channel_id: uuid.uuid4) -> Response:
        """Remove members from a channel."""
        channel = get_object_or_404(
            Channel, id=channel_id, type=Channel.CHANNEL_TYPE_GROUP
        )
        serializer = self.get_serializer(data=request.data, instance=channel)
        serializer.is_valid(raise_exception=True)
        users = serializer.validated_data["users"]
        ChannelMembership.objects.filter(user__in=users, channel=channel).delete()
        return Response(data=serializer.data, status=status.HTTP_200_OK)


class FileUploadAPIView(generics.CreateAPIView):
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer) -> None:
        serializer.save(created_by=self.request.user)


class ListChannelFiles(generics.ListAPIView):
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticated, IsChannelMember]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["datetime_created"]
    ordering = ["-datetime_created"]

    def get_object(self) -> Channel:
        channel = get_object_or_404(Channel, id=self.kwargs["channel_id"])
        return channel

    def get_queryset(self) -> QuerySet[File]:
        channel = self.get_object()
        return File.objects.filter(message__channel=channel)


class ChannelMessagesAPIView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsChannelMember]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["datetime_created"]
    ordering = ["-datetime_created"]

    def get_object(self) -> Channel:
        channel = get_object_or_404(Channel, id=self.kwargs["channel_id"])
        self.channel = channel
        return channel

    def get_queryset(self) -> QuerySet[Message]:
        channel = self.get_object()
        return Message.objects.filter(channel=channel).order_by("-datetime_created")

    def perform_create(self, serializer) -> None:
        serializer.save(channel=self.channel, created_by=self.request.user)
        cent = CentWrapper()
        cent.publish(
            action=constants.CENTRIFUGO_ACTION_MESSAGE_CREATE,
            channel=self.channel,
            data=serializer.data,
            user=self.request.user,
        )


class ChannelMessageDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsObjectCreator]

    def get_object(self) -> Message:
        channel = get_object_or_404(Channel, id=self.kwargs["channel_id"])
        self.channel = channel
        return get_object_or_404(Message, id=self.kwargs["message_id"], channel=channel)

    def perform_update(self, serializer) -> None:
        serializer.save(edited=True)
        cent = CentWrapper()
        cent.publish(
            action=constants.CENTRIFUGO_ACTION_MESSAGE_EDIT,
            channel=self.channel,
            data=serializer.data,
            user=self.request.user,
        )

    def perform_destroy(self, instance) -> None:
        data = MessageSerializer(instance=instance).data
        super().perform_destroy(instance)
        cent = CentWrapper()
        cent.publish(
            action=constants.CENTRIFUGO_ACTION_MESSAGE_DELETE,
            channel=self.channel,
            data=data,
            user=self.request.user,
        )


class ReactionAPIView(generics.CreateAPIView):
    serializer_class = ReactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsChannelMember]

    def get_object(self) -> Channel:
        channel = get_object_or_404(Channel, id=self.kwargs["channel_id"])
        self.channel = channel
        return channel

    def perform_create(self, serializer) -> None:
        serializer.save(created_by=self.request.user)
        cent = CentWrapper()
        cent.publish(
            action=constants.CENTRIFUGO_ACTION_REACTION_CREATE,
            channel=self.channel,
            data=serializer.data,
            user=self.request.user,
        )


class ReactionDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsObjectCreator]

    def get_object(self) -> Message:
        channel = get_object_or_404(Channel, id=self.kwargs["channel_id"])
        self.channel = channel
        return get_object_or_404(
            Reaction, id=self.kwargs["reaction_id"], message__channel=channel
        )

    def perform_update(self, serializer) -> None:
        serializer.save()
        cent = CentWrapper()
        cent.publish(
            action=constants.CENTRIFUGO_ACTION_REACTION_EDIT,
            channel=self.channel,
            data=serializer.data,
            user=self.request.user,
        )

    def perform_destroy(self, instance) -> None:
        data = ReactionSerializer(instance=instance).data
        super().perform_destroy(instance)
        cent = CentWrapper()
        cent.publish(
            action=constants.CENTRIFUGO_ACTION_REACTION_DELETE,
            channel=self.channel,
            data=data,
            user=self.request.user,
        )


class DirectMessageAPIView(generics.CreateAPIView):
    """Send a direct message using the receivers id."""

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsChannelMember]
    filter_backends = [filters.OrderingFilter]

    def get_object(self) -> Channel:
        user = get_object_or_404(User, id=self.kwargs["user_id"])
        channel = (
            Channel.objects.annotate(usercount=Count(F("users__id")))
            .filter(
                users__in=[self.request.user], type=Channel.CHANNEL_TYPE_DM, usercount=2
            )
            .filter(users__in=[user])
            .first()
        )

        if not channel:
            channel = Channel.objects.create(
                created_by=self.request.user,
                type=Channel.CHANNEL_TYPE_DM,
                is_active=True,
            )

            ChannelMembership.objects.create(
                channel=channel,
                user=user,
                added_by=self.request.user,
                is_admin=True,
            )

            # incase this is a self DM we dont want to re-add the user
            if user != self.request.user:
                ChannelMembership.objects.create(
                    channel=channel,
                    user=self.request.user,
                    added_by=self.request.user,
                    is_admin=True,
                )

        self.channel = channel
        return channel

    def perform_create(self, serializer) -> None:
        serializer.save(channel=self.channel, created_by=self.request.user)
        cent = CentWrapper()
        cent.publish(
            action=constants.CENTRIFUGO_ACTION_MESSAGE_CREATE,
            channel=self.channel,
            data=serializer.data,
            user=self.request.user,
        )

from django.urls import path

from bmovez.messaging.api.v1.views import (
    AddChannelMemeberAPIView,
    ChannelAPIView,
    ChannelMessageDetailAPIView,
    ChannelMessagesAPIView,
    DirectMessageAPIView,
    FileUploadAPIView,
    ListChannelFiles,
    ReactionAPIView,
    ReactionDetailAPIView,
    RemoveChannelMemberAPIView,
    RetrieveUpdateChannelAPIView,
)

urlpatterns = [
    path("channels/", ChannelAPIView.as_view(), name="channel_list_create"),
    path(
        "channels/<uuid:id>/",
        RetrieveUpdateChannelAPIView.as_view(),
        name="channel_retrieve_update",
    ),
    path(
        "channels/<uuid:channel_id>/add-members/",
        AddChannelMemeberAPIView.as_view(),
        name="add_channel_member",
    ),
    path(
        "channels/<uuid:channel_id>/remove-members/",
        RemoveChannelMemberAPIView.as_view(),
        name="remove_channel_members",
    ),
    path(
        "messages/<uuid:channel_id>/",
        ChannelMessagesAPIView.as_view(),
        name="message_list_create",
    ),
    path(
        "messages/dm/<uuid:user_id>/",
        DirectMessageAPIView.as_view(),
        name="direct_message_creation",
    ),
    path(
        "messages/<uuid:channel_id>/<uuid:message_id>/",
        ChannelMessageDetailAPIView.as_view(),
        name="message_detail",
    ),
    path("files/", FileUploadAPIView.as_view(), name="file_create"),
    path(
        "files/<uuid:channel_id>/",
        ListChannelFiles.as_view(),
        name="channel_files_list",
    ),
    path(
        "reactions/<uuid:channel_id>/",
        ReactionAPIView.as_view(),
        name="create_reaction",
    ),
    path(
        "reactions/<uuid:channel_id>/<uuid:reaction_id>/",
        ReactionDetailAPIView.as_view(),
        name="reaction_details",
    ),
]

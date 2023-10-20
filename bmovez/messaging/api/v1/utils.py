import logging
from typing import Any

from cent import CentException, Client
from django.conf import settings

from bmovez.messaging.models import Channel, ChannelMembership
from bmovez.users.models import User

logger = logging.getLogger()


def assign_members_to_channel(
    channel: Channel, users: list[User], initiator: User | None
) -> list[ChannelMembership]:
    """Assign users to a channel."""

    memberships: list[ChannelMembership] = []
    channel_memberships = (
        ChannelMembership.objects.prefetch_related("user")
        .filter(channel=channel)
        .distinct()
    )

    for user in users:
        # if user not already a member then add user
        if not channel_memberships.filter(user=user).exists():
            membership = ChannelMembership(
                channel=channel,
                user=user,
                added_by=initiator,
            )
            memberships.append(membership)

    return ChannelMembership.objects.bulk_create(memberships, ignore_conflicts=False)


class CentWrapper:
    def __init__(self):
        self.client = Client(
            address=settings.CENTRIFUGO_API_ADDRESS,
            api_key=settings.CENTRIFUGO_API_KEY,
            timeout=0.5,
        )

    def publish(
        self,
        action: str,
        channel: Channel,
        data: dict[str, Any],
        user: User | None,
    ):
        """Publish a message to centrifugo."""

        centrifugo_data = {"action": action, "data": data, "sender": str(user.id)}

        try:
            self.client.publish(channel=str(channel.id), data=centrifugo_data)
        except (CentException, TypeError):
            logger.error(
                msg=(
                    "bmoves::messging::api::v1::utils::CentWrapper::publish::"
                    "Error occured while publishin data to centrifugo"
                ),
            )

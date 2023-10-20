from typing import Any

from rest_framework import serializers

from bmovez.team.models import Team, TeamInivitation, TeamMembership
from bmovez.users.api.v1.serializers import UserSerializer


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = "__all__"
        read_only_fields = [
            "id",
            "datetime_created",
            "datetime_updated",
            "users",
            "channels",
            "created_by",
        ]

    def create(self, validated_data: dict[str, Any]) -> Team:
        team = super().create(validated_data)
        TeamMembership.objects.create(
            team=team,
            user=self.context["request"].user,
            added_by=self.context["request"].user,
            is_admin=True,
            invitation=None,
        )
        return team

    def to_representation(self, instance: Team) -> dict[str, Any]:
        members = TeamMembership.objects.filter(team=instance)

        data = {
            "id": str(instance.id),
            "users": [
                {
                    **UserSerializer(instance=membership.user).data,
                    "membership_data": {
                        "added_by": str(membership.added_by.id),
                        "is_admin": membership.is_admin,
                        "datetime_created": membership.datetime_created.isoformat(),
                        "datetime_updated": membership.datetime_updated.isoformat(),
                    },
                }
                for membership in members
            ],
            "channels": [str(channel.id) for channel in instance.channels.all()],
            "title": instance.title,
            "description": instance.description,
            "icon": instance.icon.url if instance.icon else None,
            "datetime_created": instance.datetime_created.isoformat(),
            "datetime_updated": instance.datetime_updated.isoformat(),
        }

        return data


class TeamMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMembership
        fields = "__all__"
        read_only_fields = [
            "id",
            "team",
            "added_by",
            "datetime_created",
            "datetime_created",
        ]
        exclude = ["invitation"]

    def to_representation(self, instance: TeamMembership) -> dict[str, Any]:
        data = {
            "id": str(instance.id),
            "team": str(instance.team.id),
            "user": UserSerializer(instance=instance.user).data,
            "added_by": UserSerializer(instance=instance.added_by).data,
            "is_admin": instance.is_admin,
            "datetime_created": instance.datetime_created.isoformat(),
            "datetime_updated": instance.datetime_updated.isoformat(),
        }
        return data


class TeamInivitationSerializer(serializers.ModelSerializer):
    status = serializers.CharField(default=TeamInivitation.INVITATION_STATUS_PENDING)
    duration = serializers.IntegerField(min_value=1, max_value=10)

    class Meta:
        model = TeamInivitation
        fields = "__all__"
        read_only_fields = [
            "id",
            "team",
            "created_by",
            "datetime_created",
            "datetime_created",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate invitation data"""
        data = super().validate(attrs)

        # Esure that Invitation creator can only set invitation status to
        # cancled or pending
        if self.context["request"] == data["invitee"]:
            if data["status"] not in [
                TeamInivitation.INVITATION_STATUS_ACCEPTED,
                TeamInivitation.INVITATION_STATUS_REJECTED,
            ]:
                raise serializers.ValidationError({"status": "Status not allowed."})
        else:
            if data["status"] not in [
                TeamInivitation.INVITATION_STATUS_CANCLED,
                TeamInivitation.INVITATION_STATUS_PENDING,
            ]:
                raise serializers.ValidationError({"status": "Status not allowed."})

        return data

    def update(
        self, instance: TeamInivitation, validated_data: dict[str, Any]
    ) -> TeamInivitation:
        validated_data.pop("invitee", "")
        validated_data.pop("duration", "")
        invitation: TeamInivitation = super().update(instance, validated_data)

        if invitation.status == TeamInivitation.INVITATION_STATUS_ACCEPTED:
            # if the user has accepted the invitation then we create their membership data
            TeamMembership.objects.create(
                team=invitation.team,
                user=invitation.invitee,
                added_by=invitation.created_by,
                invitation=invitation,
            )

        return invitation

    def to_representation(self, instance: TeamInivitation) -> dict[str, Any]:
        data = {
            "id": str(instance.id),
            "created_by": UserSerializer(instance=instance.created_by).data,
            "invitee": UserSerializer(instance=instance.invitee).data,
            "team": {
                "id": str(instance.team.id),
                "title": instance.team.title,
                "description": instance.team.description,
            },
            "status": instance.status,
            "duration": instance.duration,
            "datetime_created": instance.datetime_created.isoformat(),
            "datetime_updated": instance.datetime_updated.isoformat(),
        }
        return data

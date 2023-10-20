import uuid

from django.db import models


class Team(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )
    users = models.ManyToManyField(
        "users.User", through="team.TeamMembership", through_fields=("team", "user")
    )
    channels = models.ManyToManyField("messaging.Channel")
    created_by = models.ForeignKey(
        "users.User", related_name="my_teams", on_delete=models.CASCADE
    )
    title = models.CharField(blank=True, null=True, max_length=100)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(
        upload_to="team/icons/", null=True, blank=True, max_length=300
    )
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)


class TeamMembership(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )

    team = models.ForeignKey("team.Team", on_delete=models.CASCADE)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    added_by = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="created_team_memberships"
    )
    is_admin = models.BooleanField(default=False)
    invitation = models.ForeignKey(
        "team.TeamInivitation", on_delete=models.CASCADE, null=True
    )
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.constraints.UniqueConstraint(
                fields=["team", "user"], name="unique team membership"
            )
        ]


class TeamInivitation(models.Model):
    INVITATION_STATUS_PENDING = "pending"
    INVITATION_STATUS_ACCEPTED = "accepted"
    INVITATION_STATUS_REJECTED = "rejected"
    INVITATION_STATUS_CANCLED = "cancled"
    INVITATION_STATUS_EXPIRED = "expired"

    INVITATION_STATUS_CHOICES = (
        (INVITATION_STATUS_PENDING, "Pending"),
        (INVITATION_STATUS_ACCEPTED, "Accepted"),
        (INVITATION_STATUS_REJECTED, "Rejected"),
        (INVITATION_STATUS_CANCLED, "Cancled"),
        (INVITATION_STATUS_EXPIRED, "Expired"),
    )

    id = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True, editable=False, primary_key=True
    )

    created_by = models.ForeignKey(
        "users.User", related_name="my_teams_invitation", on_delete=models.CASCADE
    )
    invitee = models.ForeignKey("users.User", on_delete=models.CASCADE)
    team = models.ForeignKey("team.Team", on_delete=models.CASCADE)
    status = models.CharField(max_length=100, choices=INVITATION_STATUS_CHOICES)
    duration = models.IntegerField(default=5, help_text="Duration in days")
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)

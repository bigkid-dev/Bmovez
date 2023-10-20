from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, permissions

from bmovez.team.api.v1.permissions import TeamPermission
from bmovez.team.api.v1.serializers import TeamInivitationSerializer, TeamSerializer
from bmovez.team.models import Team, TeamInivitation


class TeamAPIView(generics.ListCreateAPIView):
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["datetime_updated", "datetime_created"]
    ordering = ["-datetime_updated"]
    search_fields = ["username", "name"]

    def get_queryset(self) -> QuerySet[Team]:
        return self.request.user.team_set.all()

    def perform_create(self, serializer: TeamSerializer) -> None:
        serializer.save(created_by=self.request.user)


class RetrieveUpdateTeamAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated, TeamPermission]

    def get_object(self) -> Team:
        return get_object_or_404(Team, id=self.kwargs["team_id"])


class TeamInvitationAPIView(generics.ListCreateAPIView):
    serializer_class = TeamInivitationSerializer
    permission_classes = [permissions.IsAuthenticated, TeamPermission]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["datetime_updated", "datetime_created"]
    ordering = ["-datetime_updated"]

    def get_object(self) -> Team:
        self.team = get_object_or_404(Team, id=self.kwargs["team_id"])
        return self.team

    def get_queryset(self) -> QuerySet[TeamInivitation]:
        return TeamInivitation.objects.filter(team=self.team)

    def perform_create(self, serializer: TeamInivitationSerializer) -> None:
        serializer.save(team=self.team, created_by=self.request.user)


class RetrieveUpdateTeamInvitationAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = TeamInivitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self) -> Team:
        self.team = get_object_or_404(Team, id=self.kwargs["team_id"])
        invitation = get_object_or_404(
            TeamInivitation, id=self.kwargs["invitation_id"], team=self.team
        )
        return invitation


class UserInvitationAPIView(generics.ListAPIView):
    serializer_class = TeamInivitationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["datetime_updated", "datetime_created"]
    ordering = ["-datetime_updated"]

    def get_queryset(self) -> QuerySet[TeamInivitation]:
        return TeamInivitation.objects.filter(invitee=self.request.user)

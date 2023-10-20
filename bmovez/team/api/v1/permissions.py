from rest_framework.generics import GenericAPIView
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from bmovez.team.models import Team, TeamInivitation, TeamMembership


class TeamPermission(BasePermission):
    def has_permission(self, request: Request, view: GenericAPIView) -> bool:
        team = view.get_object()

        team_membership = TeamMembership.objects.filter(
            user=request.user, team=team
        ).first()

        if not team_membership:
            return False

        if request.method in SAFE_METHODS and team_membership:
            return True

        return team_membership.is_admin

    def has_object_permission(
        self, request: Request, view: GenericAPIView, obj: Team
    ) -> bool:
        team_membership = TeamMembership.objects.filter(
            user=request.user, team=obj
        ).first()

        if not team_membership:
            return False

        return team_membership.is_admin


class TeamInvitationPermission(BasePermission):
    def has_permission(self, request: Request, view: GenericAPIView) -> bool:
        invitation = view.get_object()
        return self.has_object_permission(request, view, obj=invitation)

    def has_object_permission(
        self, request: Request, view: GenericAPIView, obj: TeamInivitation
    ) -> bool:
        if obj.invitee == request.user:
            return True

        membership = TeamMembership.objects.filter(
            user=request.user, team=obj.team, is_admin=True
        ).first()

        return bool(membership)

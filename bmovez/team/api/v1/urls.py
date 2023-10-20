from django.urls import path

from bmovez.team.api.v1.views import (
    RetrieveUpdateTeamAPIView,
    RetrieveUpdateTeamInvitationAPIView,
    TeamAPIView,
    TeamInvitationAPIView,
    UserInvitationAPIView,
)

urlpatterns = [
    path("teams/", TeamAPIView.as_view(), name="team_list_create"),
    path(
        "teams/<uuid:team_id>/",
        RetrieveUpdateTeamAPIView.as_view(),
        name="team_details",
    ),
    path(
        "invitations/<uuid:team_id>/",
        TeamInvitationAPIView.as_view(),
        name="team_invitation_list_create",
    ),
    path(
        "invitations/<uuid:team_id>/<uuid:invitation_id>/",
        RetrieveUpdateTeamInvitationAPIView.as_view(),
        name="team_invitation_details",
    ),
    path(
        "invitations/me/", UserInvitationAPIView.as_view(), name="user_initation_list"
    ),
]

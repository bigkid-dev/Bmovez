from typing import Any

from rest_framework import permissions
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request

from bmovez.messaging.models import Channel, ChannelMembership


class IsUserOrReadOnly(permissions.BasePermission):
    def has_permission(self, request: Request, view: GenericAPIView) -> bool:
        return bool(request.method in permissions.SAFE_METHODS) or bool(
            request.user == view.get_object()
        )


class IsChannelMember(permissions.BasePermission):
    def has_permission(self, request: Request, view: GenericAPIView) -> bool:
        channel = view.get_object()
        return bool(
            ChannelMembership.objects.filter(user=request.user, channel=channel).first()
        )


class IsObjectCreator(permissions.BasePermission):
    def has_permission(self, request: Request, view: GenericAPIView) -> bool:
        obj = view.get_object()
        return bool(obj.created_by == request.user)

    def has_object_permission(
        self, request: Request, view: GenericAPIView, obj: Any
    ) -> bool:
        return bool(obj.created_by == request.user)


class IsChannelAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request: Request, view: GenericAPIView) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        membership_data = ChannelMembership.objects.filter(
            user=request.user, channel=view.get_object()
        ).first()

        if not membership_data:
            return False

        return membership_data.is_admin

    def has_object_permission(
        self, request: Request, view: GenericAPIView, obj: Channel
    ) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        membership_data = ChannelMembership.objects.filter(
            user=request.user, channel=obj
        ).first()

        if not membership_data:
            return False

        return membership_data.is_admin


class IsAllowedToEditMembershipOrReadOnly(permissions.BasePermission):
    def has_object_permission(
        self, request: Request, view: GenericAPIView, obj: ChannelMembership
    ) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        requester_membership = ChannelMembership.objects.filter(
            user=request.user, channel=obj.channel
        ).first()

        if not requester_membership:
            return False

        return obj.user == request.user or requester_membership.is_admin

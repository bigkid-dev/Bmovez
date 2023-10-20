import logging
from typing import Any

import jwt
from django.conf import settings
from django.core import signing
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework_simplejwt.tokens import RefreshToken

from bmovez.users.api.v1.uitls import (
    create_pbx_profile,
    generate_email_verification_link,
    generate_password_reset_key,
    validate_email_verification_signature,
    validate_otp_pin,
)
from bmovez.users.models import FreepbxExtentionProfile, User
from bmovez.utils.managers import FreePbxConnector
from bmovez.utils.tasks import send_mail_task

logger = logging.getLogger()


class FreepbxExtentionProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreepbxExtentionProfile
        fields = ["extention_id", "caller_id"]
        read_only_fields = ["extention_id"]

    def create(self, validated_data: Any) -> Any:
        """Overiden Method."""

    def update(
        self, instance: FreepbxExtentionProfile, validated_data: dict[str, Any]
    ) -> FreepbxExtentionProfile:
        """Update caller id."""
        instance = super().update(instance, validated_data)
        # update caller id in freepbx
        query = """
            mutation($extention_id: ID!, $name: String, $caller_id: String) {
                updateExtension(
                    input: {
                        extensionId: $extention_id
                        name: $name
                        outboundCid: $caller_id
                    }
                )
                {
                        status
                        message
                }
            }
        """
        params = {
            "name": f"{instance.user.username}",
            "extention_id": instance.extention_id,
            "caller_id": instance.caller_id,
        }

        connector = FreePbxConnector()
        connector.request(query_string=query, query_params=params)
        return instance


class UserSerializer(serializers.ModelSerializer):
    token = None
    pbx_profile = FreepbxExtentionProfileSerializer(
        source="freepbxextentionprofile",
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "date_joined",
            "last_login",
            "username",
            "name",
            "email",
            "password",
            "profile_picture",
            "phone_number",
            "pbx_profile",
        ]

        read_only_fields = [
            "id",
            "date_joined",
            "last_login",
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def generate_auth_token(self, user: User) -> None:
        """Generate authentication token."""
        refresh_token = RefreshToken.for_user(user)
        claims = {"sub": str(user.id), "info": {"email": user.email}}

        pbx_profile = getattr(user, "freepbxextentionprofile", None)
        self.token = {
            "pbx_password": pbx_profile.extention_password if pbx_profile else None,
            "backend": str(refresh_token.access_token),
            "centrifugo": jwt.encode(claims, settings.CENTRIFUGO_TOKEN_HMAC_SECRET_KEY),
        }

    def create(self, validated_data: dict[str, Any]) -> User:
        """create user."""
        user = super().create(validated_data)
        user.set_password(validated_data["password"])
        # NOTE (change to back to False when a working ESP is procured )
        user.is_active = True
        user.save()
        create_pbx_profile(user=user)  # NOTE (Move this to a celery task)
        self.generate_auth_token(user)

        request: Request = self.context["request"]

        email_verification_link = request.build_absolute_uri(
            generate_email_verification_link(user)
        )

        send_mail_task(
            ses_template_id=settings.EMAIL_TEMPLATES_IDS["EMAIL_VERIFICATION"],
            recipients=[user.email],
            merge_data={
                user.email: {"name": user.name, "link": email_verification_link}
            },
            defualt_template_data="{'name': user.name, 'link': email_verification_link}",
        )

        return user

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        """Update user."""
        user = super().update(instance, validated_data)

        if "password" in validated_data.keys():
            user.set_password(validated_data["password"])
            user.save(update_fields=["password"])
            self.generate_auth_token(user)
        return user

    def to_representation(self, instance: User) -> dict[str, Any]:
        """return proper structure for user"""
       
        data = {**super().to_representation(instance)}
        if self.token:
            data.update({"auth_token": self.token})
        return data

    def validate_username(self, value: str) -> str:
        """check that username is unique"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exits")
        return value

    def validate_phone_number(self, value: str) -> str:
        """Check that phone number is unique"""
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "A user with this phone number already exits"
            )
        return value

    def validate_email(self, value: str) -> str:
        """Check that email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email address already exits"
            )
        return value


class SignInSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict[str, Any]) -> User:
        super().validate(attrs)
        user = User.objects.filter(username=attrs["username"], is_active=True).first()

        if user and user.check_password(attrs["password"]):
            return user

        raise serializers.ValidationError(
            "No active account found with the given credentials"
        )

    def to_representation(self, instance: User) -> dict[str, Any]:
        user_serializer = UserSerializer(instance=instance)
        user_serializer.generate_auth_token(instance)
        return user_serializer.to_representation(instance)


class OTPCreationSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)


class OTPValidationSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    pin = serializers.CharField(max_length=6, min_length=6, write_only=True)
    password_reset_key = serializers.CharField(read_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        super().validate(attrs)
        user = User.objects.filter(email=attrs["email"]).first()

        if user:
            is_valid = validate_otp_pin(pin=attrs["pin"], user=user)
            if is_valid:
                key, signed_key = generate_password_reset_key(user)
                user.password_reset_key = key
                user.save(update_fields=["password_reset_key"])
                return {"password_reset_key": signed_key}
        raise serializers.ValidationError("This otp is either invalid or has expired.")


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    password_reset_key = serializers.CharField(write_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        super().validate(attrs)

        # unsign password_reset_key
        try:
            signer = signing.TimestampSigner()
            data = signer.unsign_object(attrs["password_reset_key"])
            user = User.objects.filter(
                email=attrs["email"], password_reset_key=data["key"]
            ).first()
        except KeyError as error:
            logger.error(
                "bmoves::users::api::v1::serializers::ResetPasswordSerializer:: Keyerror occured.",
                extra={"details": str(error)},
            )
        else:
            if user:
                user.password_reset_key = None
                user.set_password(attrs["new_password"])
                user.save(update_fields=["password", "password_reset_key"])
                return {}
        raise serializers.ValidationError(
            "An error occured in the process please retry."
        )


class EmailVerificationSerializer(serializers.Serializer):
    signature = serializers.CharField()

    def validate(self, attrs: dict[str, Any]) -> dict[str, User]:
        super().validate(attrs)
        user = validate_email_verification_signature(signature=attrs["signature"])

        if not user:
            raise serializers.ValidationError("This link is invalid or has expired.")

        return {"user": user}


class ThrirdPartyConnectionSerializer(serializers.Serializer):
    freepbx_ip = serializers.IPAddressField(read_only=True)
    freepbx_port = serializers.IntegerField(read_only=True)

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpResponse
from rest_framework import filters as rest_filters
from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from .uitls import generate_token04
from config.settings.local import  ZEGO_APP_ID, ZEGO_SECRET




from bmovez.users.api.v1.serializers import (
    EmailVerificationSerializer,
    FreepbxExtentionProfileSerializer,
    OTPCreationSerializer,
    OTPValidationSerializer,
    ResetPasswordSerializer,
    SignInSerializer,
    ThrirdPartyConnectionSerializer,
    UserSerializer,
)
from bmovez.users.api.v1.uitls import (
    create_pbx_profile,
    generate_email_verification_link,
    generate_otp_pin,
)
from bmovez.users.models import FreepbxExtentionProfile, ResetPasswordOTP, User
from bmovez.utils.tasks import send_mail_task


class UserSignUpAPIView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class UserDetailsAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self) -> User:
        return self.request.user


class UserSignInAPIView(generics.GenericAPIView):
    serializer_class = SignInSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.data)


class GetResetPasswordOTPAPIView(generics.GenericAPIView):
    serializer_class = OTPCreationSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        """Generate otp for password reset and send to users email."""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"]).first()

        if user:
            otp, signed_pin = generate_otp_pin(user)

            # delete all active otp pins
            old_pins = ResetPasswordOTP.objects.filter(user=user, is_active=True)

            for pin in old_pins:
                pin.is_active = False
                pin.is_expired = True

            ResetPasswordOTP.objects.bulk_update(
                old_pins, fields=["is_active", "is_expired"]
            )

            # create new otp pin entry
            ResetPasswordOTP.objects.create(user=user, signed_pin=signed_pin)

            # send otp to user's email
            send_mail_task.delay(
                ses_template_id=settings.EMAIL_TEMPLATES_IDS["RESET_PASSWORD_OTP"],
                recipients=[user.email],
                merge_data={user.email: {"name": user.name, "code": otp}},
                defualt_template_data="{'name': user.name, 'code': otp}",
            )

        return Response(status=status.HTTP_200_OK)


class VerifyResetPasswordOTPAPIView(generics.GenericAPIView):
    serializer_class = OTPValidationSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        """Verify otp."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.data)


class ResetPasswordAPIView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        """Reset a users password."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_200_OK)


class GenerateEmailVerificationView(generics.GenericAPIView):
    serializer_class = (
        OTPCreationSerializer  # using otp serializer class since it only email field
    )
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request) -> Response:
        """Resend email verification."""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"]).first()

        if user:
            email_verification_link = request.build_absolute_uri(
                generate_email_verification_link(user)
            )
            send_mail_task.delay(
                ses_template_id=settings.EMAIL_TEMPLATES_IDS["EMAIL_VERIFICATION"],
                recipients=[user.email],
                merge_data={
                    user.email: {"name": user.name, "link": email_verification_link}
                },
                defualt_template_data="{'name': user.name, 'link': email_verification_link}",
            )

        return Response(status=status.HTTP_200_OK)


class VerifyEmailView(generics.GenericAPIView):
    serializer_class = EmailVerificationSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request: Request, signature: str) -> HttpResponse:
        serializer = self.get_serializer(data={"signature": signature})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        # we activate the user
        user.is_active = True
        user.save(update_fields=["is_active"])
        # create users voip data
        create_pbx_profile(user=user)
        return HttpResponse(
            "<H1>Your account has been verified you may return to the app.</H1>"
        )


class UserListAPIView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = (rest_filters.OrderingFilter, rest_filters.SearchFilter)
    ordering = ["name"]
    search_fields = ["username", "name"]

    def get_queryset(self) -> QuerySet[User]:
        return User.objects.filter(is_active=True)


class UserPBXSetting(generics.UpdateAPIView):
    serializer_class = FreepbxExtentionProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self) -> FreepbxExtentionProfile:
        return self.request.user.freepbxextentionprofile


class ThirdParyConnectionAPIView(generics.GenericAPIView):
    serializer_class = ThrirdPartyConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        data = {
            "freepbx_ip": settings.FREEPBX_IP,
            "freepbx_port": settings.FREEPBX_UDP_PORT,
        }
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.initial_data, status=status.HTTP_200_OK)
    

class CreateTokenAPI(APIView):
    permission_classes = []

    def get(self, request, format=None):
        app_id = int(ZEGO_APP_ID)
        secret = str(ZEGO_SECRET)
        token = generate_token04(app_id=app_id, user_id="demo", secret=secret , effective_time_in_seconds=151200, payload='')
        print(token)
        return Response({'token': token.token}, status=200)


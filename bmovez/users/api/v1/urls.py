from django.urls import path

from bmovez.users.api.v1.views import (
    GenerateEmailVerificationView,
    GetResetPasswordOTPAPIView,
    ResetPasswordAPIView,
    UserDetailsAPIView,
    UserListAPIView,
    UserPBXSetting,
    UserSignInAPIView,
    UserSignUpAPIView,
    VerifyEmailView,
    VerifyResetPasswordOTPAPIView,
    CreateTokenAPI,
)

urlpatterns = [
    path("signup/", UserSignUpAPIView.as_view(), name="signup"),
    path("signin/", UserSignInAPIView.as_view(), name="signin"),
    path("me/", UserDetailsAPIView.as_view(), name="user_details"),
    path("me/pbx-settings/", UserPBXSetting.as_view(), name="user_pbx_profile"),
    path("reset-password/", ResetPasswordAPIView.as_view(), name="reset_password"),
    path(
        "reset-password/get-otp/", GetResetPasswordOTPAPIView.as_view(), name="get_otp"
    ),
    path(
        "reset-password/verify-otp/",
        VerifyResetPasswordOTPAPIView.as_view(),
        name="verify_otp",
    ),
    path(
        "email-verification/request/",
        GenerateEmailVerificationView.as_view(),
        name="request_email_verification",
    ),
    path(
        "email-verification/<str:signature>/",
        VerifyEmailView.as_view(),
        name="email_verification",
    ),
    path("users/", UserListAPIView.as_view(), name="user_list"),
    path("create-token/",  CreateTokenAPI.as_view()),
]

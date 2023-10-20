import logging
import random
import string
from datetime import timedelta
from string import ascii_letters


from django.conf import settings
from django.core import signing
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from bmovez.users.models import FreepbxExtentionProfile, ResetPasswordOTP, User
from bmovez.utils.managers import AuthenticationFailed, BadGQLRequest, FreePbxConnector

import json
import random
import time
import struct
import binascii
from Crypto.Cipher import AES

logger = logging.getLogger()


def generate_authtoken(user: User) -> dict[str, str]:
    """Generate jwt token."""
    refresh_token = RefreshToken.for_user(user)
    return {
        "access": str(refresh_token.access_token),
        "refresh": str(refresh_token.refresh),
    }


def generate_otp_pin(user: User) -> tuple[int, str]:
    """Generate new otp pin."""
    unsigned_pin = random.randint(100000, 999999)
    signer = signing.TimestampSigner()
    signed_pin = signer.sign_object({"token": unsigned_pin})
    return unsigned_pin, signed_pin


def generate_pbx_password(user: User) -> str:
    """"""
    s1 = list(string.ascii_lowercase)
    s2 = list(string.ascii_uppercase)
    s3 = list(string.digits)
    s4 = list(string.punctuation)

    # shuffle all lists
    random.shuffle(s1)
    random.shuffle(s2)
    random.shuffle(s3)
    random.shuffle(s4)

    password_lenght = settings.FREEPBX_EXTENTION_PASSWORD_LENGTH
    # calculate 30% & 20% of number of characters
    part1 = round(password_lenght * (30 / 100))
    part2 = round(password_lenght * (20 / 100))

    # generation of the password (60% letters and 40% digits & punctuations)
    result = []

    for x in range(part1):
        result.append(s1[x])
        result.append(s2[x])

    for x in range(part2):
        result.append(s3[x])
        result.append(s4[x])

    # shuffle result
    random.shuffle(result)
    return "".join(result)


def validate_otp_pin(pin: str, user: User) -> bool:
    """Validate otp pin"""

    otp = (
        ResetPasswordOTP.objects.filter(user=user, is_active=True)
        .order_by("datetime_created")
        .first()
    )

    if not otp:
        return False

    try:
        max_age = timedelta(minutes=otp.duration_in_minutes)

        signer = signing.TimestampSigner()
        data = signer.unsign_object(otp.signed_pin, max_age=max_age)

        if str(data["token"]) == str(pin):
            otp.is_active = False
            otp.save(update_fields=["is_active"])
            return True

    except signing.SignatureExpired:
        pass
    except KeyError as error:
        logger.exception(
            "bmoves::users::api::v1::utils::validate_otp_pin:: keyerror occured",
            stack_info=True,
            extra={"details": str(error.with_traceback())},
        )

    return False


def generate_password_reset_key(user: User) -> tuple[str, str]:
    key = "".join(random.sample(ascii_letters, k=10))
    signer = signing.TimestampSigner()
    signed_key = signer.sign_object({"key": key, "email": user.email})
    return key, signed_key


def generate_email_verification_link(user: User) -> str:
    """Generate email verification link."""
    signer = signing.TimestampSigner()
    signature = signer.sign_object({"email": user.email})
    url = reverse("users_api_v1:email_verification", args=[signature])
    return url


def validate_email_verification_signature(signature: str) -> User | None:
    """Verifies email verification signature."""

    try:
        max_age = timedelta(hours=settings.EMAIL_VERIFCATION_MAX_AGE)
        signer = signing.TimestampSigner()
        data = signer.unsign_object(signature, max_age=max_age)

        email = data["email"]
        return User.objects.filter(email=email).first()
    except (signing.SignatureExpired, signing.BadSignature):
        pass
    except KeyError as error:
        logger.exception(
            "bmoves::users::api::v1::utils::validate_email_verification_signature:: keyerror occured",
            stack_info=True,
            extra={"details": str(error.with_traceback())},
        )


def create_pbx_profile(user: User) -> None:
    if getattr(user, "freepbxextentionprofile", None):
        return

    top_extention = FreepbxExtentionProfile.objects.order_by("-extention_id").first()

    if top_extention:
        next_extention = (
            top_extention.extention_id + settings.FREEPBX_EXTENTION_DIFFERENCE
        )
    else:
        next_extention = settings.FREEPBX_STARTING_EXTENTION

    create_query = """
        mutation($extention_id: ID!, $name: String!, $caller_id: String, $email: String!) {
            addExtension(
                input: {
                    extensionId: $extention_id
                    name: $name
                    tech: "pjsip"
                    channelName: "Movez Backend API"
                    outboundCid: $caller_id
                    email: $email
                    umEnable: false
                    vmEnable: false
                    maxContacts: "3"
                }
            ) {
                status
                message
            }
        }
    """
    update_query = """
        mutation($extention_id: ID!, $name: String, $password: String, $caller_id: String) {
            updateExtension(
                input: {
                    extensionId: $extention_id
                    name: $name
                    extPassword: $password
                    outboundCid: $caller_id
                }
            )
            {
                    status
                    message
            }
        }
    """
    extension_password = generate_pbx_password(user=user)
    params = {
        "name": f"{user.username}",
        "extention_id": next_extention,
        "caller_id": user.name,
        "email": user.email,
        "password": extension_password,
    }

    try:
        connector = FreePbxConnector()
        # create extention
        connector.request(query_string=create_query, query_params=params)

        # set extention password and caller id
        connector.request(query_string=update_query, query_params=params)

        FreepbxExtentionProfile.objects.create(
            user=user,
            extention_id=next_extention,
            caller_id=user.name,
            extention_password=extension_password,
        )
    except (BadGQLRequest, AuthenticationFailed):
        logger.exception(
            "bmoves::users::api::v1::utils::create_pbx_profile:: Error occured while creating freepbx profile.",
            stack_info=True,
        )


#!/usr/bin/env python -u
# coding:utf-8


ERROR_CODE_SUCCESS = 0                              # 获取鉴权 token 成功
ERROR_CODE_APP_ID_INVALID = 1                       # 调用方法时传入 appID 参数错误
ERROR_CODE_USER_ID_INVALID = 3                      # 调用方法时传入 userID 参数错误
ERROR_CODE_SECRET_INVALID = 5                       # 调用方法时传入 secret 参数错误
ERROR_CODE_EFFECTIVE_TIME_IN_SECONDS_INVALID = 6    # 调用方法时传入 effective_time_in_seconds 参数错误


class TokenInfo:
    def __init__(self, token, error_code, error_message):
        self.token = token
        self.error_code = error_code
        self.error_message = error_message


def __make_nonce():
    return random.getrandbits(31)


def __make_random_iv():
    str = '0123456789abcdefghijklmnopqrstuvwxyz'
    iv = ""
    for i in range(16):
        index = int(random.random() * 16)
        iv += str[index]
    return iv


def __aes_pkcs5_padding(cipher_text, block_size):
    padding_size = len(cipher_text) if (len(cipher_text) == len(
        cipher_text.encode('utf-8'))) else len(cipher_text.encode('utf-8'))
    padding = block_size - padding_size % block_size
    if padding < 0:
        return None
    padding_text = chr(padding) * padding
    return cipher_text + padding_text


def __aes_encrypy(plain_text, key, iv):
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    content_padding = __aes_pkcs5_padding(plain_text, 16)
    encrypt_bytes = cipher.encrypt(content_padding.encode('utf-8'))
    return encrypt_bytes


def generate_token04(app_id, user_id, secret, effective_time_in_seconds, payload):
    '''基本描述
        获取 token 的方法
    详细描述

    Args:
        app_id: Zego派发的数字ID, 各个开发者的唯一标识
        user_id: 用户ID
        secret: 在鉴权 token 计算过程中 AES 加密需要的密钥,32字节的字符串
        effective_time_in_seconds token: 的有效时长，单位：秒
        payload:有效载荷

    Returns:
        TokenInfo: 包含三个对象，token, error_code, error_message
    '''

    if type(app_id) != int or app_id == 0:
        return TokenInfo("", ERROR_CODE_APP_ID_INVALID, "appID invalid")
    if type(user_id) != str or user_id == "":
        return TokenInfo("", ERROR_CODE_USER_ID_INVALID, "userID invalid")
    if type(secret) != str or len(secret) != 32:
        return TokenInfo("", ERROR_CODE_SECRET_INVALID, "secret must be a 32 byte string")
    if type(effective_time_in_seconds) != int or effective_time_in_seconds <= 0:
        return TokenInfo("", ERROR_CODE_EFFECTIVE_TIME_IN_SECONDS_INVALID, "effective_time_in_seconds invalid")
    create_time = int(time.time())
    expire_time = create_time + effective_time_in_seconds
    nonce = __make_nonce()

    _token = {"app_id": app_id, "user_id": user_id, "nonce": nonce,
              "ctime": create_time, "expire": expire_time, "payload": payload}
    plain_text = json.dumps(_token, separators=(',', ':'), ensure_ascii=False)

    iv = __make_random_iv()

    encrypt_buf = __aes_encrypy(plain_text, secret, iv)

    result_size = len(encrypt_buf) + 28
    result = bytearray(result_size)

    big_endian_expire_time = struct.pack("!q", expire_time)
    result[0: 0 + len(big_endian_expire_time)] = big_endian_expire_time[:]

    big_endian_iv_size = struct.pack("!h", len(iv))
    result[8: 8 + len(big_endian_iv_size)] = big_endian_iv_size[:]

    buffer = bytearray(iv.encode('utf-8'))
    result[10: 10 + len(buffer)] = buffer[:]

    big_endian_buf_size = struct.pack("!h", len(encrypt_buf))
    result[26: 26 + len(big_endian_buf_size)] = big_endian_buf_size[:]

    result[28: len(result)] = encrypt_buf[:]

    token = "04" + binascii.b2a_base64(result, newline=False).decode()

    return TokenInfo(token, ERROR_CODE_SUCCESS, "success")



#708125776

#501c83b46ab814cfe1d3e837487948d5


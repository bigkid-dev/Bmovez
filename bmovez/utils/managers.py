import logging
from datetime import timedelta
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone
from gql import Client, gql
from gql.transport.exceptions import TransportQueryError, TransportServerError
from gql.transport.requests import RequestsHTTPTransport

from bmovez.users.models import FreePBXOauth2Access

logger = logging.getLogger()


class BadGQLRequest(Exception):
    """Bad graph QL request."""


class AuthenticationFailed(Exception):
    """Authentication failed after 3 retries."""


class FreePbxConnector:
    def __init__(self) -> None:
        self.headers = {"Content-Type": "application/json"}
        self.__authenticate()

    def __authenticate(self, auth_failed: bool = False):
        """Authenticate session."""

        # retrieve latest pbx access record
        access_records = (
            FreePBXOauth2Access.objects.filter(
                expired=False, expires_in__gt=timezone.now()
            )
            .select_for_update()
            .order_by("-expires_in")
        )

        latest_record = access_records.first()

        if (latest_record is None) or auth_failed:
            token_data = self.__retrieve_auth_token()
            latest_record = FreePBXOauth2Access.objects.create(
                token_type=token_data["token_type"],
                expires_in=timezone.now() + timedelta(seconds=token_data["expires_in"]),
                expired=False,
                signed_access_token=FreePBXOauth2Access.sign_access_token(
                    token_data["access_token"]
                ),
            )

        self.headers[
            "Authorization"
        ] = f"{latest_record.token_type} {latest_record.get_unsigned_access_token()}"
        access_records.exclude(id=latest_record.id).update(expired=True)
        transport = RequestsHTTPTransport(
            url=settings.FREEPBX_GQL_URL, verify=True, retries=3, headers=self.headers
        )
        self.graphQlClient = Client(
            transport=transport, fetch_schema_from_transport=True
        )

    def __retrieve_auth_token(self, retries: int = 0) -> dict[str, Any]:
        """Retrieve authtoken from freepbx."""
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": settings.FREEPBX_CLIENT_ID,
            "client_secret": settings.FREEPBX_CLIENT_SECRETE,
        }

        try:
            response = requests.post(
                url=settings.FREEPBX_ACCESS_TOKEN_URL,
                data=auth_data,
            )
        except requests.HTTPError as error:
            logger.error(
                msg=(
                    "bmoves::utils::managers::FreePbxConnector::__retrieve_auth_token::"
                    "HTTPError occured while retriving auth token from freepbx"
                ),
                extra={"message": str(error)},
            )

            if retries <= 3:
                return self.__retrieve_auth_token(retries=retries + 1)
            else:
                raise AuthenticationFailed()

        if response.status_code != 200 and retries <= 3:
            logger.error(
                msg=(
                    "bmoves::utils::managers::FreePbxConnector::__retrieve_auth_token::"
                    "Bad status code while retriving auth token from freepbx."
                ),
                extra={
                    "status_code": response.status_code,
                    "retries": retries,
                    "response_data": response.text,
                },
            )
            return self.__retrieve_auth_token(retries=retries + 1)
        elif response.status_code != 200:
            raise AuthenticationFailed()

        return response.json()

    def request(
        self, query_string: str, query_params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make graphQl request."""

        try:
            query = gql(query_string)
            response_data = self.graphQlClient.execute(
                document=query, variable_values=query_params
            )
        except TransportServerError as error:
            if error.code == 401:
                # try re-authenticating
                self.__authenticate(auth_failed=True)
                return self.request(
                    query_string=query_string, query_params=query_params
                )
            else:
                logger.error(
                    msg=(
                        "bmoves::utils::managers::FreePbxConnector::request::"
                        "Error occured while requesting data from freepbx graphql endpoint."
                    ),
                    extra={
                        "status_code": error.code,
                        "query": query_string,
                        "query_params": query_params,
                    },
                )
        except TransportQueryError as error:
            raise BadGQLRequest() from error

        return response_data

import logging
from typing import Any

from django.core.mail import EmailMessage

from config.celery_app import app as CELERY_APP

Logger = logging.getLogger()


@CELERY_APP.task(name="send_mail_task")
def send_mail_task(
    ses_template_id: str,
    recipients: list[str],
    merge_data: dict[str, Any],
    defualt_template_data: str,
    merge_global_data: dict[str, Any] | None = None,
) -> None:
    """Send emails asynchronously."""

    try:
        print(merge_data)
        message = EmailMessage(to=recipients)
        message.template_id = ses_template_id
        message.merge_data = merge_data
        if merge_global_data:
            message.global_data = merge_global_data

        message.send()
    except Exception as error:
        Logger.log(msg=error, level=logging.ERROR)

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TeamConfig(AppConfig):
    name = "bmovez.team"
    verbose_name = _("Team")

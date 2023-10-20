from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from bmovez.users.api.v1.views import ThirdParyConnectionAPIView

urlpatterns = [
    # V1 API Endpoints
    path(
        "api/v1/accounts/",
        include(("bmovez.users.api.v1.urls", "users_api_v1"), namespace="users_api_v1"),
    ),
    path(
        "api/v1/messaging/",
        include(
            ("bmovez.messaging.api.v1.urls", "messagings_api_v1"),
            namespace="messagings_api_v1",
        ),
    ),
    path("3rd-parties/", ThirdParyConnectionAPIView.as_view()),
    path(
        "api/v1/team/",
        include(
            ("bmovez.team.api.v1.urls", "teams_api_v1"),
            namespace="teams_api_v1",
        ),
    ),
    # API DOCS
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

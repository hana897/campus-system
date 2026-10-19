from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, JsonResponse
import mimetypes


def backend_status(request):
    return JsonResponse({"service": "Campus Security System API", "status": "ok"})


def serve_media(request, name):
    """Serve uploaded media from the configured storage, in development and production."""
    try:
        file = default_storage.open(name)
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("File not found")
    content_type = getattr(default_storage, "mime_type", lambda _: None)(name) or mimetypes.guess_type(name)[0]
    return FileResponse(file, content_type=content_type or "application/octet-stream")

urlpatterns = [

    path("", backend_status, name="backend_status"),

    path(
        "admin/",
        admin.site.urls
    ),

    path(
        "",
        include("accounts.urls")
    ),

    path(
        "dashboard/",
        include("dashboard.urls")
    ),

    path(
        "verification/",
        include("verification.urls")
    ),
    path(
        "reports/",
        include("reports.urls")
    ),
    path(
        "assets/",
        include("assets.urls")
    ),
    path(
        "owners/",
        include("owners.urls")
    ),
    path(
        "api/",
        include("api.urls")
    ),

]

urlpatterns += [
    path(
        settings.MEDIA_URL.lstrip("/") + "<path:name>",
        serve_media,
        name="serve_media"
    ),
]
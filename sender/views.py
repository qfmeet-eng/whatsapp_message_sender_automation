from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from automation_core import (
    DEFAULT_MAX_MESSAGES,
    DEFAULT_TICK_WAIT_TIMEOUT_SECONDS,
    RunSettings,
)

from .job_state import job_manager


EXCEL_EXTENSIONS = {".xlsx", ".xls"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


@require_GET
def index(request):
    return render(
        request,
        "sender/index.html",
        {
            "default_max_messages": DEFAULT_MAX_MESSAGES,
            "default_tick_timeout": DEFAULT_TICK_WAIT_TIMEOUT_SECONDS,
        },
    )


@require_POST
def start(request):
    if job_manager.snapshot()["running"]:
        return JsonResponse({"ok": False, "error": "Process is already running."}, status=409)

    message = request.POST.get("message", "").strip()
    max_messages = request.POST.get("max_messages", "").strip()
    tick_timeout = request.POST.get("tick_timeout", "").strip()
    excel_file = request.FILES.get("excel_file")
    image_file = request.FILES.get("image_file")

    if not message:
        return JsonResponse({"ok": False, "error": "Message is required."}, status=400)
    if excel_file is None:
        return JsonResponse({"ok": False, "error": "Excel file is required."}, status=400)
    if image_file is None:
        return JsonResponse({"ok": False, "error": "Image file is required."}, status=400)

    try:
        max_messages_value = int(max_messages)
        tick_timeout_value = int(tick_timeout)
    except ValueError:
        return JsonResponse({"ok": False, "error": "Settings must be valid numbers."}, status=400)

    if max_messages_value <= 0:
        return JsonResponse({"ok": False, "error": "Max messages must be greater than 0."}, status=400)
    if tick_timeout_value < 0:
        return JsonResponse({"ok": False, "error": "Tick timeout cannot be negative."}, status=400)

    if Path(excel_file.name).suffix.lower() not in EXCEL_EXTENSIONS:
        return JsonResponse({"ok": False, "error": "Excel file must be .xlsx or .xls."}, status=400)
    if Path(image_file.name).suffix.lower() not in IMAGE_EXTENSIONS:
        return JsonResponse({"ok": False, "error": "Image file must be jpg, jpeg, png, or bmp."}, status=400)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_dir = Path(settings.MEDIA_ROOT) / "uploads" / run_id
    report_dir = Path(settings.MEDIA_ROOT) / "reports" / run_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    storage = FileSystemStorage(location=upload_dir)
    excel_name = storage.save(excel_file.name, excel_file)
    image_name = storage.save(image_file.name, image_file)

    failed_report = report_dir / "whatsapp_failed_report.xlsx"
    inactive_report = report_dir / "whatsapp_inactive_numbers.xlsx"

    run_settings = RunSettings(
        message=message,
        excel_file=upload_dir / excel_name,
        image_file=upload_dir / image_name,
        max_messages=max_messages_value,
        tick_wait_timeout_seconds=tick_timeout_value,
        failed_report_file=failed_report,
        inactive_report_file=inactive_report,
    )

    report_urls = {
        "failed": {
            "label": "Failed report",
            "path": str(failed_report),
            "url": f"{settings.MEDIA_URL}reports/{run_id}/whatsapp_failed_report.xlsx",
        },
        "inactive": {
            "label": "Inactive numbers",
            "path": str(inactive_report),
            "url": f"{settings.MEDIA_URL}reports/{run_id}/whatsapp_inactive_numbers.xlsx",
        },
    }

    ok, message_text = job_manager.start(run_settings, run_id, report_urls)
    if not ok:
        return JsonResponse({"ok": False, "error": message_text}, status=409)

    return JsonResponse({"ok": True, "message": message_text})


@require_POST
def stop(request):
    ok, message_text = job_manager.stop()
    return JsonResponse({"ok": ok, "message": message_text})


@require_GET
def status(request):
    return JsonResponse(job_manager.snapshot())

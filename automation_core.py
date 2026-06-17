import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyautogui
import pyperclip

try:
    from pywinauto import Desktop
except ImportError:
    Desktop = None


SCRIPT_DIR = Path(__file__).resolve().parent
REPORT_FILE = SCRIPT_DIR / "whatsapp_failed_report.xlsx"
INACTIVE_REPORT_FILE = SCRIPT_DIR / "whatsapp_inactive_numbers.xlsx"

COUNTRY_CODE = "91"
WAIT_AFTER_CLOSE = 10
IMAGE_PASTE_WAIT = 5
MESSAGE_PASTE_WAIT = 8
CHAT_OPEN_WAIT = 15
UI_SCAN_INTERVAL = 1
TICK_CHECK_INTERVAL = 2
TICK_FALLBACK_CONFIRM_SECONDS = 5
DEFAULT_TICK_WAIT_TIMEOUT_SECONDS = 0
DEFAULT_MAX_MESSAGES = 50

NOT_ON_WHATSAPP_PHRASES = (
    "no results found",
    "no chats, contacts or messages found",
    "no contacts found",
    "no result",
    "not on whatsapp",
    "isn't on whatsapp",
    "phone number shared via url is invalid",
    "invalid phone number",
    "couldn't find",
)

CHAT_READY_PHRASES = (
    "type a message",
    "write a message",
    "message input",
    "compose a message",
)

WHATSAPP_LOGIN_PHRASES = (
    "get started",
    "scan the qr code",
    "link with phone number",
    "to set up whatsapp",
    "open whatsapp on your phone",
    "point your phone to this screen",
    "link a device",
    "loading your chats",
    "organizing messages",
    "connecting",
    "tap menu",
    "tap settings",
)

DELIVERY_STATUS_WORDS = ("sent", "delivered", "read")
SENDING_STATUS_PHRASES = ("sending", "waiting for this message", "retry")

pyautogui.PAUSE = 0.2


@dataclass
class RunSettings:
    message: str
    excel_file: Path
    image_file: Path
    max_messages: int
    tick_wait_timeout_seconds: int
    failed_report_file: Path = REPORT_FILE
    inactive_report_file: Path = INACTIVE_REPORT_FILE


def normalize_phone(value):
    if pd.isna(value):
        return ""

    if isinstance(value, float) and value.is_integer():
        raw_value = str(int(value))
    else:
        raw_value = str(value)

    phone = re.sub(r"\D", "", raw_value)

    if phone.startswith("00" + COUNTRY_CODE) and len(phone) == 14:
        phone = phone[4:]
    if phone.startswith(COUNTRY_CODE) and len(phone) == 12:
        phone = phone[2:]
    if phone.startswith("0") and len(phone) == 11:
        phone = phone[1:]

    return phone


def is_valid_number(num):
    return re.fullmatch(r"\d{10}", num) is not None


def normal_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def safe_sleep(seconds, stop_event=None):
    end_time = time.time() + seconds
    while time.time() < end_time:
        if stop_event and stop_event.is_set():
            return False
        time.sleep(min(0.2, end_time - time.time()))
    return True


def whatsapp_window():
    if Desktop is None:
        return None

    try:
        desktop = Desktop(backend="uia")
        for window in desktop.windows():
            try:
                title = normal_text(window.window_text())
                if "whatsapp" in title and window.is_visible():
                    return window
            except Exception:
                continue
    except Exception:
        return None

    return None


def read_whatsapp_texts():
    window = whatsapp_window()
    if window is None:
        return []

    texts = []
    try:
        descendants = window.descendants()
    except Exception:
        return texts

    for element in descendants:
        for getter in (
            lambda item: item.window_text(),
            lambda item: item.element_info.name,
        ):
            try:
                text = getter(element)
            except Exception:
                continue

            text = str(text or "").strip()
            if text:
                texts.append(text)

    return texts


def text_blob(texts):
    return "\n".join(normal_text(text) for text in texts)


def has_phrase(texts, phrases):
    blob = text_blob(texts)
    return any(phrase in blob for phrase in phrases)


def chat_is_ready(texts):
    return has_phrase(texts, CHAT_READY_PHRASES)


def delivery_statuses(texts):
    statuses = []

    for text in texts:
        normalized = normal_text(text).strip(" .:")
        if normalized in DELIVERY_STATUS_WORDS:
            statuses.append(normalized)
            continue

        if "message status" in normalized:
            for status in DELIVERY_STATUS_WORDS:
                if re.search(rf"\b{status}\b", normalized):
                    statuses.append(status)
                    break

    return statuses


def has_sending_status(texts):
    return has_phrase(texts, SENDING_STATUS_PHRASES)


def wait_for_chat_ready_or_missing(phone, stop_event, log):
    if Desktop is None:
        log("UI check dependency missing. Continuing with old timing.")
        safe_sleep(CHAT_OPEN_WAIT, stop_event)
        return "ready", "UI scanner unavailable"

    end_time = time.time() + CHAT_OPEN_WAIT
    saw_any_ui_text = False

    while time.time() < end_time:
        if stop_event.is_set():
            return "stopped", "Stopped by user"

        texts = read_whatsapp_texts()
        if texts:
            saw_any_ui_text = True

        if has_phrase(texts, NOT_ON_WHATSAPP_PHRASES):
            return "missing", "Number not found on WhatsApp"

        if chat_is_ready(texts):
            return "ready", "Chat opened"

        safe_sleep(UI_SCAN_INTERVAL, stop_event)

    if not saw_any_ui_text:
        log("UI text could not be read. Continuing with old timing.")
        return "ready", "UI scanner could not read WhatsApp text"

    return "missing", f"Chat did not open for {phone}"


def wait_for_whatsapp_login(stop_event, log):
    if Desktop is None:
        log("UI check dependency missing. Cannot verify WhatsApp login status.")
        return True

    log("Checking if WhatsApp is logged in and ready...")

    # We will check for up to 10 seconds to see if the window opens
    window_found = False
    for _ in range(5):
        if stop_event.is_set():
            return False
        if whatsapp_window() is not None:
            window_found = True
            break
        safe_sleep(2, stop_event)

    # If not running, attempt to open it
    if not window_found:
        log("WhatsApp not detected. Opening WhatsApp Desktop...")
        try:
            os.startfile("whatsapp:")
            safe_sleep(5, stop_event)
        except Exception as exc:
            log(f"Could not open WhatsApp: {exc}")
            return True

    # Now verify login status
    login_detected = False
    while True:
        if stop_event.is_set():
            return False

        window = whatsapp_window()
        if window is None:
            log("WhatsApp was closed. Reopening...")
            try:
                os.startfile("whatsapp:")
            except Exception:
                pass
            safe_sleep(5, stop_event)
            continue

        texts = read_whatsapp_texts()
        is_login_page = has_phrase(texts, WHATSAPP_LOGIN_PHRASES)

        if is_login_page:
            if not login_detected:
                log("WhatsApp QR Code / Login page detected! Please scan the QR code to log in. Waiting...")
                login_detected = True
            safe_sleep(3, stop_event)
            continue

        if login_detected:
            log("Login completed! WhatsApp is now ready.")
            safe_sleep(3, stop_event)
            break
        else:
            log("WhatsApp is logged in and ready.")
            break

    return True


def wait_for_delivery_tick(baseline_status_count, timeout_seconds, stop_event, log):
    if Desktop is None:
        log("Tick check dependency missing. Waiting with old delay.")
        safe_sleep(WAIT_AFTER_CLOSE, stop_event)
        return "not checked"

    start_time = time.time()
    last_notice = start_time
    saw_sending = False

    while True:
        if stop_event.is_set():
            return "stopped"

        texts = read_whatsapp_texts()
        statuses = delivery_statuses(texts)
        elapsed = time.time() - start_time

        is_currently_sending = has_sending_status(texts)
        if is_currently_sending:
            saw_sending = True

        # 1. If we see that the status count has increased and it is not currently sending, it is sent
        if len(statuses) > baseline_status_count and not is_currently_sending:
            return statuses[-1]

        # 2. If we saw it sending, and now it finished sending (sending status is gone)
        if saw_sending and not is_currently_sending and statuses:
            return statuses[-1]

        # 3. Fallback: if a reasonable time has passed, no active sending is visible, and we have a status, accept it
        if statuses and elapsed >= TICK_FALLBACK_CONFIRM_SECONDS and not is_currently_sending:
            return statuses[-1]

        # 4. Timeout limit reached (if configured by user)
        if timeout_seconds and elapsed >= timeout_seconds:
            return None

        if time.time() - last_notice >= 30:
            log("Still waiting for WhatsApp single/double tick...")
            last_notice = time.time()

        safe_sleep(TICK_CHECK_INTERVAL, stop_event)


def copy_image(image_file, stop_event):
    try:
        from PIL import Image
        import win32clipboard
        from io import BytesIO

        image = Image.open(image_file)
        output = BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        safe_sleep(1, stop_event)
    except Exception as e:
        # Fallback to visual Copy/Paste via Default Photos App if PIL/win32clipboard is missing
        os.startfile(image_file)
        safe_sleep(2, stop_event)
        pyautogui.hotkey("ctrl", "c")
        safe_sleep(1, stop_event)
        pyautogui.hotkey("alt", "f4")
        safe_sleep(1, stop_event)


def close_whatsapp(stop_event=None):
    pyautogui.hotkey("alt", "f4")
    safe_sleep(WAIT_AFTER_CLOSE, stop_event)


def add_report_row(report, row_number, row, phone, status, error):
    item = {
        "row_number": row_number,
        "original_phone": row.get("phone", ""),
        "phone": phone,
        "status": status,
        "error": error,
    }

    for column in row.index:
        if column not in item:
            item[column] = row[column]

    report.append(item)


def clear_old_reports(settings, log):
    for file_path in (settings.failed_report_file, settings.inactive_report_file):
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError as exc:
            log(f"Could not clear old report {file_path.name}: {exc}")


def save_report(report, file_path, label, log):
    if report:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(report).to_excel(file_path, index=False)
        log(f"{label} saved: {file_path}")
    else:
        log(f"No {label.lower()} found.")


def run_automation(settings, stop_event, log, stats):
    failed_report = []
    inactive_report = []
    sent_count = 0
    processed_count = 0

    stats(sent=0, inactive=0, failed=0, processed=0)
    clear_old_reports(settings, log)

    try:
        # Check if WhatsApp is logged in before processing the Excel
        if not wait_for_whatsapp_login(stop_event, log):
            return
        df = pd.read_excel(settings.excel_file)
        if "phone" not in df.columns:
            log("Excel must contain phone column.")
            return

        total_rows = len(df)
        log(f"Loaded {total_rows} rows from Excel.")

        for index, row in df.iterrows():
            if stop_event.is_set():
                log("Stopped before next number.")
                break

            row_number = int(index) + 2

            if sent_count >= settings.max_messages:
                log(f"Reached the limit of {settings.max_messages} messages.")
                break

            phone = normalize_phone(row["phone"])
            processed_count += 1
            stats(processed=processed_count)

            if not is_valid_number(phone):
                log(f"Invalid number: {phone}")
                add_report_row(
                    failed_report,
                    row_number,
                    row,
                    phone,
                    "INVALID NUMBER",
                    "Not valid Indian number",
                )
                add_report_row(
                    inactive_report,
                    row_number,
                    row,
                    phone,
                    "INVALID NUMBER",
                    "Not valid Indian number",
                )
                stats(inactive=len(inactive_report), failed=len(failed_report))
                continue

            try:
                log(f"Opening WhatsApp for {phone}...")
                opened_via_protocol = False
                try:
                    os.startfile(f"whatsapp://send?phone={phone}")
                    opened_via_protocol = True
                    safe_sleep(5, stop_event)
                except Exception as exc:
                    log(f"Could not open via whatsapp:// protocol: {exc}. Trying manual search fallback...")

                if not opened_via_protocol:
                    pyautogui.hotkey("win", "s")
                    safe_sleep(1.5, stop_event)
                    pyautogui.write("WhatsApp")
                    safe_sleep(1.5, stop_event)
                    pyautogui.press("enter")
                    safe_sleep(6, stop_event)

                    if stop_event.is_set():
                        log("Stopped by user.")
                        close_whatsapp(stop_event)
                        break

                    pyautogui.hotkey("ctrl", "n")
                    safe_sleep(2, stop_event)

                    pyautogui.write(phone)
                    safe_sleep(2, stop_event)
                    pyautogui.press("enter")

                chat_status, chat_error = wait_for_chat_ready_or_missing(
                    phone,
                    stop_event,
                    log,
                )

                if chat_status == "stopped":
                    log("Stopped by user.")
                    close_whatsapp(stop_event)
                    break

                if chat_status != "ready":
                    log(f"Inactive / not on WhatsApp: {phone}")
                    add_report_row(
                        failed_report,
                        row_number,
                        row,
                        phone,
                        "INACTIVE ON WHATSAPP",
                        chat_error,
                    )
                    add_report_row(
                        inactive_report,
                        row_number,
                        row,
                        phone,
                        "INACTIVE ON WHATSAPP",
                        chat_error,
                    )
                    stats(inactive=len(inactive_report), failed=len(failed_report))
                    close_whatsapp(stop_event)
                    continue

                copy_image(settings.image_file, stop_event)

                pyautogui.hotkey("ctrl", "v")
                safe_sleep(IMAGE_PASTE_WAIT, stop_event)

                pyperclip.copy(settings.message)
                safe_sleep(1, stop_event)

                pyautogui.hotkey("ctrl", "v")
                safe_sleep(MESSAGE_PASTE_WAIT, stop_event)

                baseline_status_count = len(delivery_statuses(read_whatsapp_texts()))
                pyautogui.press("enter")
                sent_count += 1
                stats(sent=sent_count)

                log(f"Send pressed: {phone}. Waiting for single/double tick...")
                tick_status = wait_for_delivery_tick(
                    baseline_status_count,
                    settings.tick_wait_timeout_seconds,
                    stop_event,
                    log,
                )

                if tick_status == "stopped":
                    log("Stopped by user while waiting for tick.")
                    close_whatsapp(stop_event)
                    break

                if tick_status is None:
                    log(f"Tick not confirmed. Stopping before next number: {phone}")
                    add_report_row(
                        failed_report,
                        row_number,
                        row,
                        phone,
                        "TICK NOT CONFIRMED",
                        "Single/double tick was not confirmed",
                    )
                    stats(failed=len(failed_report))
                    close_whatsapp(stop_event)
                    break

                log(f"Sent and tick confirmed ({tick_status}): {phone}")
                close_whatsapp(stop_event)

            except Exception as exc:
                log(f"Failed: {phone} - {exc}")
                add_report_row(
                    failed_report,
                    row_number,
                    row,
                    phone,
                    "FAILED",
                    str(exc),
                )
                stats(failed=len(failed_report))
                close_whatsapp(stop_event)

    except Exception as exc:
        log(f"Process failed: {exc}")

    finally:
        save_report(
            failed_report,
            settings.failed_report_file,
            "Failed/not-on-WhatsApp report",
            log,
        )
        save_report(
            inactive_report,
            settings.inactive_report_file,
            "Inactive WhatsApp numbers report",
            log,
        )
        if settings.failed_report_file.exists():
            try:
                import shutil
                dest = SCRIPT_DIR / "whatsapp_failed_report.xlsx"
                shutil.copy2(settings.failed_report_file, dest)
                log(f"Latest failed report copied to workspace: {dest.name}")
            except Exception as e:
                log(f"Could not copy failed report to script dir: {e}")

        if settings.inactive_report_file.exists():
            try:
                import shutil
                dest = SCRIPT_DIR / "whatsapp_inactive_numbers.xlsx"
                shutil.copy2(settings.inactive_report_file, dest)
                log(f"Latest inactive report copied to workspace: {dest.name}")
            except Exception as e:
                log(f"Could not copy inactive report to script dir: {e}")
        log("PROCESS COMPLETED")

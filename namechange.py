import os
import socket
import sys
import threading
import webbrowser


def find_open_port(start_port):
    port = int(start_port)
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                port += 1
                continue
        return port


def open_browser(port):
    webbrowser.open(f"http://127.0.0.1:{port}/")


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "whatsapp_web.settings")

    from django.core.management import execute_from_command_line

    if len(sys.argv) == 1:
        port = find_open_port(os.environ.get("PORT", "8000"))
        threading.Timer(1.2, open_browser, args=(port,)).start()
        execute_from_command_line([sys.argv[0], "runserver", f"127.0.0.1:{port}", "--noreload"])
        return

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

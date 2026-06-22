import ipaddress
import socket

import uvicorn
from rich.markup import escape
from rich.panel import Panel

from app_main.identity.client_ip import local_lan_ip
from app_main.terminal_theme import make_console


def _format_host_for_url(host: str) -> str:
    try:
        if ipaddress.ip_address(host).version == 6:
            return f"[{host}]"
    except ValueError:
        pass
    return host


def _print_access_urls(port: int, base_path: str = "") -> None:
    prefix = base_path.rstrip("/")
    suffix = f"{prefix}/" if prefix else "/"
    lan = local_lan_ip()
    lan_url = _format_host_for_url(lan)

    lines = [
        f"[label]监听[/label]  [value]0.0.0.0:{port}[/value]",
        f"[label]本机[/label]    [url]http://127.0.0.1:{port}{escape(suffix)}[/url]",
        f"[label]局域网[/label]  [url]http://{escape(lan_url)}:{port}{escape(suffix)}[/url]",
    ]
    if prefix:
        lines.append(
            f"[label]反代 upstream[/label]  [url]http://127.0.0.1:{port}{escape(suffix)}[/url]"
        )
        lines.append(
            f"[label]反代（80 端口）[/label]  [url]http://{escape(lan_url)}{escape(suffix)}[/url]"
        )

    console = make_console()
    console.print(Panel("\n".join(lines), title="[banner.title]访问地址[/banner.title]", border_style="dim"))
    console.print()


def run_server_with_startup_print(port: int, app=None, base_path: str = "") -> None:
    """启动服务；端口为 0 时由系统分配并在启动后打印实际端口。"""
    if app is None:
        from app_main.app import create_app

        app = create_app()

    if port == 0:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("0.0.0.0", 0))
        actual_port = sock.getsockname()[1]
        sock.close()
        _print_access_urls(actual_port, base_path)
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=actual_port,
            log_level="warning",
            log_config=None,
            access_log=False,
        )
        return

    _print_access_urls(port, base_path)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="warning",
        log_config=None,
        access_log=False,
    )

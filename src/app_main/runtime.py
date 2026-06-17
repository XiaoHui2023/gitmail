import ipaddress
import socket

import uvicorn

from app_main.identity.client_ip import local_lan_ip


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
    print(f"服务已监听: [::]:{port}（双栈，含 IPv4 映射）")
    print(f"本机访问: http://127.0.0.1:{port}{suffix}")
    print(f"本机访问: http://[::1]:{port}{suffix}")
    lan = local_lan_ip()
    lan_url = _format_host_for_url(lan)
    print(f"局域网访问: http://{lan_url}:{port}{suffix}")
    if prefix:
        print(f"反向代理 upstream 建议: http://[::1]:{port}{suffix}")
        print(f"反向代理（80 端口）: http://{lan_url}{suffix}")
        try:
            if ipaddress.ip_address(lan).version == 6:
                print("提示: 纯 IPv6 环境请将 proxy_pass 指向 [::1]，勿用 127.0.0.1")
        except ValueError:
            pass


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
        uvicorn.run(app, host="::", port=actual_port, log_level="info")
        return

    _print_access_urls(port, base_path)
    uvicorn.run(app, host="::", port=port, log_level="info")

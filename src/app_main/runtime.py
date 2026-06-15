import socket

import uvicorn


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def _print_access_urls(host: str, port: int, base_path: str = "") -> None:
    prefix = base_path.rstrip("/")
    suffix = f"{prefix}/" if prefix else "/"
    print(f"服务已监听: {host}:{port}")
    print(f"本机访问: http://127.0.0.1:{port}{suffix}")
    print(f"局域网访问: http://{_local_ip()}:{port}{suffix}")
    if prefix:
        lan_ip = _local_ip()
        print(f"反向代理（80 端口）: http://127.0.0.1{suffix}")
        print(f"反向代理（80 端口）: http://{lan_ip}{suffix}")


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
        _print_access_urls("0.0.0.0", actual_port, base_path)
        uvicorn.run(app, host="0.0.0.0", port=actual_port, log_level="info")
        return

    _print_access_urls("0.0.0.0", port, base_path)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

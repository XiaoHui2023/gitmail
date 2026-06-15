import argparse
import logging

from app_main.app import create_app, set_config_path
from app_main.config_loader import resolve_config_path
from app_main.runtime import run_server_with_startup_print


def main() -> None:
    parser = argparse.ArgumentParser(description="gitmail 本地 Web 服务")
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        metavar="config",
        help="配置文件路径，默认当前目录下 config.yaml",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    config_path = resolve_config_path(args.config)
    set_config_path(config_path)
    app = create_app(config_path)
    listen_port = 0
    base_path = ""
    if config_path.is_file():
        from app_main.config_loader import load_config

        cfg = load_config(config_path)
        listen_port = cfg.listen_port
        base_path = cfg.public_base_path.strip().rstrip("/")
    run_server_with_startup_print(listen_port, app=app, base_path=base_path)


if __name__ == "__main__":
    main()

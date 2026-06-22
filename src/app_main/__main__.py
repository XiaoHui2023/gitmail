import argparse

from app_main.app import create_app, set_config_path
from app_main.config_loader import load_config, resolve_config_path
from app_main.env_settings import AiSettings, SmtpSettings
from app_main.feature_runtime import OperationalAi, OperationalSmtp
from app_main.logging_setup import setup_logging
from app_main.models.config import AppConfig
from app_main.paths import create_log_session_dir
from app_main.runtime import run_server_with_startup_print
from app_main.startup_checks import run_startup_checks
from app_main.startup_display import print_startup_status


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
    config_path = resolve_config_path(args.config)
    config_found = config_path.is_file()
    if config_found:
        config = load_config(config_path)
    else:
        config = AppConfig(email_domain="example.com", projects=[])

    log_session_dir = create_log_session_dir(config.log_dir)
    setup_logging(log_session_dir)

    smtp = OperationalSmtp(SmtpSettings())
    ai = OperationalAi(AiSettings())
    run_startup_checks(smtp, ai)
    print_startup_status(
        config,
        smtp,
        ai,
        config_path=config_path,
        config_found=config_found,
        log_session_dir=log_session_dir,
    )

    set_config_path(config_path)
    app = create_app(config_path, smtp=smtp, ai=ai)
    run_server_with_startup_print(
        config.listen_port,
        app=app,
        base_path=config.public_base_path.strip().rstrip("/"),
    )


if __name__ == "__main__":
    main()

from pathlib import Path
import sys


def resolve_data_dir() -> Path:
    """运行期数据目录（SQLite 等）。"""
    if getattr(sys, "frozen", False):
        return Path.cwd() / "data"
    return Path(__file__).resolve().parents[2] / "data"


def resolve_frontend_dist() -> Path:
    """定位 Vite 构建产物目录，兼容开发与 PyInstaller 打包。"""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return base / "frontend" / "dist"
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"

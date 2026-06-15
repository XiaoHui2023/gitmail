# gitmail

Git 邮件相关本地 Web 工具。浏览器访问界面，后端在同一进程提供 API 与静态页面。

## 项目结构与目录布局

```text
gitmail/
  src/app_main/          # FastAPI 应用、API 路由、启动入口
  frontend/              # React + Vite 前端
  tests/                 # pytest
  update.bat / update.sh # 创建虚拟环境并安装依赖
  test.bat / test.sh     # 运行测试
```

## 命令行参数

入口：`python -m app_main [config]`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `config` | 字符串 | | `config.yaml` | 配置文件路径（位置参数） |

服务固定监听 `0.0.0.0`；`listen_port`、`public_base_path` 等在 `config.yaml` 中配置。启动后在终端打印本机与局域网访问地址。

复制 `config.example.yaml` 为 `config.yaml` 并填写监控项目；复制 `.env.example` 为 `.env` 填写 SMTP（发信用）。

## 开发

**后端**

```bat
update.bat
# config.yaml 中 listen_port: 8765
python -m app_main
```

**前端**（另开终端）

```bat
cd frontend
npm install
npm run dev
```

Vite 将 `/api` 代理到 `http://127.0.0.1:8765`。

## 发布

**单文件可执行体**（含前端静态资源，解压即用）：

```bat
tools\pack.bat
```

产物在 `dist/`：

- `gitmail.exe` — Windows 单文件服务
- `gitmail-0.0.0-windows.zip` — 可执行体 + README + 配置示例

Linux / Git Bash：

```bash
./tools/pack.sh
```

Linux 上会对 onefile 再跑 staticx（需系统 `patchelf`），并生成 `gitmail-<version>-linux.tar.gz`。

运行前复制 `config.example.yaml` 为 `config.yaml`、`.env.example` 为 `.env` 并填写；在解压目录执行：

```bat
gitmail.exe
```

`config.yaml` 中设置 `listen_port`（如 `8000`）。若已有 80 端口站点，可设 `public_base_path: /tools/gitmail`，由反向代理把该路径转发到本服务监听端口。

## 前端

目录：`frontend/`

| 命令 | 说明 |
| --- | --- |
| `npm install` | 安装依赖 |
| `npm run dev` | 开发服务器 |
| `npm run build` | 生产构建 |

Vite `base` 为 `./`；API 请求使用相对路径 `/api/...`。子路径部署时配置 `public_base_path`，前端使用 HashRouter，刷新不 404。

### 挂在已有 80 端口站点下

gitmail 仍在本机某端口监听（如 `8765`），由 Nginx 等反向代理把子路径转发过来。`config.yaml` 示例：

```yaml
listen_port: 8765
public_base_path: /tools/gitmail
trusted_proxy_header: X-Forwarded-For
```

Nginx 片段（站点根已在 80 端口）：

```nginx
location /tools/gitmail/ {
    proxy_pass http://127.0.0.1:8765/tools/gitmail/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

用户访问 `http://<服务器IP>/tools/gitmail/`，无需 `:端口`。

## 测试

```bat
test.bat
```

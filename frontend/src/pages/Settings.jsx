import { useEffect, useState } from "react";
import {
  fetchMe,
  fetchSettings,
  fetchStatus,
  saveSettings,
} from "../api.js";

export default function SettingsPage() {
  const [user, setUser] = useState(null);
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [monitor, setMonitor] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([fetchMe(), fetchStatus()])
      .then(([me, status]) => {
        setUser(me);
        setMonitor(status.monitor);
        if (!me.allowed) return null;
        return fetchSettings();
      })
      .then((settings) => {
        if (settings) setEmailEnabled(!!settings.email_enabled);
      })
      .catch((err) => setError(err.message));
  }, []);

  async function onToggle(checked) {
    setSaving(true);
    setError("");
    try {
      const res = await saveSettings(checked);
      setEmailEnabled(!!res.email_enabled);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <h1 className="page-title">设置</h1>
      {error && <div className="error-banner">{error}</div>}
      <div className="card">
        <dl className="meta-grid">
          <dt>用户名</dt>
          <dd>{user?.username ?? "…"}</dd>
          <dt>IP 地址</dt>
          <dd>{user?.ip ?? "…"}</dd>
          <dt>邮箱</dt>
          <dd>{user?.email || "（未识别）"}</dd>
          <dt>识别方式</dt>
          <dd>{user?.resolve_method ?? "—"}</dd>
          <dt>白名单</dt>
          <dd>{user?.allowed ? "已通过" : "未通过"}</dd>
        </dl>
        {user?.allowed ? (
          <label>
            <input
              type="checkbox"
              checked={emailEnabled}
              disabled={saving || user.username === "unknown"}
              onChange={(e) => onToggle(e.target.checked)}
            />
            仓库更新时发送邮件
          </label>
        ) : (
          <p className="empty">当前 IP 不在白名单，无法修改邮件设置或订阅。</p>
        )}
      </div>
      {monitor ? (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>监控摘要</h2>
          <dl className="meta-grid">
            <dt>调度状态</dt>
            <dd>{monitor.running ? "运行中" : "已停止"}</dd>
            <dt>上一轮耗时</dt>
            <dd>{monitor.last_round_seconds?.toFixed(1) ?? "—"} 秒</dd>
            <dt>仓库数</dt>
            <dd>{monitor.last_round_repo_count ?? 0}</dd>
            <dt>失败数</dt>
            <dd>{monitor.failed_repo_count ?? 0}</dd>
          </dl>
        </div>
      ) : null}
    </section>
  );
}

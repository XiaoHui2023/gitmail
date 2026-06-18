import { useEffect, useState } from "react";
import {
  fetchMe,
  fetchSettings,
  saveSettings,
} from "../api.js";

export default function SettingsPage() {
  const [user, setUser] = useState(null);
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchMe()
      .then((me) => {
        setUser(me);
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
        </dl>
        {user?.allowed ? (
          <div className="setting-row">
            <div className="setting-copy">
              <div className="setting-title">仓库更新时发送邮件</div>
              <div className="setting-state">{emailEnabled ? "已开启" : "已关闭"}</div>
            </div>
            <button
              type="button"
              className="switch-control"
              role="switch"
              aria-checked={emailEnabled}
              disabled={saving || user.username === "unknown"}
              onClick={() => onToggle(!emailEnabled)}
            >
              <span className="switch-thumb" />
            </button>
          </div>
        ) : (
          <p className="empty">当前 IP 不在白名单，无法修改邮件设置或订阅。</p>
        )}
      </div>
    </section>
  );
}

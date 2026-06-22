import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createWebhook,
  deleteWebhook,
  fetchMe,
  fetchRepos,
  fetchWebhooks,
  testWebhook,
  updateWebhook,
} from "../api.js";

function formatDelivery(delivery) {
  if (!delivery) return "尚未投递";
  const when = new Date(delivery.at * 1000).toLocaleString();
  if (delivery.ok) {
    const code = delivery.status_code ? `HTTP ${delivery.status_code}` : "成功";
    return `${code} · ${when}`;
  }
  const detail = delivery.error || `HTTP ${delivery.status_code ?? "?"}`;
  return `失败（${detail}）· ${when}`;
}

function emptyForm() {
  return {
    repo_key: "",
    url: "",
    label: "",
    enabled: true,
    secret: "",
  };
}

export default function WebhooksPage() {
  const [user, setUser] = useState(null);
  const [items, setItems] = useState([]);
  const [repos, setRepos] = useState([]);
  const [error, setError] = useState("");
  const [repoFilter, setRepoFilter] = useState("");
  const [form, setForm] = useState(emptyForm());
  const [editingId, setEditingId] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [createdSecret, setCreatedSecret] = useState("");
  const [busy, setBusy] = useState("");
  const [testResult, setTestResult] = useState(null);

  const load = useCallback(async () => {
    const me = await fetchMe();
    setUser(me);
    if (!me.allowed) return;
    const [hooks, repoData] = await Promise.all([fetchWebhooks(), fetchRepos()]);
    setItems(hooks.items || []);
    setRepos(repoData.items || []);
  }, []);

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, [load]);

  const repoOptions = useMemo(() => {
    const needle = repoFilter.trim().toLowerCase();
    return repos
      .filter((repo) => repo.status === "ok")
      .filter((repo) => {
        if (!needle) return true;
        const text = `${repo.project_name} ${repo.repo_path} ${repo.repo_key}`.toLowerCase();
        return text.includes(needle);
      })
      .slice(0, 80);
  }, [repos, repoFilter]);

  function openCreate() {
    setEditingId("");
    setForm(emptyForm());
    setCreatedSecret("");
    setTestResult(null);
    setShowForm(true);
    setError("");
  }

  function openEdit(item) {
    setEditingId(item.id);
    setForm({
      repo_key: item.repo_key,
      url: item.url,
      label: item.label || "",
      enabled: item.enabled,
      secret: "",
    });
    setCreatedSecret("");
    setTestResult(null);
    setShowForm(true);
    setError("");
  }

  function closeForm() {
    setShowForm(false);
    setEditingId("");
    setForm(emptyForm());
    setCreatedSecret("");
  }

  async function onSubmit(event) {
    event.preventDefault();
    setBusy("save");
    setError("");
    setCreatedSecret("");
    try {
      if (!form.repo_key.trim()) {
        throw new Error("请选择仓库");
      }
      if (!form.url.trim()) {
        throw new Error("请填写回调 URL");
      }
      if (editingId) {
        const payload = {
          repo_key: form.repo_key.trim(),
          url: form.url.trim(),
          label: form.label.trim(),
          enabled: form.enabled,
        };
        if (form.secret.trim()) {
          payload.secret = form.secret.trim();
        }
        await updateWebhook(editingId, payload);
        closeForm();
      } else {
        const payload = {
          repo_key: form.repo_key.trim(),
          url: form.url.trim(),
          label: form.label.trim(),
          enabled: form.enabled,
        };
        if (form.secret.trim()) {
          payload.secret = form.secret.trim();
        }
        const created = await createWebhook(payload);
        if (created.secret) {
          setCreatedSecret(created.secret);
        } else {
          closeForm();
        }
      }
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function onDelete(item) {
    if (!window.confirm(`删除 Webhook：${item.project_name} / ${item.repo_path}？`)) {
      return;
    }
    setBusy(item.id);
    setError("");
    try {
      await deleteWebhook(item.id);
      if (editingId === item.id) {
        closeForm();
      }
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function onTest(item) {
    setBusy(`test:${item.id}`);
    setTestResult(null);
    setError("");
    try {
      const result = await testWebhook(item.id);
      setTestResult({ id: item.id, ...result });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function onToggleEnabled(item) {
    setBusy(`toggle:${item.id}`);
    setError("");
    try {
      await updateWebhook(item.id, { enabled: !item.enabled });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="webhooks-page">
      <div className="webhooks-header">
        <h1 className="page-title">Webhook</h1>
        {user?.allowed ? (
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            新建
          </button>
        ) : null}
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      {!user?.allowed ? (
        <p className="empty">当前 IP 不在白名单，无法管理 Webhook。</p>
      ) : null}

      {showForm && user?.allowed ? (
        <form className="card webhooks-form" onSubmit={onSubmit}>
          <h2 className="webhooks-form-title">{editingId ? "编辑 Webhook" : "新建 Webhook"}</h2>

          <label className="field-block">
            <span className="field-label">仓库</span>
            <input
              type="search"
              className="field-input"
              placeholder="输入项目名或路径筛选"
              value={repoFilter}
              onChange={(event) => setRepoFilter(event.target.value)}
            />
            <select
              className="field-input"
              required
              value={form.repo_key}
              onChange={(event) => setForm((prev) => ({ ...prev, repo_key: event.target.value }))}
            >
              <option value="">选择仓库…</option>
              {repoOptions.map((repo) => (
                <option key={repo.repo_key} value={repo.repo_key}>
                  {repo.project_name} / {repo.repo_path}
                </option>
              ))}
            </select>
          </label>

          <label className="field-block">
            <span className="field-label">回调 URL</span>
            <input
              className="field-input"
              type="url"
              required
              placeholder="https://example.com/hooks/gitmail"
              value={form.url}
              onChange={(event) => setForm((prev) => ({ ...prev, url: event.target.value }))}
            />
          </label>

          <label className="field-block">
            <span className="field-label">备注</span>
            <input
              className="field-input"
              type="text"
              placeholder="例如：CI 构建"
              value={form.label}
              onChange={(event) => setForm((prev) => ({ ...prev, label: event.target.value }))}
            />
          </label>

          <label className="field-block">
            <span className="field-label">
              签名密钥{editingId ? "（留空则不修改）" : "（留空则自动生成）"}
            </span>
            <input
              className="field-input"
              type="text"
              value={form.secret}
              onChange={(event) => setForm((prev) => ({ ...prev, secret: event.target.value }))}
            />
          </label>

          <label className="field-inline">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) => setForm((prev) => ({ ...prev, enabled: event.target.checked }))}
            />
            <span>启用</span>
          </label>

          {createdSecret ? (
            <div className="secret-banner">
              请保存签名密钥（仅显示一次）：<code>{createdSecret}</code>
            </div>
          ) : null}

          <div className="webhooks-form-actions">
            <button type="submit" className="btn btn-primary" disabled={busy === "save"}>
              {editingId ? "保存" : "创建"}
            </button>
            <button type="button" className="btn" onClick={closeForm}>
              {createdSecret ? "完成" : "取消"}
            </button>
          </div>
        </form>
      ) : null}

      {user?.allowed && !showForm ? (
        items.length === 0 ? (
          <p className="empty">尚未配置 Webhook。仓库更新后将向指定地址发送 HTTP POST。</p>
        ) : (
          <div className="webhooks-list">
            {items.map((item) => (
              <article key={item.id} className="card webhook-card">
                <div className="webhook-card-head">
                  <div>
                    <div className="webhook-repo">
                      {item.project_name} / {item.repo_path}
                    </div>
                    {item.label ? <div className="webhook-label">{item.label}</div> : null}
                    <div className="webhook-url">{item.url}</div>
                    <div className="webhook-delivery">{formatDelivery(item.last_delivery)}</div>
                  </div>
                  <button
                    type="button"
                    className="switch-control"
                    role="switch"
                    aria-checked={item.enabled}
                    disabled={busy === `toggle:${item.id}`}
                    onClick={() => onToggleEnabled(item)}
                  >
                    <span className="switch-thumb" />
                  </button>
                </div>
                <div className="webhook-card-actions">
                  <button
                    type="button"
                    className="btn"
                    disabled={busy === `test:${item.id}`}
                    onClick={() => onTest(item)}
                  >
                    调试
                  </button>
                  <button type="button" className="btn" onClick={() => openEdit(item)}>
                    编辑
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    disabled={busy === item.id}
                    onClick={() => onDelete(item)}
                  >
                    删除
                  </button>
                </div>
                {testResult?.id === item.id ? (
                  <div className={`test-result ${testResult.ok ? "ok" : "fail"}`}>
                    {testResult.ok ? "调试成功" : "调试失败"} · {testResult.duration_ms}ms
                    {testResult.status_code ? ` · HTTP ${testResult.status_code}` : ""}
                    {testResult.error ? ` · ${testResult.error}` : ""}
                    {testResult.response_preview ? (
                      <div className="test-result-body">{testResult.response_preview}</div>
                    ) : null}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        )
      ) : null}
    </section>
  );
}

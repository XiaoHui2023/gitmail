import { useCallback, useEffect, useState } from "react";
import {
  fetchMe,
  fetchRepos,
  fetchSubscribedRepos,
  subscribeRepo,
  unsubscribeRepo,
} from "../api.js";
import { AbsoluteTime, RelativeAge, RepoPath } from "./RelativeTime.jsx";

function ExternalLinkIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M14 3h7v7h-2V6.4l-9.2 9.2-1.4-1.4L17.6 5H14V3ZM5 5h6v2H7v10h10v-4h2v6H5V5Z"
      />
    </svg>
  );
}

function BellIcon({ filled = false }) {
  if (filled) {
    return (
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path
          fill="currentColor"
          d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 1 0-14 0v5l-2 2v1h18v-1l-2-2Z"
        />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5-6.7V4a2 2 0 1 0-4 0v.3A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2Z"
      />
    </svg>
  );
}

function RepoStatus({ repo }) {
  if (repo.status === "error") {
    return (
      <div className="repo-status">
        <span className="status-pill error">异常</span>
        {repo.error_message ? (
          <div className="repo-status-detail">{repo.error_message}</div>
        ) : null}
      </div>
    );
  }
  if (repo.status === "unreachable") {
    return (
      <div className="repo-status">
        <span className="status-pill">未检出</span>
      </div>
    );
  }
  if (repo.status === "pending") {
    return (
      <div className="repo-status">
        <span className="status-pill pending">待检查</span>
      </div>
    );
  }
  return (
    <div className="repo-status">
      <span className="status-pill ok">正常</span>
    </div>
  );
}

export default function RepoList({
  mode = "all",
  pollSeconds = 30,
  title,
  showSubscribe = true,
  monitorHealth = null,
}) {
  const [items, setItems] = useState([]);
  const [projectFilter, setProjectFilter] = useState("");
  const [pathFilter, setPathFilter] = useState("");
  const [error, setError] = useState("");
  const [user, setUser] = useState(null);
  const [busyKey, setBusyKey] = useState("");

  const load = useCallback(async () => {
    try {
      const params = {
        project: projectFilter.trim(),
        path: pathFilter.trim(),
      };
      const fetcher = mode === "subscribed" ? fetchSubscribedRepos : fetchRepos;
      const [repoData, me] = await Promise.all([
        fetcher(params),
        fetchMe().catch(() => null),
      ]);
      setItems(repoData.items || []);
      setUser(me);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [mode, projectFilter, pathFilter]);

  useEffect(() => {
    load();
    const id = setInterval(load, Math.max(10, pollSeconds) * 1000);
    return () => clearInterval(id);
  }, [load, pollSeconds]);

  const showActions =
    user?.allowed && (showSubscribe || mode === "subscribed");

  async function toggleSubscribe(repo) {
    if (!user?.allowed) return;
    setBusyKey(repo.repo_key);
    try {
      if (repo.subscribed) {
        await unsubscribeRepo(repo.repo_key);
      } else {
        await subscribeRepo(repo.repo_key);
      }
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyKey("");
    }
  }

  return (
    <section>
      <h1 className="page-title">{title}</h1>
      {monitorHealth?.project_errors &&
      Object.keys(monitorHealth.project_errors).length > 0 ? (
        <div className="error-banner">
          {Object.entries(monitorHealth.project_errors).map(([name, msg]) => (
            <div key={name}>
              项目 {name}：{msg}
            </div>
          ))}
        </div>
      ) : null}
      {monitorHealth?.failed_repo_count > 0 ? (
        <p className="monitor-hint">
          本轮监控有 {monitorHealth.failed_repo_count} 个仓库检查失败，详见下表「状态」列。
          服务端日志亦会记录每条失败原因。
        </p>
      ) : null}
      {error && <div className="error-banner">{error}</div>}
      <div className="filters">
        <input
          placeholder="按项目名过滤"
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
        />
        <input
          placeholder="按仓库路径过滤"
          value={pathFilter}
          onChange={(e) => setPathFilter(e.target.value)}
        />
      </div>
      {items.length === 0 ? (
        <p className="empty">{mode === "subscribed" ? "暂无订阅的仓库" : "暂无监控仓库"}</p>
      ) : (
        <table className="repo-table">
          <thead>
            <tr>
              <th>仓库</th>
              <th>提交时间</th>
              <th>距今</th>
              <th>状态</th>
              <th className="repo-actions-col" aria-label="操作" />
            </tr>
          </thead>
          <tbody>
            {items.map((repo) => (
              <tr key={repo.repo_key}>
                <td>
                  <RepoPath projectName={repo.project_name} repoPath={repo.repo_path} />
                </td>
                <td className="time-absolute-cell">
                  <AbsoluteTime timestamp={repo.last_commit_time} />
                </td>
                <td className="time-relative-cell">
                  <RelativeAge timestamp={repo.last_commit_time} />
                </td>
                <td>
                  <RepoStatus repo={repo} />
                </td>
                <td className="repo-actions-cell">
                  <div className="repo-row-actions">
                    {repo.gerrit_project_url ? (
                      <a
                        className="icon-btn"
                        href={repo.gerrit_project_url}
                        target="_blank"
                        rel="noreferrer"
                        aria-label="打开 Gerrit 项目页"
                        title="Gerrit"
                      >
                        <ExternalLinkIcon />
                      </a>
                    ) : null}
                    {showActions ? (
                      <button
                        type="button"
                        className="icon-btn"
                        aria-label={repo.subscribed ? "取消订阅" : "订阅"}
                        aria-pressed={repo.subscribed}
                        title={repo.subscribed ? "取消订阅" : "订阅"}
                        disabled={busyKey === repo.repo_key}
                        onClick={() => toggleSubscribe(repo)}
                      >
                        <BellIcon filled={repo.subscribed} />
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

import { useCallback, useEffect, useState } from "react";
import {
  fetchMe,
  fetchRepos,
  fetchSubscribedRepos,
  subscribeRepo,
  unsubscribeRepo,
} from "../api.js";
import RelativeTime, { RepoPath } from "./RelativeTime.jsx";

export default function RepoList({
  mode = "all",
  pollSeconds = 30,
  title,
  showSubscribe = true,
  subtleUnsubscribe = false,
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
              <th>最近更新</th>
              <th>状态</th>
              {showSubscribe && user?.allowed ? <th /> : null}
              {mode === "subscribed" && user?.allowed ? <th /> : null}
            </tr>
          </thead>
          <tbody>
            {items.map((repo) => (
              <tr key={repo.repo_key}>
                <td>
                  <RepoPath projectName={repo.project_name} repoPath={repo.repo_path} />
                  {repo.gerrit_project_url ? (
                    <div>
                      <a href={repo.gerrit_project_url} target="_blank" rel="noreferrer">
                        Gerrit
                      </a>
                    </div>
                  ) : null}
                </td>
                <td>
                  <RelativeTime timestamp={repo.last_commit_time} />
                </td>
                <td>
                  {repo.status === "error" ? (
                    <span className="status-pill error" title={repo.error_message || ""}>
                      异常
                    </span>
                  ) : repo.status === "unreachable" ? (
                    <span className="status-pill">未检出</span>
                  ) : (
                    <span className="status-pill">正常</span>
                  )}
                </td>
                {showSubscribe && user?.allowed ? (
                  <td>
                    <button
                      type="button"
                      className={repo.subscribed ? "btn" : "btn btn-primary"}
                      disabled={busyKey === repo.repo_key}
                      onClick={() => toggleSubscribe(repo)}
                    >
                      {repo.subscribed ? "取消订阅" : "订阅"}
                    </button>
                  </td>
                ) : null}
                {mode === "subscribed" && user?.allowed ? (
                  <td>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={busyKey === repo.repo_key}
                      onClick={() => toggleSubscribe(repo)}
                    >
                      取消
                    </button>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

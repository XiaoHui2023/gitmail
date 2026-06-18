import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchMe,
  fetchRepos,
  fetchSubscribedRepos,
  subscribeRepo,
  unsubscribeRepo,
} from "../api.js";
import { CommitTimeAge, RepoPath } from "./RelativeTime.jsx";

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

export default function RepoList({
  mode = "all",
  pollSeconds = 30,
  title,
  showSubscribe = true,
}) {
  const [items, setItems] = useState([]);
  const [projectFilter, setProjectFilter] = useState("");
  const [pathFilter, setPathFilter] = useState("");
  const [error, setError] = useState("");
  const [user, setUser] = useState(null);
  const [busyKey, setBusyKey] = useState("");
  const [sortKey, setSortKey] = useState("time");
  const requestSeqRef = useRef(0);

  const load = useCallback(async () => {
    const requestSeq = requestSeqRef.current + 1;
    requestSeqRef.current = requestSeq;
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
      if (requestSeq !== requestSeqRef.current) return;
      setItems(repoData.items || []);
      setUser(me);
      setError("");
    } catch (err) {
      if (requestSeq !== requestSeqRef.current) return;
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

  const sortedItems = useMemo(() => {
    const collator = new Intl.Collator("zh-Hans-CN", {
      numeric: true,
      sensitivity: "base",
    });
    return [...items].sort((a, b) => {
      if (sortKey === "name") {
        const repoCompare = collator.compare(a.repo_path || "", b.repo_path || "");
        if (repoCompare !== 0) return repoCompare;
        return collator.compare(a.project_name || "", b.project_name || "");
      }
      const aTime = Number(a.last_commit_time);
      const bTime = Number(b.last_commit_time);
      const aValid = Number.isFinite(aTime);
      const bValid = Number.isFinite(bTime);
      if (aValid && bValid && bTime !== aTime) return bTime - aTime;
      if (aValid !== bValid) return aValid ? -1 : 1;
      return collator.compare(a.repo_path || "", b.repo_path || "");
    });
  }, [items, sortKey]);

  function SortIcon({ active, direction }) {
    return <span className="sort-icon" aria-hidden="true">{active ? direction : ""}</span>;
  }

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
              <th>
                <button
                  type="button"
                  className="sort-header"
                  aria-pressed={sortKey === "name"}
                  onClick={() => setSortKey("name")}
                >
                  仓库
                  <SortIcon active={sortKey === "name"} direction="▲" />
                </button>
              </th>
              <th>最近提交</th>
              <th>
                <button
                  type="button"
                  className="sort-header"
                  aria-pressed={sortKey === "time"}
                  onClick={() => setSortKey("time")}
                >
                  提交时间
                  <SortIcon active={sortKey === "time"} direction="▼" />
                </button>
              </th>
              <th className="repo-actions-col" aria-label="操作" />
            </tr>
          </thead>
          <tbody>
            {sortedItems.map((repo) => (
              <tr key={repo.repo_key}>
                <td>
                  <RepoPath projectName={repo.project_name} repoPath={repo.repo_path} />
                </td>
                <td className="commit-subject-cell">
                  <span className="commit-subject" title={repo.last_commit_subject || ""}>
                    {repo.last_commit_subject || "—"}
                  </span>
                </td>
                <td className="time-combined-cell">
                  <CommitTimeAge timestamp={repo.last_commit_time} />
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

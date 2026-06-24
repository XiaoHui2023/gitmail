import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchMe,
  fetchRepos,
  fetchStatus,
  fetchSubscribedRepos,
  subscribeRepo,
  unsubscribeRepo,
} from "../api.js";
import { CommitTimeAge, RepoPath } from "./RelativeTime.jsx";
import { RecentCommitCell } from "./RecentCommitCell.jsx";

const AGE_PRESETS = [
  { value: "", label: "提交时间：不限" },
  { value: "within:1d", label: "1 天内有提交" },
  { value: "within:7d", label: "7 天内有提交" },
  { value: "within:30d", label: "30 天内有提交" },
  { value: "older:7d", label: "超过 7 天未提交" },
  { value: "older:30d", label: "超过 30 天未提交" },
  { value: "older:90d", label: "超过 90 天未提交" },
  { value: "older:180d", label: "超过 180 天未提交" },
  { value: "older:365d", label: "超过 1 年未提交" },
  { value: "custom", label: "自定义…" },
];

const AGE_UNITS = [
  { value: "h", label: "小时" },
  { value: "d", label: "天" },
  { value: "w", label: "周" },
  { value: "m", label: "月" },
  { value: "y", label: "年" },
];

const DURATION_MULT = { h: 3600, d: 86400, w: 604800, m: 2592000, y: 31536000 };

function parseDurationToken(token) {
  const match = /^(\d+)([hdwmy])$/.exec(String(token || "").trim());
  if (!match) return null;
  const amount = Number(match[1]);
  if (!Number.isFinite(amount) || amount <= 0) return null;
  return amount * DURATION_MULT[match[2]];
}

function resolveAgeFilter(preset, customDirection, customValue, customUnit) {
  if (!preset) return null;
  if (preset === "custom") {
    const seconds = parseDurationToken(`${customValue}${customUnit}`);
    if (!seconds) return null;
    return { dir: customDirection, seconds };
  }
  const [dir, dur] = preset.split(":");
  const seconds = parseDurationToken(dur);
  if (!seconds || (dir !== "within" && dir !== "older")) return null;
  return { dir, seconds };
}

function matchesAgeFilter(repo, filter) {
  if (!filter) return true;
  const ts = Number(repo.last_commit_time);
  const now = Date.now() / 1000;
  if (!Number.isFinite(ts)) {
    return filter.dir === "older";
  }
  const age = now - ts;
  if (filter.dir === "within") return age <= filter.seconds;
  return age >= filter.seconds;
}

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

function RepoTableSkeleton({ rows = 8 }) {
  return (
    <table className="repo-table repo-table-skeleton" aria-hidden="true">
      <thead>
        <tr>
          <th>仓库</th>
          <th>最近提交</th>
          <th>提交时间</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: rows }, (_, i) => (
          <tr key={i}>
            <td><span className="skeleton-bar skeleton-bar-md" /></td>
            <td><span className="skeleton-bar skeleton-bar-lg" /></td>
            <td><span className="skeleton-bar skeleton-bar-sm" /></td>
            <td><span className="skeleton-bar skeleton-bar-xs" /></td>
          </tr>
        ))}
      </tbody>
    </table>
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
  const [agePreset, setAgePreset] = useState("");
  const [ageCustomDirection, setAgeCustomDirection] = useState("older");
  const [ageCustomValue, setAgeCustomValue] = useState("30");
  const [ageCustomUnit, setAgeCustomUnit] = useState("d");
  const [error, setError] = useState("");
  const [user, setUser] = useState(null);
  const [busyKey, setBusyKey] = useState("");
  const [sortKey, setSortKey] = useState("time");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [monitorRepoCount, setMonitorRepoCount] = useState(null);
  const requestSeqRef = useRef(0);
  const hasLoadedRef = useRef(false);

  const load = useCallback(async () => {
    const requestSeq = requestSeqRef.current + 1;
    requestSeqRef.current = requestSeq;
    const isInitial = !hasLoadedRef.current;
    if (isInitial) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }
    try {
      const params = {
        project: projectFilter.trim(),
        path: pathFilter.trim(),
      };
      const fetcher = mode === "subscribed" ? fetchSubscribedRepos : fetchRepos;
      const [repoData, me, status] = await Promise.all([
        fetcher(params),
        fetchMe().catch(() => null),
        fetchStatus().catch(() => null),
      ]);
      if (requestSeq !== requestSeqRef.current) return;
      setItems(repoData.items || []);
      setUser(me);
      if (status?.monitor?.last_round_repo_count != null) {
        setMonitorRepoCount(status.monitor.last_round_repo_count);
      }
      setError("");
      hasLoadedRef.current = true;
    } catch (err) {
      if (requestSeq !== requestSeqRef.current) return;
      setError(err.message);
      hasLoadedRef.current = true;
    } finally {
      if (requestSeq === requestSeqRef.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [mode, projectFilter, pathFilter]);

  useEffect(() => {
    load();
    const id = setInterval(load, Math.max(10, pollSeconds) * 1000);
    return () => clearInterval(id);
  }, [load, pollSeconds]);

  const ageFilter = useMemo(
    () => resolveAgeFilter(agePreset, ageCustomDirection, ageCustomValue, ageCustomUnit),
    [agePreset, ageCustomDirection, ageCustomValue, ageCustomUnit],
  );

  const showActions =
    user?.allowed && (showSubscribe || mode === "subscribed");

  const filteredItems = useMemo(
    () => items.filter((repo) => matchesAgeFilter(repo, ageFilter)),
    [items, ageFilter],
  );

  const sortedItems = useMemo(() => {
    const collator = new Intl.Collator("zh-Hans-CN", {
      numeric: true,
      sensitivity: "base",
    });
    return [...filteredItems].sort((a, b) => {
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
  }, [filteredItems, sortKey]);

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

  const showCustomAge = agePreset === "custom";
  const customAgeInvalid =
    showCustomAge && !parseDurationToken(`${ageCustomValue}${ageCustomUnit}`);

  let emptyMessage = null;
  if (!loading) {
    if (items.length === 0) {
      if (monitorRepoCount > 0) {
        emptyMessage = "正在同步仓库信息，请稍候…";
      } else {
        emptyMessage = mode === "subscribed" ? "暂无订阅的仓库" : "暂无监控仓库";
      }
    } else if (sortedItems.length === 0) {
      emptyMessage = "无符合提交时间条件的仓库";
    }
  }

  return (
    <section>
      <div className="page-title-row">
        <h1 className="page-title">{title}</h1>
        {refreshing && !loading ? (
          <span className="refresh-indicator" aria-live="polite">刷新中…</span>
        ) : null}
      </div>
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
        <select
          className="filter-select"
          value={agePreset}
          onChange={(e) => setAgePreset(e.target.value)}
          aria-label="按提交时间过滤"
        >
          {AGE_PRESETS.map((opt) => (
            <option key={opt.value || "all"} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {showCustomAge ? (
          <div className="age-custom-group" role="group" aria-label="自定义提交时间过滤">
            <select
              className="filter-select filter-select-narrow"
              value={ageCustomDirection}
              onChange={(e) => setAgeCustomDirection(e.target.value)}
              aria-label="过滤方向"
            >
              <option value="within">以内</option>
              <option value="older">超过</option>
            </select>
            <input
              className="filter-input-narrow"
              type="number"
              min="1"
              inputMode="numeric"
              value={ageCustomValue}
              onChange={(e) => setAgeCustomValue(e.target.value)}
              aria-label="时间数值"
              aria-invalid={customAgeInvalid}
            />
            <select
              className="filter-select filter-select-narrow"
              value={ageCustomUnit}
              onChange={(e) => setAgeCustomUnit(e.target.value)}
              aria-label="时间单位"
            >
              {AGE_UNITS.map((unit) => (
                <option key={unit.value} value={unit.value}>
                  {unit.label}
                </option>
              ))}
            </select>
            <span className="age-custom-hint">
              {ageCustomDirection === "within" ? "内有提交" : "未提交"}
            </span>
          </div>
        ) : null}
      </div>
      {!loading && items.length > 0 ? (
        <p className="filter-summary" aria-live="polite">
          显示 {sortedItems.length} / {items.length} 个仓库
        </p>
      ) : null}
      {loading ? (
        <div className="loading-panel" aria-busy="true" aria-label="正在加载仓库列表">
          <p className="loading-hint">正在加载仓库列表…</p>
          <RepoTableSkeleton />
        </div>
      ) : emptyMessage ? (
        <p className="empty">{emptyMessage}</p>
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
                <td className="repo-path-cell">
                  <RepoPath projectName={repo.project_name} repoPath={repo.repo_path} />
                </td>
                <td className="commit-subject-cell">
                  <RecentCommitCell repo={repo} />
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

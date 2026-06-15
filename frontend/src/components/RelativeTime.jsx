import { useEffect, useState } from "react";

function formatAbsolute(ts) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

function relativeLabel(ts) {
  if (!ts) return { text: "暂无", className: "age-stale" };
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  let text;
  if (seconds < 60) text = `${seconds} 秒前`;
  else if (seconds < 3600) text = `${Math.floor(seconds / 60)} 分钟前`;
  else if (seconds < 86400) text = `${Math.floor(seconds / 3600)} 小时前`;
  else text = `${Math.floor(seconds / 86400)} 天前`;

  let className = "age-stale";
  if (seconds < 3600) className = "age-fresh";
  else if (seconds < 86400) className = "age-day";
  else if (seconds < 604800) className = "age-week";
  return { text, className };
}

export default function RelativeTime({ timestamp }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 30000);
    return () => clearInterval(id);
  }, []);
  const rel = relativeLabel(timestamp);
  return (
    <div>
      <div>{formatAbsolute(timestamp)}</div>
      <div className={rel.className}>{rel.text}</div>
    </div>
  );
}

export function RepoPath({ projectName, repoPath }) {
  return (
    <span className="repo-path">
      {projectName}
      <span className="sep">&gt;</span>
      {repoPath.split("/").map((part, idx, arr) => (
        <span key={`${part}-${idx}`}>
          {part}
          {idx < arr.length - 1 ? <span className="sep">&gt;</span> : null}
        </span>
      ))}
    </span>
  );
}

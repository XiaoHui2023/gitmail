import { useEffect, useState } from "react";
import EllipsisTooltip from "./EllipsisTooltip.jsx";

function formatAbsolute(ts) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

function relativeLabel(ts) {
  if (!ts) return { text: "n/a", className: "age-stale" };
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  let text;
  if (seconds < 60) text = `${seconds}s`;
  else if (seconds < 3600) text = `${Math.floor(seconds / 60)}m`;
  else if (seconds < 86400) text = `${Math.floor(seconds / 3600)}h`;
  else if (seconds < 604800) text = `${Math.floor(seconds / 86400)}d`;
  else text = `${Math.floor(seconds / 604800)}w`;

  let className = "age-stale";
  let style;
  if (seconds < 3600) className = "age-fresh";
  else if (seconds < 86400) className = "age-day";
  else if (seconds < 604800) className = "age-week";
  if (seconds < 3600) {
    const freshWeight = Math.round(85 - (seconds / 3600) * 50);
    style = {
      color: `color-mix(in srgb, var(--age-fresh) ${freshWeight}%, var(--age-day))`,
    };
  }
  return { text, className, style };
}

function useRelativeTick() {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 30000);
    return () => clearInterval(id);
  }, []);
}

export function AbsoluteTime({ timestamp }) {
  return <span className="time-absolute">{formatAbsolute(timestamp)}</span>;
}

export function RelativeAge({ timestamp }) {
  useRelativeTick();
  const rel = relativeLabel(timestamp);
  return <span className={rel.className} style={rel.style}>{rel.text}</span>;
}

export function CommitTimeAge({ timestamp }) {
  useRelativeTick();
  const rel = relativeLabel(timestamp);
  return (
    <span className="commit-time-age">
      <span className="time-absolute">{formatAbsolute(timestamp)}</span>
      <span className={`time-age-separator ${rel.className}`} style={rel.style}>+</span>
      <span className={rel.className} style={rel.style}>{rel.text}</span>
    </span>
  );
}

export function RepoPath({ projectName, repoPath }) {
  const path = repoPath || "";
  const fullText = projectName ? `${projectName} > ${path}` : path || "—";

  return (
    <EllipsisTooltip text={fullText} className="repo-path-tooltip">
      <span className="repo-path">
        {projectName ? (
          <>
            {projectName}
            <span className="sep">&gt;</span>
          </>
        ) : null}
        {path.split("/").map((part, idx, arr) => (
          <span key={`${part}-${idx}`}>
            {part}
            {idx < arr.length - 1 ? <span className="sep">&gt;</span> : null}
          </span>
        ))}
      </span>
    </EllipsisTooltip>
  );
}

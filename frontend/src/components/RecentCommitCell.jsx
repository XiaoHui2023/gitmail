import EllipsisTooltip from "./EllipsisTooltip.jsx";

function AiPendingDot() {
  return <span className="ai-pending-dot" aria-label="AI 总结生成中" title="AI 总结生成中" />;
}

/**
 * 最近提交列：pending 时显示 commit 主题；ready 时显示 AI 总结。
 */
export function RecentCommitCell({ repo }) {
  const status = repo.ai_summary_status;
  const hasSummary = status === "ready" && repo.ai_summary;
  const pending = status === "pending";

  if (hasSummary) {
    return (
      <EllipsisTooltip text={repo.ai_summary} variant="ai" className="ai-summary-cell" />
    );
  }

  const subject = repo.last_commit_subject || "—";
  return (
    <span className="commit-fallback-wrap">
      {pending ? <AiPendingDot /> : null}
      <EllipsisTooltip text={subject} className="commit-subject-tooltip" />
    </span>
  );
}

import { useId, useRef, useState } from "react";

/**
 * 单行省略 + 悬停显示完整内容的提示框。
 */
export default function EllipsisTooltip({
  text,
  className = "",
  variant = "default",
}) {
  const tipId = useId();
  const cellRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [overflow, setOverflow] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });

  const display = text || "—";

  function refreshOverflow() {
    const el = cellRef.current;
    if (!el) return false;
    return el.scrollWidth > el.clientWidth + 1;
  }

  function showTip() {
    const clipped = refreshOverflow();
    setOverflow(clipped);
    if (!clipped && variant !== "ai") return;
    const el = cellRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setCoords({
      top: rect.bottom + 8,
      left: Math.min(rect.left, window.innerWidth - 420),
    });
    setOpen(true);
  }

  function hideTip() {
    setOpen(false);
  }

  const showPopup = open && (overflow || variant === "ai") && display !== "—";

  return (
    <span
      className={`ellipsis-tooltip-wrap ${className}`.trim()}
      onMouseEnter={showTip}
      onMouseLeave={hideTip}
      onFocus={showTip}
      onBlur={hideTip}
    >
      <span
        ref={cellRef}
        className={`ellipsis-tooltip-text ${variant === "ai" ? "ai-summary-text" : ""}`}
        tabIndex={0}
        aria-describedby={showPopup ? tipId : undefined}
      >
        {display}
      </span>
      {showPopup ? (
        <span
          id={tipId}
          role="tooltip"
          className="ellipsis-tooltip-popup"
          style={{ top: coords.top, left: coords.left }}
        >
          {display}
        </span>
      ) : null}
    </span>
  );
}

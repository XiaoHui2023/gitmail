export default function GitMailLogo({ className = "" }) {
  return (
    <span className={`app-brand ${className}`.trim()} aria-label="GitMail">
      <svg
        className="app-brand-icon"
        viewBox="0 0 32 32"
        width="28"
        height="28"
        aria-hidden="true"
      >
        <rect
          x="3"
          y="8"
          width="26"
          height="18"
          rx="3"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        />
        <path
          d="M3 11l13 9 13-9"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="24" cy="9" r="6.5" fill="var(--color-primary-bg)" />
        <path
          d="M24 6.5v5M21.5 9h5"
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="1.75"
          strokeLinecap="round"
        />
      </svg>
    </span>
  );
}

export default function GitMailMark({ className = "" }) {
  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      width="28"
      height="28"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="2" y="4" width="28" height="24" rx="6" fill="var(--color-accent)" />
      <path
        d="M6 11 L16 18 L26 11"
        fill="none"
        stroke="var(--color-on-accent)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M6 11 V21 C6 22.1 6.9 23 8 23 H24 C25.1 23 26 22.1 26 21 V11"
        fill="none"
        stroke="var(--color-on-accent)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="23" cy="9" r="4.5" fill="var(--color-primary-bg)" />
      <path
        d="M23 6.5 V11.5 M20.5 9 H25.5"
        stroke="var(--color-accent)"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

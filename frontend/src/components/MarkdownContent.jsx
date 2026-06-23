import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MarkdownContent({ text, className = "" }) {
  if (!text) return null;
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} className={className}>
      {text}
    </ReactMarkdown>
  );
}

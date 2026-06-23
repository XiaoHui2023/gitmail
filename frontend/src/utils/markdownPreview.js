/**
 * 将 Markdown 总结压缩为表格单元格中的一行预览文本。
 */
export function markdownPreview(text) {
  if (!text) return "";
  return text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*\d+\.\s+/gm, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^\s*>\s?/gm, "")
    .replace(/\s*\n+\s*/g, " · ")
    .trim();
}

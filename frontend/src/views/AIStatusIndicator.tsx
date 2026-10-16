import type { AIStatusKind } from "../models/ide";

interface Props {
  kind: AIStatusKind;
  text: string;
  detail: string;
  footer?: boolean;
}

export function AIStatusIndicator({ kind, text, detail, footer = false }: Props) {
  return (
    <span
      className={`ai-indicator ai-${kind} ${footer ? "ai-footer" : "local-status"}`}
      role="status"
      tabIndex={footer ? 0 : undefined}
      aria-label={`IA: ${text}. ${detail}`}
      title={footer ? undefined : detail}
      data-tooltip={detail}
    >
      <span className="ai-status-dot" aria-hidden="true" />
      <span>{footer ? `IA: ${text}` : text}</span>
    </span>
  );
}

import { useEffect, useRef, type ReactNode } from "react";

export function HoverMenu({ label, className, children }: {
  label: string;
  className?: string;
  children: ReactNode;
}) {
  const element = useRef<HTMLDetailsElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  function cancelClose() {
    clearTimeout(timer.current);
  }
  function close() {
    const menu = element.current;
    if (!menu) return;
    menu.open = false;
    menu.querySelectorAll("details[open]").forEach(item => item.removeAttribute("open"));
  }
  useEffect(() => () => cancelClose(), []);
  return (
    <details ref={element} className={className}
      onPointerEnter={event => {
        if (event.pointerType !== "mouse") return;
        cancelClose();
        const menu = event.currentTarget;
        for (const sibling of menu.parentElement?.children ?? []) {
          if (sibling !== menu && sibling instanceof HTMLDetailsElement) {
            sibling.removeAttribute("open");
            sibling.querySelectorAll("details[open]").forEach(item => item.removeAttribute("open"));
          }
        }
        menu.open = true;
      }}
      onPointerLeave={event => {
        if (event.pointerType !== "mouse") return;
        cancelClose();
        timer.current = setTimeout(close, 180);
      }}
      onBlur={event => {
        if (!event.currentTarget.contains(event.relatedTarget) && !event.currentTarget.matches(":hover")) {
          cancelClose();
          close();
        }
      }}>
      <summary onClick={event => {
        if (event.detail > 0 && event.currentTarget.parentElement?.matches(":hover")) {
          event.preventDefault();
          cancelClose();
          if (element.current) element.current.open = true;
        }
      }}>{label}</summary>
      {children}
    </details>
  );
}

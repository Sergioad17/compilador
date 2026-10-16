import { useState, type PointerEvent } from "react";
export function useLayoutController() {
  const [sizes, setSizes] = useState({ explorer: 220, chat: 310, bottom: 240 });
  function resize(name: keyof typeof sizes, event: PointerEvent<HTMLElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    const initial = { x: event.clientX, y: event.clientY, value: sizes[name] };
    const element = event.currentTarget;
    function move(event: globalThis.PointerEvent) {
      const delta =
        name === "bottom"
          ? initial.y - event.clientY
          : name === "chat"
            ? initial.x - event.clientX
            : event.clientX - initial.x;
      const max =
        name === "bottom"
          ? window.innerHeight * 0.65
          : window.innerWidth * 0.35;
      setSizes((value) => ({
        ...value,
        [name]: Math.max(
          name === "bottom" ? 140 : 160,
          Math.min(max, initial.value + delta),
        ),
      }));
    }
    function stop() {
      element.removeEventListener("pointermove", move);
      element.removeEventListener("pointerup", stop);
      element.removeEventListener("pointercancel", stop);
    }
    element.addEventListener("pointermove", move);
    element.addEventListener("pointerup", stop);
    element.addEventListener("pointercancel", stop);
  }
  return { sizes, resize };
}

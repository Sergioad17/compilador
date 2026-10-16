import { useEffect, useState } from "react";
import { closeWindow, minimizeWindow, observeMaximized, toggleMaximizeWindow } from "../services/window";
import { isTauri } from "@tauri-apps/api/core";

export function useWindowController() {
  const [maximized, setMaximized] = useState(false);
  useEffect(() => {
    let disposed = false;
    let stop: (() => void) | undefined;
    void observeMaximized(value => { if (!disposed) setMaximized(value); })
      .then(unlisten => { if (disposed) unlisten(); else stop = unlisten; })
      .catch(console.error);
    return () => { disposed = true; stop?.(); };
  }, []);
  return {
    native: isTauri(), maximized,
    minimize: () => { void minimizeWindow().catch(console.error); },
    maximize: () => { void toggleMaximizeWindow().catch(console.error); },
    close: () => { void closeWindow().catch(console.error); },
  };
}

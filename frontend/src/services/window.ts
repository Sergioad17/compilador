import { isTauri } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { Image } from "@tauri-apps/api/image";

export async function setWindowIcon(url: string) {
  if (!isTauri()) return;
  const image = await Image.fromBytes(
    new Uint8Array(await (await fetch(url)).arrayBuffer()),
  );
  try {
    await getCurrentWindow().setIcon(image);
  } finally {
    await image.close();
  }
}
export async function closeWindow() {
  if (isTauri()) await getCurrentWindow().close();
}
export async function minimizeWindow() {
  if (isTauri()) await getCurrentWindow().minimize();
}
export async function toggleMaximizeWindow() {
  if (isTauri()) await getCurrentWindow().toggleMaximize();
}
export async function observeMaximized(update: (value: boolean) => void) {
  if (!isTauri()) return () => {};
  const window = getCurrentWindow();
  const refresh = async () => update(await window.isMaximized());
  const unlisten = await window.onResized(() => { void refresh().catch(console.error); });
  try { await refresh(); } catch (error) { unlisten(); throw error; }
  return unlisten;
}

export async function guardWindowClose(
  canClose: () => Promise<boolean>,
  cleanup: () => Promise<void>,
) {
  if (!isTauri()) return () => {};
  let closing = false;
  return getCurrentWindow().onCloseRequested(async (event) => {
    event.preventDefault();
    if (closing) return;
    closing = true;
    try {
      if (await canClose()) {
        await cleanup();
        await getCurrentWindow().destroy();
      }
    } finally {
      closing = false;
    }
  });
}

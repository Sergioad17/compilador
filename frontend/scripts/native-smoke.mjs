import { chromium, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { join } from "node:path";

const browser = await chromium.connectOverCDP(
  process.env.MIEZEE_CDP || "http://127.0.0.1:9222",
);
const page = browser.contexts()[0].pages()[0];
const originalPreferences = await page.evaluate(() => localStorage.getItem("miezee.preferences"));
const failures = [];
page.on("pageerror", (error) => failures.push(error.message));
try {
  await page.waitForSelector(".monaco-editor");
  await expect(page.locator(".chat-pending")).toHaveCount(0, {
    timeout: 240000,
  });
  await expect(page.locator(".file-list button").first()).toBeVisible();
  await page.locator(".monaco-editor").click();
  await page.keyboard.press("Control+a");
  await page.keyboard.insertText(
    'a = input("Primer numero: ")\nb = input("Segundo numero: ")\nprint("Resultado:", int(a) + int(b))\nprint("Unicode: \\u00f1")',
  );
  await page
    .getByRole("button", { name: "Ejecutar (F6)", exact: true })
    .click();
  await expect(page.locator(".console-output")).toContainText(
    "Primer numero: ",
  );
  const input = page.getByRole("textbox", { name: "Entrada de consola" });
  await input.fill("1");
  await input.press("Enter");
  await expect(page.locator(".console-output")).toContainText(
    "Primer numero: 1\nSegundo numero: ",
  );
  await input.fill("2");
  await input.press("Enter");
  await expect(page.locator(".console-output")).toContainText(
    "Segundo numero: 2\nResultado: 3",
  );
  await expect(page.locator(".console-output")).toContainText(
    "Unicode: \u00f1",
  );
  console.log("Consola nativa: entrada, salida y Unicode OK");
  await page.locator(".monaco-editor").click();
  await page.keyboard.press("Control+a");
  await page.keyboard.insertText(
    'import tkinter as tk\nroot = tk.Tk()\nroot.title("Miezee verificacion")\ntk.Label(root, text="Pantalla real").pack()\nroot.after(4000, root.destroy)',
  );
  await page.keyboard.press("F7");
  await expect(page.locator(".statusbar")).toContainText("Ejecutando");
  const titles = execFileSync(
    "powershell.exe",
    [
      "-NoProfile",
      "-Command",
      "Get-Process -Name python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty MainWindowTitle",
    ],
    { encoding: "utf8" },
  );
  if (!titles.includes("Miezee verificacion"))
    throw new Error("No se detecto la ventana tkinter real");
  console.log("Vista previa nativa: ventana tkinter real OK");
  await expect(page.locator(".preview-view pre")).toContainText(
    "Proceso finalizado con codigo 0",
    { timeout: 10000 },
  );
  await page.locator(".monaco-editor").click();
  await page.keyboard.press("Control+a");
  await page.keyboard.press("Backspace");
  const composer = page.getByRole("textbox", { name: "Mensaje al asistente" });
  const previousReplies = await page.locator(".bubble.assistant").count();
  await composer.fill(
    "/GenerarFuncion crea una funcion Python que reciba un numero y devuelva su doble",
  );
  await composer.press("Enter");
  await expect(page.locator(".bubble.assistant")).toHaveCount(
    previousReplies + 1,
    { timeout: 240000 },
  );
  await expect(page.locator(".bubble.assistant").last()).toContainText(
    "Codigo validado y enviado al editor",
    { timeout: 240000 },
  );
  await expect(page.locator(".monaco-editor .view-lines")).toContainText(
    "def ",
  );
  await expect(page.locator(".monaco-editor .view-lines")).not.toContainText(
    "import tkinter",
  );
  await expect(page.locator(".bubble.assistant").last()).not.toContainText(
    "def ",
  );
  console.log("Ollama real: generacion validada al editor OK");
  if (process.env.MIEZEE_CAPTURE_DIR)
    await page.screenshot({
      path: join(process.env.MIEZEE_CAPTURE_DIR, "native-default.png"),
    });
  await page
    .locator(".menubar > details")
    .filter({ has: page.locator("summary", { hasText: /^Editar$/ }) })
    .locator(":scope > summary")
    .click();
  await page.locator(".theme-submenu > summary").click();
  await page
    .getByRole("menuitemradio", { name: "Morado", exact: true })
    .click();
  await page.keyboard.press("Escape");
  if (process.env.MIEZEE_CAPTURE_DIR)
    await page.screenshot({
      path: join(process.env.MIEZEE_CAPTURE_DIR, "native-purple.png"),
    });
  if (failures.length) throw new Error(failures.join("\n"));
  console.log("Tema e iconos: sin errores de JavaScript");
} finally {
  await page.evaluate(value => { if (value === null) localStorage.removeItem("miezee.preferences"); else localStorage.setItem("miezee.preferences", value); }, originalPreferences);
  await browser.close();
}

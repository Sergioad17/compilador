import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  let inputCount = 0;
  let pending = "";
  let running = false;
  const clean = {
    ok: true,
    errors: [],
    symbols: [
      { name: "sumar", type: "Funcion", line: 1, kind: "funcion python" },
    ],
    rules: ["PY01", "PY02"],
  };
  await page.exposeFunction(
    "nativeInvoke",
    async (command: string, args: Record<string, string>) => {
      if (command === "plugin:window|is_maximized") return false;
      if (command === "list_files")
        return {
          root: "C:/examples",
          files: [{ name: "sumas.py", path: "C:/examples/sumas.py" }],
        };
      if (command === "read_file")
        return {
          id: "C:/examples/sumas.py",
          path: "C:/examples/sumas.py",
          name: "sumas.py",
          source: "def sumar(a, b):\n    return a + b\n",
        };
      if (command === "python_request") {
        if (args.operation === "analyze") return clean;
        if (args.operation === "translate")
          return { translation: "FUNCION sumar RETORNA DECIMAL" };
        if (args.operation === "status")
          return { available: true, text: "Corre localmente" };
        if (args.operation === "chat")
          return {
            text: "**Codigo aplicado.** __Verificado__",
            code: "print('generado')",
          };
      }
      if (command === "start_program") {
        running = true;
        pending = "Primer numero: ";
        inputCount = 0;
        return { started: true, analysis: clean };
      }
      if (command === "poll_program") {
        const text = pending;
        pending = "";
        return {
          chunks: [
            {
              stream: "stdout",
              bytes: Array.from(new TextEncoder().encode(text)),
            },
          ],
          running,
          exitCode: running ? null : 0,
        };
      }
      if (command === "program_input") {
        inputCount++;
        pending = inputCount === 1 ? "Segundo numero: " : "Resultado: 3\n";
        if (inputCount === 2) running = false;
        return null;
      }
      if (command === "stop_program") {
        running = false;
        return null;
      }
      if (command === "confirm_close") return true;
      if (command === "save_file")
        return {
          id: "saved",
          path: "C:/examples/guardado.py",
          name: "guardado.py",
          source: args.source,
        };
      return 1;
    },
  );
  await page.addInitScript(() => {
    const host = window as unknown as {
      isTauri: boolean;
      __TAURI_INTERNALS__: unknown;
      nativeInvoke: (command: string, args: object) => Promise<unknown>;
    };
    host.isTauri = true;
    const calls: string[] = [];
    (window as unknown as { windowCalls: string[] }).windowCalls = calls;
    host.__TAURI_INTERNALS__ = {
      metadata: { currentWindow: { label: "main" }, currentWebview: { label: "main" } },
      invoke: (command: string, args: object) => {
        calls.push(command);
        return host.nativeInvoke(command, args);
      },
      transformCallback: () => 1,
      unregisterCallback: () => {},
    };
  });
  await page.goto("/");
});

test("opens examples, analyzes and translates the active document", async ({
  page,
}) => {
  await page.getByRole("button", { name: "sumas.py", exact: true }).click();
  await expect(page.locator(".tab.active")).toContainText("sumas.py");
  await page
    .getByRole("button", { name: "Analizar (F5)", exact: true })
    .click();
  await expect(page.getByText("Sin errores detectados.")).toBeVisible();
  await page
    .getByRole("button", { name: "Tabla de simbolos", exact: true })
    .click();
  await expect(
    page.getByRole("cell", { name: "sumar", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Traducir (F9)", exact: true })
    .click();
  await expect(page.locator(".panel-content pre")).toContainText(
    "FUNCION sumar",
  );
});

test("Default uses neutral surfaces and accents", async ({ page }) => {
  await expect(page.locator(".app-header")).toHaveCSS("background-color", "rgb(36, 36, 36)");
  await expect(page.locator(".statusbar")).toHaveCSS("background-color", "rgb(37, 37, 37)");
  await expect(page.locator(".tab.active")).toHaveCSS("border-top-color", "rgb(168, 168, 168)");
  await expect(page.locator(".bubble.assistant").first()).toHaveCSS("background-color", "rgb(53, 53, 53)");
});

test("integrated window buttons invoke native window controls", async ({ page }) => {
  await page.getByRole("button", { name: "Minimizar", exact: true }).click();
  await page.getByRole("button", { name: "Maximizar", exact: true }).click();
  await page.getByRole("button", { name: "Cerrar ventana", exact: true }).click();
  const calls = await page.evaluate(() => (window as unknown as { windowCalls: string[] }).windowCalls);
  expect(calls).toContain("plugin:window|minimize");
  expect(calls).toContain("plugin:window|toggle_maximize");
  expect(calls).toContain("plugin:window|close");
  await expect(page.locator(".window-drag-space")).toHaveAttribute("data-tauri-drag-region", "true");
});

test("menus open on hover and close when the pointer leaves", async ({ page }) => {
  const menus = page.locator(".menubar > details");
  const file = menus.filter({ has: page.locator("summary", { hasText: /^Archivo$/ }) });
  const edit = menus.filter({ has: page.locator("summary", { hasText: /^Editar$/ }) });
  await file.locator(":scope > summary").hover();
  await expect(file).toHaveAttribute("open", "");
  await file.locator(".menu button").first().hover();
  await expect(file).toHaveAttribute("open", "");
  await edit.locator(":scope > summary").hover();
  await expect(file).not.toHaveAttribute("open", "");
  await expect(edit).toHaveAttribute("open", "");
  await page.locator(".theme-submenu > summary").hover();
  await expect(page.locator(".theme-submenu")).toHaveAttribute("open", "");
  await page.locator(".header-tools").hover();
  await expect(menus.locator("[open]")).toHaveCount(0);
  await expect(edit).not.toHaveAttribute("open", "");
});

test("hover menus allow repeated submenu selections and brief pointer exits", async ({ page }) => {
  const edit = page.locator(".menubar > details").filter({ has: page.locator("summary", { hasText: /^Editar$/ }) });
  for (const theme of ["Morado", "Default", "Morado", "Default"]) {
    await edit.locator(":scope > summary").hover();
    await page.locator(".theme-submenu > summary").hover();
    const choice = page.getByRole("menuitemradio", { name: theme, exact: true });
    await choice.hover();
    await choice.click();
    if (theme === "Morado") await expect(page.locator(".app-shell")).toHaveClass(/theme-purple/);
    else await expect(page.locator(".app-shell")).not.toHaveClass(/theme-purple/);
    await page.locator(".header-tools").hover();
    await expect(edit).not.toHaveAttribute("open", "");
  }
  await edit.locator(":scope > summary").hover();
  await page.mouse.move(1, 1);
  await edit.locator(".menu button").first().hover();
  await expect(edit).toHaveAttribute("open", "");
  await page.locator(".header-tools").hover();
  await expect(edit).not.toHaveAttribute("open", "");
});

test("saving onto an open file leaves a single target tab", async ({ page }) => {
  await page.getByRole("button", { name: "sumas.py", exact: true }).click();
  await expect(page.locator(".tab.active")).toContainText("sumas.py");
  await expect(page.locator(".monaco-editor .view-lines")).toContainText("def sumar");
  await page.locator(".monaco-editor").click();
  await page.keyboard.press("Control+s");
  await expect(page.locator(".tab.active")).toContainText("guardado.py");
  await page.locator(".tab").first().getByRole("button").first().click();
  await page.locator(".monaco-editor").click();
  await page.keyboard.insertText("print(2)");
  await page.keyboard.press("Control+Shift+s");
  await expect(page.locator(".tab")).toHaveCount(1);
  await expect(page.locator(".tab.active")).toContainText("guardado.py");
  await expect(page.locator(".monaco-editor .view-lines")).toContainText("print(2)");
});

test("console input and output remain on separate lines", async ({ page }) => {
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
    "Proceso finalizado con codigo 0",
  );
});

test("slash generation applies code to editor and renders message formatting", async ({
  page,
}) => {
  const composer = page.getByRole("textbox", { name: "Mensaje al asistente" });
  await composer.fill("/Generar");
  await expect(
    page.getByRole("option", { name: "/GenerarPantalla", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("option", { name: "/GenerarPantalla", exact: true })
    .click();
  await composer.fill("/GenerarPantalla una pantalla simple");
  await composer.press("Enter");
  await expect(page.locator(".bubble.assistant strong")).toContainText(
    "Codigo aplicado.",
  );
  await expect(page.locator(".bubble.assistant u")).toContainText("Verificado");
  await expect(page.locator(".bubble.user").last()).toHaveCSS("align-self", "flex-end");
  await expect(page.locator(".bubble.assistant").last()).toHaveCSS("align-self", "flex-start");
  await expect(page.locator(".bubble.assistant").last()).not.toContainText(
    "print",
  );
  await expect(page.locator(".monaco-editor .view-lines")).toContainText(
    "generado",
  );
});

test("themes and visibility controls work", async ({ page }) => {
  await page
    .locator(".menubar > details")
    .filter({ has: page.locator("summary", { hasText: /^Editar$/ }) })
    .locator(":scope > summary")
    .click();
  await page.locator(".theme-submenu > summary").click();
  await page
    .getByRole("menuitemradio", { name: "Morado", exact: true })
    .click();
  await expect(page.locator(".app-shell")).toHaveClass(/theme-purple/);
  await expect(page.locator(".bubble.assistant").first()).toHaveCSS("box-shadow", "none");
  await expect(page.locator(".statusbar")).toHaveCSS("background-color", "rgb(36, 34, 38)");
  await expect(page.locator(".tab.active")).toHaveCSS("border-top-color", "rgb(166, 139, 199)");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Explorador", exact: true }).click();
  await expect(page.locator(".sidebar")).toBeHidden();
  await page.keyboard.press("Control+Shift+P");
  await expect(
    page.getByRole("dialog", { name: "Paleta de comandos" }),
  ).toBeVisible();
});

test("long conversations stay inside the chat and editor shortcuts work", async ({ page }) => {
  const composer = page.getByRole("textbox", { name: "Mensaje al asistente" });
  for (let index = 0; index < 8; index++) {
    const replies = await page.locator(".bubble.assistant").count();
    await composer.fill("crea una funcion " + index);
    await composer.press("Enter");
    await expect(page.locator(".bubble.assistant")).toHaveCount(replies + 1);
  }
  const bounds = await page.locator(".chat-composer").boundingBox();
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(820);
  expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBeLessThanOrEqual(820);
  await page.locator(".monaco-editor").click();
  await page.keyboard.press("Control+j");
  await expect(page.locator(".bottom-panel")).toBeHidden();
  await page.keyboard.press("Control+j");
  await expect(page.locator(".bottom-panel")).toBeVisible();
  await page.keyboard.press("Control+s");
  await expect(page.locator(".tab.active")).toContainText("guardado.py");
  await expect(page.locator(".tab.active")).not.toContainText(" *");
});

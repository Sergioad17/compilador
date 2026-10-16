import { spawn } from "node:child_process";
import { rmSync } from "node:fs";
import { join, resolve, sep } from "node:path";

const root = resolve(process.cwd());
const artifacts = resolve(root, "test-results");
if (!artifacts.startsWith(root + sep)) throw new Error("Ruta de pruebas fuera del proyecto.");
const child = spawn(process.execPath, [join(root, "node_modules", "@playwright", "test", "cli.js"), "test"], { stdio: "inherit" });
child.on("close", code => { rmSync(artifacts, { recursive: true, force: true }); console.log("Archivos temporales de pruebas eliminados."); process.exit(code ?? 1); });
child.on("error", error => { console.error(error); rmSync(artifacts, { recursive: true, force: true }); process.exit(1); });
process.on("SIGINT", () => child.kill("SIGINT"));

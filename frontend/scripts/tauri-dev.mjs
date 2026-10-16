import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join, delimiter } from "node:path";
import { createServer } from "node:net";

const cargo = join(
  process.env.USERPROFILE || process.env.HOME || "",
  ".cargo",
  "bin",
);
const env = {
  ...process.env,
  PATH: `${cargo}${delimiter}${process.env.PATH || ""}`,
};
const cli = join(
  process.cwd(),
  "node_modules",
  "@tauri-apps",
  "cli",
  "tauri.js",
);
if (!existsSync(cli))
  throw new Error("Ejecuta npm install en frontend primero.");
let port = 5173;
for (; port < 5190; port++) {
  const available = await new Promise((resolve) => {
    const server = createServer();
    server.once("error", () => resolve(false));
    server.listen(port, "127.0.0.1", () => server.close(() => resolve(true)));
  });
  if (available) break;
}
if (port === 5190) throw new Error("No hay un puerto libre para el frontend.");
const config = JSON.stringify({ build: {
  beforeDevCommand: `npm run dev -- --host 127.0.0.1 --port ${port} --strictPort`,
  devUrl: `http://127.0.0.1:${port}`,
} });
const child = spawn(process.execPath, [cli, "dev", "--config", config], { env, stdio: "inherit" });
child.on("exit", (code) => process.exit(code ?? 1));
process.on("SIGINT", () => child.kill("SIGINT"));

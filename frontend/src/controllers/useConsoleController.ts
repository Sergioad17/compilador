import { useEffect, useRef, useState } from "react";
import { backend } from "../services/backend";

export function useConsoleController(onError: (text: string) => void) {
  const [output, setOutput] = useState("");
  const [running, setRunning] = useState(false);
  const [starting, setStarting] = useState(false);
  const decoder = useRef({
    stdout: new TextDecoder("utf-8"),
    stderr: new TextDecoder("utf-8"),
  });
  const append = (text: string) =>
    setOutput((value) => (value + text).slice(-200000));
  useEffect(() => {
    if (!running) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const data = await backend.poll();
        if (disposed) return;
        for (const chunk of data.chunks)
          append(
            decoder.current[chunk.stream].decode(new Uint8Array(chunk.bytes), {
              stream: true,
            }),
          );
        if (!data.running)
          append(
            decoder.current.stdout.decode() + decoder.current.stderr.decode(),
          );
        if (!data.running) {
          setRunning(false);
          append(
            `\n[Proceso finalizado con codigo ${data.exitCode ?? "desconocido"}]\n`,
          );
        } else timer = setTimeout(poll, 80);
      } catch (error) {
        if (!disposed) {
          setRunning(false);
          onError(String(error));
        }
      }
    }
    void poll();
    return () => {
      disposed = true;
      clearTimeout(timer);
    };
  }, [running]);
  async function start(source: string, cwd?: string) {
    if (starting) return null;
    setStarting(true);
    try {
      await backend.stop();
      setRunning(false);
      const result = await backend.start(source, cwd);
      decoder.current = {
        stdout: new TextDecoder("utf-8"),
        stderr: new TextDecoder("utf-8"),
      };
      setOutput(
        result.started
          ? "> Ejecutando codigo actual\n"
          : "No se puede ejecutar: corrige los errores del analizador.\n",
      );
      setRunning(result.started);
      return result.analysis;
    } catch (error) {
      onError(String(error));
      return null;
    } finally {
      setStarting(false);
    }
  }
  async function input(text: string) {
    try {
      // Echo before sending so the next output cannot overlap submitted input.
      append(`${output.endsWith("\n") ? "> " : ""}${text}\n`);
      await backend.input(text);
    } catch (error) {
      onError(String(error));
    }
  }
  async function stop() {
    try {
      await backend.stop();
      setRunning(false);
      append("\n[Proceso detenido]\n");
    } catch (error) {
      onError(String(error));
    }
  }
  return {
    output,
    running,
    starting,
    start,
    input,
    stop,
    clear: () => setOutput(""),
  };
}

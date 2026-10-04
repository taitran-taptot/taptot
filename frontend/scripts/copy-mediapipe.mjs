import { copyFile, mkdir, access, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const wasmSrc = path.join(root, "node_modules", "@mediapipe", "tasks-vision", "wasm");
const wasmDest = path.join(root, "public", "mediapipe", "wasm");
const modelDest = path.join(root, "public", "mediapipe", "pose_landmarker_lite.task");
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";
const WASM_FILES = [
  "vision_wasm_internal.js",
  "vision_wasm_internal.wasm",
  "vision_wasm_nosimd_internal.js",
  "vision_wasm_nosimd_internal.wasm",
];

async function exists(file) {
  try {
    await access(file);
    return true;
  } catch {
    return false;
  }
}

await mkdir(wasmDest, { recursive: true });
for (const name of WASM_FILES) {
  await copyFile(path.join(wasmSrc, name), path.join(wasmDest, name));
}

if (!(await exists(modelDest))) {
  const res = await fetch(MODEL_URL);
  if (!res.ok) {
    throw new Error(`Failed to download pose model: HTTP ${res.status}`);
  }
  await writeFile(modelDest, Buffer.from(await res.arrayBuffer()));
}

console.log("Copied MediaPipe pose assets to public/mediapipe");

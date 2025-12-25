import fs from "node:fs";
import path from "node:path";

const projectRoot = path.resolve(process.cwd());
const srcRoot = path.join(projectRoot, "src");
const i18nFile = path.join(srcRoot, "lib", "i18n.ts");

function readText(p) {
  return fs.readFileSync(p, "utf8");
}

function listFiles(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === ".next" || entry.name === "node_modules") continue;
      out.push(...listFiles(p));
    } else {
      if (p.endsWith(".ts") || p.endsWith(".tsx")) out.push(p);
    }
  }
  return out;
}

// Best-effort extraction of translation keys from src/lib/i18n.ts (resources object).
// This is intentionally strict enough for CI gating, but not a full TS parser.
function extractTranslationKeysFromI18nTs() {
  const content = readText(i18nFile);
  const start = content.indexOf("const resources =");
  if (start === -1) {
    throw new Error("resources object not found in src/lib/i18n.ts");
  }

  // Find the opening "{" after const resources =
  const openIdx = content.indexOf("{", start);
  if (openIdx === -1) throw new Error("resources object open brace not found");

  // Naive brace matching to isolate the object literal.
  let depth = 0;
  let endIdx = -1;
  for (let i = openIdx; i < content.length; i++) {
    const ch = content[i];
    if (ch === "{") depth++;
    if (ch === "}") {
      depth--;
      if (depth === 0) {
        endIdx = i;
        break;
      }
    }
  }
  if (endIdx === -1) throw new Error("resources object could not be bounded");

  const objText = content.slice(openIdx, endIdx + 1);
  // Convert TS "as const" away if it exists (we cut before it anyway)
  const jsonish = objText
    // Remove comments
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|\n)\s*\/\/.*$/gm, "")
    // Remove trailing commas
    .replace(/,\s*([}\]])/g, "$1");

  // We cannot parse TS object safely; instead we scan for quoted keys in t("...") usage
  // and ensure they exist under at least one locale. We'll build a flat set of keys by
  // scanning for "translation: {" blocks and collecting nested keys.

  const keySet = new Set();
  // Collect dot-notation keys by walking a simplified JSON parse of each locale.translation.
  // Try to eval in a sandbox-ish way using Function.
  // eslint-disable-next-line no-new-func
  const resourcesObj = Function(`"use strict"; return (${jsonish});`)();
  for (const locale of Object.keys(resourcesObj)) {
    const translation = resourcesObj[locale]?.translation;
    if (!translation) continue;
    walkKeys("", translation, keySet);
  }
  return keySet;
}

function walkKeys(prefix, obj, set) {
  if (!obj || typeof obj !== "object") return;
  for (const [k, v] of Object.entries(obj)) {
    const next = prefix ? `${prefix}.${k}` : k;
    set.add(next);
    walkKeys(next, v, set);
  }
}

function extractUsedTranslationKeys() {
  const files = listFiles(srcRoot);
  const used = new Set();

  const tCall = /\bt\(\s*(["'`])([^"'`]+)\1/g;

  for (const file of files) {
    const text = readText(file);
    let m;
    while ((m = tCall.exec(text))) {
      const key = m[2];
      // Ignore dynamic keys
      if (key.includes("${") || key.includes("`")) continue;
      used.add(key);
    }
  }
  return used;
}

const availableKeys = extractTranslationKeysFromI18nTs();
const usedKeys = extractUsedTranslationKeys();

const missing = [...usedKeys].filter((k) => !availableKeys.has(k));
missing.sort();

if (missing.length) {
  console.error(`Missing i18n keys: ${missing.length}`);
  for (const k of missing.slice(0, 200)) {
    console.error(` - ${k}`);
  }
  process.exit(1);
}

console.log(`i18n OK (${usedKeys.size} keys used, ${availableKeys.size} keys available)`);


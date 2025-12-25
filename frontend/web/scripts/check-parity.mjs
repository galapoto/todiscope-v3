import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const DEFAULT_BASE_URL = "http://localhost:8400";
const DEFAULT_REGISTRY_PATH = path.join(process.cwd(), "src", "engines", "registry.ts");

function readArg(flag, fallback) {
  const idx = process.argv.indexOf(flag);
  if (idx === -1) return fallback;
  const value = process.argv[idx + 1];
  if (!value || value.startsWith("--")) return fallback;
  return value;
}

const baseUrl = readArg("--base", DEFAULT_BASE_URL).replace(/\/+$/, "");
const apiKey = readArg("--api-key", process.env.NEXT_PUBLIC_API_KEY || "");
const registryPath = readArg("--registry", DEFAULT_REGISTRY_PATH);

function backendEngineIdToSlug(engineId) {
  const overrides = {
    engine_construction_cost_intelligence: "cost-intelligence",
    engine_enterprise_litigation_dispute: "litigation-analysis",
  };
  if (overrides[engineId]) return overrides[engineId];
  if (!engineId.startsWith("engine_")) return null;
  return engineId.slice("engine_".length).replaceAll("_", "-");
}

async function fetchJson(urlPath) {
  const response = await fetch(`${baseUrl}${urlPath}`, {
    headers: apiKey ? { "X-API-Key": apiKey } : {},
  });
  const text = await response.text();
  let json = null;
  try {
    json = JSON.parse(text);
  } catch {
    json = null;
  }
  return { ok: response.ok, status: response.status, json, text };
}

async function probe(urlPath) {
  try {
    const response = await fetch(`${baseUrl}${urlPath}`, {
      method: "GET",
      headers: apiKey ? { "X-API-Key": apiKey } : {},
    });
    const status = response.status;
    return { status, exists: status !== 404, ok: response.ok };
  } catch (error) {
    return {
      status: 0,
      exists: false,
      ok: false,
      error: error instanceof Error ? error.message : "Network error",
    };
  }
}

function parseFrontendEngineIds(sourceText) {
  const startIdx = sourceText.indexOf("export const engineRegistry");
  if (startIdx === -1) {
    throw new Error("Could not locate `export const engineRegistry` in registry.ts");
  }
  const slice = sourceText.slice(startIdx);
  const objectStart = slice.indexOf("{");
  const objectEnd = slice.indexOf("};");
  if (objectStart === -1 || objectEnd === -1 || objectEnd <= objectStart) {
    throw new Error("Could not parse engineRegistry object literal boundaries in registry.ts");
  }
  const objectBody = slice.slice(objectStart + 1, objectEnd);

  const ids = new Set();
  const keyRegex = /^\s*["']([^"']+)["']\s*:\s*\{/gm;
  let match;
  while ((match = keyRegex.exec(objectBody))) {
    ids.add(match[1]);
  }
  return [...ids].sort();
}

function setDiff(a, b) {
  const missing = [];
  for (const item of a) {
    if (!b.has(item)) missing.push(item);
  }
  return missing;
}

async function main() {
  const registryText = fs.readFileSync(registryPath, "utf8");
  const frontendEngineIds = parseFrontendEngineIds(registryText);
  const frontendSet = new Set(frontendEngineIds);

  const enabled = await fetchJson("/api/v3/engine-registry/enabled");
  if (!enabled.ok || !enabled.json?.enabled_engines) {
    console.error(
      `Failed to read enabled engines from ${baseUrl}/api/v3/engine-registry/enabled (status ${enabled.status})`
    );
    process.exit(2);
  }

  const backendSlugs = (enabled.json.enabled_engines || [])
    .map(backendEngineIdToSlug)
    .filter((id) => Boolean(id));
  const backendSet = new Set(backendSlugs);

  console.log(`Backend: ${baseUrl}`);
  console.log(`Frontend engines (registry): ${frontendEngineIds.length}`);
  console.log(`Backend engines (enabled): ${backendSlugs.length}`);

  const missingInFrontend = setDiff(backendSlugs, frontendSet);
  const missingInBackend = setDiff(frontendEngineIds, backendSet);

  if (missingInFrontend.length) {
    console.error("\nFAIL: backend engines missing from frontend registry:");
    for (const id of missingInFrontend) console.error(`- ${id}`);
  }

  if (missingInBackend.length) {
    console.warn("\nWARN: frontend registry contains engines not enabled in backend:");
    for (const id of missingInBackend) console.warn(`- ${id}`);
  }

  // Probe run endpoint for each backend-enabled engine; ensure non-404 so UI doesn't dead-end.
  let missingEndpoints = 0;
  for (const engineId of backendSlugs) {
    const run = await probe(`/api/v3/engines/${engineId}/run`);
    if (!run.exists) {
      missingEndpoints += 1;
      console.error(`❌ ${engineId}: /run missing (404)`);
    } else if (!run.ok) {
      console.log(`⚠️ ${engineId}: /run exists (${run.status})`);
    } else {
      console.log(`✅ ${engineId}: /run ok (${run.status})`);
    }
  }

  if (missingInFrontend.length || missingEndpoints) {
    console.error(
      `\nFAIL: parity check failed (${missingInFrontend.length} missing engines, ${missingEndpoints} missing endpoints).`
    );
    process.exit(1);
  }

  console.log("\nOK: backend-enabled engines are represented in frontend registry and have non-404 run endpoints.");
}

main().catch((err) => {
  console.error(err);
  process.exit(2);
});


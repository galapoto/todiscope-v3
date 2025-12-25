import fs from "node:fs";
import path from "node:path";

function bytes(n) {
  return `${(n / 1024).toFixed(1)}KB`;
}

const root = path.resolve(process.cwd());
const chunksDir = path.join(root, ".next", "static", "chunks");

if (!fs.existsSync(chunksDir)) {
  console.log("No .next/static/chunks found. Run `npm run build` first.");
  process.exit(0);
}

const files = fs
  .readdirSync(chunksDir)
  .filter((f) => f.endsWith(".js"))
  .map((f) => ({ file: f, size: fs.statSync(path.join(chunksDir, f)).size }))
  .sort((a, b) => b.size - a.size);

const total = files.reduce((sum, f) => sum + f.size, 0);
console.log(`chunks: ${files.length}`);
console.log(`total js: ${bytes(total)}`);

console.log("top 10:");
for (const entry of files.slice(0, 10)) {
  console.log(` - ${bytes(entry.size)} ${entry.file}`);
}

const limitMb = Number(process.env.BUNDLE_WARN_MB ?? "2.5");
const limitBytes = limitMb * 1024 * 1024;
if (total > limitBytes) {
  console.warn(`WARN: total chunk JS exceeds ${limitMb}MB`);
  process.exit(0);
}

console.log("bundle size OK");


import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const packageRoot = resolve(import.meta.dirname, "..");
const repositoryRoot = resolve(packageRoot, "../..");
const contractPath = join(
  repositoryRoot,
  "docs",
  "levels_product_handoff",
  "levels_product_handoff",
  "05_OPENAPI.yaml",
);
const generatedPath = join(packageRoot, "src", "schema.ts");
const temporaryDirectory = mkdtempSync(join(tmpdir(), "levels-openapi-"));
const temporaryOutput = join(temporaryDirectory, "schema.ts");
const generatorScript = join(
  repositoryRoot,
  "node_modules",
  "openapi-typescript",
  "bin",
  "cli.js",
);

try {
  const result = spawnSync(
    process.execPath,
    [generatorScript, contractPath, "-o", temporaryOutput],
    { cwd: repositoryRoot, encoding: "utf8" },
  );

  if (result.status !== 0) {
    process.stderr.write(result.stderr || result.stdout || "OpenAPI generation failed.\n");
    process.exit(result.status ?? 1);
  }

  if (!existsSync(generatedPath)) {
    console.error("Generated API schema is missing. Run `npm run openapi:generate`.");
    process.exit(1);
  }

  if (readFileSync(generatedPath, "utf8") !== readFileSync(temporaryOutput, "utf8")) {
    console.error("Generated API schema is stale. Run `npm run openapi:generate`.");
    process.exit(1);
  }

  console.log("Generated API schema matches the authoritative OpenAPI contract.");
} finally {
  rmSync(temporaryDirectory, { force: true, recursive: true });
}

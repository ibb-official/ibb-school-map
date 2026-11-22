#!/usr/bin/env node
/**
 * Optimizes generated campus GLB files via @gltf-transform (dedup + prune + weld)
 * while strictly preserving all W-* / E-* node names and material names required
 * by `CampusScene3D.tsx` and `pbrMaterialSystem.ts`.
 */

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCRATCH_ROOT =
  process.env.BUILD_SCRATCH_ROOT || path.join(process.env.HOME || "/tmp", ".build");
const TOOLS_NM = path.join(SCRATCH_ROOT, "校园地图/tools/node_modules");

const require = createRequire(import.meta.url);
const { NodeIO, PropertyType } = require(path.join(TOOLS_NM, "@gltf-transform/core"));
const { KHRMeshQuantization } = require(path.join(TOOLS_NM, "@gltf-transform/extensions"));
const { dedup, prune, quantize, weld } = require(path.join(TOOLS_NM, "@gltf-transform/functions"));

async function optimizeOne(filePath, preservePositions = false) {
  if (!fs.existsSync(filePath)) return;
  const before = fs.statSync(filePath).size;
  const io = new NodeIO().registerExtensions([KHRMeshQuantization]);
  const doc = await io.read(filePath);
  const steps = [
    // Deduplicate accessors/textures/meshes ONLY — never merge distinct named materials (e.g. IntLight buckets)
    dedup({ propertyTypes: [PropertyType.ACCESSOR, PropertyType.MESH, PropertyType.TEXTURE] }),
    weld({ tolerance: 1e-4 }),
    prune({ keepAttributes: true, keepLeaves: true }),
  ];
  if (preservePositions) {
    // Classic mode: keep POSITION as lossless FLOAT32 (zero 14-bit quantization snapping!)
    // while packing NORMAL/TEXCOORD_0/COLOR_0 compactly under KHR_mesh_quantization.
    doc.createExtension(KHRMeshQuantization).setRequired(true);
    steps.push(
      quantize({
        pattern: /^(NORMAL|TEXCOORD_0|COLOR_0)$/,
        quantizeNormal: 8,
        quantizeTexcoord: 12,
        quantizeColor: 8,
      })
    );
  } else {
    steps.push(
      quantize({
        quantizePosition: 14,
        quantizeNormal: 10,
        quantizeTexcoord: 12,
        quantizeColor: 8,
      })
    );
  }
  await doc.transform(...steps);
  await io.write(filePath, doc);
  const after = fs.statSync(filePath).size;
  const pct = ((1 - after / before) * 100).toFixed(1);
  console.log(
    `[optimize_glb${preservePositions ? ":float32-pos" : ""}] ${path.basename(filePath)}: ${(before / 1024).toFixed(1)} KB -> ${(after / 1024).toFixed(1)} KB (-${pct}%)`
  );
}

async function main() {
  const rawArgs = process.argv.slice(2);
  const preservePositions = rawArgs.includes("--preserve-positions");
  const files = rawArgs.filter((a) => !a.startsWith("--"));
  for (const fp of files) {
    await optimizeOne(fp, preservePositions);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

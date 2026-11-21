#!/usr/bin/env node
/**
 * Bakes high-resolution campus signage/relief atlases + botanical foliage cards
 * into compressed WebP Albedo + Sobel Tangent-Space Normal Maps + ORM Maps.
 *
 * Output:
 *   - public/textures/campus/{signage_gates,plaques_stage,west_details}_{albedo,normal}.webp
 *   - public/textures/foliage/foliage_{broad,pine,ginkgo,magnolia,persimmon,rose}_{albedo,normal}.webp
 *   - public/textures/env/interior_atlas.webp
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");
const SCRATCH_ROOT =
  process.env.BUILD_SCRATCH_ROOT || path.join(process.env.HOME || "/tmp", ".build");
const TMP_DIR = path.join(SCRATCH_ROOT, "校园地图/baked_src");
const TOOLS_NODE_MODULES = path.join(SCRATCH_ROOT, "校园地图/tools/node_modules");

const require = createRequire(import.meta.url);
let sharp;
try {
  sharp = require("sharp");
} catch {
  sharp = require(path.join(TOOLS_NODE_MODULES, "sharp"));
}

function clampByte(v) {
  return Math.max(0, Math.min(255, Math.round(v)));
}

/**
 * Compute OpenGL tangent-space Normal Map (Y+) from a greyscale height buffer using Sobel 3x3.
 */
async function bakeNormalFromHeight(heightSrcPath, outWebpPath, strength = 2.6, invertY = false) {
  const { data, info } = await sharp(heightSrcPath)
    .greyscale()
    .blur(0.75)
    .raw()
    .toBuffer({ resolveWithObject: true });

  const w = info.width;
  const h = info.height;
  const out = Buffer.alloc(w * h * 3);

  const sample = (x, y) => {
    const cx = Math.max(0, Math.min(w - 1, x));
    const cy = Math.max(0, Math.min(h - 1, y));
    return data[cy * w + cx] / 255.0;
  };

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const tl = sample(x - 1, y - 1);
      const t = sample(x, y - 1);
      const tr = sample(x + 1, y - 1);
      const l = sample(x - 1, y);
      const r = sample(x + 1, y);
      const bl = sample(x - 1, y + 1);
      const b = sample(x, y + 1);
      const br = sample(x + 1, y + 1);

      const gx = (tr + 2 * r + br) - (tl + 2 * l + bl);
      const gy = (bl + 2 * b + br) - (tl + 2 * t + tr);

      const nx = -gx * strength;
      const ny = (invertY ? -gy : gy) * strength;
      const nz = 1.0;
      const len = Math.hypot(nx, ny, nz) || 1.0;

      const idx = (y * w + x) * 3;
      out[idx] = clampByte(((nx / len) * 0.5 + 0.5) * 255);
      out[idx + 1] = clampByte(((ny / len) * 0.5 + 0.5) * 255);
      out[idx + 2] = clampByte(((nz / len) * 0.5 + 0.5) * 255);
    }
  }

  await sharp(out, { raw: { width: w, height: h, channels: 3 } })
    .webp({ quality: 88, effort: 5 })
    .toFile(outWebpPath);
}

async function main() {
  fs.mkdirSync(TMP_DIR, { recursive: true });
  const campusDir = path.join(REPO_ROOT, "public/textures/campus");
  const foliageDir = path.join(REPO_ROOT, "public/textures/foliage");
  const envDir = path.join(REPO_ROOT, "public/textures/env");
  fs.mkdirSync(campusDir, { recursive: true });
  fs.mkdirSync(foliageDir, { recursive: true });
  fs.mkdirSync(envDir, { recursive: true });

  console.log("1. Rendering high-res campus signage & relief atlases via Swift...");
  execFileSync("swift", [path.join(__dirname, "render_textures.swift"), TMP_DIR], {
    stdio: "inherit",
  });

  console.log("2. Rendering botanical foliage cluster cards & interior parallax atlas...");
  execFileSync("swift", [path.join(__dirname, "render_foliage_and_atlases.swift"), TMP_DIR], {
    stdio: "inherit",
  });

  // Convert campus signage/relief atlases to WebP + Sobel normal maps (for C-Wing relief, Shendu carving, metal seams)
  const campusAtlases = [
    { src: "tex_signage_gates.png", out: "signage_gates", normalStrength: 2.2 },
    { src: "tex_plaques_stage.png", out: "plaques_stage", normalStrength: 2.4 },
    { src: "tex_west_details.png", out: "west_details", normalStrength: 3.0 },
  ];

  for (const item of campusAtlases) {
    const srcPath = path.join(TMP_DIR, item.src);
    await sharp(srcPath)
      .webp({ quality: 88, alphaQuality: 92, effort: 5 })
      .toFile(path.join(campusDir, `${item.out}_albedo.webp`));

    await bakeNormalFromHeight(
      srcPath,
      path.join(campusDir, `${item.out}_normal.webp`),
      item.normalStrength,
      true
    );
    console.log(`[OK] campus/${item.out}_{albedo,normal}.webp`);
  }

  // Convert 6 foliage species cards to WebP + Sobel normals
  const species = ["broad", "pine", "ginkgo", "magnolia", "persimmon", "rose"];
  for (const sp of species) {
    const albSrc = path.join(TMP_DIR, `foliage_${sp}_albedo.png`);
    const hSrc = path.join(TMP_DIR, `foliage_${sp}_height.png`);
    await sharp(albSrc)
      .resize(512, 512)
      .webp({ quality: 86, alphaQuality: 92, effort: 5 })
      .toFile(path.join(foliageDir, `foliage_${sp}_albedo.webp`));
    await sharp(hSrc)
      .resize(512, 512)
      .png()
      .toFile(path.join(TMP_DIR, `foliage_${sp}_height_512.png`));
    await bakeNormalFromHeight(
      path.join(TMP_DIR, `foliage_${sp}_height_512.png`),
      path.join(foliageDir, `foliage_${sp}_normal.webp`),
      2.6,
      false
    );
    console.log(`[OK] foliage/foliage_${sp}_{albedo,normal}.webp`);
  }

  // Convert interior parallax room atlas
  await sharp(path.join(TMP_DIR, "interior_atlas.png"))
    .webp({ quality: 84, effort: 5 })
    .toFile(path.join(envDir, "interior_atlas.webp"));
  console.log("[OK] env/interior_atlas.webp");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

#!/usr/bin/env node
/**
 * Fetches CC0 photogrammetry PBR texture sets from Poly Haven API and converts
 * them into color-calibrated, GPU-friendly WebP maps (albedo / normal / orm)
 * under `public/textures/pbr/<materialId>/`.
 *
 * License: All downloaded textures are CC0 1.0 Public Domain (Poly Haven).
 * Requires `sharp` (installed in $BUILD_SCRATCH_ROOT/校园地图/tools or NODE_PATH).
 */

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");
const OUT_ROOT = path.join(REPO_ROOT, "public/textures/pbr");
const SCRATCH_ROOT =
  process.env.BUILD_SCRATCH_ROOT || path.join(process.env.HOME || "/tmp", ".build");
const CACHE_DIR = path.join(SCRATCH_ROOT, "校园地图/polyhaven_cache");
const TOOLS_NODE_MODULES = path.join(SCRATCH_ROOT, "校园地图/tools/node_modules");

const require = createRequire(import.meta.url);
let sharp;
try {
  sharp = require("sharp");
} catch {
  sharp = require(path.join(TOOLS_NODE_MODULES, "sharp"));
}

const USER_AGENT = "ibb-school-map-pbr-pipeline/1.0 (https://github.com/ibb-official/ibb-school-map)";

/**
 * Curated Poly Haven CC0 textures calibrated to Beijing No. 166 Middle School
 * reference photographs (`public/images/ref/*.webp`).
 */
const MATERIALS = [
  {
    id: "qingzhuan",
    polyhavenId: "brick_wall_001",
    label: "北京青砖（校史馆/院墙/门房）",
    size: 1024,
    // Desaturate and cool-shift into authentic Beijing grey kiln brick
    albedoTransform: { saturation: 0.14, brightness: 0.88, tint: [148, 154, 162], tintBlend: 0.42 },
    roughnessScale: 1.02,
    normalStrength: 1.25,
  },
  {
    id: "red_brick",
    polyhavenId: "red_brick_03",
    label: "红褐劈开砖（B座/A座/北巷红砖）",
    size: 1024,
    albedoTransform: { saturation: 0.86, brightness: 0.96, tint: [164, 88, 68], tintBlend: 0.22 },
    roughnessScale: 0.98,
    normalStrength: 1.2,
  },
  {
    id: "stucco",
    polyhavenId: "white_plaster_02",
    label: "浅米白拉毛灰泥（主教学楼立面）",
    size: 1024,
    albedoTransform: { saturation: 0.25, brightness: 1.04, tint: [240, 236, 228], tintBlend: 0.35 },
    roughnessScale: 0.96,
    normalStrength: 0.9,
  },
  {
    id: "grey_rib",
    polyhavenId: "concrete_layers_02",
    label: "浅灰横肋建筑饰面（C座/楼梯间/A座上层）",
    size: 1024,
    albedoTransform: { saturation: 0.12, brightness: 1.08, tint: [176, 180, 186], tintBlend: 0.38 },
    roughnessScale: 0.95,
    normalStrength: 1.35,
    addHorizontalRibs: true,
  },
  {
    id: "marble",
    polyhavenId: "marble_01",
    label: "米白玉纹大理石（西门门柱/保安厅/主席台石壁）",
    size: 1024,
    albedoTransform: { saturation: 0.18, brightness: 1.02, tint: [232, 232, 230], tintBlend: 0.26 },
    roughnessScale: 0.42,
    normalStrength: 0.72,
    addSlabJoints: false,
  },
  {
    id: "plaza_tile",
    polyhavenId: "granite_tile",
    label: "花岗岩广场石砖铺装",
    size: 1024,
    albedoTransform: { saturation: 0.18, brightness: 1.05, tint: [176, 180, 186], tintBlend: 0.3 },
    roughnessScale: 0.88,
    normalStrength: 1.15,
  },
  {
    id: "dark_slate",
    polyhavenId: "stone_tiles_02",
    label: "深灰石材台基与板岩地坪",
    size: 1024,
    albedoTransform: { saturation: 0.15, brightness: 0.64, tint: [76, 80, 88], tintBlend: 0.38 },
    roughnessScale: 0.78,
    normalStrength: 1.2,
  },
  {
    id: "asphalt",
    polyhavenId: "asphalt_02",
    label: "胡同沥青路面（同福夹道/东四六条）",
    size: 1024,
    albedoTransform: { saturation: 0.16, brightness: 0.82, tint: [74, 78, 84], tintBlend: 0.22 },
    roughnessScale: 0.95,
    normalStrength: 1.25,
  },
  {
    id: "roof_tile",
    polyhavenId: "grey_roof_tiles_02",
    label: "传统瓦垄屋面（灰筒瓦/可染色红瓦与蓝琉璃瓦）",
    size: 1024,
    albedoTransform: { saturation: 0.12, brightness: 0.95, tint: [110, 116, 124], tintBlend: 0.25 },
    roughnessScale: 0.86,
    normalStrength: 1.45,
  },
  {
    id: "track_epdm",
    polyhavenId: "gravel_embedded_concrete",
    label: "深红褐颗粒 EPDM 塑胶跑道",
    size: 1024,
    albedoTransform: { saturation: 0.22, brightness: 0.94, tint: [176, 66, 48], tintBlend: 0.76 },
    roughnessScale: 1.02,
    normalStrength: 1.1,
  },
  {
    id: "court_pu",
    polyhavenId: "concrete_floor_02",
    label: "平整硅PU球场地坪（可染色红/绿）",
    size: 1024,
    albedoTransform: { saturation: 0.08, brightness: 1.28, tint: [228, 228, 228], tintBlend: 0.52 },
    roughnessScale: 0.58,
    normalStrength: 0.45,
  },
  {
    id: "grass",
    polyhavenId: "leafy_grass",
    label: "校园绿地草坪与生态绿顶",
    size: 1024,
    albedoTransform: { saturation: 1.08, brightness: 0.98, tint: [86, 136, 62], tintBlend: 0.24 },
    roughnessScale: 1.05,
    normalStrength: 1.15,
  },
  {
    id: "bark",
    polyhavenId: "bark_brown_02",
    label: "乔木自然树皮",
    size: 512,
    albedoTransform: { saturation: 0.88, brightness: 0.92, tint: [96, 76, 58], tintBlend: 0.18 },
    roughnessScale: 1.05,
    normalStrength: 1.4,
  },
  {
    id: "rockery",
    polyhavenId: "rock_boulder_dry",
    label: "慎独石粗花岗岩与太湖石假山",
    size: 1024,
    albedoTransform: { saturation: 0.16, brightness: 1.02, tint: [158, 158, 154], tintBlend: 0.3 },
    roughnessScale: 0.96,
    normalStrength: 1.35,
  },
  {
    id: "wood",
    polyhavenId: "wood_table_001",
    label: "校园廊柱/展厅/课桌木饰面",
    size: 512,
    albedoTransform: { saturation: 0.92, brightness: 1.0, tint: [166, 120, 82], tintBlend: 0.15 },
    roughnessScale: 0.72,
    normalStrength: 0.85,
  },
];

async function fetchJson(url) {
  const res = await fetch(url, { headers: { "User-Agent": USER_AGENT } });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return res.json();
}

async function downloadFile(url, destPath) {
  if (fs.existsSync(destPath) && fs.statSync(destPath).size > 2048) {
    return destPath;
  }
  fs.mkdirSync(path.dirname(destPath), { recursive: true });
  const res = await fetch(url, { headers: { "User-Agent": USER_AGENT } });
  if (!res.ok) throw new Error(`HTTP ${res.status} downloading ${url}`);
  const buf = Buffer.from(await res.arrayBuffer());
  fs.writeFileSync(destPath, buf);
  return destPath;
}

function pickUrl(filesJson, mapKeys) {
  for (const key of mapKeys) {
    const entry = filesJson[key];
    if (!entry) continue;
    const resObj = entry["1k"] || entry["2k"];
    if (!resObj) continue;
    for (const fmt of ["jpg", "png"]) {
      if (resObj[fmt]?.url) return { url: resObj[fmt].url, key, fmt };
    }
  }
  return null;
}

function clampByte(v) {
  return Math.max(0, Math.min(255, Math.round(v)));
}

async function processAlbedo(srcPath, destPath, mat) {
  const { size, albedoTransform } = mat;
  let pipe = sharp(srcPath).resize(size, size, { fit: "fill" }).removeAlpha();
  if (albedoTransform?.brightness || albedoTransform?.saturation !== undefined) {
    pipe = pipe.modulate({
      brightness: albedoTransform.brightness ?? 1.0,
      saturation: albedoTransform.saturation ?? 1.0,
    });
  }
  const { data, info } = await pipe.raw().toBuffer({ resolveWithObject: true });
  const [tr, tg, tb] = albedoTransform?.tint || [255, 255, 255];
  const blend = albedoTransform?.tintBlend ?? 0;

  for (let y = 0; y < info.height; y++) {
    // Subtle architectural ribs or marble panel joints baked into albedo
    let ribMul = 1.0;
    if (mat.addHorizontalRibs) {
      const m = y % 64;
      if (m < 4) ribMul = 0.78;
      else if (m < 8) ribMul = 1.08;
    }
    for (let x = 0; x < info.width; x++) {
      let jointMul = ribMul;
      if (mat.addSlabJoints) {
        if (y % 256 < 3 || x % 512 < 3) jointMul *= 0.76;
      }
      const i = (y * info.width + x) * 3;
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      // Multiply-blend target tint while preserving natural photogrammetry luminance contrast
      const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0;
      const tintedR = tr * (0.45 + 0.95 * lum);
      const tintedG = tg * (0.45 + 0.95 * lum);
      const tintedB = tb * (0.45 + 0.95 * lum);
      data[i] = clampByte((r * (1 - blend) + tintedR * blend) * jointMul);
      data[i + 1] = clampByte((g * (1 - blend) + tintedG * blend) * jointMul);
      data[i + 2] = clampByte((b * (1 - blend) + tintedB * blend) * jointMul);
    }
  }

  await sharp(data, { raw: { width: info.width, height: info.height, channels: 3 } })
    .webp({ quality: 82, effort: 5 })
    .toFile(destPath);
}

async function processNormal(srcPath, destPath, mat) {
  const { size } = mat;
  const strength = mat.normalStrength ?? 1.0;
  const { data, info } = await sharp(srcPath)
    .resize(size, size, { fit: "fill" })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  for (let y = 0; y < info.height; y++) {
    let ribNy = 0;
    if (mat.addHorizontalRibs) {
      const m = y % 64;
      if (m < 3) ribNy = -0.58;
      else if (m < 6) ribNy = 0.52;
    }
    for (let x = 0; x < info.width; x++) {
      const i = (y * info.width + x) * 3;
      let nx = (data[i] / 255.0) * 2.0 - 1.0;
      let ny = (data[i + 1] / 255.0) * 2.0 - 1.0;
      let nz = (data[i + 2] / 255.0) * 2.0 - 1.0;

      nx *= strength;
      ny = ny * strength + ribNy;
      if (mat.addSlabJoints) {
        if (y % 256 === 0) ny -= 0.48;
        else if (y % 256 === 2) ny += 0.48;
        if (x % 512 === 0) nx -= 0.48;
        else if (x % 512 === 2) nx += 0.48;
      }

      const len = Math.hypot(nx, ny, Math.max(0.15, nz)) || 1.0;
      data[i] = clampByte(((nx / len) * 0.5 + 0.5) * 255);
      data[i + 1] = clampByte(((ny / len) * 0.5 + 0.5) * 255);
      data[i + 2] = clampByte(((Math.max(0.15, nz) / len) * 0.5 + 0.5) * 255);
    }
  }

  await sharp(data, { raw: { width: info.width, height: info.height, channels: 3 } })
    .webp({ quality: 88, effort: 5 })
    .toFile(destPath);
}

async function processORM(armPath, roughPath, aoPath, destPath, mat) {
  const { size } = mat;
  const rScale = mat.roughnessScale ?? 1.0;

  let outBuf;
  if (armPath) {
    const { data } = await sharp(armPath)
      .resize(size, size, { fit: "fill" })
      .removeAlpha()
      .raw()
      .toBuffer({ resolveWithObject: true });
    for (let i = 0; i < data.length; i += 3) {
      // Poly Haven ARM layout: R = AO, G = Roughness, B = Metalness
      const ao = data[i];
      const rough = clampByte(data[i + 1] * rScale);
      const metal = data[i + 2];
      data[i] = ao;
      data[i + 1] = rough;
      data[i + 2] = metal;
    }
    outBuf = data;
  } else {
    outBuf = Buffer.alloc(size * size * 3);
    const roughData = roughPath
      ? (await sharp(roughPath).resize(size, size, { fit: "fill" }).greyscale().raw().toBuffer())
      : null;
    const aoData = aoPath
      ? (await sharp(aoPath).resize(size, size, { fit: "fill" }).greyscale().raw().toBuffer())
      : null;
    for (let p = 0; p < size * size; p++) {
      outBuf[p * 3] = aoData ? aoData[p] : 255;
      outBuf[p * 3 + 1] = clampByte((roughData ? roughData[p] : 200) * rScale);
      outBuf[p * 3 + 2] = 0;
    }
  }

  await sharp(outBuf, { raw: { width: size, height: size, channels: 3 } })
    .webp({ quality: 82, effort: 5 })
    .toFile(destPath);
}

async function processMaterial(mat) {
  const matOut = path.join(OUT_ROOT, mat.id);
  fs.mkdirSync(matOut, { recursive: true });

  const filesJson = await fetchJson(`https://api.polyhaven.com/files/${mat.polyhavenId}`);
  const diffPick = pickUrl(filesJson, ["Diffuse", "col", "albedo"]);
  const normPick = pickUrl(filesJson, ["nor_gl", "Normal"]);
  const armPick = pickUrl(filesJson, ["arm"]);
  const roughPick = armPick ? null : pickUrl(filesJson, ["Rough", "roughness"]);
  const aoPick = armPick ? null : pickUrl(filesJson, ["AO", "ao"]);

  if (!diffPick || !normPick) {
    throw new Error(`Missing diff/nor_gl for ${mat.polyhavenId}: keys=${Object.keys(filesJson).join(",")}`);
  }

  const cacheMat = path.join(CACHE_DIR, mat.polyhavenId);
  const diffLocal = await downloadFile(diffPick.url, path.join(cacheMat, `diff.${diffPick.fmt}`));
  const normLocal = await downloadFile(normPick.url, path.join(cacheMat, `nor_gl.${normPick.fmt}`));
  const armLocal = armPick
    ? await downloadFile(armPick.url, path.join(cacheMat, `arm.${armPick.fmt}`))
    : null;
  const roughLocal = roughPick
    ? await downloadFile(roughPick.url, path.join(cacheMat, `rough.${roughPick.fmt}`))
    : null;
  const aoLocal = aoPick
    ? await downloadFile(aoPick.url, path.join(cacheMat, `ao.${aoPick.fmt}`))
    : null;

  const albedoOut = path.join(matOut, "albedo.webp");
  const normalOut = path.join(matOut, "normal.webp");
  const ormOut = path.join(matOut, "orm.webp");

  await Promise.all([
    processAlbedo(diffLocal, albedoOut, mat),
    processNormal(normLocal, normalOut, mat),
    processORM(armLocal, roughLocal, aoLocal, ormOut, mat),
  ]);

  const bytes =
    fs.statSync(albedoOut).size + fs.statSync(normalOut).size + fs.statSync(ormOut).size;
  console.log(
    `[OK] ${mat.id.padEnd(12)} <- ${mat.polyhavenId.padEnd(25)} (${(bytes / 1024).toFixed(1)} KB total)`
  );
  return { id: mat.id, polyhavenId: mat.polyhavenId, label: mat.label, bytes };
}

async function generateUtilityTextures() {
  const utilDir = path.join(REPO_ROOT, "public/textures/env");
  fs.mkdirSync(utilDir, { recursive: true });

  // 1. Seamless multi-octave water ripple normal map (512x512)
  const ws = 512;
  const hMap = new Float32Array(ws * ws);
  const waves = [
    [2, 3, 0.34, 0.2],
    [-4, 2, 0.24, 1.4],
    [5, -6, 0.18, 2.7],
    [-8, -5, 0.12, 0.9],
    [11, 9, 0.08, 3.1],
    [-14, 13, 0.05, 4.5],
    [19, -17, 0.035, 1.8],
  ];
  for (let y = 0; y < ws; y++) {
    const v = (y / ws) * Math.PI * 2;
    for (let x = 0; x < ws; x++) {
      const u = (x / ws) * Math.PI * 2;
      let h = 0;
      for (const [fx, fy, amp, ph] of waves) {
        h += Math.sin(u * fx + v * fy + ph) * amp;
      }
      hMap[y * ws + x] = h;
    }
  }
  const nBuf = Buffer.alloc(ws * ws * 3);
  const scale = 2.6;
  for (let y = 0; y < ws; y++) {
    const ym = (y - 1 + ws) % ws;
    const yp = (y + 1) % ws;
    for (let x = 0; x < ws; x++) {
      const xm = (x - 1 + ws) % ws;
      const xp = (x + 1) % ws;
      const dx = (hMap[y * ws + xp] - hMap[y * ws + xm]) * scale;
      const dy = (hMap[yp * ws + x] - hMap[ym * ws + x]) * scale;
      const nx = -dx;
      const ny = -dy;
      const nz = 1.0;
      const l = Math.hypot(nx, ny, nz);
      const i = (y * ws + x) * 3;
      nBuf[i] = clampByte(((nx / l) * 0.5 + 0.5) * 255);
      nBuf[i + 1] = clampByte(((ny / l) * 0.5 + 0.5) * 255);
      nBuf[i + 2] = clampByte(((nz / l) * 0.5 + 0.5) * 255);
    }
  }
  await sharp(nBuf, { raw: { width: ws, height: ws, channels: 3 } })
    .webp({ quality: 90, effort: 5 })
    .toFile(path.join(utilDir, "water_normal.webp"));

  // 2. Seamless puddle / weathering noise map (512x512 RGB: R=low-freq puddle mask, G=mid-freq wetness, B=micro grime)
  const pBuf = Buffer.alloc(ws * ws * 3);
  const hash2 = (ix, iy, period) => {
    const x = ((ix % period) + period) % period;
    const y = ((iy % period) + period) % period;
    const n = Math.sin(x * 127.1 + y * 311.7) * 43758.5453123;
    return n - Math.floor(n);
  };
  const vnoise = (u, v, freq) => {
    const x = u * freq;
    const y = v * freq;
    const ix = Math.floor(x);
    const iy = Math.floor(y);
    const fx = x - ix;
    const fy = y - iy;
    const sx = fx * fx * (3 - 2 * fx);
    const sy = fy * fy * (3 - 2 * fy);
    const a = hash2(ix, iy, freq);
    const b = hash2(ix + 1, iy, freq);
    const c = hash2(ix, iy + 1, freq);
    const d = hash2(ix + 1, iy + 1, freq);
    return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy;
  };
  for (let y = 0; y < ws; y++) {
    const v = y / ws;
    for (let x = 0; x < ws; x++) {
      const u = x / ws;
      const r = vnoise(u, v, 4) * 0.62 + vnoise(u, v, 8) * 0.28 + vnoise(u, v, 16) * 0.1;
      const g = vnoise(u, v, 8) * 0.5 + vnoise(u, v, 16) * 0.35 + vnoise(u, v, 32) * 0.15;
      const b = vnoise(u, v, 16) * 0.45 + vnoise(u, v, 32) * 0.35 + vnoise(u, v, 64) * 0.2;
      const i = (y * ws + x) * 3;
      pBuf[i] = clampByte(r * 255);
      pBuf[i + 1] = clampByte(g * 255);
      pBuf[i + 2] = clampByte(b * 255);
    }
  }
  await sharp(pBuf, { raw: { width: ws, height: ws, channels: 3 } })
    .webp({ quality: 86, effort: 5 })
    .toFile(path.join(utilDir, "puddle_noise.webp"));

  console.log("[OK] Generated env/water_normal.webp & env/puddle_noise.webp");
}

async function main() {
  fs.mkdirSync(OUT_ROOT, { recursive: true });
  fs.mkdirSync(CACHE_DIR, { recursive: true });

  const results = [];
  // Process in small concurrent batches to be polite to Poly Haven CDN
  for (let i = 0; i < MATERIALS.length; i += 3) {
    const batch = MATERIALS.slice(i, i + 3);
    const batchRes = await Promise.all(batch.map((m) => processMaterial(m)));
    results.push(...batchRes);
  }

  await generateUtilityTextures();

  const totalKB = results.reduce((s, r) => s + r.bytes, 0) / 1024;
  console.log(`\nAll ${results.length} CC0 PBR sets ready. Total size: ${(totalKB / 1024).toFixed(2)} MB`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

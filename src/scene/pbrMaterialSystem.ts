import * as THREE from "three";
import { QualityTier } from "@/data/types";

export interface GlobalShaderUniforms {
  uTime: { value: number };
  uWetness: { value: number };
  uSnow: { value: number };
  uWindStrength: { value: number };
  uNightFactor: { value: number };
  uPuddleNoise: { value: THREE.Texture | null };
  uWaterNormal: { value: THREE.Texture | null };
}

export interface UpgradedMaterialBuckets {
  /** 7 independently timed ceiling LED fixture materials (0..3 class, 4..5 warm hero, 6 hall) */
  interiorLights: Map<number, THREE.MeshStandardMaterial[]>;
  /** 7 matching interior bounced-wall/ceiling glow materials */
  interiorGlows: Map<number, THREE.MeshStandardMaterial[]>;
  /** Outdoor courtyard lamps & wall sconces */
  outdoorLamps: THREE.MeshStandardMaterial[];
  /** Sports floodlight heads */
  floodlightHeads: THREE.MeshStandardMaterial[];
  /** Gate & stage LED signage boards */
  ledSignage: THREE.MeshStandardMaterial[];
  /** Dynamic animated water materials (rockery basin + waterfall) */
  waterMaterials: THREE.MeshStandardMaterial[];
  /** All created/upgraded materials & textures for clean GPU disposal */
  disposables: {
    textures: Set<THREE.Texture>;
    materials: Set<THREE.Material>;
  };
}

interface PBRSetConfig {
  folder: string;
  tint?: number;
  roughness?: number;
  metalness?: number;
  normalScale?: number;
  clearcoat?: number;
  clearcoatRoughness?: number;
  aoIntensity?: number;
  allowWeather?: boolean;
}

const PBR_MATERIAL_MAP: Record<string, PBRSetConfig> = {
  Mat_PBR_Qingzhuan: { folder: "qingzhuan", roughness: 0.94, normalScale: 1.25, aoIntensity: 0.85, allowWeather: true },
  Mat_PBR_RedBrick: { folder: "red_brick", roughness: 0.92, normalScale: 1.22, aoIntensity: 0.85, allowWeather: true },
  Mat_PBR_Stucco: { folder: "stucco", roughness: 0.88, normalScale: 0.85, aoIntensity: 0.6, allowWeather: true },
  Mat_PBR_GreyRib: { folder: "grey_rib", roughness: 0.84, normalScale: 1.35, aoIntensity: 0.75, allowWeather: true },
  Mat_PBR_Marble: {
    folder: "marble",
    roughness: 0.34,
    normalScale: 0.68,
    clearcoat: 0.58,
    clearcoatRoughness: 0.16,
    aoIntensity: 0.5,
    allowWeather: true,
  },
  Mat_PBR_PlazaTile: { folder: "plaza_tile", roughness: 0.84, normalScale: 1.15, aoIntensity: 0.78, allowWeather: true },
  Mat_PBR_DarkSlate: { folder: "dark_slate", roughness: 0.74, normalScale: 1.2, aoIntensity: 0.8, allowWeather: true },
  Mat_PBR_Asphalt: { folder: "asphalt", roughness: 0.92, normalScale: 1.28, aoIntensity: 0.85, allowWeather: true },
  Mat_PBR_GreyTile: { folder: "roof_tile", tint: 0xa2aab4, roughness: 0.78, normalScale: 1.45, aoIntensity: 0.85, allowWeather: true },
  Mat_PBR_RedTile: { folder: "roof_tile", tint: 0xd46a64, roughness: 0.72, normalScale: 1.4, aoIntensity: 0.8, allowWeather: true },
  Mat_PBR_BlueTile: {
    folder: "roof_tile",
    tint: 0x3b86e8,
    roughness: 0.38,
    clearcoat: 0.65,
    clearcoatRoughness: 0.18,
    normalScale: 1.35,
    aoIntensity: 0.75,
    allowWeather: true,
  },
  Mat_PBR_GreenRoof: { folder: "grass", tint: 0x89a87a, roughness: 0.88, normalScale: 1.0, aoIntensity: 0.7, allowWeather: true },
  Mat_PBR_TrackEPDM: { folder: "track_epdm", roughness: 0.92, normalScale: 1.15, aoIntensity: 0.8, allowWeather: true },
  Mat_PBR_CourtPU: { folder: "court_pu", tint: 0xd87c66, roughness: 0.52, normalScale: 0.45, aoIntensity: 0.45, allowWeather: true },
  Mat_PBR_CourtGreen: { folder: "court_pu", tint: 0x268252, roughness: 0.50, normalScale: 0.45, aoIntensity: 0.45, allowWeather: true },
  Mat_PBR_Grass: { folder: "grass", roughness: 0.94, normalScale: 1.1, aoIntensity: 0.85, allowWeather: true },
  Mat_PBR_Bark: { folder: "bark", roughness: 0.95, normalScale: 1.4, aoIntensity: 0.9, allowWeather: true },
  Mat_PBR_Wood: { folder: "wood", roughness: 0.66, normalScale: 0.85, aoIntensity: 0.55, allowWeather: false },
  Mat_PBR_Rockery: { folder: "rockery", roughness: 0.88, normalScale: 1.35, aoIntensity: 0.9, allowWeather: true },
  Mat_PBR_BurgundyMetal: {
    folder: "grey_rib",
    tint: 0x7e2a28,
    roughness: 0.42,
    metalness: 0.42,
    clearcoat: 0.25,
    normalScale: 0.6,
    allowWeather: true,
  },
};

const FOLIAGE_MATERIAL_MAP: Record<string, { file: string; tint: number }> = {
  Mat_Foliage_Broad: { file: "foliage_broad", tint: 0xffffff },
  Mat_Foliage_Pine: { file: "foliage_pine", tint: 0xf4faf4 },
  Mat_Foliage_Ginkgo: { file: "foliage_ginkgo", tint: 0xfff6dc },
  Mat_Foliage_Magnolia: { file: "foliage_magnolia", tint: 0xffffff },
  Mat_Foliage_Persimmon: { file: "foliage_persimmon", tint: 0xffffff },
  Mat_Foliage_Rose: { file: "foliage_rose", tint: 0xffffff },
};

const CAMPUS_NORMAL_MAP: Record<string, { normalUrl: string; normalScale: number }> = {
  Mat_Gates: { normalUrl: "/textures/campus/signage_gates_normal.webp", normalScale: 0.95 },
  Mat_StagePlaques: { normalUrl: "/textures/campus/plaques_stage_normal.webp", normalScale: 1.05 },
  Mat_WestDetails: { normalUrl: "/textures/campus/west_details_normal.webp", normalScale: 1.25 },
};

const INT_LIGHT_BUCKET_MAP: Record<string, number> = {
  Mat_IntLight_Class_0: 0,
  Mat_IntLight_Class_1: 1,
  Mat_IntLight_Class_2: 2,
  Mat_IntLight_Class_3: 3,
  Mat_IntLight_Warm_0: 4,
  Mat_IntLight_Warm_1: 5,
  Mat_IntLight_Hall: 6,
};

const INT_GLOW_BUCKET_MAP: Record<string, number> = {
  Mat_IntGlow_0: 0,
  Mat_IntGlow_1: 1,
  Mat_IntGlow_2: 2,
  Mat_IntGlow_3: 3,
  Mat_IntGlow_4: 4,
  Mat_IntGlow_5: 5,
  Mat_IntGlow_6: 6,
};

function injectWeatherSurfaceShader(
  mat: THREE.MeshStandardMaterial,
  shared: GlobalShaderUniforms,
  snowWeight = 1.0,
  puddleWeight = 1.0
): void {
  const prevKey = mat.customProgramCacheKey?.() ?? "";
  mat.customProgramCacheKey = () => `${prevKey}_weather_${snowWeight}_${puddleWeight}`;

  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = shared.uTime;
    shader.uniforms.uWetness = shared.uWetness;
    shader.uniforms.uSnow = shared.uSnow;
    shader.uniforms.uPuddleNoise = shared.uPuddleNoise;
    shader.uniforms.uSnowWeight = { value: snowWeight };
    shader.uniforms.uPuddleWeight = { value: puddleWeight };

    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        /* glsl */ `
        #include <common>
        varying vec3 vCampusWorldPos;
        varying vec3 vCampusWorldNorm;
        `
      )
      .replace(
        "#include <worldpos_vertex>",
        /* glsl */ `
        #include <worldpos_vertex>
        vec4 cwp = modelMatrix * vec4(transformed, 1.0);
        vCampusWorldPos = cwp.xyz;
        vCampusWorldNorm = normalize(mat3(modelMatrix) * objectNormal);
        `
      );

    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        /* glsl */ `
        #include <common>
        uniform float uTime;
        uniform float uWetness;
        uniform float uSnow;
        uniform float uSnowWeight;
        uniform float uPuddleWeight;
        uniform sampler2D uPuddleNoise;
        varying vec3 vCampusWorldPos;
        varying vec3 vCampusWorldNorm;
        `
      )
      .replace(
        "#include <color_fragment>",
        /* glsl */ `
        #include <color_fragment>
        vec3 cNoise = texture2D(uPuddleNoise, vCampusWorldPos.xz * 0.035).rgb;
        float upMask = smoothstep(0.55, 0.88, vCampusWorldNorm.y);
        if (uWetness > 0.01) {
          float wetPorosity = mix(0.68, 0.52, upMask);
          diffuseColor.rgb *= mix(1.0, wetPorosity + 0.14 * cNoise.g, uWetness);
        }
        float baseAO = smoothstep(0.0, 1.6, vCampusWorldPos.y);
        diffuseColor.rgb *= mix(0.88 + 0.08 * cNoise.b, 1.0, baseAO);
        if (uSnow > 0.01 && uSnowWeight > 0.01) {
          float snowMask = smoothstep(0.42, 0.78, vCampusWorldNorm.y + (cNoise.r - 0.5) * 0.25) * uSnow * uSnowWeight;
          vec3 snowAlbedo = vec3(0.92, 0.95, 0.99);
          diffuseColor.rgb = mix(diffuseColor.rgb, snowAlbedo, snowMask * 0.92);
        }
        `
      )
      .replace(
        "#include <roughnessmap_fragment>",
        /* glsl */ `
        #include <roughnessmap_fragment>
        if (uWetness > 0.01) {
          vec3 wNoise = texture2D(uPuddleNoise, vCampusWorldPos.xz * 0.035).rgb;
          float upFace = smoothstep(0.62, 0.92, vCampusWorldNorm.y);
          float puddle = smoothstep(0.46, 0.66, wNoise.r) * upFace * uWetness * uPuddleWeight;
          roughnessFactor = mix(roughnessFactor, roughnessFactor * 0.42, uWetness * 0.85);
          roughnessFactor = mix(roughnessFactor, 0.055, puddle);
        }
        if (uSnow > 0.01 && uSnowWeight > 0.01) {
          vec3 sNoise = texture2D(uPuddleNoise, vCampusWorldPos.xz * 0.035).rgb;
          float sMask = smoothstep(0.44, 0.78, vCampusWorldNorm.y + (sNoise.r - 0.5) * 0.25) * uSnow * uSnowWeight;
          roughnessFactor = mix(roughnessFactor, 0.76, sMask);
        }
        `
      );
  };
}

function injectFoliageShader(
  mat: THREE.MeshStandardMaterial,
  shared: GlobalShaderUniforms
): void {
  mat.customProgramCacheKey = () => "campus_foliage_static_snow_v2";
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uSnow = shared.uSnow;

    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        /* glsl */ `
        #include <common>
        varying vec3 vFoliageWorldNorm;
        `
      )
      .replace(
        "#include <worldpos_vertex>",
        /* glsl */ `
        #include <worldpos_vertex>
        vFoliageWorldNorm = normalize(mat3(modelMatrix) * objectNormal);
        `
      );

    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        /* glsl */ `
        #include <common>
        uniform float uSnow;
        varying vec3 vFoliageWorldNorm;
        `
      )
      .replace(
        "#include <color_fragment>",
        /* glsl */ `
        #include <color_fragment>
        if (uSnow > 0.01) {
          float crownSnow = smoothstep(0.28, 0.72, vFoliageWorldNorm.y) * uSnow;
          diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.93, 0.96, 1.0), crownSnow * 0.75);
        }
        `
      );
  };
}

function createContextParallaxWindowMaterial(
  interiorAtlas: THREE.Texture,
  shared: GlobalShaderUniforms
): THREE.MeshStandardMaterial {
  const mat = new THREE.MeshStandardMaterial({
    name: "Mat_Context_Window",
    color: new THREE.Color(0x88a2bc),
    roughness: 0.12,
    metalness: 0.15,
    envMapIntensity: 1.25,
  });

  mat.customProgramCacheKey = () => "campus_context_parallax_v1";
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uInteriorAtlas = { value: interiorAtlas };
    shader.uniforms.uNightFactor = shared.uNightFactor;

    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        /* glsl */ `
        #include <common>
        varying vec3 vCtxWorldPos;
        varying vec3 vCtxWorldNorm;
        `
      )
      .replace(
        "#include <worldpos_vertex>",
        /* glsl */ `
        #include <worldpos_vertex>
        vCtxWorldPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
        vCtxWorldNorm = normalize(mat3(modelMatrix) * objectNormal);
        `
      );

    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        /* glsl */ `
        #include <common>
        uniform sampler2D uInteriorAtlas;
        uniform float uNightFactor;
        varying vec3 vCtxWorldPos;
        varying vec3 vCtxWorldNorm;

        float ctxHash(vec2 p) {
          return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
        }
        `
      )
      .replace(
        "#include <emissivemap_fragment>",
        /* glsl */ `
        #include <emissivemap_fragment>
        vec2 winCoord = vec2(
          (abs(vCtxWorldNorm.x) > 0.5 ? vCtxWorldPos.z : vCtxWorldPos.x) * 0.42,
          vCtxWorldPos.y * 0.34
        );
        vec2 cellId = floor(winCoord);
        vec2 localUv = fract(winCoord);

        vec3 viewW = normalize(vCtxWorldPos - cameraPosition);
        vec3 rightAxis = normalize(cross(vec3(0.0, 1.0, 0.0), vCtxWorldNorm + vec3(0.0001)));
        vec3 upAxis = normalize(cross(vCtxWorldNorm, rightAxis));
        float denom = max(abs(dot(viewW, vCtxWorldNorm)), 0.25);
        vec2 parallax = vec2(dot(viewW, rightAxis), dot(viewW, upAxis)) / denom * 0.28;
        vec2 roomUv = clamp(localUv + parallax, 0.04, 0.96);

        float rnd = ctxHash(cellId);
        float colIdx = floor(fract(rnd * 13.7) * 4.0);
        float rowIdx = floor(fract(rnd * 29.3) * 4.0);
        vec2 atlasUv = (vec2(colIdx, rowIdx) + roomUv) * 0.25;
        vec3 roomCol = texture2D(uInteriorAtlas, atlasUv).rgb;

        float litThreshold = mix(0.95, 0.36, uNightFactor);
        float isLit = smoothstep(litThreshold, litThreshold + 0.08, rnd) * smoothstep(0.08, 0.65, uNightFactor);
        vec3 warmTint = mix(vec3(1.0, 0.78, 0.48), vec3(0.92, 0.94, 1.0), step(0.84, fract(rnd * 7.1)));
        totalEmissiveRadiance += roomCol * warmTint * isLit * 1.45;
        `
      );
  };
  return mat;
}

/**
 * Resource-gated PBR Material System for Enhanced Mode:
 * - low:    loads ONLY albedo + foliage albedo (~2.8 MB); skips normal, ORM, env, campus normals, weather shader
 * - medium: adds normal maps + env maps + weather/parallax shaders (~7.2 MB); skips ORM maps (~1.3 MB saved)
 * - high:   loads full PBR (albedo + normal + ORM) with 8x anisotropy
 * - ultra:  loads full PBR with maximum hardware anisotropy (unrestricted on all devices)
 */
export class PBRMaterialSystem {
  private readonly loader = new THREE.TextureLoader();
  private readonly textureCache = new Map<string, THREE.Texture>();
  private readonly maxAnisotropy: number;
  private readonly loadNormals: boolean;
  private readonly loadOrm: boolean;
  private readonly loadEnvTextures: boolean;
  private readonly usePhysicalShaders: boolean;
  public readonly sharedUniforms: GlobalShaderUniforms;

  constructor(renderer: THREE.WebGLRenderer, quality: QualityTier) {
    const hwMaxAniso = renderer.capabilities.getMaxAnisotropy();
    const anisoCap =
      quality === "low" ? 1 : quality === "medium" ? 4 : quality === "high" ? 8 : hwMaxAniso;
    this.maxAnisotropy = Math.min(anisoCap, hwMaxAniso);

    this.loadNormals = quality !== "low";
    this.loadOrm = quality === "high" || quality === "ultra";
    this.loadEnvTextures = quality !== "low";
    this.usePhysicalShaders = quality !== "low";

    const puddleNoise = this.loadEnvTextures
      ? this.loadTex("/textures/env/puddle_noise.webp", false, true)
      : null;
    const waterNormal = this.loadEnvTextures
      ? this.loadTex("/textures/env/water_normal.webp", false, true)
      : null;

    this.sharedUniforms = {
      uTime: { value: 0 },
      uWetness: { value: 0 },
      uSnow: { value: 0 },
      uWindStrength: { value: 0.35 },
      uNightFactor: { value: 0 },
      uPuddleNoise: { value: puddleNoise },
      uWaterNormal: { value: waterNormal },
    };
  }

  private loadTex(url: string, isSRGB: boolean, repeat: boolean): THREE.Texture {
    const key = `${url}|${isSRGB ? "srgb" : "lin"}|${repeat ? "rep" : "clp"}`;
    const cached = this.textureCache.get(key);
    if (cached) return cached;

    const tex = this.loader.load(url);
    tex.colorSpace = isSRGB ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    tex.wrapS = repeat ? THREE.RepeatWrapping : THREE.ClampToEdgeWrapping;
    tex.wrapT = repeat ? THREE.RepeatWrapping : THREE.ClampToEdgeWrapping;
    tex.anisotropy = this.maxAnisotropy;
    tex.flipY = false;
    tex.needsUpdate = true;
    this.textureCache.set(key, tex);
    return tex;
  }

  public upgradeLoadedScene(root: THREE.Object3D): UpgradedMaterialBuckets {
    const buckets: UpgradedMaterialBuckets = {
      interiorLights: new Map(),
      interiorGlows: new Map(),
      outdoorLamps: [],
      floodlightHeads: [],
      ledSignage: [],
      waterMaterials: [],
      disposables: {
        textures: new Set(),
        materials: new Set(),
      },
    };
    for (let i = 0; i < 7; i++) {
      buckets.interiorLights.set(i, []);
      buckets.interiorGlows.set(i, []);
    }

    const upgradedByName = new Map<string, THREE.Material>();
    const interiorAtlas = this.loadEnvTextures
      ? this.loadTex("/textures/env/interior_atlas.webp", true, false)
      : null;
    const waterNormal = this.sharedUniforms.uWaterNormal.value;

    const upgradeOne = (orig: THREE.Material): THREE.Material => {
      const name = orig.name || "";
      if (name && upgradedByName.has(name)) {
        return upgradedByName.get(name)!;
      }

      const stdOrig = orig as THREE.MeshStandardMaterial;

      // 1. Semantic photogrammetry PBR surfaces (strictly gated by quality tier)
      const pbrSpec = PBR_MATERIAL_MAP[name];
      if (pbrSpec) {
        const baseUrl = `/textures/pbr/${pbrSpec.folder}`;
        const albedo = this.loadTex(`${baseUrl}/albedo.webp`, true, true);
        const normal = this.loadNormals ? this.loadTex(`${baseUrl}/normal.webp`, false, true) : null;
        const orm = this.loadOrm ? this.loadTex(`${baseUrl}/orm.webp`, false, true) : null;

        const usePhysical = this.usePhysicalShaders && pbrSpec.clearcoat !== undefined;
        const commonParams: THREE.MeshStandardMaterialParameters = {
          name,
          color: new THREE.Color(pbrSpec.tint ?? 0xffffff),
          map: albedo,
          roughness: pbrSpec.roughness ?? 0.9,
          metalness: pbrSpec.metalness ?? 0.0,
          vertexColors: Boolean(stdOrig.vertexColors),
        };
        if (normal) {
          commonParams.normalMap = normal;
          commonParams.normalScale = new THREE.Vector2(
            pbrSpec.normalScale ?? 1.0,
            pbrSpec.normalScale ?? 1.0
          );
        }
        if (orm) {
          commonParams.aoMap = orm;
          commonParams.aoMapIntensity = pbrSpec.aoIntensity ?? 0.75;
          commonParams.roughnessMap = orm;
          commonParams.metalnessMap = orm;
        }

        const mat = usePhysical
          ? new THREE.MeshPhysicalMaterial({
              ...commonParams,
              clearcoat: pbrSpec.clearcoat ?? 0,
              clearcoatRoughness: pbrSpec.clearcoatRoughness ?? 0.2,
            })
          : new THREE.MeshStandardMaterial(commonParams);

        if (this.loadEnvTextures && pbrSpec.allowWeather) {
          const isGroundOrRoof =
            name.includes("Plaza") ||
            name.includes("Asphalt") ||
            name.includes("Track") ||
            name.includes("Court") ||
            name.includes("Tile") ||
            name.includes("Roof") ||
            name.includes("Grass") ||
            name.includes("Slate");
          injectWeatherSurfaceShader(mat, this.sharedUniforms, 1.0, isGroundOrRoof ? 1.0 : 0.35);
        }

        upgradedByName.set(name, mat);
        buckets.disposables.materials.add(mat);
        return mat;
      }

      // 2. Botanical alpha-cutout foliage cluster cards (albedo always needed for alpha cutout; normal gated)
      const folSpec = FOLIAGE_MATERIAL_MAP[name];
      if (folSpec) {
        const albedo = this.loadTex(`/textures/foliage/${folSpec.file}_albedo.webp`, true, false);
        const normal = this.loadNormals
          ? this.loadTex(`/textures/foliage/${folSpec.file}_normal.webp`, false, false)
          : null;
        const mat = new THREE.MeshStandardMaterial({
          name,
          color: new THREE.Color(folSpec.tint),
          map: albedo,
          ...(normal ? { normalMap: normal, normalScale: new THREE.Vector2(0.85, 0.85) } : {}),
          roughness: 0.74,
          metalness: 0.0,
          alphaTest: 0.42,
          side: THREE.DoubleSide,
          vertexColors: Boolean(stdOrig.vertexColors),
        });
        injectFoliageShader(mat, this.sharedUniforms);
        upgradedByName.set(name, mat);
        buckets.disposables.materials.add(mat);
        return mat;
      }

      // 3. Campus architectural glass
      if (name === "Mat_Glass_Physical" || name === "Mat_WarmGlass_Physical") {
        const isWarm = name === "Mat_WarmGlass_Physical";
        const mat = this.usePhysicalShaders
          ? new THREE.MeshPhysicalMaterial({
              name,
              color: new THREE.Color(isWarm ? 0xf7e7c8 : 0xc6dff0),
              roughness: 0.06,
              metalness: 0.05,
              ior: 1.5,
              reflectivity: 0.92,
              clearcoat: 1.0,
              clearcoatRoughness: 0.04,
              transparent: true,
              opacity: isWarm ? 0.42 : 0.32,
              depthWrite: false,
              side: THREE.DoubleSide,
              envMapIntensity: 1.45,
            })
          : new THREE.MeshStandardMaterial({
              name,
              color: new THREE.Color(isWarm ? 0xf7e7c8 : 0xc6dff0),
              roughness: 0.14,
              metalness: 0.1,
              transparent: true,
              opacity: isWarm ? 0.44 : 0.34,
              depthWrite: false,
              side: THREE.DoubleSide,
            });
        upgradedByName.set(name, mat);
        buckets.disposables.materials.add(mat);
        return mat;
      }

      // 4. Context surrounding building windows
      if (name === "Mat_Context_Window") {
        const mat = interiorAtlas
          ? createContextParallaxWindowMaterial(interiorAtlas, this.sharedUniforms)
          : new THREE.MeshStandardMaterial({
              name: "Mat_Context_Window",
              color: new THREE.Color(0x7c97b2),
              roughness: 0.25,
              metalness: 0.1,
            });
        upgradedByName.set(name, mat);
        buckets.disposables.materials.add(mat);
        return mat;
      }

      // 5. Tensile stage canopy
      if (name === "Mat_TensileMembrane") {
        const mat = this.usePhysicalShaders
          ? new THREE.MeshPhysicalMaterial({
              name,
              color: new THREE.Color(0xf6f8fb),
              roughness: 0.44,
              metalness: 0.0,
              sheen: 0.65,
              sheenRoughness: 0.55,
              sheenColor: new THREE.Color(0xfff4e6),
              side: THREE.DoubleSide,
              vertexColors: Boolean(stdOrig.vertexColors),
            })
          : new THREE.MeshStandardMaterial({
              name,
              color: new THREE.Color(0xf6f8fb),
              roughness: 0.5,
              metalness: 0.0,
              side: THREE.DoubleSide,
              vertexColors: Boolean(stdOrig.vertexColors),
            });
        if (this.loadEnvTextures) {
          injectWeatherSurfaceShader(mat, this.sharedUniforms, 0.85, 0.25);
        }
        upgradedByName.set(name, mat);
        buckets.disposables.materials.add(mat);
        return mat;
      }

      // 6. Rockery pool & waterfall water
      if (name === "Mat_RockeryWater" || name === "Mat_WaterfallStream") {
        const isPool = name === "Mat_RockeryWater";
        if (waterNormal && this.usePhysicalShaders) {
          const wNormClone = waterNormal.clone();
          wNormClone.wrapS = THREE.RepeatWrapping;
          wNormClone.wrapT = THREE.RepeatWrapping;
          wNormClone.repeat.set(isPool ? 3.5 : 2.0, isPool ? 3.5 : 4.0);
          wNormClone.needsUpdate = true;
          buckets.disposables.textures.add(wNormClone);

          const mat = new THREE.MeshPhysicalMaterial({
            name,
            color: new THREE.Color(isPool ? 0x1c6a7d : 0xcdf0fa),
            normalMap: wNormClone,
            normalScale: new THREE.Vector2(isPool ? 0.42 : 0.65, isPool ? 0.42 : 0.65),
            roughness: 0.06,
            metalness: 0.05,
            ior: 1.333,
            reflectivity: 0.95,
            clearcoat: 1.0,
            clearcoatRoughness: 0.05,
            transparent: true,
            opacity: isPool ? 0.78 : 0.66,
            side: THREE.DoubleSide,
            envMapIntensity: 1.6,
          });
          buckets.waterMaterials.push(mat);
          upgradedByName.set(name, mat);
          buckets.disposables.materials.add(mat);
          return mat;
        }
        const simpleWater = new THREE.MeshStandardMaterial({
          name,
          color: new THREE.Color(isPool ? 0x1c6a7d : 0xcdf0fa),
          roughness: 0.16,
          metalness: 0.05,
          transparent: true,
          opacity: isPool ? 0.78 : 0.66,
          side: THREE.DoubleSide,
        });
        upgradedByName.set(name, simpleWater);
        buckets.disposables.materials.add(simpleWater);
        return simpleWater;
      }

      // 7. Embedded campus atlases (Sobel normal maps gated by quality tier)
      if (stdOrig.isMeshStandardMaterial) {
        if (stdOrig.map) {
          stdOrig.map.anisotropy = this.maxAnisotropy;
        }
        if (this.loadNormals) {
          const campusNorm = CAMPUS_NORMAL_MAP[name];
          if (campusNorm) {
            stdOrig.normalMap = this.loadTex(campusNorm.normalUrl, false, false);
            stdOrig.normalScale = new THREE.Vector2(campusNorm.normalScale, campusNorm.normalScale);
            stdOrig.needsUpdate = true;
          }
        }

        if (name === "Mat_BronzeStatue") {
          stdOrig.roughness = 0.34;
          stdOrig.metalness = 0.78;
          stdOrig.envMapIntensity = 1.3;
        } else if (name === "Mat_Stainless" || name === "Mat_StainlessGate") {
          stdOrig.roughness = 0.22;
          stdOrig.metalness = 0.88;
          stdOrig.envMapIntensity = 1.4;
        } else if (
          this.loadEnvTextures &&
          (name === "Mat_WhiteAlu" || name === "Mat_DarkSteel" || name === "Mat_BlueSteel")
        ) {
          injectWeatherSurfaceShader(stdOrig, this.sharedUniforms, 0.55, 0.2);
        }

        if (name in INT_LIGHT_BUCKET_MAP) {
          buckets.interiorLights.get(INT_LIGHT_BUCKET_MAP[name])!.push(stdOrig);
        } else if (name in INT_GLOW_BUCKET_MAP) {
          buckets.interiorGlows.get(INT_GLOW_BUCKET_MAP[name])!.push(stdOrig);
        } else if (name === "Mat_Lamp_Warm") {
          buckets.outdoorLamps.push(stdOrig);
        } else if (name === "Mat_Floodlight") {
          buckets.floodlightHeads.push(stdOrig);
        } else if (name === "Mat_LED" || name === "Mat_StageLED") {
          buckets.ledSignage.push(stdOrig);
        }

        upgradedByName.set(name, stdOrig);
      }

      return orig;
    };

    root.traverse((obj) => {
      if (!(obj as THREE.Mesh).isMesh) return;
      const mesh = obj as THREE.Mesh;

      const geo = mesh.geometry;
      if (this.loadOrm && geo && geo.attributes.uv && !geo.attributes.uv2) {
        geo.setAttribute("uv2", geo.attributes.uv);
      }

      if (Array.isArray(mesh.material)) {
        mesh.material = mesh.material.map(upgradeOne);
      } else if (mesh.material) {
        mesh.material = upgradeOne(mesh.material);
      }

      const firstMat = Array.isArray(mesh.material) ? mesh.material[0] : mesh.material;
      const matName = firstMat?.name ?? "";
      const isTranslucent =
        matName === "Mat_Glass_Physical" ||
        matName === "Mat_WarmGlass_Physical" ||
        matName === "Mat_RockeryWater" ||
        matName === "Mat_WaterfallStream" ||
        matName === "Mat_FenceMesh";

      mesh.castShadow = !isTranslucent;
      mesh.receiveShadow = matName !== "Mat_Glass_Physical";
    });

    return buckets;
  }

  public tick(
    elapsedSec: number,
    wetness: number,
    snow: number,
    windStrength: number,
    nightFactor: number,
    waterMaterials: THREE.MeshStandardMaterial[]
  ): void {
    this.sharedUniforms.uTime.value = elapsedSec;
    this.sharedUniforms.uWetness.value = wetness;
    this.sharedUniforms.uSnow.value = snow;
    this.sharedUniforms.uWindStrength.value = windStrength;
    this.sharedUniforms.uNightFactor.value = nightFactor;

    for (const wm of waterMaterials) {
      if (wm.normalMap) {
        const speed = wm.name === "Mat_WaterfallStream" ? 0.45 : 0.045;
        wm.normalMap.offset.set(elapsedSec * speed * 0.6, elapsedSec * speed);
      }
    }
  }

  public dispose(): void {
    for (const tex of this.textureCache.values()) {
      tex.dispose();
    }
    this.textureCache.clear();
  }
}

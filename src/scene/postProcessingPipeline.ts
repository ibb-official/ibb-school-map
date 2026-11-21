import * as THREE from "three";
import {
  BlendFunction,
  BloomEffect,
  Effect,
  EffectComposer,
  EffectPass,
  KernelSize,
  NormalPass,
  OutlineEffect,
  RenderPass,
  SMAAEffect,
  SMAAPreset,
  ToneMappingEffect,
  ToneMappingMode,
} from "postprocessing";
import { N8AOPostPass } from "n8ao";
import { QualityTier } from "@/data/types";

/**
 * Custom WebGL2 Screen-Space Ray-Traced Reflections (SSR) + Single-Bounce
 * Global Illumination Color Bleeding (SSGI) Effect.
 *
 * Uses the depth buffer + NormalPass view-space normals to trace local rays across:
 * - Wet rain-slicked ground, puddles, polished marble & water surfaces (crisp SSR)
 * - Sunlit terracotta/brick walls & bright night window spill (subtle SSGI bounce)
 */
const CAMPUS_RT_FRAG = /* glsl */ `
  uniform sampler2D uNormalBuffer;
  uniform mat4 uProjectionMatrix;
  uniform mat4 uInvProjectionMatrix;
  uniform mat4 uInvViewMatrix;
  uniform float uWetness;
  uniform float uNightFactor;
  uniform float uSsrStrength;
  uniform float uSsgiStrength;

  vec3 reconstructViewPos(vec2 uv, float depth) {
    vec4 ndc = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 vp = uInvProjectionMatrix * ndc;
    return vp.xyz / max(vp.w, 1e-5);
  }

  vec2 projectToUv(vec3 viewPos) {
    vec4 clip = uProjectionMatrix * vec4(viewPos, 1.0);
    vec2 ndc = clip.xy / max(clip.w, 1e-5);
    return ndc * 0.5 + 0.5;
  }

  void mainImage(const in vec4 inputColor, const in vec2 uv, const in float depth, out vec4 outputColor) {
    if (depth >= 0.9995 || (uSsrStrength <= 0.001 && uSsgiStrength <= 0.001)) {
      outputColor = inputColor;
      return;
    }

    vec3 encN = texture2D(uNormalBuffer, uv).xyz;
    vec3 rawN = encN * 2.0 - 1.0;
    if (dot(rawN, rawN) < 0.001) {
      outputColor = inputColor;
      return;
    }
    vec3 viewNormal = normalize(rawN);
    vec3 worldNormal = normalize(mat3(uInvViewMatrix) * viewNormal);
    vec3 viewPos = reconstructViewPos(uv, depth);
    vec3 viewDir = normalize(viewPos);

    vec3 col = inputColor.rgb;

    // 1. Screen-Space Reflections on wet ground, puddles, marble & glossy facades
    if (uSsrStrength > 0.001) {
      float upReflect = smoothstep(0.65, 0.96, worldNormal.y) * (0.14 + 0.86 * uWetness);
      float fresnel = pow(1.0 - clamp(dot(-viewDir, viewNormal), 0.0, 1.0), 3.4);
      // Slight glossy Fresnel reflection on vertical glass/marble + strong wet horizontal reflections
      float reflWeight = clamp(upReflect * (0.28 + 0.65 * fresnel) + (1.0 - upReflect) * fresnel * 0.16, 0.0, 0.72) * uSsrStrength;

      if (reflWeight > 0.02) {
        vec3 reflDir = normalize(reflect(viewDir, viewNormal));
        // Only march rays traveling roughly forward/into scene
        if (reflDir.z < 0.35) {
          float stepScale = clamp(abs(viewPos.z) * 0.032, 0.35, 3.2);
          vec3 rayPos = viewPos + viewNormal * 0.08;
          vec3 hitCol = vec3(0.0);
          float hitWeight = 0.0;

          for (int i = 1; i <= 14; i++) {
            float fi = float(i);
            rayPos += reflDir * stepScale * (0.7 + fi * 0.14);
            vec2 hitUv = projectToUv(rayPos);
            if (hitUv.x <= 0.01 || hitUv.x >= 0.99 || hitUv.y <= 0.01 || hitUv.y >= 0.99) {
              break;
            }
            float sampleDepth = readDepth(hitUv);
            if (sampleDepth >= 0.9995) {
              continue;
            }
            vec3 samplePos = reconstructViewPos(hitUv, sampleDepth);
            float dz = samplePos.z - rayPos.z;
            if (dz > 0.0 && dz < stepScale * 2.2) {
              float edgeFade = smoothstep(0.0, 0.12, min(min(hitUv.x, 1.0 - hitUv.x), min(hitUv.y, 1.0 - hitUv.y)));
              float distFade = 1.0 - fi / 15.0;
              hitCol = texture2D(inputBuffer, hitUv).rgb;
              hitWeight = edgeFade * distFade;
              break;
            }
          }

          if (hitWeight > 0.001) {
            // Boost reflections of bright nighttime windows/lamps on wet ground
            float nightPop = 1.0 + uNightFactor * 0.45;
            col = mix(col, hitCol * nightPop, clamp(reflWeight * hitWeight, 0.0, 0.62));
          }
        }
      }
    }

    // 2. Single-Bounce Screen-Space Global Illumination (Color Bleeding)
    if (uSsgiStrength > 0.001) {
      vec3 giAccum = vec3(0.0);
      float wSum = 0.0;
      float radius = clamp(0.048 / max(abs(viewPos.z) * 0.022, 0.45), 0.012, 0.055);
      // 8 Golden-angle spiral screen taps for smooth, noise-free indirect color bleed
      const float GOLDEN = 2.39996323;
      for (int k = 0; k < 8; k++) {
        float fk = float(k) + 0.5;
        float r = radius * sqrt(fk / 8.0);
        float ang = fk * GOLDEN + uv.x * 12.0 + uv.y * 19.0;
        vec2 tapUv = clamp(uv + vec2(cos(ang), sin(ang)) * r, vec2(0.005), vec2(0.995));
        float tapDepth = readDepth(tapUv);
        if (tapDepth >= 0.9992) continue;
        vec3 tapPos = reconstructViewPos(tapUv, tapDepth);
        vec3 delta = tapPos - viewPos;
        float dist = length(delta);
        if (dist < 0.05 || dist > 14.0) continue;
        vec3 dirToTap = delta / dist;
        float ndl = max(dot(viewNormal, dirToTap), 0.0);
        if (ndl > 0.05) {
          vec3 tapCol = texture2D(inputBuffer, tapUv).rgb;
          float lum = dot(tapCol, vec3(0.2126, 0.7152, 0.0722));
          // Favor bright emissive windows, warm sunlit facades & terracotta bounce
          float atten = 1.0 / (1.0 + dist * dist * 0.18);
          float w = ndl * atten * (0.55 + clamp(lum, 0.0, 2.5));
          giAccum += tapCol * w;
          wSum += w;
        }
      }
      if (wSum > 0.001) {
        vec3 indirect = (giAccum / max(wSum, 1.0)) * (0.24 + 0.14 * uNightFactor) * uSsgiStrength;
        col += indirect * clamp(inputColor.rgb + vec3(0.18), vec3(0.0), vec3(1.0));
      }
    }

    outputColor = vec4(col, inputColor.a);
  }
`;

class CampusRayTraceEffect extends Effect {
  constructor(normalTexture: THREE.Texture) {
    super("CampusRayTraceEffect", CAMPUS_RT_FRAG, {
      blendFunction: BlendFunction.NORMAL,
      attributes: 1, // EffectAttribute.DEPTH
      uniforms: new Map<string, THREE.Uniform>([
        ["uNormalBuffer", new THREE.Uniform(normalTexture)],
        ["uProjectionMatrix", new THREE.Uniform(new THREE.Matrix4())],
        ["uInvProjectionMatrix", new THREE.Uniform(new THREE.Matrix4())],
        ["uInvViewMatrix", new THREE.Uniform(new THREE.Matrix4())],
        ["uWetness", new THREE.Uniform(0)],
        ["uNightFactor", new THREE.Uniform(0)],
        ["uSsrStrength", new THREE.Uniform(0.85)],
        ["uSsgiStrength", new THREE.Uniform(0.75)],
      ]),
    });
  }

  public sync(
    camera: THREE.PerspectiveCamera,
    wetness: number,
    nightFactor: number,
    ssrStrength: number,
    ssgiStrength: number
  ): void {
    (this.uniforms.get("uProjectionMatrix")!.value as THREE.Matrix4).copy(camera.projectionMatrix);
    (this.uniforms.get("uInvProjectionMatrix")!.value as THREE.Matrix4).copy(camera.projectionMatrixInverse);
    (this.uniforms.get("uInvViewMatrix")!.value as THREE.Matrix4).copy(camera.matrixWorld);
    this.uniforms.get("uWetness")!.value = wetness;
    this.uniforms.get("uNightFactor")!.value = nightFactor;
    this.uniforms.get("uSsrStrength")!.value = ssrStrength;
    this.uniforms.get("uSsgiStrength")!.value = ssgiStrength;
  }
}

export class PostProcessingPipeline {
  public readonly composer: EffectComposer;
  private readonly normalPass: NormalPass;
  private readonly n8aoPass: N8AOPostPass;
  private readonly rtEffect: CampusRayTraceEffect;
  private readonly bloomEffect: BloomEffect;
  private readonly outlineEffect: OutlineEffect;
  private readonly camera: THREE.PerspectiveCamera;
  private quality: QualityTier;

  constructor(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    camera: THREE.PerspectiveCamera,
    width: number,
    height: number,
    quality: QualityTier
  ) {
    this.camera = camera;
    this.quality = quality;

    this.composer = new EffectComposer(renderer, {
      frameBufferType: THREE.HalfFloatType,
      multisampling: quality === "smooth" ? 0 : 4,
    });

    const renderPass = new RenderPass(scene, camera);
    this.composer.addPass(renderPass);

    // NormalPass supplies smooth view-space normals to CampusRayTraceEffect (SSR + SSGI)
    this.normalPass = new NormalPass(scene, camera);
    this.composer.addPass(this.normalPass);

    // High-performance Ground-Truth style Ambient Occlusion (N8AO)
    this.n8aoPass = new N8AOPostPass(scene, camera, width, height);
    this.n8aoPass.configuration.aoRadius = 1.65;
    this.n8aoPass.configuration.distanceFalloff = 1.15;
    this.n8aoPass.configuration.intensity = 1.95;
    this.n8aoPass.configuration.gammaCorrection = false; // ToneMappingEffect handles final output encoding
    this.composer.addPass(this.n8aoPass);

    // Screen-Space Reflections + Single-Bounce GI
    this.rtEffect = new CampusRayTraceEffect(this.normalPass.texture);

    // Crisp non-destructive selection/hover outline (preserves glass & interior lights!)
    this.outlineEffect = new OutlineEffect(scene, camera, {
      blendFunction: BlendFunction.SCREEN,
      edgeStrength: 2.8,
      pulseSpeed: 0.0,
      visibleEdgeColor: 0xf59e0b,
      hiddenEdgeColor: 0x38bdf8,
      multisampling: 0,
      resolutionScale: 0.75,
      blur: false,
      xRay: true,
    });

    // Cinematic HDR Mipmap Bloom (makes sunset sun, night windows, streetlamps & LED boards softly glow)
    this.bloomEffect = new BloomEffect({
      mipmapBlur: true,
      luminanceThreshold: 1.05,
      luminanceSmoothing: 0.28,
      intensity: 0.48,
      radius: 0.62,
      kernelSize: KernelSize.MEDIUM,
    });

    const toneMappingEffect = new ToneMappingEffect({
      mode: ToneMappingMode.AGX,
    });

    const smaaEffect = new SMAAEffect({
      preset: quality === "cinematic" ? SMAAPreset.HIGH : SMAAPreset.MEDIUM,
    });

    const mainEffectPass = new EffectPass(
      camera,
      this.rtEffect,
      this.outlineEffect,
      this.bloomEffect,
      toneMappingEffect,
      smaaEffect
    );
    this.composer.addPass(mainEffectPass);

    this.setQuality(quality);
  }

  public setQuality(quality: QualityTier): void {
    this.quality = quality;
    if (quality === "smooth") {
      this.n8aoPass.setQualityMode("Performance");
      this.n8aoPass.configuration.halfRes = true;
      this.n8aoPass.configuration.intensity = 1.55;
      this.normalPass.enabled = false;
    } else if (quality === "refined") {
      this.n8aoPass.setQualityMode("Medium");
      this.n8aoPass.configuration.halfRes = true;
      this.n8aoPass.configuration.intensity = 1.95;
      this.normalPass.enabled = true;
    } else {
      this.n8aoPass.setQualityMode("High");
      this.n8aoPass.configuration.halfRes = false;
      this.n8aoPass.configuration.intensity = 2.15;
      this.normalPass.enabled = true;
    }
  }

  public setHighlightedObjects(objects: THREE.Object3D[], mode: "selected" | "hovered" | "none"): void {
    this.outlineEffect.selection.clear();
    if (mode === "none" || objects.length === 0) return;
    this.outlineEffect.visibleEdgeColor.setHex(mode === "selected" ? 0xf59e0b : 0x38bdf8);
    this.outlineEffect.hiddenEdgeColor.setHex(mode === "selected" ? 0xb45309 : 0x0284c7);
    this.outlineEffect.selection.set(objects);
  }

  public updateFrame(wetness: number, nightFactor: number, twilightGlow: number): void {
    const ssrStrength =
      this.quality === "smooth" ? 0.0 : this.quality === "refined" ? 0.82 : 1.0;
    const ssgiStrength =
      this.quality === "cinematic" ? 0.85 : this.quality === "refined" ? 0.35 : 0.0;

    this.rtEffect.sync(this.camera, wetness, nightFactor, ssrStrength, ssgiStrength);
    // Night & golden hour get slightly richer bloom for lamps, glowing classroom windows & sunset sky
    this.bloomEffect.intensity = 0.38 + nightFactor * 0.42 + twilightGlow * 0.22;
    this.bloomEffect.luminanceMaterial.threshold = 1.08 - nightFactor * 0.16;
  }

  public render(dt: number): void {
    this.composer.render(dt);
  }

  public setSize(width: number, height: number): void {
    this.composer.setSize(width, height);
    this.n8aoPass.setSize(width, height);
  }

  public dispose(): void {
    this.composer.dispose();
  }
}

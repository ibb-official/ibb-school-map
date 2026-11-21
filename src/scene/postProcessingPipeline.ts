import * as THREE from "three";
import {
  BlendFunction,
  BloomEffect,
  Effect,
  EffectAttribute,
  EffectComposer,
  EffectPass,
  KernelSize,
  NormalPass,
  OutlineEffect,
  RenderPass,
  ToneMappingEffect,
  ToneMappingMode,
} from "postprocessing";
import { N8AOPostPass } from "n8ao";
import { QualityTier } from "@/data/types";

/**
 * Physically restrained WebGL2 Screen-Space Reflections (SSR) for rain-wet ground &
 * glossy surfaces + smooth clamped single-bounce GI (Ultra mode only).
 *
 * Designed specifically for zero shimmer / zero light-pumping when orbiting or zooming:
 * - Dry matte walls/roofs do NOT receive noisy SSR
 * - Ray stepping uses smooth depth-tolerant intersection without screen-UV phase jitter
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

    // 1. Clean Screen-Space Reflections strictly on rain-wet ground/puddles (zero dry-concrete shimmer!)
    if (uSsrStrength > 0.001 && uWetness > 0.05) {
      float upReflect = smoothstep(0.74, 0.96, worldNormal.y) * uWetness;
      float fresnel = pow(1.0 - clamp(dot(-viewDir, viewNormal), 0.0, 1.0), 3.6);
      float reflWeight = clamp(upReflect * (0.24 + 0.58 * fresnel), 0.0, 0.62) * uSsrStrength;

      if (reflWeight > 0.025) {
        vec3 reflDir = normalize(reflect(viewDir, viewNormal));
        if (reflDir.z < 0.25) {
          float stepScale = clamp(abs(viewPos.z) * 0.024, 0.3, 2.2);
          vec3 rayPos = viewPos + viewNormal * 0.1;
          vec3 hitCol = vec3(0.0);
          float hitWeight = 0.0;

          for (int i = 1; i <= 20; i++) {
            float fi = float(i);
            rayPos += reflDir * stepScale * (0.65 + fi * 0.1);
            vec2 hitUv = projectToUv(rayPos);
            if (hitUv.x <= 0.02 || hitUv.x >= 0.98 || hitUv.y <= 0.02 || hitUv.y >= 0.98) {
              break;
            }
            float sampleDepth = readDepth(hitUv);
            if (sampleDepth >= 0.9995) {
              continue;
            }
            vec3 samplePos = reconstructViewPos(hitUv, sampleDepth);
            float dz = samplePos.z - rayPos.z;
            if (dz > 0.0 && dz < stepScale * 2.0) {
              float edgeFade = smoothstep(0.02, 0.16, min(min(hitUv.x, 1.0 - hitUv.x), min(hitUv.y, 1.0 - hitUv.y)));
              float distFade = 1.0 - fi / 21.0;
              hitCol = texture2D(inputBuffer, hitUv).rgb;
              hitWeight = edgeFade * distFade;
              break;
            }
          }

          if (hitWeight > 0.001) {
            float nightPop = 1.0 + uNightFactor * 0.4;
            col = mix(col, hitCol * nightPop, clamp(reflWeight * hitWeight, 0.0, 0.56));
          }
        }
      }
    }

    // 2. Smooth, bounded single-bounce indirect color bleed (Ultra quality only; fixed tap angles prevent shimmer)
    if (uSsgiStrength > 0.001) {
      vec3 giAccum = vec3(0.0);
      float wSum = 0.0;
      float radius = 0.028;
      const float GOLDEN = 2.39996323;
      for (int k = 0; k < 12; k++) {
        float fk = float(k) + 0.5;
        float r = radius * sqrt(fk / 12.0);
        float ang = fk * GOLDEN;
        vec2 tapUv = clamp(uv + vec2(cos(ang), sin(ang)) * r, vec2(0.01), vec2(0.99));
        float tapDepth = readDepth(tapUv);
        if (tapDepth >= 0.9992) continue;
        vec3 tapPos = reconstructViewPos(tapUv, tapDepth);
        vec3 delta = tapPos - viewPos;
        float dist = length(delta);
        if (dist < 0.15 || dist > 9.0) continue;
        vec3 dirToTap = delta / dist;
        float ndl = max(dot(viewNormal, dirToTap), 0.0);
        if (ndl > 0.1) {
          vec3 tapCol = min(texture2D(inputBuffer, tapUv).rgb, vec3(2.5));
          float atten = 1.0 / (1.0 + dist * dist * 0.28);
          float w = ndl * atten;
          giAccum += tapCol * w;
          wSum += w;
        }
      }
      if (wSum > 0.001) {
        vec3 indirect = (giAccum / max(wSum, 1.8)) * (0.14 + 0.10 * uNightFactor) * uSsgiStrength;
        col += indirect * clamp(inputColor.rgb + vec3(0.12), vec3(0.0), vec3(0.85));
      }
    }

    outputColor = vec4(col, inputColor.a);
  }
`;

/**
 * Contrast-Adaptive Sharpening (CAS-inspired) pass executed AFTER tone mapping.
 * Restores photographic crispness to brickwork mortar, engraved stone plaques,
 * window mullions, and botanical foliage without white halo ringing.
 */
const CAMPUS_SHARPEN_FRAG = /* glsl */ `
  uniform float uSharpness;

  void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
    if (uSharpness <= 0.001) {
      outputColor = inputColor;
      return;
    }

    vec3 c = inputColor.rgb;
    vec3 n = texture2D(inputBuffer, uv + vec2(0.0, texelSize.y)).rgb;
    vec3 s = texture2D(inputBuffer, uv - vec2(0.0, texelSize.y)).rgb;
    vec3 e = texture2D(inputBuffer, uv + vec2(texelSize.x, 0.0)).rgb;
    vec3 w = texture2D(inputBuffer, uv - vec2(texelSize.x, 0.0)).rgb;

    vec3 mn = min(c, min(min(n, s), min(e, w)));
    vec3 mx = max(c, max(max(n, s), max(e, w)));

    // Adaptive gain reduces sharpening automatically across extreme high-contrast silhouettes to avoid ringing
    vec3 amp = clamp(min(mn, 1.0 - mx) / max(mx, vec3(1e-4)), 0.0, 1.0);
    amp = sqrt(amp);
    vec3 weight = amp * (-0.16 * uSharpness);

    vec3 sharpened = (c + (n + s + e + w) * weight) / (1.0 + 4.0 * weight);
    outputColor = vec4(clamp(sharpened, 0.0, 1.0), inputColor.a);
  }
`;

class CampusRayTraceEffect extends Effect {
  constructor(normalTexture: THREE.Texture) {
    super("CampusRayTraceEffect", CAMPUS_RT_FRAG, {
      blendFunction: BlendFunction.NORMAL,
      attributes: EffectAttribute.DEPTH,
      uniforms: new Map<string, THREE.Uniform>([
        ["uNormalBuffer", new THREE.Uniform(normalTexture)],
        ["uProjectionMatrix", new THREE.Uniform(new THREE.Matrix4())],
        ["uInvProjectionMatrix", new THREE.Uniform(new THREE.Matrix4())],
        ["uInvViewMatrix", new THREE.Uniform(new THREE.Matrix4())],
        ["uWetness", new THREE.Uniform(0)],
        ["uNightFactor", new THREE.Uniform(0)],
        ["uSsrStrength", new THREE.Uniform(0.0)],
        ["uSsgiStrength", new THREE.Uniform(0.0)],
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

class CampusSharpenEffect extends Effect {
  constructor() {
    super("CampusSharpenEffect", CAMPUS_SHARPEN_FRAG, {
      blendFunction: BlendFunction.NORMAL,
      attributes: EffectAttribute.CONVOLUTION,
      uniforms: new Map<string, THREE.Uniform>([
        ["uSharpness", new THREE.Uniform(0.2)],
      ]),
    });
  }

  public setSharpness(value: number): void {
    this.uniforms.get("uSharpness")!.value = value;
  }
}

export class PostProcessingPipeline {
  public readonly composer: EffectComposer;
  private readonly normalPass: NormalPass;
  private readonly n8aoPass: N8AOPostPass;
  private readonly rtEffect: CampusRayTraceEffect;
  private readonly bloomEffect: BloomEffect;
  private readonly outlineEffect: OutlineEffect;
  private readonly sharpenEffect: CampusSharpenEffect;
  private readonly camera: THREE.PerspectiveCamera;
  private readonly maxMsaaSamples: number;
  private readonly isMobileTier: boolean;
  private quality: QualityTier;

  constructor(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    camera: THREE.PerspectiveCamera,
    width: number,
    height: number,
    quality: QualityTier,
    isMobileTier = false
  ) {
    this.camera = camera;
    this.quality = quality;
    this.isMobileTier = isMobileTier;
    this.maxMsaaSamples = Math.min(4, renderer.capabilities.maxSamples || 0);

    // Hardware WebGL2 MSAA delivers crisp subpixel edges without post-process SMAA texture blur;
    // on mobile "smooth" tier keep MSAA at 0 to preserve 60fps & battery life.
    this.composer = new EffectComposer(renderer, {
      frameBufferType: THREE.HalfFloatType,
      multisampling:
        quality === "smooth"
          ? isMobileTier
            ? 0
            : Math.min(2, this.maxMsaaSamples)
          : isMobileTier && quality === "refined"
            ? Math.min(2, this.maxMsaaSamples)
            : this.maxMsaaSamples,
    });

    const renderPass = new RenderPass(scene, camera);
    this.composer.addPass(renderPass);

    // NormalPass supplies smooth view-space normals to CampusRayTraceEffect when SSR/SSGI is active
    this.normalPass = new NormalPass(scene, camera);
    this.composer.addPass(this.normalPass);

    // Tight full-resolution HiDPI architectural contact AO (must use drawingBufferSize, never CSS pixels!)
    const drawingSize = renderer.getDrawingBufferSize(new THREE.Vector2());
    this.n8aoPass = new N8AOPostPass(
      scene,
      camera,
      Math.max(1, drawingSize.x),
      Math.max(1, drawingSize.y)
    );
    this.n8aoPass.configuration.aoRadius = 0.95;
    this.n8aoPass.configuration.distanceFalloff = 1.0;
    this.n8aoPass.configuration.intensity = 1.35;
    this.n8aoPass.configuration.halfRes = isMobileTier && quality === "smooth";
    this.n8aoPass.configuration.gammaCorrection = false; // ToneMappingEffect handles final output encoding
    this.composer.addPass(this.n8aoPass);

    this.rtEffect = new CampusRayTraceEffect(this.normalPass.texture);

    // Full-resolution non-destructive selection/hover outline (0.5x scale on mobile for faster GPU fill)
    this.outlineEffect = new OutlineEffect(scene, camera, {
      blendFunction: BlendFunction.SCREEN,
      edgeStrength: 2.6,
      pulseSpeed: 0.0,
      visibleEdgeColor: 0xf59e0b,
      hiddenEdgeColor: 0x38bdf8,
      multisampling: 0,
      resolutionScale: isMobileTier ? 0.5 : 1.0,
      blur: false,
      xRay: true,
    });

    // High-threshold HDR Mipmap Bloom (daylight architecture stays razor-sharp; sunset & night lamps glow!)
    this.bloomEffect = new BloomEffect({
      mipmapBlur: true,
      luminanceThreshold: 1.65,
      luminanceSmoothing: 0.22,
      intensity: 0.18,
      radius: 0.42,
      kernelSize: isMobileTier ? KernelSize.SMALL : KernelSize.MEDIUM,
    });

    const toneMappingEffect = new ToneMappingEffect({
      mode: ToneMappingMode.AGX,
    });

    const mainEffectPass = new EffectPass(
      camera,
      this.rtEffect,
      this.outlineEffect,
      this.bloomEffect,
      toneMappingEffect
    );
    this.composer.addPass(mainEffectPass);

    // Post-tonemap Contrast-Adaptive Sharpening for ultra-crisp brickwork, mullions & engraved signage
    this.sharpenEffect = new CampusSharpenEffect();
    const sharpenPass = new EffectPass(camera, this.sharpenEffect);
    this.composer.addPass(sharpenPass);

    this.setQuality(quality);
    // Sync all internal pass targets (including N8AOPostPass) to exact HiDPI drawingBufferSize
    this.composer.setSize(width, height, false);
  }

  public setQuality(quality: QualityTier): void {
    this.quality = quality;
    if (quality === "smooth") {
      this.composer.multisampling = this.isMobileTier
        ? 0
        : Math.min(2, this.maxMsaaSamples);
      this.n8aoPass.setQualityMode("Performance");
      this.n8aoPass.configuration.halfRes = this.isMobileTier;
      this.n8aoPass.configuration.denoiseRadius = 4;
      this.n8aoPass.configuration.aoRadius = 0.9;
      this.n8aoPass.configuration.intensity = 1.1;
      this.sharpenEffect.setSharpness(0.08);
      this.normalPass.enabled = false;
    } else if (quality === "refined") {
      this.composer.multisampling = this.isMobileTier
        ? Math.min(2, this.maxMsaaSamples)
        : this.maxMsaaSamples;
      this.n8aoPass.setQualityMode("Medium");
      this.n8aoPass.configuration.halfRes = false;
      this.n8aoPass.configuration.denoiseRadius = 4;
      this.n8aoPass.configuration.aoRadius = 0.95;
      this.n8aoPass.configuration.intensity = 1.35;
      this.sharpenEffect.setSharpness(0.22);
      this.normalPass.enabled = false; // Enabled dynamically only when wet rain puddles need SSR
    } else {
      // Ultra High Quality ("极致画质"): 4x MSAA + Ultra full-res N8AO + SSR/SSGI + crisp CAS sharpening
      this.composer.multisampling = this.maxMsaaSamples;
      this.n8aoPass.setQualityMode("Ultra");
      this.n8aoPass.configuration.halfRes = false;
      this.n8aoPass.configuration.denoiseRadius = 4;
      this.n8aoPass.configuration.aoRadius = 0.95;
      this.n8aoPass.configuration.intensity = 1.5;
      this.sharpenEffect.setSharpness(0.42);
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
    const needWetSsr = this.quality !== "smooth" && wetness > 0.05;
    const needSsgi = this.quality === "cinematic";
    this.normalPass.enabled = needWetSsr || needSsgi;

    const ssrStrength = needWetSsr ? (this.quality === "cinematic" ? 1.0 : 0.8) : 0.0;
    const ssgiStrength = needSsgi ? 0.65 : 0.0;

    this.rtEffect.sync(this.camera, wetness, nightFactor, ssrStrength, ssgiStrength);

    // Keep daylight razor-sharp (high threshold 1.65, low intensity 0.16); let sunset & night lamps bloom gracefully
    this.bloomEffect.intensity = 0.16 + nightFactor * 0.44 + twilightGlow * 0.16;
    this.bloomEffect.luminanceMaterial.threshold = 1.65 - nightFactor * 0.58 - twilightGlow * 0.18;
  }

  public render(dt: number): void {
    this.composer.render(dt);
  }

  public setSize(width: number, height: number): void {
    // EffectComposer automatically converts CSS width/height to HiDPI drawingBufferSize
    // and forwards drawingBufferSize to every pass (including N8AOPostPass).
    // Never overwrite n8aoPass.setSize with raw CSS pixels!
    this.composer.setSize(width, height, false);
  }

  public dispose(): void {
    this.composer.dispose();
  }
}

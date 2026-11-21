import * as THREE from "three";
import { SolarAtmosphereSample } from "./sunAstronomy";

const SKY_DOME_VERT = /* glsl */ `
  varying vec3 vWorldDir;
  void main() {
    vec4 wp = modelMatrix * vec4(position, 1.0);
    vWorldDir = normalize(position);
    gl_Position = projectionMatrix * viewMatrix * wp;
  }
`;

/**
 * Physically inspired Rayleigh + Mie atmospheric sky dome with:
 * - Crisp solar disk & circumsolar aureole
 * - Rich sunrise/sunset golden-crimson horizon scattering (朝霞 / 晚霞)
 * - Procedural multi-octave FBM volumetric-feel clouds lit from underneath by low sun (火烧云)
 * - Sparkling night starfield + soft lunar halo
 */
const SKY_DOME_FRAG = /* glsl */ `
  uniform vec3 uSunDir;
  uniform vec3 uMoonDir;
  uniform float uNightFactor;
  uniform float uTwilightGlow;
  uniform float uCloudCoverage;
  uniform vec3 uCloudTint;
  uniform vec3 uFogColor;
  uniform float uTime;
  uniform float uWeatherDarken;

  varying vec3 vWorldDir;

  float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
  }

  float vnoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash21(i);
    float b = hash21(i + vec2(1.0, 0.0));
    float c = hash21(i + vec2(0.0, 1.0));
    float d = hash21(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
  }

  float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.52;
    mat2 rot = mat2(0.80, -0.60, 0.60, 0.80);
    for (int i = 0; i < 5; i++) {
      v += a * vnoise(p);
      p = rot * p * 2.04 + vec2(11.3, 7.1);
      a *= 0.50;
    }
    return v;
  }

  void main() {
    vec3 dir = normalize(vWorldDir);
    float elev = clamp(dir.y, -0.2, 1.0);
    float up = max(dir.y, 0.0);

    // 1. Atmospheric Zenith -> Mid -> Horizon gradient across day, golden hour, blue hour & night
    vec3 dayZenith = vec3(0.11, 0.34, 0.72);
    vec3 dayMid = vec3(0.36, 0.62, 0.90);
    vec3 dayHorizon = vec3(0.76, 0.87, 0.96);

    vec3 twZenith = vec3(0.13, 0.19, 0.42);
    vec3 twMid = vec3(0.56, 0.33, 0.44);
    vec3 twHorizon = vec3(1.15, 0.48, 0.22);

    vec3 nightZenith = vec3(0.012, 0.022, 0.055);
    vec3 nightMid = vec3(0.024, 0.042, 0.095);
    vec3 nightHorizon = vec3(0.055, 0.075, 0.135);

    vec3 zenithCol = mix(mix(dayZenith, twZenith, uTwilightGlow * 0.88), nightZenith, uNightFactor);
    vec3 midCol = mix(mix(dayMid, twMid, uTwilightGlow * 0.90), nightMid, uNightFactor);
    vec3 horizonCol = mix(mix(dayHorizon, twHorizon, uTwilightGlow * 0.95), nightHorizon, uNightFactor);

    // Directional sunrise/sunset warm belt near sun azimuth
    vec3 sunDirN = normalize(uSunDir);
    float sunDot = max(dot(dir, sunDirN), 0.0);
    float horizSunBias = pow(max(dot(normalize(vec3(dir.x, 0.0, dir.z)), normalize(vec3(sunDirN.x, 0.0, sunDirN.z))), 0.0), 3.0);

    float hCurve = pow(1.0 - up, 3.2);
    float midCurve = pow(1.0 - up, 1.25);
    vec3 sky = mix(zenithCol, midCol, midCurve);
    sky = mix(sky, horizonCol, hCurve);

    // Mie forward scatter glow (creates radiant golden/pink sunrise & sunset dome)
    vec3 glowTint = mix(vec3(1.0, 0.94, 0.82), vec3(1.35, 0.52, 0.18), uTwilightGlow);
    float mieHalo = pow(sunDot, 7.0) * (0.28 + 0.85 * uTwilightGlow) * (1.0 - uNightFactor * 0.92);
    float wideSpread = horizSunBias * pow(1.0 - up, 2.2) * uTwilightGlow * 0.55;
    sky += glowTint * (mieHalo + wideSpread) * (1.0 - uWeatherDarken * 0.65);

    // Crisp solar disk (softened under heavy overcast/rain)
    float sunVis = smoothstep(-0.02, 0.03, sunDirN.y) * (1.0 - uWeatherDarken * 0.82);
    float sunDisk = smoothstep(0.99935, 0.99982, sunDot) * 10.0 * sunVis;
    float sunCorona = pow(sunDot, 160.0) * 1.8 * sunVis;
    sky += mix(vec3(1.0, 0.96, 0.88), vec3(1.0, 0.62, 0.28), uTwilightGlow) * (sunDisk + sunCorona);

    // Night stars & subtle lunar disk
    if (uNightFactor > 0.15 && up > 0.03) {
      vec3 moonDirN = normalize(uMoonDir);
      float moonDot = max(dot(dir, moonDirN), 0.0);
      float moonDisk = smoothstep(0.9995, 0.99985, moonDot) * 2.2 * uNightFactor * (1.0 - uWeatherDarken * 0.8);
      float moonHalo = pow(moonDot, 48.0) * 0.22 * uNightFactor * (1.0 - uWeatherDarken * 0.7);
      sky += vec3(0.78, 0.88, 1.0) * (moonDisk + moonHalo);

      // Crisp procedural starfield attenuated near horizon and by cloud cover
      vec2 starGrid = floor(dir.xz / max(dir.y + 0.12, 0.12) * 210.0);
      float starRand = hash21(starGrid);
      if (starRand > 0.9955) {
        float twinkle = 0.65 + 0.35 * sin(uTime * 2.2 + starRand * 120.0);
        float starBright = smoothstep(0.9955, 0.9998, starRand) * twinkle * uNightFactor * smoothstep(0.05, 0.35, up) * (1.0 - uCloudCoverage * 0.85);
        sky += vec3(0.86, 0.92, 1.0) * starBright * 1.3;
      }
    }

    // 2. Volumetric-feel FBM Clouds with low-sun under-lighting (火烧云 / 朝霞晚霞)
    if (dir.y > 0.015) {
      vec2 cloudUV = dir.xz / (dir.y + 0.14) * 0.58 + vec2(uTime * 0.0045, uTime * 0.0018);
      float n1 = fbm(cloudUV);
      float n2 = fbm(cloudUV * 2.35 - vec2(uTime * 0.003, 0.0));
      float density = n1 * 0.72 + n2 * 0.28;
      float threshold = mix(0.68, 0.32, clamp(uCloudCoverage, 0.0, 1.0));
      float cloudMask = smoothstep(threshold, threshold + 0.24, density);
      // Fade clouds gently into distant horizon haze
      cloudMask *= smoothstep(0.015, 0.16, dir.y);

      // Cloud shading: bright silver lining toward sun, warm crimson under-lighting at dusk/dawn
      float sunOffset = fbm(cloudUV + normalize(sunDirN.xz + vec2(0.001)) * 0.12);
      float selfShadow = clamp((density - sunOffset) * 2.4 + 0.55, 0.2, 1.0);

      vec3 cloudBase = mix(vec3(0.94, 0.96, 1.0), vec3(0.10, 0.14, 0.23), uNightFactor);
      vec3 cloudShadowCol = mix(vec3(0.56, 0.64, 0.76), vec3(0.05, 0.07, 0.13), uNightFactor);
      vec3 fireCol = vec3(1.45, 0.44, 0.18);
      vec3 roseCol = vec3(1.05, 0.38, 0.44);

      vec3 litCloud = mix(cloudShadowCol, cloudBase, selfShadow);
      // Dramatic sunrise/sunset cloud bottom glow
      float fireWeight = uTwilightGlow * (0.45 + 0.55 * pow(sunDot, 2.2)) * (1.0 - uWeatherDarken * 0.55);
      litCloud = mix(litCloud, mix(roseCol, fireCol, pow(sunDot, 1.5)), fireWeight * 0.88);
      litCloud = mix(litCloud, uCloudTint, 0.26);

      // Silver lining rim when looking near sun
      litCloud += glowTint * pow(sunDot, 14.0) * (1.0 - cloudMask * 0.4) * 0.42 * (1.0 - uNightFactor);

      sky = mix(sky, litCloud, cloudMask * mix(0.82, 0.94, uCloudCoverage));
    }

    // 3. Weather overcast veiling & smooth horizon ground-apron blend
    sky = mix(sky, uFogColor * (1.0 - 0.1 * uNightFactor), uWeatherDarken * 0.42 * (1.0 - up * 0.5));
    if (elev < 0.02) {
      float below = smoothstep(0.02, -0.06, elev);
      sky = mix(sky, uFogColor * 0.82, below);
    }

    gl_FragColor = vec4(sky, 1.0);
  }
`;

export class AtmosphereSkySystem {
  public readonly domeMesh: THREE.Mesh;
  private readonly domeMaterial: THREE.ShaderMaterial;
  private readonly envScene: THREE.Scene;
  private readonly envDomeMaterial: THREE.ShaderMaterial;
  private readonly pmrem: THREE.PMREMGenerator;
  private envTarget: THREE.WebGLRenderTarget | null = null;
  private lastBakedKey = "";
  private lastBakeMs = 0;

  constructor(renderer: THREE.WebGLRenderer) {
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.pmrem.compileEquirectangularShader();

    const makeMat = () =>
      new THREE.ShaderMaterial({
        vertexShader: SKY_DOME_VERT,
        fragmentShader: SKY_DOME_FRAG,
        side: THREE.BackSide,
        depthWrite: false,
        fog: false,
        uniforms: {
          uSunDir: { value: new THREE.Vector3(0.5, 0.6, 0.4) },
          uMoonDir: { value: new THREE.Vector3(-0.4, 0.6, -0.4) },
          uNightFactor: { value: 0.0 },
          uTwilightGlow: { value: 0.0 },
          uCloudCoverage: { value: 0.28 },
          uCloudTint: { value: new THREE.Color(0xffffff) },
          uFogColor: { value: new THREE.Color(0xd0e2f4) },
          uTime: { value: 0.0 },
          uWeatherDarken: { value: 0.0 },
        },
      });

    this.domeMaterial = makeMat();
    const domeGeo = new THREE.SphereGeometry(520, 48, 32);
    this.domeMesh = new THREE.Mesh(domeGeo, this.domeMaterial);
    this.domeMesh.name = "__atmosphere_sky_dome";
    this.domeMesh.frustumCulled = false;
    this.domeMesh.renderOrder = -1000;

    // Dedicated lightweight scene for real-time PMREM HDR sky IBL baking
    this.envScene = new THREE.Scene();
    this.envDomeMaterial = makeMat();
    const envGeo = new THREE.SphereGeometry(40, 32, 20);
    const envMesh = new THREE.Mesh(envGeo, this.envDomeMaterial);
    this.envScene.add(envMesh);

    // Subtle ground bounce disc in envScene so upward-facing glass/metal reflects realistic campus ground tone
    const gndGeo = new THREE.CircleGeometry(39, 24);
    gndGeo.rotateX(-Math.PI / 2);
    const gndMat = new THREE.MeshBasicMaterial({ color: 0x3b3f46 });
    const gndDisc = new THREE.Mesh(gndGeo, gndMat);
    gndDisc.position.y = -2.0;
    this.envScene.add(gndDisc);
  }

  public update(
    sample: SolarAtmosphereSample,
    weatherDarken: number,
    elapsedSec: number,
    mainScene: THREE.Scene,
    forceBakeEnv = false
  ): void {
    const syncUniforms = (mat: THREE.ShaderMaterial) => {
      mat.uniforms.uSunDir.value.copy(sample.sunDir);
      mat.uniforms.uMoonDir.value.copy(sample.keyLightDir);
      mat.uniforms.uNightFactor.value = sample.nightFactor;
      mat.uniforms.uTwilightGlow.value = sample.twilightGlow;
      mat.uniforms.uCloudCoverage.value = sample.cloudCoverage;
      mat.uniforms.uCloudTint.value.copy(sample.cloudTint);
      mat.uniforms.uFogColor.value.copy(sample.fogColor);
      mat.uniforms.uTime.value = elapsedSec;
      mat.uniforms.uWeatherDarken.value = weatherDarken;
    };

    syncUniforms(this.domeMaterial);
    syncUniforms(this.envDomeMaterial);

    // Keep ground reflection disc matching day/night/snow luminance
    const gndObj = this.envScene.children[1] as THREE.Mesh | undefined;
    if (gndObj && gndObj.material instanceof THREE.MeshBasicMaterial) {
      gndObj.material.color.copy(sample.hemiGroundColor).multiplyScalar(sample.isNight ? 0.35 : 0.72);
    }

    // Throttled dynamic PMREM IBL re-bake when time/weather meaningfully shifts (max ~6 Hz during scrubbing)
    const bakeKey = `${Math.round(sample.sunElevationDeg * 2)}_${Math.round(sample.sunAzimuthDeg)}_${Math.round(sample.cloudCoverage * 20)}_${Math.round(weatherDarken * 20)}_${Math.round(sample.snowCoverage * 10)}`;
    const now = performance.now();
    if (forceBakeEnv || (bakeKey !== this.lastBakedKey && now - this.lastBakeMs > 160)) {
      this.lastBakedKey = bakeKey;
      this.lastBakeMs = now;
      const nextTarget = this.pmrem.fromScene(this.envScene, 0.025, 0.1, 100);
      if (this.envTarget) {
        this.envTarget.dispose();
      }
      this.envTarget = nextTarget;
      mainScene.environment = nextTarget.texture;
    }
    mainScene.environmentIntensity = sample.envIntensity;
  }

  /** Renders an equirectangular DataTexture / CubeRenderTarget snapshot for GPU Path Tracer environment. */
  public getEnvTexture(): THREE.Texture | null {
    return this.envTarget?.texture ?? null;
  }

  public dispose(): void {
    this.domeMesh.geometry.dispose();
    this.domeMaterial.dispose();
    for (const child of this.envScene.children) {
      if ((child as THREE.Mesh).isMesh) {
        const m = child as THREE.Mesh;
        m.geometry.dispose();
        (m.material as THREE.Material).dispose();
      }
    }
    this.envTarget?.dispose();
    this.pmrem.dispose();
  }
}

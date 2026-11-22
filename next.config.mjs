import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const noopFontsPath = path.join(__dirname, "src/lib/s2NoopFonts.ts");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  images: {
    unoptimized: true,
  },
  webpack(config, { webpack }) {
    config.plugins = config.plugins || [];
    // Replace Spectrum 2's relative `./Fonts.mjs` (which injects blocked Typekit scripts/fonts) with a local no-op
    config.plugins.push(
      new webpack.NormalModuleReplacementPlugin(/^\.\/Fonts\.(m|c)?js$/, (resource) => {
        if (
          resource.context &&
          /@react-spectrum[/\\]s2[/\\]dist[/\\]private/.test(resource.context)
        ) {
          resource.request = noopFontsPath;
        }
      })
    );
    return config;
  },
  async headers() {
    return [
      {
        source: "/models/:path*.glb",
        headers: [
          { key: "Content-Type", value: "model/gltf-binary" },
          {
            key: "Cache-Control",
            value: "public, max-age=0, must-revalidate",
          },
        ],
      },
      {
        source: "/textures/:path*.webp",
        headers: [
          { key: "Content-Type", value: "image/webp" },
          {
            key: "Cache-Control",
            value: "public, max-age=604800, stale-while-revalidate=86400",
          },
        ],
      },
    ];
  },
};

export default nextConfig;

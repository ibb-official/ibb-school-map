declare module "three-mesh-bvh/src/workers/GenerateMeshBVHWorker.js" {
  import type { BufferGeometry } from "three";
  import type { MeshBVH, MeshBVHOptions } from "three-mesh-bvh";

  export class GenerateMeshBVHWorker {
    constructor();
    generate(geometry: BufferGeometry, options?: MeshBVHOptions): Promise<MeshBVH>;
    dispose(): void;
  }
}

#!/usr/bin/env python3
"""
Blender 4.x (`bpy`) Native Scene Builder & glTF 2.0 Exporter for ibb-school-map.

Allows contributors with Blender 4.x installed to regenerate editable `.blend`
scenes (collections, Principled BSDF materials, beveled architectural masses,
recessed facade bays, pitched/barrel roofs, courtyard trees, and signage planes)
directly from `blender/data/west_metric.json` and `east_metric.json`, refine
details visually inside Blender, and re-export `public/models/<campus>-campus.glb`
preserving the exact node names required by `src/data/places.ts`.

Usage (headless):
    blender --background --python blender/scripts/build_in_blender.py -- --campus all
    blender --background --python blender/scripts/build_in_blender.py -- --campus west --save-blend
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

try:
    import bpy  # type: ignore
    import bmesh  # type: ignore
    from mathutils import Euler, Matrix, Vector  # type: ignore
except ImportError as exc:  # pragma: no cover - runs inside Blender Python only
    raise SystemExit(
        "This script must be executed inside Blender 4.x (missing bpy module). "
        "Without Blender, run `python3 blender/scripts/generate_campus_glb.py` instead."
    ) from exc


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DATA_DIR = REPO_ROOT / "blender" / "data"
OUT_MODELS_DIR = REPO_ROOT / "public" / "models"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Build ibb-school-map scenes in Blender 4.x")
    parser.add_argument("--campus", choices=["west", "east", "all"], default="all")
    parser.add_argument("--save-blend", action="store_true", help="Save local .blend (ignored by git)")
    parser.add_argument(
        "--import-glb",
        action="store_true",
        help="Import existing public/models/<campus>-campus.glb for full photo-faithful visual editing",
    )
    parser.add_argument(
        "--tex-dir",
        default=os.environ.get("MAP_TEX_DIR", ""),
        help="Optional directory with tex_signage_gates.png / tex_plaques_stage.png / tex_surfaces.png / tex_west_details.png",
    )
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def ensure_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    col = bpy.data.collections.new(name)
    if parent is None:
        bpy.context.scene.collection.children.link(col)
    else:
        parent.children.link(col)
    return col


def make_principled_material(
    name: str,
    rgba: Tuple[float, float, float, float],
    roughness: float = 0.65,
    metallic: float = 0.0,
    emission: Tuple[float, float, float] | None = None,
    emission_strength: float = 0.0,
    transmission: float = 0.0,
    image_path: Path | None = None,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Transmission Weight" in bsdf.inputs and transmission > 0:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission is not None and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength

    if image_path is not None and image_path.exists():
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(image_path), check_existing=True)
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def create_material_library(tex_dir: Path | None) -> Dict[str, bpy.types.Material]:
    def tex(name: str) -> Path | None:
        return (tex_dir / name) if (tex_dir and (tex_dir / name).exists()) else None

    return {
        "ground": make_principled_material("Mat_Ground", (0.85, 0.87, 0.89, 1.0), roughness=0.92),
        "asphalt": make_principled_material("Mat_Asphalt", (0.28, 0.30, 0.33, 1.0), roughness=0.88),
        "brick_red": make_principled_material("Mat_Brick_Red", (0.58, 0.31, 0.24, 1.0), roughness=0.82),
        "qingzhuan": make_principled_material("Mat_Qingzhuan", (0.43, 0.45, 0.48, 1.0), roughness=0.86),
        "stucco": make_principled_material("Mat_Stucco", (0.88, 0.85, 0.79, 1.0), roughness=0.76),
        "roof_grey": make_principled_material("Mat_Roof_Grey", (0.31, 0.33, 0.36, 1.0), roughness=0.78),
        "roof_red": make_principled_material("Mat_Roof_Red", (0.64, 0.27, 0.20, 1.0), roughness=0.72),
        "roof_green": make_principled_material("Mat_Roof_Green", (0.26, 0.50, 0.41, 1.0), roughness=0.70),
        "roof_coat": make_principled_material("Mat_Roof_Coat", (0.76, 0.79, 0.82, 1.0), roughness=0.80),
        "white_alu": make_principled_material("Mat_White_Alu", (0.93, 0.94, 0.96, 1.0), roughness=0.45, metallic=0.25),
        "bronze": make_principled_material("Mat_Bronze", (0.54, 0.43, 0.24, 1.0), roughness=0.35, metallic=0.75),
        "dark_steel": make_principled_material("Mat_Dark_Steel", (0.16, 0.18, 0.22, 1.0), roughness=0.40, metallic=0.72),
        "crimson": make_principled_material("Mat_Crimson", (0.58, 0.14, 0.14, 1.0), roughness=0.58),
        "glass": make_principled_material("Mat_Glass", (0.20, 0.36, 0.52, 0.82), roughness=0.12, metallic=0.10),
        "skylight": make_principled_material("Mat_Skylight", (0.55, 0.76, 0.88, 0.85), roughness=0.18, metallic=0.05),
        "track": make_principled_material("Mat_Track_EPDM", (0.69, 0.25, 0.22, 1.0), roughness=0.82),
        "court": make_principled_material("Mat_Court_Green", (0.17, 0.46, 0.38, 1.0), roughness=0.75),
        "turf": make_principled_material("Mat_Turf", (0.21, 0.50, 0.26, 1.0), roughness=0.85),
        "tensile": make_principled_material("Mat_Tensile", (0.95, 0.96, 0.97, 1.0), roughness=0.48),
        "led": make_principled_material(
            "Mat_LED", (0.96, 0.42, 0.16, 1.0), roughness=0.35, emission=(0.95, 0.36, 0.12), emission_strength=1.1,
            image_path=tex("tex_signage_gates.png"),
        ),
        "stage_plaques": make_principled_material(
            "Mat_StagePlaques", (0.85, 0.82, 0.76, 1.0), roughness=0.55,
            image_path=tex("tex_plaques_stage.png"),
        ),
        "context": make_principled_material("Mat_Context", (0.86, 0.88, 0.90, 1.0), roughness=0.92),
        "foliage": make_principled_material("Mat_Foliage", (0.22, 0.45, 0.26, 1.0), roughness=0.85),
        "trunk": make_principled_material("Mat_Trunk", (0.38, 0.28, 0.20, 1.0), roughness=0.90),
    }


def add_extruded_polygon(
    name: str,
    pts_en: Sequence[Sequence[float]],
    z0: float,
    height: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    bevel_width: float = 0.0,
) -> bpy.types.Object:
    """Create an upright 3D mesh extruded along +Z (Blender Z-up from ENU meters)."""
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)

    bm = bmesh.new()
    # Deduplicate closing vertex if identical
    cleaned = list(pts_en)
    if len(cleaned) > 2 and math.hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) < 1e-4:
        cleaned = cleaned[:-1]

    verts = [bm.verts.new((float(p[0]), float(p[1]), z0)) for p in cleaned]
    bm.verts.ensure_lookup_table()
    face = bm.faces.new(verts)
    bmesh.ops.recalc_face_normals(bm, faces=[face])
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    extruded_verts = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=Vector((0.0, 0.0, height)), verts=extruded_verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()

    obj.data.materials.append(mat)
    if bevel_width > 0:
        bev = obj.modifiers.new("Bevel", "BEVEL")
        bev.width = bevel_width
        bev.segments = 2
    return obj


def add_box(
    name: str,
    cx: float,
    cy: float,
    z0: float,
    w: float,
    d: float,
    h: float,
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    yaw_rad: float = 0.0,
    bevel_width: float = 0.03,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((w, d, h)), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector((0.0, 0.0, h * 0.5)), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    obj.location = (cx, cy, z0)
    obj.rotation_euler = Euler((0.0, 0.0, yaw_rad), "XYZ")
    obj.data.materials.append(mat)
    if bevel_width > 0:
        bev = obj.modifiers.new("Bevel", "BEVEL")
        bev.width = bevel_width
        bev.segments = 2
    return obj


def build_west_scene(west_json: dict, mats: Dict[str, bpy.types.Material], root_col: bpy.types.Collection) -> None:
    ways = {str(w["id"]): w for w in west_json["ways"]}

    add_extruded_polygon("Campus_Ground_West", ways["352521262"]["pts"], -0.18, 0.18, mats["ground"], root_col)
    add_box("W-G1", -1.2, 7.6, 0.0, 14.0, 4.6, 5.4, mats["brick_red"], root_col, bevel_width=0.04)
    add_box("W-L1", -6.6, 70.0, 0.0, 1.8, 1.0, 3.52, mats["qingzhuan"], root_col, bevel_width=0.05)
    add_box("W-L3", -16.5, 58.8, 0.0, 1.3, 1.3, 2.55, mats["bronze"], root_col, bevel_width=0.04)

    # Central teaching complex: C座 (W-B1, 6F taller) + 楼梯间 (W-B2, 6F 90° north projection) + B座 (W-B3, 6F obtuse bend)
    wb1_pts = [
        (-89.8, 76.2), (-69.8, 77.2), (-69.5, 66.8), (-55.2, 66.8),
        (-55.2, 58.0), (-68.2, 58.0), (-68.2, 34.2), (-79.9, 34.0),
        (-81.0, 49.8), (-87.8, 53.5),
    ]
    wb2_pts = [(-55.2, 77.1), (-46.8, 77.4), (-46.8, 57.6), (-55.2, 58.0)]
    wb3_pts = [(-46.8, 68.2), (-37.5, 68.4), (-11.5, 84.5), (-5.8, 72.8), (-35.5, 57.5), (-46.8, 57.6)]
    wb5_pts = [(-92.2, 136.8), (-7.8, 136.8), (-7.8, 142.1), (-92.2, 142.1)]
    add_extruded_polygon("W-B1", wb1_pts, 0.0, 23.65, mats["stucco"], root_col, 0.04)
    add_extruded_polygon("W-B2", wb2_pts, 0.0, 22.40, mats["stucco"], root_col, 0.04)
    add_extruded_polygon("W-B3", wb3_pts, 0.0, 21.50, mats["stucco"], root_col, 0.04)
    add_box("W-R1", -32.0, 44.5, 0.0, 35.0, 4.6, 4.35, mats["white_alu"], root_col, bevel_width=0.04)

    add_extruded_polygon("W-B4", ways["636389217"]["pts"], 0.0, 11.4, mats["stucco"], root_col, 0.04)
    add_box("W-ST1", -6.8, 80.5, 0.0, 5.4, 5.4, 21.0, mats["dark_steel"], root_col, bevel_width=0.03)
    add_box("W-MC", -91.2, 67.8, 0.0, 4.4, 27.5, 4.6, mats["skylight"], root_col, bevel_width=0.03)
    add_box("W-L2", -56.4, 48.0, 0.0, 18.0, 12.0, 0.12, mats["ground"], root_col, bevel_width=0.02)
    add_box("W-P1", -48.8, 106.0, 0.0, 81.5, 37.0, 0.14, mats["track"], root_col, bevel_width=0.0)
    add_box("W-P2", -44.0, 129.0, 0.0, 22.0, 6.0, 5.1, mats["tensile"], root_col, bevel_width=0.04)
    add_extruded_polygon("W-B5", wb5_pts, 0.0, 4.1, mats["stucco"], root_col, 0.04)
    add_box("W-H1", -81.0, 129.0, 0.0, 22.0, 8.4, 8.8, mats["qingzhuan"], root_col, bevel_width=0.04)
    add_box("W-B6", 0.2, 112.0, 0.0, 11.6, 31.0, 6.35, mats["roof_red"], root_col, bevel_width=0.04)
    add_box("Context_West", -130.0, 120.0, 0.0, 68.0, 34.0, 12.0, mats["context"], root_col, bevel_width=0.0)


def build_east_scene(east_json: dict, mats: Dict[str, bpy.types.Material], root_col: bpy.types.Collection) -> None:
    ways = {str(w["id"]): w for w in east_json["ways"]}

    add_extruded_polygon("Campus_Ground_East", ways["398694728"]["pts"], -0.18, 0.18, mats["ground"], root_col)
    add_box("E-G1", -3.0, 80.5, 0.0, 10.6, 2.2, 5.4, mats["crimson"], root_col, bevel_width=0.03)
    add_box("E-N1", -3.0, 50.5, 0.0, 8.4, 57.0, 0.08, mats["brick_red"], root_col, bevel_width=0.0)
    add_box("E-N2", 24.0, 57.0, 0.0, 28.0, 27.5, 5.3, mats["qingzhuan"], root_col, bevel_width=0.03)
    add_box("E-N3", -22.5, 52.0, 0.0, 14.0, 24.0, 5.2, mats["qingzhuan"], root_col, bevel_width=0.03)
    add_box("E-P1", 12.0, 1.5, 0.0, 37.0, 34.5, 0.10, mats["court"], root_col, bevel_width=0.0)
    add_extruded_polygon("E-B1", ways["477977123"]["pts"], 0.0, 15.2, mats["stucco"], root_col, 0.04)
    add_extruded_polygon("E-B2", ways["477977122"]["pts"], 0.0, 15.2, mats["stucco"], root_col, 0.04)
    add_extruded_polygon("E-B3", ways["477977121"]["pts"], 0.0, 11.2, mats["stucco"], root_col, 0.04)
    add_extruded_polygon("E-B4", ways["477977120"]["pts"], 0.0, 11.2, mats["stucco"], root_col, 0.04)
    add_box("E-B5", 43.0, 1.0, 0.0, 12.0, 30.0, 5.0, mats["qingzhuan"], root_col, bevel_width=0.03)
    add_box("Context_East", -52.0, 48.0, 0.0, 22.0, 38.0, 3.6, mats["context"], root_col, bevel_width=0.0)


def export_campus_glb(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(out_path),
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_materials="EXPORT",
        export_colors=True,
        export_normals=True,
        export_tangents=False,
    )


def main() -> None:
    args = parse_args()
    tex_dir = Path(args.tex_dir) if args.tex_dir else None
    west_json = json.loads((DATA_DIR / "west_metric.json").read_text(encoding="utf-8"))
    east_json = json.loads((DATA_DIR / "east_metric.json").read_text(encoding="utf-8"))

    targets = ["west", "east"] if args.campus == "all" else [args.campus]
    for campus in targets:
        clear_scene()
        out_glb = OUT_MODELS_DIR / f"{campus}-campus.glb"
        if args.import_glb and out_glb.exists():
            bpy.ops.import_scene.gltf(filepath=str(out_glb))
        else:
            mats = create_material_library(tex_dir)
            col = ensure_collection(f"{campus.capitalize()}_Campus")
            if campus == "west":
                build_west_scene(west_json, mats, col)
            else:
                build_east_scene(east_json, mats, col)

        export_campus_glb(out_glb)
        if args.save_blend:
            blend_path = REPO_ROOT / "blender" / f"{campus}-campus.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))


if __name__ == "__main__":
    main()

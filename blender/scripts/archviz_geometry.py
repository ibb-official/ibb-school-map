"""
ArchViz High-Precision Geometry & PBR Material Upgrade Helpers for ibb-school-map.

Provides:
  - Semantic PBR material registry & automatic world-space metric UV tiling
    (eliminating 256px atlas stretch on walls, roofs, plazas, and tracks).
  - Beveled architectural blocks with smooth/weighted normals for realistic edge highlights.
  - Physical transparent glass + procedural 3D shallow interiors (walls, ceilings, floors,
    curtains, chalkboards, desks, bookshelves, dining tables, and 6-bucket ceiling LED fixtures)
    for realistic daytime depth and multi-temperature nighttime window lighting.
  - Botanical alpha-cutout foliage cluster trees (7 campus species) with spherical normal
    transfer for natural sunlit canopy shading and GPU wind sway.
  - High-subdivision smooth-normal hero sculptures (Shendu boulder, Bing Xin bronze bust,
    Taihu rockery crags) and campus luminaire fixtures + light anchor registry.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]
UVBox = Tuple[float, float, float, float]

# ---------------------------------------------------------------------------
# Metric tiling sizes (in meters per 1.0 UV repeat) for seamless CC0 PBR maps
# ---------------------------------------------------------------------------
METRIC_PBR_SPECS: Dict[str, dict] = {
    "pbr_qingzhuan": {
        "name": "Mat_PBR_Qingzhuan",
        "color": (0.48, 0.50, 0.53, 1.0),
        "roughness": 0.86,
        "metallic": 0.0,
        "tile": 2.2,
    },
    "pbr_red_brick": {
        "name": "Mat_PBR_RedBrick",
        "color": (0.60, 0.33, 0.25, 1.0),
        "roughness": 0.84,
        "metallic": 0.0,
        "tile": 2.0,
    },
    "pbr_stucco": {
        "name": "Mat_PBR_Stucco",
        "color": (0.93, 0.91, 0.88, 1.0),
        "roughness": 0.82,
        "metallic": 0.0,
        "tile": 3.0,
    },
    "pbr_grey_rib": {
        "name": "Mat_PBR_GreyRib",
        "color": (0.68, 0.70, 0.72, 1.0),
        "roughness": 0.78,
        "metallic": 0.02,
        "tile": 2.6,
    },
    "pbr_marble": {
        "name": "Mat_PBR_Marble",
        "color": (0.89, 0.89, 0.88, 1.0),
        "roughness": 0.24,
        "metallic": 0.0,
        "tile": 2.4,
    },
    "pbr_plaza_tile": {
        "name": "Mat_PBR_PlazaTile",
        "color": (0.68, 0.70, 0.72, 1.0),
        "roughness": 0.76,
        "metallic": 0.0,
        "tile": 2.4,
    },
    "pbr_dark_slate": {
        "name": "Mat_PBR_DarkSlate",
        "color": (0.30, 0.32, 0.35, 1.0),
        "roughness": 0.68,
        "metallic": 0.02,
        "tile": 2.2,
    },
    "pbr_asphalt": {
        "name": "Mat_PBR_Asphalt",
        "color": (0.28, 0.29, 0.31, 1.0),
        "roughness": 0.88,
        "metallic": 0.0,
        "tile": 3.6,
    },
    "pbr_grey_tile": {
        "name": "Mat_PBR_GreyTile",
        "color": (0.38, 0.40, 0.43, 1.0),
        "roughness": 0.72,
        "metallic": 0.04,
        "tile": 2.2,
    },
    "pbr_red_tile": {
        "name": "Mat_PBR_RedTile",
        "color": (0.58, 0.28, 0.29, 1.0),
        "roughness": 0.66,
        "metallic": 0.04,
        "tile": 2.2,
    },
    "pbr_blue_tile": {
        "name": "Mat_PBR_BlueTile",
        "color": (0.16, 0.42, 0.72, 1.0),
        "roughness": 0.36,
        "metallic": 0.08,
        "tile": 2.2,
    },
    "pbr_green_roof": {
        "name": "Mat_PBR_GreenRoof",
        "color": (0.36, 0.50, 0.34, 1.0),
        "roughness": 0.84,
        "metallic": 0.0,
        "tile": 3.2,
    },
    "pbr_track_epdm": {
        "name": "Mat_PBR_TrackEPDM",
        "color": (0.68, 0.25, 0.19, 1.0),
        "roughness": 0.88,
        "metallic": 0.0,
        "tile": 2.4,
    },
    "pbr_court_pu": {
        "name": "Mat_PBR_CourtPU",
        "color": (0.80, 0.44, 0.36, 1.0),
        "roughness": 0.46,
        "metallic": 0.02,
        "tile": 3.8,
    },
    "pbr_court_green": {
        "name": "Mat_PBR_CourtGreen",
        "color": (0.15, 0.47, 0.30, 1.0),
        "roughness": 0.46,
        "metallic": 0.02,
        "tile": 3.8,
    },
    "pbr_grass": {
        "name": "Mat_PBR_Grass",
        "color": (0.32, 0.52, 0.24, 1.0),
        "roughness": 0.92,
        "metallic": 0.0,
        "tile": 2.8,
    },
    "pbr_bark": {
        "name": "Mat_PBR_Bark",
        "color": (0.36, 0.28, 0.21, 1.0),
        "roughness": 0.92,
        "metallic": 0.0,
        "tile": 1.4,
    },
    "pbr_wood": {
        "name": "Mat_PBR_Wood",
        "color": (0.58, 0.42, 0.28, 1.0),
        "roughness": 0.62,
        "metallic": 0.0,
        "tile": 1.6,
    },
    "pbr_rockery": {
        "name": "Mat_PBR_Rockery",
        "color": (0.56, 0.56, 0.54, 1.0),
        "roughness": 0.86,
        "metallic": 0.0,
        "tile": 1.8,
    },
    "pbr_burgundy": {
        "name": "Mat_PBR_BurgundyMetal",
        "color": (0.40, 0.14, 0.13, 1.0),
        "roughness": 0.42,
        "metallic": 0.32,
        "tile": 2.4,
    },
}


def register_archviz_materials(exp, mats: dict) -> Tuple[Dict[int, float], Dict[Tuple[int, UVBox], Tuple[int, float]]]:
    """
    Registers semantic PBR materials, physical transparent glass, shallow-interior
    room/luminaire materials, botanical foliage card materials, and campus lamp materials.

    Returns:
      - metric_mat_tiles: {mat_idx -> tile_meters}
      - legacy_redirect: {(old_mat_idx, uv_box) -> (new_mat_idx, tile_meters)}
    """
    metric_mat_tiles: Dict[int, float] = {}

    for key, spec in METRIC_PBR_SPECS.items():
        idx = exp.add_mat(
            spec["name"],
            base_color=spec["color"],
            metallic=spec["metallic"],
            roughness=spec["roughness"],
        )
        mats[key] = idx
        metric_mat_tiles[idx] = spec["tile"]

    # Upgrade existing bark / tensile / rockery aliases directly
    mats["trunk"] = mats["pbr_bark"]
    mats["rockery_stone"] = mats["pbr_rockery"]

    # Physical transparent architectural glass (day: sky reflection, night: warm interior see-through)
    mats["glass_phys"] = exp.add_mat(
        "Mat_Glass_Physical",
        base_color=(0.74, 0.86, 0.94, 0.34),
        metallic=0.04,
        roughness=0.06,
        alpha_mode="BLEND",
        double_sided=True,
    )
    # Surrounding context building window (upgraded at runtime with GLSL Parallax Interior Mapping)
    mats["context_window"] = exp.add_mat(
        "Mat_Context_Window",
        base_color=(0.24, 0.35, 0.46, 1.0),
        metallic=0.12,
        roughness=0.12,
    )
    # Warm glazed sunroom / vestibule glass (semi-transparent + subtle interior warmth)
    mats["warm_glass_phys"] = exp.add_mat(
        "Mat_WarmGlass_Physical",
        base_color=(0.94, 0.88, 0.74, 0.44),
        metallic=0.02,
        roughness=0.10,
        alpha_mode="BLEND",
        double_sided=True,
    )

    # Shallow-interior structural materials
    mats["int_wall"] = exp.add_mat("Mat_Int_Wall", base_color=(0.90, 0.88, 0.83, 1.0), roughness=0.92)
    mats["int_floor"] = exp.add_mat("Mat_Int_Floor", base_color=(0.56, 0.54, 0.51, 1.0), roughness=0.78)
    mats["int_curtain"] = exp.add_mat(
        "Mat_Int_Curtain", base_color=(0.82, 0.80, 0.74, 1.0), roughness=0.95, double_sided=True
    )
    mats["int_board"] = exp.add_mat("Mat_Int_Board", base_color=(0.14, 0.27, 0.20, 1.0), roughness=0.68)
    mats["int_books"] = exp.add_mat("Mat_Int_Books", base_color=(0.48, 0.30, 0.22, 1.0), roughness=0.82)

    # 7 independently controllable interior lighting groups (4 classroom, 2 warm hero/heritage, 1 hallway)
    # Each group has:
    #   - luminaire fixture strip (`Mat_IntLight_*`) -> strong HDR emissive at night
    #   - room interior bounced wall/ceiling surface (`Mat_IntGlow_*`) -> soft bounced glow at night
    light_defs = [
        ("int_light_0", "Mat_IntLight_Class_0", "int_glow_0", "Mat_IntGlow_0", (0.95, 0.93, 0.89, 1.0), (0.041, 0.040, 0.036)),
        ("int_light_1", "Mat_IntLight_Class_1", "int_glow_1", "Mat_IntGlow_1", (0.94, 0.92, 0.87, 1.0), (0.042, 0.041, 0.035)),
        ("int_light_2", "Mat_IntLight_Class_2", "int_glow_2", "Mat_IntGlow_2", (0.96, 0.94, 0.90, 1.0), (0.043, 0.042, 0.038)),
        ("int_light_3", "Mat_IntLight_Class_3", "int_glow_3", "Mat_IntGlow_3", (0.93, 0.91, 0.86, 1.0), (0.044, 0.039, 0.034)),
        ("int_light_warm0", "Mat_IntLight_Warm_0", "int_glow_warm0", "Mat_IntGlow_4", (0.95, 0.89, 0.78, 1.0), (0.055, 0.044, 0.028)),
        ("int_light_warm1", "Mat_IntLight_Warm_1", "int_glow_warm1", "Mat_IntGlow_5", (0.93, 0.87, 0.76, 1.0), (0.058, 0.042, 0.024)),
        ("int_light_hall", "Mat_IntLight_Hall", "int_glow_hall", "Mat_IntGlow_6", (0.91, 0.93, 0.96, 1.0), (0.040, 0.045, 0.052)),
    ]
    for lk, lname, gk, gname, wall_col, em_col in light_defs:
        mats[lk] = exp.add_mat(lname, base_color=(0.98, 0.98, 0.96, 1.0), roughness=0.25, emissive=em_col)
        mats[gk] = exp.add_mat(gname, base_color=wall_col, roughness=0.90, emissive=(0.0, 0.0, 0.0))

    # Botanical alpha-cutout foliage materials (linked to public/textures/foliage/ at runtime)
    foliage_defs = [
        ("foliage_broad", "Mat_Foliage_Broad", (0.28, 0.46, 0.22, 1.0)),
        ("foliage_pine", "Mat_Foliage_Pine", (0.16, 0.34, 0.20, 1.0)),
        ("foliage_ginkgo", "Mat_Foliage_Ginkgo", (0.82, 0.68, 0.18, 1.0)),
        ("foliage_magnolia", "Mat_Foliage_Magnolia", (0.25, 0.42, 0.24, 1.0)),
        ("foliage_persimmon", "Mat_Foliage_Persimmon", (0.30, 0.44, 0.20, 1.0)),
        ("foliage_rose", "Mat_Foliage_Rose", (0.24, 0.42, 0.20, 1.0)),
    ]
    for fk, fname, col in foliage_defs:
        mats[fk] = exp.add_mat(fname, base_color=col, roughness=0.76, double_sided=True, alpha_mode="MASK")

    # Outdoor campus lamp heads (warm courtyard/street lamps & cool-white sports floodlights)
    mats["lamp_warm"] = exp.add_mat(
        "Mat_Lamp_Warm",
        base_color=(1.0, 0.94, 0.80, 1.0),
        roughness=0.20,
        emissive=(0.15, 0.11, 0.05),
    )
    mats["lamp_flood"] = mats["floodlight"]

    legacy_redirect: Dict[Tuple[int, UVBox], Tuple[int, float]] = {}
    return metric_mat_tiles, legacy_redirect


def populate_legacy_redirects(
    mats: dict,
    uv_consts: dict,
    metric_mat_tiles: Dict[int, float],
) -> Dict[Tuple[int, UVBox], Tuple[int, float]]:
    """Maps legacy (atlas_mat_idx, uv_box) pairs onto dedicated seamless metric PBR materials."""
    redir: Dict[Tuple[int, UVBox], Tuple[int, float]] = {}

    def bind(old_key: str, uv_key: str, new_key: str) -> None:
        if old_key in mats and uv_key in uv_consts and new_key in mats:
            redir[(mats[old_key], uv_consts[uv_key])] = (mats[new_key], metric_mat_tiles[mats[new_key]])

    # Mat_Surfaces 4x4 cell splits -> independent high-res PBR materials
    bind("surf", "UV_TERRACOTTA_BRICK", "pbr_red_brick")
    bind("surf", "UV_RED_BRICK_WALK", "pbr_red_brick")
    bind("surf", "UV_GREY_RIB", "pbr_grey_rib")
    bind("surf", "UV_QINGZHUAN", "pbr_qingzhuan")
    bind("surf", "UV_STUCCO", "pbr_stucco")
    bind("surf", "UV_GREY_TILE", "pbr_grey_tile")
    bind("surf", "UV_RED_TILE", "pbr_red_tile")
    bind("surf", "UV_GREEN_ROOF", "pbr_green_roof")
    bind("surf", "UV_TRACK_EPDM", "pbr_track_epdm")
    bind("surf", "UV_COURT_GREEN", "pbr_court_green")
    bind("surf", "UV_PLAZA_TILE", "pbr_plaza_tile")
    bind("surf", "UV_GRASS", "pbr_grass")
    bind("surf", "UV_ASPHALT", "pbr_asphalt")

    # Marble & burgundy metal on gates/pedestals -> seamless marble/metal PBR
    bind("gates", "UV_MARBLE", "pbr_marble")
    bind("gates", "UV_BURGUNDY", "pbr_burgundy")
    bind("gates", "UV_SHENDU_GRANITE", "pbr_rockery")

    # West details repeatable stone/court/roof tiles -> seamless PBR
    bind("details", "UV_DARK_SLATE_PODIUM", "pbr_dark_slate")
    bind("details", "UV_BLUE_TILE_ROOF", "pbr_blue_tile")
    bind("hard_court", "UV_HARD_COURT_APRON", "pbr_court_pu")
    bind("rockery_stone", "UV_SHENDU_GRANITE", "pbr_rockery")

    return redir


def compute_metric_quad_uvs(
    p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3, tile_m: float
) -> Tuple[Vec2, Vec2, Vec2, Vec2]:
    """Computes distortion-free world-space metric UVs for any 3D quad in glTF Y-up coords."""
    ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    vx, vy, vz = p3[0] - p0[0], p3[1] - p0[1], p3[2] - p0[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    nlen = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    ny_abs = abs(ny / nlen)

    inv_t = 1.0 / max(tile_m, 0.25)
    if ny_abs > 0.65:
        # Horizontal / gently sloped surfaces (ground, track, plaza, roofs): continuous world XZ projection
        return (
            (p0[0] * inv_t, p0[2] * inv_t),
            (p1[0] * inv_t, p1[2] * inv_t),
            (p2[0] * inv_t, p2[2] * inv_t),
            (p3[0] * inv_t, p3[2] * inv_t),
        )
    # Vertical / steep walls: project onto local horizontal tangent + Y elevation
    u_len = math.sqrt(ux * ux + uy * uy + uz * uz)
    v_len = math.sqrt(vx * vx + vy * vy + vz * vz)
    # Phase-align horizontal origin using world position so adjacent wall segments align seamlessly
    u_phase = ((p0[0] + p0[2]) * 0.5) * inv_t
    v_phase = p0[1] * inv_t
    u_span = u_len * inv_t
    v_span = v_len * inv_t
    return (
        (u_phase, v_phase),
        (u_phase + u_span, v_phase),
        (u_phase + u_span, v_phase + v_span),
        (u_phase, v_phase + v_span),
    )


def compute_metric_tri_uvs(p0: Vec3, p1: Vec3, p2: Vec3, tile_m: float) -> Tuple[Vec2, Vec2, Vec2]:
    ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    nlen = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    inv_t = 1.0 / max(tile_m, 0.25)
    if abs(ny / nlen) > 0.55:
        return (
            (p0[0] * inv_t, p0[2] * inv_t),
            (p1[0] * inv_t, p1[2] * inv_t),
            (p2[0] * inv_t, p2[2] * inv_t),
        )
    # Vertical triangle (e.g. gable wall): choose dominant horizontal axis + Y
    if abs(nx / nlen) > abs(nz / nlen):
        return (
            (p0[2] * inv_t, p0[1] * inv_t),
            (p1[2] * inv_t, p1[1] * inv_t),
            (p2[2] * inv_t, p2[1] * inv_t),
        )
    return (
        (p0[0] * inv_t, p0[1] * inv_t),
        (p1[0] * inv_t, p1[1] * inv_t),
        (p2[0] * inv_t, p2[1] * inv_t),
    )


# ---------------------------------------------------------------------------
# Procedural 3D Shallow Interior Room Builder (Visible through Physical Glass)
# ---------------------------------------------------------------------------
def _room_hash(key: str) -> int:
    return int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)


def add_shallow_room(
    nb,
    wpt,
    w0: float,
    w1: float,
    recess: float,
    win_z0: float,
    win_z1: float,
    story_z0: float,
    story_z1: float,
    mats: dict,
    room_key: str,
    room_type: str = "classroom",
    depth: float = 2.85,
) -> None:
    """
    Constructs a lightweight 3D architectural room shell directly behind a transparent
    window opening so the viewer sees real depth, ceiling LED luminaires, curtains,
    desks/chalkboards/bookshelves, and warm/cool illuminated interior walls at night.
    Strictly generic architectural elements (zero private/personal signage).
    """
    h = _room_hash(room_key)
    span = w1 - w0
    if span < 0.7 or (win_z1 - win_z0) < 0.7:
        return

    # Select lighting bucket so rooms turn on/off organically by time of day
    if room_type == "hallway":
        light_mat = mats["int_light_hall"]
        glow_mat = mats["int_glow_hall"]
    elif room_type == "warm0":
        light_mat = mats["int_light_warm0"]
        glow_mat = mats["int_glow_warm0"]
    elif room_type == "warm1":
        light_mat = mats["int_light_warm1"]
        glow_mat = mats["int_glow_warm1"]
    else:
        bi = h % 4
        light_mat = mats[f"int_light_{bi}"]
        glow_mat = mats[f"int_glow_{bi}"]

    d_front = -recess - 0.05
    d_back = -recess - depth
    z_floor = story_z0 + 0.08
    z_ceil = story_z1 - 0.14
    rw0 = w0 - 0.14
    rw1 = w1 + 0.14

    # 1. Back wall (facing outward through window)
    nb.quad_enu(
        glow_mat,
        wpt(rw0, d_back, z_floor),
        wpt(rw1, d_back, z_floor),
        wpt(rw1, d_back, z_ceil),
        wpt(rw0, d_back, z_ceil),
        c_bot=0.72,
        c_top=0.96,
    )
    # 2. Left & right side walls (facing inward)
    nb.quad_enu(
        glow_mat,
        wpt(rw0, d_front, z_floor),
        wpt(rw0, d_back, z_floor),
        wpt(rw0, d_back, z_ceil),
        wpt(rw0, d_front, z_ceil),
        c_bot=0.68,
        c_top=0.90,
    )
    nb.quad_enu(
        glow_mat,
        wpt(rw1, d_back, z_floor),
        wpt(rw1, d_front, z_floor),
        wpt(rw1, d_front, z_ceil),
        wpt(rw1, d_back, z_ceil),
        c_bot=0.68,
        c_top=0.90,
    )
    # 3. Ceiling (facing down) & Floor (facing up)
    nb.quad_enu(
        glow_mat,
        wpt(rw0, d_back, z_ceil),
        wpt(rw1, d_back, z_ceil),
        wpt(rw1, d_front, z_ceil),
        wpt(rw0, d_front, z_ceil),
        c_bot=0.96,
        c_top=0.96,
    )
    nb.quad_enu(
        mats["int_floor"],
        wpt(rw0, d_front, z_floor),
        wpt(rw1, d_front, z_floor),
        wpt(rw1, d_back, z_floor),
        wpt(rw0, d_back, z_floor),
        c_bot=0.75,
        c_top=0.82,
    )

    # 4. Overhead LED ceiling luminaire strips (glow strongly at dusk/night)
    lw0 = w0 + span * 0.16
    lw1 = w1 - span * 0.16
    lz = z_ceil - 0.05
    for d_strip in (d_front - depth * 0.30, d_front - depth * 0.68):
        nb.quad_enu(
            light_mat,
            wpt(lw0, d_strip - 0.11, lz),
            wpt(lw1, d_strip - 0.11, lz),
            wpt(lw1, d_strip + 0.11, lz),
            wpt(lw0, d_strip + 0.11, lz),
            c_bot=1.0,
            c_top=1.0,
            double_sided=True,
        )

    # 5. Subtle semi-drawn curtains / vertical blinds inside glass edges (organic facade variety)
    curtain_style = (h >> 4) % 5
    if room_type != "hallway" and curtain_style < 4:
        c_ratio = 0.10 + (curtain_style * 0.055)
        cw = span * c_ratio
        cd = d_front - 0.08
        nb.quad_enu(
            mats["int_curtain"],
            wpt(w0 + 0.02, cd, win_z0 + 0.04),
            wpt(w0 + cw, cd, win_z0 + 0.04),
            wpt(w0 + cw, cd, win_z1 - 0.02),
            wpt(w0 + 0.02, cd, win_z1 - 0.02),
            c_bot=0.84,
            c_top=0.94,
            double_sided=True,
        )
        nb.quad_enu(
            mats["int_curtain"],
            wpt(w1 - cw, cd, win_z0 + 0.04),
            wpt(w1 - 0.02, cd, win_z0 + 0.04),
            wpt(w1 - 0.02, cd, win_z1 - 0.02),
            wpt(w1 - cw, cd, win_z1 - 0.02),
            c_bot=0.84,
            c_top=0.94,
            double_sided=True,
        )

    # 6. Generic interior furniture silhouettes visible through windows
    if room_type == "classroom" or room_type == "warm0":
        # Back wall green chalkboard or display panel
        if (h >> 8) % 2 == 0 and span >= 1.8:
            bw0 = w0 + span * 0.18
            bw1 = w1 - span * 0.18
            nb.quad_enu(
                mats["int_board"],
                wpt(bw0, d_back + 0.04, z_floor + 0.95),
                wpt(bw1, d_back + 0.04, z_floor + 0.95),
                wpt(bw1, d_back + 0.04, min(z_ceil - 0.35, z_floor + 2.05)),
                wpt(bw0, d_back + 0.04, min(z_ceil - 0.35, z_floor + 2.05)),
                c_bot=0.88,
                c_top=0.95,
            )
        # 2 rows of timber student desks visible above sill height
        desk_z = z_floor + 0.76
        for row_d in (d_front - depth * 0.36, d_front - depth * 0.68):
            nb.quad_enu(
                mats["pbr_wood"],
                wpt(w0 + 0.22, row_d + 0.24, desk_z),
                wpt(w1 - 0.22, row_d + 0.24, desk_z),
                wpt(w1 - 0.22, row_d - 0.24, desk_z),
                wpt(w0 + 0.22, row_d - 0.24, desk_z),
                c_bot=0.88,
                c_top=0.94,
                double_sided=True,
            )
            # Desk modesty front apron
            nb.quad_enu(
                mats["pbr_wood"],
                wpt(w0 + 0.22, row_d + 0.24, desk_z - 0.32),
                wpt(w1 - 0.22, row_d + 0.24, desk_z - 0.32),
                wpt(w1 - 0.22, row_d + 0.24, desk_z),
                wpt(w0 + 0.22, row_d + 0.24, desk_z),
                c_bot=0.72,
                c_top=0.86,
            )
    elif room_type == "warm1":
        # Library bookshelves / museum display cabinet silhouette
        sh_d = d_back + 0.38
        nb.quad_enu(
            mats["int_books"],
            wpt(w0 + 0.25, sh_d, z_floor + 0.10),
            wpt(w1 - 0.25, sh_d, z_floor + 0.10),
            wpt(w1 - 0.25, sh_d, min(z_ceil - 0.28, z_floor + 2.25)),
            wpt(w0 + 0.25, sh_d, min(z_ceil - 0.28, z_floor + 2.25)),
            c_bot=0.76,
            c_top=0.92,
        )
    elif room_type == "hallway":
        # Sloped stair flight / corridor handrail silhouette
        nb.quad_enu(
            mats["white_alu"],
            wpt(w0 + 0.15, d_front - depth * 0.48, z_floor + 0.15),
            wpt(w1 - 0.15, d_front - depth * 0.48, z_floor + 1.55),
            wpt(w1 - 0.15, d_front - depth * 0.48, z_floor + 2.45),
            wpt(w0 + 0.15, d_front - depth * 0.48, z_floor + 1.05),
            c_bot=0.80,
            c_top=0.95,
            double_sided=True,
        )


def add_hero_room_box(
    nb,
    cx: float,
    cy: float,
    z_floor: float,
    w: float,
    d: float,
    h: float,
    mats: dict,
    light_key: str = "int_light_warm0",
    glow_key: str = "int_glow_warm0",
    furnish: str = "guardhouse",
) -> None:
    """
    Constructs a dedicated Tier-1 true 3D interior inside ground-floor hero buildings
    (Guardhouse, School History Museum lobby, Cafeteria dining hall, Library lobby).
    Inward-facing room shell + ceiling luminaires + recognizable architectural furnishings.
    """
    hw, hd = w * 0.5, d * 0.5
    z_top = z_floor + h
    gm = mats[glow_key]
    lm = mats[light_key]

    # Floor (upward) & Ceiling (downward)
    nb.quad_enu(
        mats["int_floor"],
        (cx - hw, cy - hd, z_floor),
        (cx + hw, cy - hd, z_floor),
        (cx + hw, cy + hd, z_floor),
        (cx - hw, cy + hd, z_floor),
        c_bot=0.82,
        c_top=0.86,
    )
    nb.quad_enu(
        gm,
        (cx - hw, cy + hd, z_top),
        (cx + hw, cy + hd, z_top),
        (cx + hw, cy - hd, z_top),
        (cx - hw, cy - hd, z_top),
        c_bot=0.98,
        c_top=0.98,
    )
    # 4 inward-facing walls (only render back/inner walls so open glass fronts stay unobstructed)
    # North inner wall (facing -Y)
    nb.quad_enu(
        gm,
        (cx - hw, cy + hd, z_floor),
        (cx + hw, cy + hd, z_floor),
        (cx + hw, cy + hd, z_top),
        (cx - hw, cy + hd, z_top),
        c_bot=0.78,
        c_top=0.96,
    )
    # West inner wall (facing +X)
    nb.quad_enu(
        gm,
        (cx - hw, cy - hd, z_floor),
        (cx - hw, cy + hd, z_floor),
        (cx - hw, cy + hd, z_top),
        (cx - hw, cy - hd, z_top),
        c_bot=0.76,
        c_top=0.95,
    )

    # Ceiling luminaires grid
    nx = max(1, int(w // 3.4))
    ny = max(1, int(d // 4.2))
    for ix in range(nx):
        lx = (cx - hw) + (ix + 0.5) * (w / nx)
        for iy in range(ny):
            ly = (cy - hd) + (iy + 0.5) * (d / ny)
            nb.add_box(lm, lx, ly, z_top - 0.10, min(1.35, w / nx * 0.52), min(0.36, d / ny * 0.25), 0.08)

    if furnish == "guardhouse":
        # Duty reception counter + wooden cabinet against back wall (generic, compliant)
        nb.add_box(mats["pbr_wood"], cx + hw * 0.25, cy - hd * 0.15, z_floor, 1.85, 0.72, 0.88)
        nb.add_box(mats["pbr_wood"], cx - hw * 0.42, cy + hd * 0.62, z_floor, 1.50, 0.45, 2.05)
    elif furnish == "library":
        # Parallel double-sided timber bookshelves + reading tables
        for bx in (-hw * 0.55, 0.0, hw * 0.55):
            nb.add_box(mats["pbr_wood"], cx + bx, cy - hd * 0.15, z_floor, 0.55, d * 0.55, 2.15)
            nb.add_box(mats["int_books"], cx + bx, cy - hd * 0.15, z_floor + 0.35, 0.60, d * 0.50, 1.55)
        nb.add_box(mats["pbr_wood"], cx, cy + hd * 0.35, z_floor, w * 0.58, 0.95, 0.76)
    elif furnish == "museum":
        # Warm timber gallery walls + central illuminated exhibition pedestals
        nb.add_box(mats["pbr_wood"], cx - hw * 0.2, cy, z_floor, 0.95, 1.50, 1.05)
        nb.add_box(mats["glass_phys"], cx - hw * 0.2, cy, z_floor + 1.05, 0.88, 1.42, 0.82)
        nb.add_box(mats["pbr_wood"], cx - hw * 0.82, cy, z_floor + 0.2, 0.12, d * 0.78, h * 0.76)
    elif furnish == "cafeteria":
        # Long rows of dining tables & benches inside the barrel-vault hall
        for col_x in (cx - hw * 0.48, cx + hw * 0.18):
            for ri in range(6):
                ty = (cy - hd + 3.2) + ri * ((d - 6.4) / 5.0)
                nb.add_box(mats["pbr_wood"], col_x, ty, z_floor + 0.72, 2.40, 0.88, 0.06)
                nb.add_box(mats["dark_steel"], col_x - 0.95, ty, z_floor, 0.08, 0.70, 0.72)
                nb.add_box(mats["dark_steel"], col_x + 0.95, ty, z_floor, 0.08, 0.70, 0.72)
                # Benches flanking table
                for by_off in (-0.68, 0.68):
                    nb.add_box(mats["white_alu"], col_x, ty + by_off, z_floor + 0.44, 2.20, 0.30, 0.05)
        # Warm backlit serving counter along east wall
        nb.add_box(mats["white_alu"], cx + hw * 0.74, cy, z_floor, 1.10, d * 0.74, 1.05)
        nb.add_box(lm, cx + hw * 0.78, cy, z_floor + 2.55, 0.35, d * 0.72, 0.12)


# ---------------------------------------------------------------------------
# High-Detail Botanical Foliage Cluster Trees (Spherical Normal Transfer)
# ---------------------------------------------------------------------------
def add_botanical_tree(
    nb,
    cx: float,
    cy_n: float,
    species: str,
    h: float,
    mats: dict,
    enu_to_gltf,
    seed_offset: int = 0,
    z_base: float = 0.0,
) -> None:
    """
    Replaces crude low-poly spheres/cones with realistic multi-branch trunks and
    crossed alpha-cutout botanical foliage cluster cards with spherical smooth normals.
    Supports arbitrary ground elevation `z_base` (e.g. elevated northern playground terrace).
    """
    seed = _room_hash(f"tree_{cx:.2f}_{cy_n:.2f}_{species}_{seed_offset}")
    bark_mat = mats["pbr_bark"]

    def rand01(salt: int) -> float:
        x = math.sin((seed + salt * 193) * 0.000137 + salt * 12.9898) * 43758.5453
        return x - math.floor(x)

    def add_foliage_cluster(
        fmat: int,
        kx: float,
        ky: float,
        kz: float,
        rad_xy: float,
        rad_z: float,
        crown_center: Vec3,
        cards: int = 5,
    ) -> None:
        """Crossed double-sided foliage cards with normals transferred from crown sphere center."""
        b = nb.bucket(fmat)
        cc_gltf = enu_to_gltf(*crown_center)
        for ci in range(cards):
            yaw = (math.pi * ci) / cards + rand01(ci * 17 + int(kx * 10)) * 0.45
            tilt = (rand01(ci * 31 + int(ky * 10)) - 0.5) * 0.55
            cs, sn = math.cos(yaw), math.sin(yaw)
            ct, st = math.cos(tilt), math.sin(tilt)
            # Card half-axes in ENU
            rx_e, rx_n, rx_z = cs * rad_xy, sn * rad_xy, 0.0
            ry_e, ry_n, ry_z = -sn * st * rad_z, cs * st * rad_z, ct * rad_z

            e0 = (kx - rx_e - ry_e, ky - rx_n - ry_n, kz - rx_z - ry_z)
            e1 = (kx + rx_e - ry_e, ky + rx_n - ry_n, kz + rx_z - ry_z)
            e2 = (kx + rx_e + ry_e, ky + rx_n + ry_n, kz + rx_z + ry_z)
            e3 = (kx - rx_e + ry_e, ky - rx_n + ry_n, kz - rx_z + ry_z)

            pts = [enu_to_gltf(*e0), enu_to_gltf(*e1), enu_to_gltf(*e2), enu_to_gltf(*e3)]
            norms = []
            cols = []
            for p in pts:
                dx = p[0] - cc_gltf[0]
                dy = (p[1] - cc_gltf[1]) * 1.15 + 0.35
                dz = p[2] - cc_gltf[2]
                l = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
                norms.append((dx / l, dy / l, dz / l))
                # Soft vertical canopy AO (bottom shaded, top sunlit)
                ao_v = max(0.68, min(1.0, 0.84 + 0.16 * (dy / l)))
                cols.append((ao_v, ao_v, ao_v))
            uvs = [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
            b.add_smooth_quad(pts[0], pts[1], pts[2], pts[3], norms[0], norms[1], norms[2], norms[3], uvs, cols)

        # Add one slightly tilted horizontal umbrella card for rich top-down aerial fullness
        u_yaw = rand01(99 + int(kz * 10)) * math.pi
        cs, sn = math.cos(u_yaw), math.sin(u_yaw)
        e0 = (kx - cs * rad_xy, ky - sn * rad_xy, kz + rad_z * 0.10)
        e1 = (kx + sn * rad_xy, ky - cs * rad_xy, kz - rad_z * 0.05)
        e2 = (kx + cs * rad_xy, ky + sn * rad_xy, kz + rad_z * 0.08)
        e3 = (kx - sn * rad_xy, ky + cs * rad_xy, kz - rad_z * 0.06)
        pts = [enu_to_gltf(*e0), enu_to_gltf(*e1), enu_to_gltf(*e2), enu_to_gltf(*e3)]
        norms = []
        cols = []
        for p in pts:
            dx = p[0] - cc_gltf[0]
            dy = (p[1] - cc_gltf[1]) * 1.15 + 0.55
            dz = p[2] - cc_gltf[2]
            l = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
            norms.append((dx / l, dy / l, dz / l))
            ao_v = max(0.74, min(1.0, 0.88 + 0.12 * (dy / l)))
            cols.append((ao_v, ao_v, ao_v))
        b.add_smooth_quad(
            pts[0], pts[1], pts[2], pts[3],
            norms[0], norms[1], norms[2], norms[3],
            [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)],
            cols,
        )

    if species == "rose":
        fmat = mats["foliage_rose"]
        center = (cx, cy_n, z_base + h * 0.42)
        for k in range(4):
            a = 2.0 * math.pi * k / 4.0 + rand01(k) * 0.5
            px = cx + 0.34 * math.cos(a)
            py = cy_n + 0.34 * math.sin(a)
            add_foliage_cluster(fmat, px, py, z_base + h * 0.42, h * 0.48, h * 0.42, center, cards=3)
        return

    # 1. Multi-segment subtly curving smooth trunk + primary boughs
    trunk_h = h * (0.28 if species in ("cedar", "pine") else 0.42)
    r_base = max(0.14, h * 0.028)
    r_mid = r_base * 0.68
    nb.add_smooth_cylinder(bark_mat, cx, cy_n, z_base, r_base, r_mid, trunk_h * 0.65, segs=10, ao_bot=0.64, ao_top=0.84)
    lean_x = (rand01(3) - 0.5) * 0.16
    lean_y = (rand01(4) - 0.5) * 0.16
    nb.add_smooth_cylinder(
        bark_mat,
        cx + lean_x * 0.4,
        cy_n + lean_y * 0.4,
        z_base + trunk_h * 0.62,
        r_mid,
        r_base * 0.38,
        trunk_h * 0.58,
        segs=9,
        ao_bot=0.78,
        ao_top=0.92,
    )

    if species == "cedar":
        # Himalayan Cedar (snow cedar): tall spire with 7 sweeping layered needle skirts
        fmat = mats["foliage_pine"]
        nb.add_smooth_cylinder(bark_mat, cx, cy_n, z_base + trunk_h, r_base * 0.42, 0.05, h * 0.62, segs=8, ao_bot=0.72, ao_top=0.90)
        cc = (cx, cy_n, z_base + h * 0.58)
        tiers = 7
        for ti in range(tiers):
            fz = 0.25 + ti * 0.105
            tr = h * 0.22 * (1.0 - ti * 0.115)
            n_boughs = 4 if ti < 4 else 3
            for bi in range(n_boughs):
                ang = (2.0 * math.pi * bi / n_boughs) + ti * 0.72
                bx = cx + tr * 0.52 * math.cos(ang)
                by = cy_n + tr * 0.52 * math.sin(ang)
                add_foliage_cluster(fmat, bx, by, z_base + h * fz, tr * 0.78, tr * 0.46, cc, cards=3)
        add_foliage_cluster(fmat, cx, cy_n, z_base + h * 0.94, h * 0.09, h * 0.10, cc, cards=3)
        return

    if species == "pine":
        # Chinese Pine (青松): sculptural irregular layered dark needle pads
        fmat = mats["foliage_pine"]
        cc = (cx + 0.18, cy_n, z_base + h * 0.66)
        pads = [
            (-0.18, -0.10, 0.46, 0.28, 0.16),
            (0.22, 0.08, 0.56, 0.27, 0.16),
            (-0.10, 0.18, 0.68, 0.26, 0.16),
            (0.18, -0.14, 0.78, 0.23, 0.15),
            (0.05, 0.02, 0.88, 0.20, 0.14),
        ]
        for ox, oy, fz, rxy, rz in pads:
            add_foliage_cluster(fmat, cx + ox * h, cy_n + oy * h, z_base + h * fz, h * rxy, h * rz, cc, cards=4)
        return

    # Deciduous trees (broad, ginkgo, magnolia, persimmon)
    fmat_map = {
        "ginkgo": mats["foliage_ginkgo"],
        "magnolia": mats["foliage_magnolia"],
        "persimmon": mats["foliage_persimmon"],
    }
    fmat = fmat_map.get(species, mats["foliage_broad"])

    # 3 primary angled boughs radiating into crown
    for bi in range(3):
        ang = (2.0 * math.pi * bi / 3.0) + rand01(20 + bi) * 0.6
        b_len = h * 0.22
        x0, y0, z0 = cx + lean_x * 0.5, cy_n + lean_y * 0.5, z_base + trunk_h * 0.95
        x1 = x0 + math.cos(ang) * b_len * 0.75
        y1 = y0 + math.sin(ang) * b_len * 0.75
        z1 = z0 + b_len * 0.85
        nb.add_limb(bark_mat, (x0, y0, z0), (x1, y1, z1), r_base * 0.34, r_base * 0.14, segs=6)

    cc = (cx, cy_n, z_base + h * 0.68)
    lobes = [
        (0.00, 0.00, 0.74, 0.30, 0.26),
        (-0.20, 0.07, 0.64, 0.25, 0.22),
        (0.20, -0.06, 0.66, 0.24, 0.21),
        (0.04, 0.20, 0.62, 0.23, 0.20),
        (-0.06, -0.19, 0.64, 0.23, 0.20),
        (0.02, 0.02, 0.88, 0.21, 0.18),
    ]
    for idx, (ox, oy, fz, rxy, rz) in enumerate(lobes):
        jx = (rand01(40 + idx) - 0.5) * 0.05
        jy = (rand01(60 + idx) - 0.5) * 0.05
        add_foliage_cluster(
            fmat,
            cx + (ox + jx) * h,
            cy_n + (oy + jy) * h,
            z_base + h * fz,
            h * rxy,
            h * rz,
            cc,
            cards=4,
        )


# ---------------------------------------------------------------------------
# High-Subdivision Sculpted Hero Landmarks (Shendu Boulder, Bing Xin Bust, Rockery)
# ---------------------------------------------------------------------------
def add_sculpted_shendu_boulder(nb, cx: float, cy_n: float, z0: float, h: float, mat: int, enu_to_gltf) -> None:
    """
    Smoothly subdivided natural weathered granite monolith matching west-motto-2024.webp:
    broad grounded base, organic tapering shoulders, rounded peak, flattened south inscription face.
    """
    rings = 14
    segs = 20
    rx0, ry0 = 0.64, 0.44
    pts_grid: List[List[Vec3]] = []

    for ri in range(rings + 1):
        t = ri / rings  # 0 bottom -> 1 top apex
        # Taper profile matching natural boulder silhouette
        if t < 0.72:
            scale = 1.0 - 0.28 * (t / 0.72) ** 1.6
        else:
            u = (t - 0.72) / 0.28
            scale = 0.72 * math.cos(u * math.pi * 0.48)
        z = z0 + h * t
        row: List[Vec3] = []
        for si in range(segs):
            a = (2.0 * math.pi * si) / segs
            ca, sa = math.cos(a), math.sin(a)
            # Subtle organic rock chiseled facets (quiet on south face sa < -0.5 for crisp inscription)
            n_amp = 0.03 if sa < -0.55 else 0.085
            bump = 1.0 + n_amp * math.sin(a * 3.0 + t * 5.2) + n_amp * 0.55 * math.cos(a * 5.0 - t * 7.8)
            rx = rx0 * scale * bump
            ry = ry0 * scale * bump
            # Gently flatten south face where "慎獨" is carved
            px = cx + rx * ca
            py = cy_n + ry * sa
            if sa < -0.62 and 0.08 < t < 0.84:
                py = max(py, cy_n - ry0 * scale * 0.86)
            row.append((px, py, z))
        pts_grid.append(row)

    b = nb.bucket(mat)
    # Build smooth averaged normals per grid vertex
    grid_gltf = [[enu_to_gltf(*p) for p in row] for row in pts_grid]
    center_gltf = enu_to_gltf(cx, cy_n, z0 + h * 0.42)
    norms_grid: List[List[Vec3]] = []
    for ri in range(rings + 1):
        nrow: List[Vec3] = []
        for si in range(segs):
            p = grid_gltf[ri][si]
            pl = grid_gltf[ri][(si - 1) % segs]
            pr = grid_gltf[ri][(si + 1) % segs]
            pd = grid_gltf[max(0, ri - 1)][si]
            pu = grid_gltf[min(rings, ri + 1)][si]
            tx, ty, tz = pr[0] - pl[0], pr[1] - pl[1], pr[2] - pl[2]
            bx, by, bz = pu[0] - pd[0], pu[1] - pd[1], pu[2] - pd[2]
            nx = ty * bz - tz * by
            ny = tz * bx - tx * bz
            nz = tx * by - ty * bx
            l = math.sqrt(nx * nx + ny * ny + nz * nz)
            if l < 1e-6 or ri == rings:
                dx, dy, dz = p[0] - center_gltf[0], p[1] - center_gltf[1], p[2] - center_gltf[2]
                l = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
                nrow.append((dx / l, dy / l, dz / l))
            else:
                nrow.append((nx / l, ny / l, nz / l))
        norms_grid.append(nrow)

    tile = 1.6
    for ri in range(rings):
        ao0 = 0.72 + 0.28 * (ri / rings)
        ao1 = 0.72 + 0.28 * ((ri + 1) / rings)
        for si in range(segs):
            sn = (si + 1) % segs
            p00, p10 = grid_gltf[ri][si], grid_gltf[ri][sn]
            p11, p01 = grid_gltf[ri + 1][sn], grid_gltf[ri + 1][si]
            n00, n10 = norms_grid[ri][si], norms_grid[ri][sn]
            n11, n01 = norms_grid[ri + 1][sn], norms_grid[ri + 1][si]
            u0, u1 = (si / segs) * (3.2 / tile), ((si + 1) / segs) * (3.2 / tile)
            v0, v1 = (ri / rings) * (h / tile), ((ri + 1) / rings) * (h / tile)
            b.add_smooth_quad(
                p00, p10, p11, p01,
                n00, n10, n11, n01,
                [(u0, v0), (u1, v0), (u1, v1), (u0, v1)],
                [(ao0, ao0, ao0), (ao0, ao0, ao0), (ao1, ao1, ao1), (ao1, ao1, ao1)],
            )


def add_sculpted_bingxin_bust(nb, cx: float, cy_n: float, z0: float, mat: int, enu_to_gltf) -> None:
    """Smoothly revolved & contoured bronze portrait bust for Bing Xin memorial statue."""
    # Profile slices: (dz, rx_width, ry_depth, y_offset)
    profile = [
        (0.00, 0.22, 0.16, 0.00),
        (0.10, 0.31, 0.19, -0.01),
        (0.24, 0.36, 0.20, 0.00),  # draped shoulders
        (0.38, 0.30, 0.17, 0.01),  # collarbone / shawl fold
        (0.47, 0.11, 0.10, 0.01),  # neck base
        (0.56, 0.088, 0.092, 0.00),  # neck
        (0.64, 0.115, 0.125, -0.02),  # chin & jaw
        (0.74, 0.148, 0.160, -0.01),  # cheeks & face
        (0.84, 0.156, 0.168, 0.01),  # brow & hair crown
        (0.92, 0.135, 0.155, 0.03),  # hair bun & top
        (0.97, 0.04, 0.04, 0.02),
    ]
    segs = 18
    grid_gltf: List[List[Vec3]] = []
    for dz, rx, ry, y_off in profile:
        row: List[Vec3] = []
        for si in range(segs):
            a = (2.0 * math.pi * si) / segs
            ca, sa = math.cos(a), math.sin(a)
            # Subtle nose/brow relief facing south (sa < 0) on face slice
            nose_bump = 0.018 * math.exp(-((a + math.pi * 0.5) ** 2) * 18.0) if 0.68 <= dz <= 0.80 else 0.0
            px = cx + rx * ca
            py = cy_n + y_off + (ry + nose_bump) * sa
            row.append(enu_to_gltf(px, py, z0 + dz))
        grid_gltf.append(row)

    b = nb.bucket(mat)
    rings = len(profile) - 1
    center = enu_to_gltf(cx, cy_n, z0 + 0.50)
    norms: List[List[Vec3]] = []
    for ri in range(rings + 1):
        nrow: List[Vec3] = []
        for si in range(segs):
            p = grid_gltf[ri][si]
            pl = grid_gltf[ri][(si - 1) % segs]
            pr = grid_gltf[ri][(si + 1) % segs]
            pd = grid_gltf[max(0, ri - 1)][si]
            pu = grid_gltf[min(rings, ri + 1)][si]
            tx, ty, tz = pr[0] - pl[0], pr[1] - pl[1], pr[2] - pl[2]
            bx, by, bz = pu[0] - pd[0], pu[1] - pd[1], pu[2] - pd[2]
            nx, ny, nz = ty * bz - tz * by, tz * bx - tx * bz, tx * by - ty * bx
            l = math.sqrt(nx * nx + ny * ny + nz * nz)
            if l < 1e-6 or ri == rings:
                dx, dy, dz = p[0] - center[0], p[1] - center[1], p[2] - center[2]
                l = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
                nrow.append((dx / l, dy / l, dz / l))
            else:
                nrow.append((nx / l, ny / l, nz / l))
        norms.append(nrow)

    for ri in range(rings):
        ao0 = 0.78 + 0.22 * (ri / rings)
        ao1 = 0.78 + 0.22 * ((ri + 1) / rings)
        for si in range(segs):
            sn = (si + 1) % segs
            b.add_smooth_quad(
                grid_gltf[ri][si], grid_gltf[ri][sn], grid_gltf[ri + 1][sn], grid_gltf[ri + 1][si],
                norms[ri][si], norms[ri][sn], norms[ri + 1][sn], norms[ri + 1][si],
                [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)],
                [(ao0, ao0, ao0), (ao0, ao0, ao0), (ao1, ao1, ao1), (ao1, ao1, ao1)],
            )


def add_sculpted_rockery_spire(
    nb, cx: float, cy_n: float, z0: float, h: float, rx: float, ry: float, seed: int, mat: int, enu_to_gltf
) -> None:
    """Organic vertical-fluted Taihu rockery spire with smooth shaded normals."""
    rings = 10
    segs = 14
    grid: List[List[Vec3]] = []
    for ri in range(rings + 1):
        t = ri / rings
        # Craggy tapering & slight overhang bulges typical of Taihu garden stone
        bulge = 1.0 + 0.16 * math.sin(t * math.pi * 2.5 + seed)
        taper = (1.0 - 0.78 * (t ** 1.35)) * bulge
        z = z0 + h * t
        row: List[Vec3] = []
        for si in range(segs):
            a = 2.0 * math.pi * si / segs
            flute = 1.0 + 0.22 * math.sin(a * 4.0 + seed * 1.3 + t * 2.1) + 0.12 * math.cos(a * 7.0 - t * 3.8)
            row.append(enu_to_gltf(cx + rx * taper * flute * math.cos(a), cy_n + ry * taper * flute * math.sin(a), z))
        grid.append(row)

    b = nb.bucket(mat)
    center = enu_to_gltf(cx, cy_n, z0 + h * 0.45)
    norms: List[List[Vec3]] = []
    for ri in range(rings + 1):
        nrow: List[Vec3] = []
        for si in range(segs):
            p = grid[ri][si]
            pl = grid[ri][(si - 1) % segs]
            pr = grid[ri][(si + 1) % segs]
            pd = grid[max(0, ri - 1)][si]
            pu = grid[min(rings, ri + 1)][si]
            tx, ty, tz = pr[0] - pl[0], pr[1] - pl[1], pr[2] - pl[2]
            bx, by, bz = pu[0] - pd[0], pu[1] - pd[1], pu[2] - pd[2]
            nx, ny, nz = ty * bz - tz * by, tz * bx - tx * bz, tx * by - ty * bx
            l = math.sqrt(nx * nx + ny * ny + nz * nz)
            if l < 1e-6 or ri == rings:
                dx, dy, dz = p[0] - center[0], p[1] - center[1], p[2] - center[2]
                l = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
                nrow.append((dx / l, dy / l, dz / l))
            else:
                nrow.append((nx / l, ny / l, nz / l))
        norms.append(nrow)

    tile = 1.6
    for ri in range(rings):
        ao0 = 0.68 + 0.30 * (ri / rings)
        ao1 = 0.68 + 0.30 * ((ri + 1) / rings)
        for si in range(segs):
            sn = (si + 1) % segs
            u0, u1 = (si / segs) * (2.6 / tile), ((si + 1) / segs) * (2.6 / tile)
            v0, v1 = (ri / rings) * (h / tile), ((ri + 1) / rings) * (h / tile)
            b.add_smooth_quad(
                grid[ri][si], grid[ri][sn], grid[ri + 1][sn], grid[ri + 1][si],
                norms[ri][si], norms[ri][sn], norms[ri + 1][sn], norms[ri + 1][si],
                [(u0, v0), (u1, v0), (u1, v1), (u0, v1)],
                [(ao0, ao0, ao0), (ao0, ao0, ao0), (ao1, ao1, ao1), (ao1, ao1, ao1)],
            )


# ---------------------------------------------------------------------------
# Campus Outdoor Nighttime Lamp Fixtures & Light Anchor Registry
# ---------------------------------------------------------------------------
def add_courtyard_lamp(
    nb,
    x: float,
    y: float,
    mats: dict,
    light_records: List[dict],
    pole_h: float = 3.85,
    kind: str = "courtyard",
    z0: float = 0.0,
) -> None:
    """Adds an architectural Beijing school courtyard lamp post with stepped base, decorative collar & caged lantern."""
    base_mat = mats["pbr_dark_slate"] if "pbr_dark_slate" in mats else mats["dark_steel"]
    # Stepped dark granite pedestal + flanged base collar
    nb.add_beveled_box(base_mat, x, y, z0, 0.36, 0.36, 0.18, bevel=0.025, ao_bot=0.72, ao_top=0.90)
    nb.add_smooth_cylinder(mats["dark_steel"], x, y, z0 + 0.18, 0.13, 0.09, 0.16, segs=10)
    nb.add_smooth_cylinder(mats["dark_steel"], x, y, z0 + 0.34, 0.068, 0.048, pole_h - 0.72, segs=10)
    # Lantern lower dish collar + warm frosted glass diffuser cylinder + 4 slim protective cage ribs
    z_lan = z0 + pole_h - 0.40
    nb.add_smooth_cylinder(mats["dark_steel"], x, y, z_lan - 0.04, 0.07, 0.16, 0.06, segs=10)
    nb.add_smooth_cylinder(mats["lamp_warm"], x, y, z_lan + 0.02, 0.135, 0.155, 0.32, segs=10, ao_bot=1.0, ao_top=1.0)
    for k in range(4):
        ang = (math.pi * 0.5 * k) + math.pi * 0.25
        rx, ry = x + 0.165 * math.cos(ang), y + 0.165 * math.sin(ang)
        nb.add_limb(mats["dark_steel"], (rx, ry, z_lan), (rx, ry, z_lan + 0.35), 0.011, 0.011, segs=4)
    # Two-tier overhanging conical rain hood + small finial spire
    nb.add_smooth_cylinder(mats["dark_steel"], x, y, z_lan + 0.34, 0.26, 0.10, 0.09, segs=10)
    nb.add_smooth_cylinder(mats["dark_steel"], x, y, z_lan + 0.43, 0.06, 0.015, 0.08, segs=8)
    light_records.append(
        {
            "kind": kind,
            "pos": [round(x, 2), round(z0 + pole_h - 0.18, 2), round(-y, 2)],
            "color": "#ffcf8c",
            "intensity": 14.0 if kind == "courtyard" else 18.0,
            "distance": 18.0,
        }
    )


def add_wall_sconce(
    nb,
    x: float,
    y: float,
    z: float,
    mats: dict,
    light_records: List[dict],
    color: str = "#ffd296",
    intensity: float = 10.0,
    distance: float = 12.0,
    kind: str = "sconce",
) -> None:
    """Adds a compact architectural wall/soffit sconce light fixture and registers its runtime light."""
    nb.add_box(mats["dark_steel"], x, y, z - 0.04, 0.22, 0.22, 0.06)
    nb.add_box(mats["lamp_warm"], x, y, z - 0.12, 0.18, 0.18, 0.08)
    light_records.append(
        {
            "kind": kind,
            "pos": [round(x, 2), round(z - 0.14, 2), round(-y, 2)],
            "color": color,
            "intensity": intensity,
            "distance": distance,
        }
    )


def write_campus_lights_ts(repo: Path, west_lights: List[dict], east_lights: List[dict]) -> None:
    """Exports exact glTF-space lighting anchors for both campuses to `src/data/campusLights.ts`."""
    out = repo / "src" / "data" / "campusLights.ts"
    content = (
        "// Auto-generated by blender/scripts/generate_campus_glb.py — exact glTF Y-up light anchors.\n"
        "import { CampusId } from \"./types\";\n\n"
        "export interface CampusLightAnchor {\n"
        "  kind: \"floodlight\" | \"courtyard\" | \"sconce\" | \"window_spill\" | \"gate_led\";\n"
        "  pos: [number, number, number];\n"
        "  target?: [number, number, number];\n"
        "  color: string;\n"
        "  intensity: number;\n"
        "  distance: number;\n"
        "}\n\n"
        f"export const CAMPUS_LIGHTS: Record<CampusId, CampusLightAnchor[]> = {{\n"
        f"  west: {json.dumps(west_lights, indent=2, ensure_ascii=False)},\n"
        f"  east: {json.dumps(east_lights, indent=2, ensure_ascii=False)},\n"
        "};\n"
    )
    out.write_text(content, encoding="utf-8")

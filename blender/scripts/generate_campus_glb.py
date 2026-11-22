#!/usr/bin/env python3
"""
Procedural L1-L4 Photo-Faithful glTF 2.0 (.glb) Generator for Beijing No. 166 Middle School
Generates:
  - public/models/west-campus.glb
  - public/models/east-campus.glb

Coordinate system:
  - Input metric data: ENU relative meters (e = +X East, n = +Y North, h = Up)
  - Export glTF 2.0 (right-handed Y-up): (x = e, y = h, z = -n)
  - Bakes structural pilasters, -0.20m window recesses, mullions, curved ramps,
    tensile trusses, gable/barrel roofs, hero signage, and analytical vertex AO.
"""

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from archviz_geometry import (
    add_botanical_tree,
    add_courtyard_lamp,
    add_hero_room_box,
    add_sculpted_bingxin_bust,
    add_sculpted_rockery_spire,
    add_sculpted_shendu_boulder,
    add_shallow_room,
    add_wall_sconce,
    compute_metric_quad_uvs,
    compute_metric_tri_uvs,
    populate_legacy_redirects,
    register_archviz_materials,
    write_campus_lights_ts,
)
from detailed_props import (
    add_accessible_ramp_wedge,
    add_building_entrance_portal,
    add_chinese_pavilion,
    add_detailed_ac_unit,
    add_detailed_bicycle_rack,
    add_detailed_stadium_floodlight,
    add_detailed_wall_run,
    add_granite_stairs,
    add_hollow_round_planter,
    add_planter_box,
    add_planter_foliage,
    add_realistic_basketball_hoop,
    add_realistic_bicycle_row,
    add_realistic_double_basketball_hoop,
    add_realistic_pingpong_table,
    add_rect_beam,
    add_rooftop_penthouse,
    add_stone_curved_ramp,
    add_stone_curb_polyline,
    add_torus_ring,
    add_wheeled_aframe_barricade,
)

Vec3 = Tuple[float, float, float]
Vec2 = Tuple[float, float]
RGB = Tuple[float, float, float]
UVBox = Tuple[float, float, float, float]

# ---------------------------------------------------------------------------
# UV Atlas Coordinates (glTF space: (0,0) top-left -> (1,1) bottom-right)
# ---------------------------------------------------------------------------
UV_WEST_FASCIA: UVBox = (0.01, 0.01, 0.99, 0.215)
UV_WEST_FASCIA_PLAIN: UVBox = (0.01, 0.01, 0.150, 0.213)
UV_WEST_LED_ONLY: UVBox = (0.166, 0.041, 0.834, 0.178)
UV_WEST_PLAQUE: UVBox = (0.015, 0.245, 0.268, 0.755)
UV_SHENDU_STONE: UVBox = (0.305, 0.245, 0.615, 0.755)
UV_SHENDU_GRANITE: UVBox = (0.312, 0.248, 0.608, 0.320)
UV_MARBLE: UVBox = (0.645, 0.245, 0.995, 0.515)
UV_BURGUNDY: UVBox = (0.645, 0.545, 0.995, 0.755)
UV_EAST_SIGN: UVBox = (0.015, 0.785, 0.49, 0.992)
UV_SPEED_5: UVBox = (0.525, 0.785, 0.755, 0.992)
UV_FLAG: UVBox = (0.785, 0.785, 0.995, 0.995)

UV_STAGE_LED: UVBox = (0.005, 0.005, 0.715, 0.315)
UV_PILLAR_LEFT: UVBox = (0.742, 0.005, 0.858, 0.515)
UV_PILLAR_RIGHT: UVBox = (0.882, 0.005, 0.995, 0.515)
UV_PA_SPEAKER: UVBox = (0.6855, 0.3340, 0.7344, 0.5215)
UV_B_WALL_SIGN: UVBox = (0.005, 0.345, 0.335, 0.995)
UV_BOOK_B: UVBox = (0.365, 0.345, 0.505, 0.655)
UV_BOOK_D: UVBox = (0.525, 0.345, 0.665, 0.655)
UV_BOOK_C: UVBox = (0.688, 0.530, 0.808, 0.668)
UV_CAFETERIA_SIGN: UVBox = (0.822, 0.543, 0.992, 0.654)
UV_MUSIC_SIGN: UVBox = (0.362, 0.682, 0.758, 0.830)
UV_HISTORY_SIGN: UVBox = (0.776, 0.682, 0.990, 0.752)
UV_LIBRARY_SIGN: UVBox = (0.776, 0.764, 0.990, 0.834)
UV_RELIEF_WALL: UVBox = (0.365, 0.862, 0.995, 0.995)

# Fine West Campus Details Atlas (tex_west_details.png)
UV_C_WHITE_RELIEF: UVBox = (0.0117, 0.0117, 0.3008, 0.7383)
UV_DARK_SLATE_PODIUM: UVBox = (0.3262, 0.0137, 0.5645, 0.2520)
UV_GLASS_BACKBOARD: UVBox = (0.5898, 0.0117, 0.9883, 0.2461)
UV_CRAZY_PAVING: UVBox = (0.3262, 0.2754, 0.5645, 0.5137)
UV_WHITE_PEBBLES: UVBox = (0.5918, 0.2754, 0.7676, 0.3828)
UV_ROCKERY_WATER: UVBox = (0.5918, 0.4043, 0.7676, 0.5137)
UV_FIRE_BOX: UVBox = (0.7930, 0.2734, 0.9883, 0.3984)
UV_HARD_COURT_APRON: UVBox = (0.7949, 0.4160, 0.8770, 0.5137)
UV_SALMON_WALL: UVBox = (0.8945, 0.4141, 0.9883, 0.5156)
UV_HISTORY_GLASS_DOOR: UVBox = (0.3242, 0.5352, 0.6992, 0.7461)
UV_LANE_NUMS: Tuple[UVBox, UVBox, UVBox, UVBox] = (
    (0.7227, 0.5391, 0.7832, 0.6367),
    (0.7910, 0.5391, 0.8516, 0.6367),
    (0.8594, 0.5391, 0.9199, 0.6367),
    (0.9277, 0.5391, 0.9883, 0.6367),
)
UV_AC_UNIT_FRONT: UVBox = (0.7227, 0.6523, 0.9883, 0.7461)
UV_NEIGHBOR_OCHRE: UVBox = (0.0137, 0.7676, 0.2441, 0.9863)
UV_NEIGHBOR_DIAMOND: UVBox = (0.2676, 0.7676, 0.4980, 0.9863)
UV_BLUE_TILE_ROOF: UVBox = (0.5215, 0.7676, 0.7441, 0.9863)
UV_PINGPONG_TOP: UVBox = (0.7656, 0.7656, 0.9883, 0.8711)
UV_VOLLEY_NET: UVBox = (0.7656, 0.8867, 0.9883, 0.9883)


def surf_cell(col: int, row: int, margin: float = 0.015) -> UVBox:
    return (
        col * 0.25 + margin,
        row * 0.25 + margin,
        (col + 1) * 0.25 - margin,
        (row + 1) * 0.25 - margin,
    )


UV_TERRACOTTA_BRICK = surf_cell(0, 0)
UV_GREY_RIB = surf_cell(1, 0)
UV_QINGZHUAN = surf_cell(2, 0)
UV_STUCCO = surf_cell(3, 0)
UV_GREY_TILE = surf_cell(0, 1)
UV_RED_TILE = surf_cell(1, 1)
UV_GREEN_ROOF = surf_cell(2, 1)
UV_RED_BRICK_WALK = surf_cell(3, 1)
UV_TRACK_EPDM = surf_cell(0, 2)
UV_COURT_GREEN = surf_cell(1, 2)
UV_PLAZA_TILE = surf_cell(2, 2)
UV_GRASS = surf_cell(3, 2)
UV_GLASS_WINDOW = surf_cell(0, 3)
UV_FOLIAGE = surf_cell(1, 3)
UV_ASPHALT = surf_cell(2, 3)
UV_SKYLIGHT = surf_cell(3, 3)


def enu_to_gltf(e: float, n: float, h: float) -> Vec3:
    return (e, h, -n)


def vsub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vadd(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vcross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def vnorm(a: Vec3) -> Vec3:
    l = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-8 else (0.0, 1.0, 0.0)


def clean_ring(pts: List[Vec2]) -> List[Vec2]:
    out: List[Vec2] = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 0.08:
            out.append(p)
    if len(out) > 2 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 0.08:
        out.pop()
    return out


def signed_area_2d(pts: List[Vec2]) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return 0.5 * a


def ensure_ccw(pts: List[Vec2]) -> List[Vec2]:
    c = clean_ring(pts)
    if len(c) < 3:
        return c
    if signed_area_2d(c) < 0:
        c.reverse()
    return c


def ear_clip_2d(poly: List[Vec2]) -> List[Tuple[int, int, int]]:
    """Ear-clipping triangulation of a simple CCW 2D polygon."""
    pts = ensure_ccw(poly)
    n = len(pts)
    if n < 3:
        return []
    if n == 3:
        return [(0, 1, 2)]

    def cross2(a: Vec2, b: Vec2, c: Vec2) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def in_tri(p: Vec2, a: Vec2, b: Vec2, c: Vec2) -> bool:
        c1 = cross2(a, b, p)
        c2 = cross2(b, c, p)
        c3 = cross2(c, a, p)
        return c1 >= -1e-7 and c2 >= -1e-7 and c3 >= -1e-7

    verts = list(range(n))
    tris: List[Tuple[int, int, int]] = []
    guard = 0
    while len(verts) > 3 and guard < n * n:
        guard += 1
        ear_found = False
        m = len(verts)
        for i in range(m):
            ia = verts[(i - 1) % m]
            ib = verts[i]
            ic = verts[(i + 1) % m]
            pa, pb, pc = pts[ia], pts[ib], pts[ic]
            if cross2(pa, pb, pc) <= 1e-8:
                continue
            has_inside = False
            for j in verts:
                if j in (ia, ib, ic):
                    continue
                if in_tri(pts[j], pa, pb, pc):
                    has_inside = True
                    break
            if not has_inside:
                tris.append((ia, ib, ic))
                verts.pop(i)
                ear_found = True
                break
        if not ear_found:
            break
    if len(verts) == 3:
        tris.append((verts[0], verts[1], verts[2]))
    return tris


# ---------------------------------------------------------------------------
# Mesh Collector & Geometry Helpers
# ---------------------------------------------------------------------------
class PrimitiveBucket:
    def __init__(self, mat_idx: int):
        self.mat_idx = mat_idx
        self.pos: List[Vec3] = []
        self.norm: List[Vec3] = []
        self.uv: List[Vec2] = []
        self.col: List[RGB] = []
        self.idx: List[int] = []

    def add_tri(
        self,
        p0: Vec3, p1: Vec3, p2: Vec3,
        u0: Vec2, u1: Vec2, u2: Vec2,
        c0: RGB = (1.0, 1.0, 1.0), c1: RGB = (1.0, 1.0, 1.0), c2: RGB = (1.0, 1.0, 1.0),
        double_sided: bool = False,
    ) -> None:
        n = vnorm(vcross(vsub(p1, p0), vsub(p2, p0)))
        base = len(self.pos)
        self.pos.extend([p0, p1, p2])
        self.norm.extend([n, n, n])
        self.uv.extend([u0, u1, u2])
        self.col.extend([c0, c1, c2])
        self.idx.extend([base, base + 1, base + 2])
        if double_sided:
            nb = (-n[0], -n[1], -n[2])
            b2 = len(self.pos)
            self.pos.extend([p0, p2, p1])
            self.norm.extend([nb, nb, nb])
            self.uv.extend([u0, u2, u1])
            self.col.extend([c0, c2, c1])
            self.idx.extend([b2, b2 + 1, b2 + 2])

    def add_quad(
        self,
        p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3,
        uv_box: UVBox = (0.0, 0.0, 1.0, 1.0),
        c_bot: float = 1.0, c_top: float = 1.0,
        flip_uv_x: bool = False,
        double_sided: bool = False,
    ) -> None:
        u0, v0, u1, v1 = uv_box
        if flip_uv_x:
            u0, u1 = u1, u0
        # p0 = bottom-left, p1 = bottom-right, p2 = top-right, p3 = top-left (CCW outward)
        cb = (c_bot, c_bot, c_bot)
        ct = (c_top, c_top, c_top)
        uv0, uv1, uv2, uv3 = (u0, v1), (u1, v1), (u1, v0), (u0, v0)
        n = vnorm(vcross(vsub(p1, p0), vsub(p2, p0)))
        base = len(self.pos)
        self.pos.extend([p0, p1, p2, p3])
        self.norm.extend([n, n, n, n])
        self.uv.extend([uv0, uv1, uv2, uv3])
        self.col.extend([cb, cb, ct, ct])
        self.idx.extend([base, base + 1, base + 2, base, base + 2, base + 3])
        if double_sided:
            nb = (-n[0], -n[1], -n[2])
            b2 = len(self.pos)
            self.pos.extend([p0, p3, p2, p1])
            self.norm.extend([nb, nb, nb, nb])
            self.uv.extend([uv0, uv3, uv2, uv1])
            self.col.extend([cb, ct, ct, cb])
            self.idx.extend([b2, b2 + 1, b2 + 2, b2, b2 + 2, b2 + 3])

    def add_quad_uvs(
        self,
        p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3,
        uv0: Vec2, uv1: Vec2, uv2: Vec2, uv3: Vec2,
        c_bot: float = 1.0, c_top: float = 1.0,
        double_sided: bool = False,
    ) -> None:
        cb = (c_bot, c_bot, c_bot)
        ct = (c_top, c_top, c_top)
        n = vnorm(vcross(vsub(p1, p0), vsub(p2, p0)))
        base = len(self.pos)
        self.pos.extend([p0, p1, p2, p3])
        self.norm.extend([n, n, n, n])
        self.uv.extend([uv0, uv1, uv2, uv3])
        self.col.extend([cb, cb, ct, ct])
        self.idx.extend([base, base + 1, base + 2, base, base + 2, base + 3])
        if double_sided:
            nb = (-n[0], -n[1], -n[2])
            b2 = len(self.pos)
            self.pos.extend([p0, p3, p2, p1])
            self.norm.extend([nb, nb, nb, nb])
            self.uv.extend([uv0, uv3, uv2, uv1])
            self.col.extend([cb, ct, ct, cb])
            self.idx.extend([b2, b2 + 1, b2 + 2, b2, b2 + 2, b2 + 3])

    def add_smooth_quad(
        self,
        p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3,
        n0: Vec3, n1: Vec3, n2: Vec3, n3: Vec3,
        uvs: List[Vec2],
        cols: List[RGB],
        double_sided: bool = False,
    ) -> None:
        base = len(self.pos)
        self.pos.extend([p0, p1, p2, p3])
        self.norm.extend([n0, n1, n2, n3])
        self.uv.extend(uvs)
        self.col.extend(cols)
        self.idx.extend([base, base + 1, base + 2, base, base + 2, base + 3])
        if double_sided:
            b2 = len(self.pos)
            self.pos.extend([p0, p3, p2, p1])
            self.norm.extend([
                (-n0[0], -n0[1], -n0[2]),
                (-n3[0], -n3[1], -n3[2]),
                (-n2[0], -n2[1], -n2[2]),
                (-n1[0], -n1[1], -n1[2]),
            ])
            self.uv.extend([uvs[0], uvs[3], uvs[2], uvs[1]])
            self.col.extend([cols[0], cols[3], cols[2], cols[1]])
            self.idx.extend([b2, b2 + 1, b2 + 2, b2, b2 + 2, b2 + 3])


class NodeBuilder:
    def __init__(
        self,
        name: str,
        metric_tiles: Optional[Dict[int, float]] = None,
        legacy_redirects: Optional[Dict[Tuple[int, UVBox], Tuple[int, float]]] = None,
        mats: Optional[dict] = None,
        classic_mode: bool = False,
        double_sided_mats: Optional[Set[int]] = None,
    ):
        self.name = name
        self.buckets: Dict[int, PrimitiveBucket] = {}
        self.metric_tiles: Dict[int, float] = metric_tiles or {}
        self.legacy_redirects: Dict[Tuple[int, UVBox], Tuple[int, float]] = legacy_redirects or {}
        self.mats: dict = mats or {}
        self.classic_mode: bool = classic_mode
        self.double_sided_mats: Set[int] = double_sided_mats if double_sided_mats is not None else set()

    def _resolve_mat_tile(self, mat: int, uv_box: Optional[UVBox] = None) -> Tuple[int, Optional[float]]:
        if uv_box is not None and (mat, uv_box) in self.legacy_redirects:
            return self.legacy_redirects[(mat, uv_box)]
        if mat in self.metric_tiles:
            return mat, self.metric_tiles[mat]
        return mat, None

    def bucket(self, mat_idx: int) -> PrimitiveBucket:
        if mat_idx not in self.buckets:
            self.buckets[mat_idx] = PrimitiveBucket(mat_idx)
        return self.buckets[mat_idx]

    def quad_enu(
        self,
        mat: int,
        e0: Vec3, e1: Vec3, e2: Vec3, e3: Vec3,
        uv_box: UVBox = (0.0, 0.0, 1.0, 1.0),
        c_bot: float = 1.0, c_top: float = 1.0,
        flip_uv_x: bool = False,
        double_sided: bool = False,
    ) -> None:
        # e0=(east, north, up)
        p0 = enu_to_gltf(*e0)
        p1 = enu_to_gltf(*e1)
        p2 = enu_to_gltf(*e2)
        p3 = enu_to_gltf(*e3)
        resolved_mat, tile_m = self._resolve_mat_tile(mat, uv_box)
        # Never emit duplicate back-to-back triangles when the glTF material itself is doubleSided (PR #19 anti-Z-fighting)
        if resolved_mat in self.double_sided_mats:
            double_sided = False
        if tile_m is not None:
            uv0, uv1, uv2, uv3 = compute_metric_quad_uvs(p0, p1, p2, p3, tile_m)
            self.bucket(resolved_mat).add_quad_uvs(p0, p1, p2, p3, uv0, uv1, uv2, uv3, c_bot, c_top, double_sided)
        else:
            self.bucket(resolved_mat).add_quad(p0, p1, p2, p3, uv_box, c_bot, c_top, flip_uv_x, double_sided)

    def tri_enu(
        self,
        mat: int,
        e0: Vec3, e1: Vec3, e2: Vec3,
        uv0: Vec2, uv1: Vec2, uv2: Vec2,
        c0: float = 1.0, c1: float = 1.0, c2: float = 1.0,
        double_sided: bool = False,
    ) -> None:
        p0, p1, p2 = enu_to_gltf(*e0), enu_to_gltf(*e1), enu_to_gltf(*e2)
        resolved_mat, tile_m = self._resolve_mat_tile(mat, None)
        if resolved_mat in self.double_sided_mats:
            double_sided = False
        if tile_m is not None:
            uv0, uv1, uv2 = compute_metric_tri_uvs(p0, p1, p2, tile_m)
        self.bucket(resolved_mat).add_tri(
            p0, p1, p2,
            uv0, uv1, uv2, (c0, c0, c0), (c1, c1, c1), (c2, c2, c2), double_sided=double_sided
        )

    def add_smooth_cylinder(
        self,
        mat: int,
        cx: float, cy_n: float, z_bot: float,
        r_bot: float, r_top: float, h: float,
        segs: int = 12,
        ao_bot: float = 0.76, ao_top: float = 1.0,
    ) -> None:
        resolved_mat, tile_m = self._resolve_mat_tile(mat, None)
        b = self.bucket(resolved_mat)
        zt = z_bot + h
        tile = tile_m or 1.6
        circ = max(0.5, math.pi * (r_bot + r_top))
        for i in range(segs):
            a0 = (2.0 * math.pi * i) / segs
            a1 = (2.0 * math.pi * (i + 1)) / segs
            ca0, sa0 = math.cos(a0), math.sin(a0)
            ca1, sa1 = math.cos(a1), math.sin(a1)
            p0b = enu_to_gltf(cx + r_bot * ca0, cy_n + r_bot * sa0, z_bot)
            p1b = enu_to_gltf(cx + r_bot * ca1, cy_n + r_bot * sa1, z_bot)
            p1t = enu_to_gltf(cx + r_top * ca1, cy_n + r_top * sa1, zt)
            p0t = enu_to_gltf(cx + r_top * ca0, cy_n + r_top * sa0, zt)
            n0 = (ca0, 0.0, -sa0)
            n1 = (ca1, 0.0, -sa1)
            u0 = (i / segs) * (circ / tile)
            u1 = ((i + 1) / segs) * (circ / tile)
            v1 = h / tile
            b.add_smooth_quad(
                p0b, p1b, p1t, p0t, n0, n1, n1, n0,
                [(u0, 0.0), (u1, 0.0), (u1, v1), (u0, v1)],
                [(ao_bot, ao_bot, ao_bot), (ao_bot, ao_bot, ao_bot), (ao_top, ao_top, ao_top), (ao_top, ao_top, ao_top)],
            )
            if r_top > 0.02:
                self.tri_enu(
                    resolved_mat,
                    (cx, cy_n, zt),
                    (cx + r_top * ca0, cy_n + r_top * sa0, zt),
                    (cx + r_top * ca1, cy_n + r_top * sa1, zt),
                    (0.5, 0.5), (0.1, 0.1), (0.9, 0.1),
                    ao_top, ao_top, ao_top,
                )

    def add_limb(
        self,
        mat: int,
        p_start: Vec3, p_end: Vec3,
        r0: float, r1: float,
        segs: int = 6,
    ) -> None:
        """Tapered smooth cylindrical branch between arbitrary 3D ENU endpoints."""
        resolved_mat, tile_m = self._resolve_mat_tile(mat, None)
        b = self.bucket(resolved_mat)
        dx, dy, dz = p_end[0] - p_start[0], p_end[1] - p_start[1], p_end[2] - p_start[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 0.05:
            return
        ax = (dx / length, dy / length, dz / length)
        ref = (0.0, 0.0, 1.0) if abs(ax[2]) < 0.9 else (1.0, 0.0, 0.0)
        u_ax = vnorm(vcross(ax, ref))
        v_ax = vnorm(vcross(ax, u_ax))
        tile = tile_m or 1.4
        for i in range(segs):
            a0 = 2.0 * math.pi * i / segs
            a1 = 2.0 * math.pi * (i + 1) / segs
            d0 = (u_ax[0] * math.cos(a0) + v_ax[0] * math.sin(a0), u_ax[1] * math.cos(a0) + v_ax[1] * math.sin(a0), u_ax[2] * math.cos(a0) + v_ax[2] * math.sin(a0))
            d1 = (u_ax[0] * math.cos(a1) + v_ax[0] * math.sin(a1), u_ax[1] * math.cos(a1) + v_ax[1] * math.sin(a1), u_ax[2] * math.cos(a1) + v_ax[2] * math.sin(a1))
            q0 = enu_to_gltf(p_start[0] + d0[0] * r0, p_start[1] + d0[1] * r0, p_start[2] + d0[2] * r0)
            q1 = enu_to_gltf(p_start[0] + d1[0] * r0, p_start[1] + d1[1] * r0, p_start[2] + d1[2] * r0)
            q2 = enu_to_gltf(p_end[0] + d1[0] * r1, p_end[1] + d1[1] * r1, p_end[2] + d1[2] * r1)
            q3 = enu_to_gltf(p_end[0] + d0[0] * r1, p_end[1] + d0[1] * r1, p_end[2] + d0[2] * r1)
            n0 = enu_to_gltf(*d0)
            n1 = enu_to_gltf(*d1)
            b.add_smooth_quad(
                q0, q1, q2, q3, n0, n1, n1, n0,
                [(i / segs, 0.0), ((i + 1) / segs, 0.0), ((i + 1) / segs, length / tile), (i / segs, length / tile)],
                [(0.72, 0.72, 0.72), (0.72, 0.72, 0.72), (0.90, 0.90, 0.90), (0.90, 0.90, 0.90)],
            )

    def add_beveled_box(
        self,
        mat: int,
        cx: float, cy_n: float, z_bot: float,
        w: float, d: float, h: float,
        yaw_rad: float = 0.0,
        uv_box: UVBox = (0.0, 0.0, 1.0, 1.0),
        bevel: float = 0.035,
        ao_bot: float = 0.78, ao_top: float = 1.0,
        top_mat: Optional[int] = None, top_uv: Optional[UVBox] = None,
    ) -> None:
        """Architectural box with 45-degree vertical corner chamfers & top bevel for realistic specular catchlights."""
        bv = min(bevel, w * 0.18, d * 0.18, h * 0.18)
        if bv < 0.008:
            self.add_box(mat, cx, cy_n, z_bot, w, d, h, yaw_rad, uv_box, ao_bot, ao_top, top_mat, top_uv)
            return
        hw, hd = w * 0.5, d * 0.5
        cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

        def rot(lx: float, ly: float) -> Vec2:
            return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs)

        # 8-vertex chamfered octagon footprint (CCW)
        ring = [
            rot(-hw + bv, -hd),
            rot(hw - bv, -hd),
            rot(hw, -hd + bv),
            rot(hw, hd - bv),
            rot(hw - bv, hd),
            rot(-hw + bv, hd),
            rot(-hw, hd - bv),
            rot(-hw, -hd + bv),
        ]
        # Slightly inset top ring for crisp top coping bevel
        top_ring = [
            rot(-hw + bv * 1.4, -hd + bv * 0.7),
            rot(hw - bv * 1.4, -hd + bv * 0.7),
            rot(hw - bv * 0.7, -hd + bv * 1.4),
            rot(hw - bv * 0.7, hd - bv * 1.4),
            rot(hw - bv * 1.4, hd - bv * 0.7),
            rot(-hw + bv * 1.4, hd - bv * 0.7),
            rot(-hw + bv * 0.7, hd - bv * 1.4),
            rot(-hw + bv * 0.7, -hd + bv * 1.4),
        ]
        z_sh = z_bot + h - bv
        zt = z_bot + h
        tm = top_mat if top_mat is not None else mat
        tuv = top_uv if top_uv is not None else uv_box
        for i in range(8):
            a, b_pt = ring[i], ring[(i + 1) % 8]
            ta, tb = top_ring[i], top_ring[(i + 1) % 8]
            self.quad_enu(mat, (a[0], a[1], z_bot), (b_pt[0], b_pt[1], z_bot), (b_pt[0], b_pt[1], z_sh), (a[0], a[1], z_sh), uv_box, ao_bot, ao_top)
            self.quad_enu(tm, (a[0], a[1], z_sh), (b_pt[0], b_pt[1], z_sh), (tb[0], tb[1], zt), (ta[0], ta[1], zt), tuv, ao_top * 0.96, ao_top)
        self.add_polygon_patch(top_ring, zt, tm, tuv, ao=ao_top)

    def add_box(
        self,
        mat: int,
        cx: float, cy_n: float, z_bot: float,
        w: float, d: float, h: float,
        yaw_rad: float = 0.0,
        uv_box: UVBox = (0.0, 0.0, 1.0, 1.0),
        ao_bot: float = 0.76, ao_top: float = 1.0,
        top_mat: Optional[int] = None, top_uv: Optional[UVBox] = None,
    ) -> None:
        hw, hd = w * 0.5, d * 0.5
        cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

        def rot(lx: float, ly: float) -> Vec2:
            return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs)

        c0 = rot(-hw, -hd)  # SW
        c1 = rot(hw, -hd)   # SE
        c2 = rot(hw, hd)    # NE
        c3 = rot(-hw, hd)   # NW
        zt = z_bot + h
        # 4 side walls in CCW order: S(c0->c1), E(c1->c2), N(c2->c3), W(c3->c0)
        for a, b in [(c0, c1), (c1, c2), (c2, c3), (c3, c0)]:
            self.quad_enu(
                mat,
                (a[0], a[1], z_bot), (b[0], b[1], z_bot),
                (b[0], b[1], zt), (a[0], a[1], zt),
                uv_box, ao_bot, ao_top,
            )
        tm = top_mat if top_mat is not None else mat
        tuv = top_uv if top_uv is not None else uv_box
        self.quad_enu(
            tm,
            (c0[0], c0[1], zt), (c1[0], c1[1], zt),
            (c2[0], c2[1], zt), (c3[0], c3[1], zt),
            tuv, ao_top, ao_top,
        )
        # bottom cap
        self.quad_enu(
            mat,
            (c3[0], c3[1], z_bot), (c2[0], c2[1], z_bot),
            (c1[0], c1[1], z_bot), (c0[0], c0[1], z_bot),
            uv_box, ao_bot, ao_bot,
        )

    def add_cylinder(
        self,
        mat: int,
        cx: float, cy_n: float, z_bot: float,
        r_bot: float, r_top: float, h: float,
        segs: int = 10,
        uv_box: UVBox = (0.0, 0.0, 1.0, 1.0),
        ao_bot: float = 0.78, ao_top: float = 1.0,
    ) -> None:
        u0, v0, u1, v1 = uv_box
        zt = z_bot + h
        for i in range(segs):
            a0 = (2.0 * math.pi * i) / segs
            a1 = (2.0 * math.pi * (i + 1)) / segs
            p0b = (cx + r_bot * math.cos(a0), cy_n + r_bot * math.sin(a0), z_bot)
            p1b = (cx + r_bot * math.cos(a1), cy_n + r_bot * math.sin(a1), z_bot)
            p1t = (cx + r_top * math.cos(a1), cy_n + r_top * math.sin(a1), zt)
            p0t = (cx + r_top * math.cos(a0), cy_n + r_top * math.sin(a0), zt)
            self.quad_enu(mat, p0b, p1b, p1t, p0t, uv_box, ao_bot, ao_top)
            if r_top > 0.02:
                self.tri_enu(
                    mat,
                    (cx, cy_n, zt), p0t, p1t,
                    ((u0 + u1) * 0.5, (v0 + v1) * 0.5), (u0, v0), (u1, v0),
                    ao_top, ao_top, ao_top,
                )

    def add_sphere(
        self,
        mat: int,
        cx: float, cy_n: float, cz: float,
        rx: float, ry: float, rz: float,
        segs: int = 10, rings: int = 6,
        uv_box: UVBox = (0.0, 0.0, 1.0, 1.0),
        ao: float = 0.95,
    ) -> None:
        """Low-poly UV sphere in ENU space (tree crowns, flowers, fruit, busts)."""
        for i in range(rings):
            phi0 = -math.pi * 0.5 + math.pi * i / rings
            phi1 = -math.pi * 0.5 + math.pi * (i + 1) / rings
            c0, c1 = math.cos(phi0), math.cos(phi1)
            s0, s1 = math.sin(phi0), math.sin(phi1)
            for j in range(segs):
                th0 = 2.0 * math.pi * j / segs
                th1 = 2.0 * math.pi * (j + 1) / segs
                p00 = (cx + rx * c0 * math.cos(th0), cy_n + rz * c0 * math.sin(th0), cz + ry * s0)
                p10 = (cx + rx * c0 * math.cos(th1), cy_n + rz * c0 * math.sin(th1), cz + ry * s0)
                p11 = (cx + rx * c1 * math.cos(th1), cy_n + rz * c1 * math.sin(th1), cz + ry * s1)
                p01 = (cx + rx * c1 * math.cos(th0), cy_n + rz * c1 * math.sin(th0), cz + ry * s1)
                self.quad_enu(
                    mat, p00, p10, p11, p01, uv_box,
                    ao * (0.90 + 0.10 * (i / max(rings - 1, 1))),
                    ao * (0.90 + 0.10 * ((i + 1) / max(rings - 1, 1))),
                )

    def add_polygon_slab(
        self,
        poly_ccw: List[Vec2],
        z_bot: float, z_top: float,
        side_mat: int, top_mat: int,
        side_uv: UVBox, top_uv: UVBox,
        tile_m: float = 8.0,
        ao_bot: float = 0.85, ao_top: float = 1.0,
    ) -> None:
        pts = ensure_ccw(poly_ccw)
        n = len(pts)
        if n < 3:
            return
        for i in range(n):
            a = pts[i]
            b = pts[(i + 1) % n]
            self.quad_enu(
                side_mat,
                (a[0], a[1], z_bot), (b[0], b[1], z_bot),
                (b[0], b[1], z_top), (a[0], a[1], z_top),
                side_uv, ao_bot, ao_top,
            )
        tris = ear_clip_2d(pts)
        resolved_top, top_tile = self._resolve_mat_tile(top_mat, top_uv)
        tu0, tv0, tu1, tv1 = top_uv
        du, dv = tu1 - tu0, tv1 - tv0
        for ia, ib, ic in tris:
            pa, pb, pc = pts[ia], pts[ib], pts[ic]
            if top_tile is not None:
                inv_t = 1.0 / max(top_tile, 0.25)
                uva = (pa[0] * inv_t, -pa[1] * inv_t)
                uvb = (pb[0] * inv_t, -pb[1] * inv_t)
                uvc = (pc[0] * inv_t, -pc[1] * inv_t)
                self.bucket(resolved_top).add_tri(
                    enu_to_gltf(pa[0], pa[1], z_top),
                    enu_to_gltf(pb[0], pb[1], z_top),
                    enu_to_gltf(pc[0], pc[1], z_top),
                    uva, uvb, uvc,
                    (ao_top, ao_top, ao_top), (ao_top, ao_top, ao_top), (ao_top, ao_top, ao_top),
                )
            else:
                self.tri_enu(
                    resolved_top,
                    (pa[0], pa[1], z_top), (pb[0], pb[1], z_top), (pc[0], pc[1], z_top),
                    (tu0 + 0.1 * du, tv0 + 0.1 * dv),
                    (tu0 + 0.9 * du, tv0 + 0.1 * dv),
                    (tu0 + 0.5 * du, tv0 + 0.9 * dv),
                    ao_top, ao_top, ao_top,
                )

    def add_polygon_patch(
        self,
        poly_ccw: List[Vec2],
        z: float,
        mat: int,
        uv_box: UVBox,
        scale_m: float = 10.0,
        ao: float = 1.0,
    ) -> None:
        pts = ensure_ccw(poly_ccw)
        if len(pts) < 3:
            return
        resolved_mat, tile_m = self._resolve_mat_tile(mat, uv_box)
        tris = ear_clip_2d(pts)
        if tile_m is not None:
            inv_t = 1.0 / max(tile_m, 0.25)
            for ia, ib, ic in tris:
                pa, pb, pc = pts[ia], pts[ib], pts[ic]
                self.bucket(resolved_mat).add_tri(
                    enu_to_gltf(pa[0], pa[1], z),
                    enu_to_gltf(pb[0], pb[1], z),
                    enu_to_gltf(pc[0], pc[1], z),
                    (pa[0] * inv_t, -pa[1] * inv_t),
                    (pb[0] * inv_t, -pb[1] * inv_t),
                    (pc[0] * inv_t, -pc[1] * inv_t),
                    (ao, ao, ao), (ao, ao, ao), (ao, ao, ao),
                )
            return

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        spanx = max(maxx - minx, 0.1)
        spany = max(maxy - miny, 0.1)
        u0, v0, u1, v1 = uv_box
        for ia, ib, ic in tris:
            pa, pb, pc = pts[ia], pts[ib], pts[ic]
            uva = (u0 + ((pa[0] - minx) / spanx) * (u1 - u0), v1 - ((pa[1] - miny) / spany) * (v1 - v0))
            uvb = (u0 + ((pb[0] - minx) / spanx) * (u1 - u0), v1 - ((pb[1] - miny) / spany) * (v1 - v0))
            uvc = (u0 + ((pc[0] - minx) / spanx) * (u1 - u0), v1 - ((pc[1] - miny) / spany) * (v1 - v0))
            self.tri_enu(
                resolved_mat,
                (pa[0], pa[1], z), (pb[0], pb[1], z), (pc[0], pc[1], z),
                uva, uvb, uvc, ao, ao, ao,
            )

    def add_detailed_building(
        self,
        poly_raw: List[Vec2],
        stories: int,
        story_h: float,
        plinth_h: float,
        wall_mat: int, wall_uv: UVBox,
        band_mat: int, band_uv: UVBox,
        roof_mat: int, roof_uv: UVBox,
        win_mat: int, win_uv: UVBox,
        mullion_mat: int,
        plaster_plinth_mat: int, plaster_plinth_uv: UVBox,
        parapet_h: float = 0.85,
        add_rail: bool = True,
        bay_w: float = 3.5,
        recess: float = 0.22,
        ground_z: float = 0.0,
        solid_x_planes: Optional[List[float]] = None,
        party_max_y_on_x: Optional[Dict[float, float]] = None,
        rail_mat: Optional[int] = None,
        window_grille: bool = False,
        grille_mat: Optional[int] = None,
        simple_recess: bool = False,
        interior_mode: str = "classroom",
        add_downspouts: Optional[bool] = None,
    ) -> None:
        """
        Extrudes a multi-story building polygon with structural pilasters, spandrel bands,
        deep -0.22m window recesses, 3D aluminum frames & projecting stone sills, multi-bar
        exterior security grilles, closed inner parapet walls & beveled coping stones, 3D
        tubular rooftop safety railings, corner rainwater downspouts, physical glazing,
        and procedural 3D shallow interiors + ceiling luminaires.
        """
        pts = ensure_ccw(poly_raw)
        n = len(pts)
        if n < 3:
            return
        total_h = plinth_h + stories * story_h
        top_z = ground_z + total_h
        is_context_bldg = (interior_mode == "context")
        if add_downspouts is None:
            add_downspouts = (not is_context_bldg) and (not simple_recess) and (stories >= 2)
        use_phys_glass = (not self.classic_mode) and (not is_context_bldg) and ("glass_phys" in self.mats)
        resolved_win_mat = (
            self.mats["context_window"]
            if ((not self.classic_mode) and is_context_bldg and "context_window" in self.mats)
            else (self.mats["glass_phys"] if use_phys_glass else win_mat)
        )
        resolved_win_uv = (0.0, 0.0, 1.0, 1.0) if ((not self.classic_mode) and (is_context_bldg or use_phys_glass)) else win_uv

        for i in range(n):
            a = pts[i]
            b = pts[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            seg_len = math.hypot(dx, dy)
            if seg_len < 0.4:
                continue
            tx, ty = dx / seg_len, dy / seg_len
            # CCW polygon: outward normal is (+ty, -tx)
            nx, ny = ty, -tx

            def wpt(along: float, out_d: float, z: float) -> Vec3:
                return (a[0] + tx * along + nx * out_d, a[1] + ty * along + ny * out_d, z)

            is_party_wall = False
            if solid_x_planes:
                for px in solid_x_planes:
                    if abs(a[0] - px) < 0.25 and abs(b[0] - px) < 0.25:
                        max_y_lim = party_max_y_on_x.get(px) if party_max_y_on_x else None
                        if max_y_lim is None or max(a[1], b[1]) <= max_y_lim:
                            is_party_wall = True
                            break
            if is_party_wall:
                # Slightly inset solid wall so adjacent connected wing has zero Z-fighting
                self.quad_enu(
                    wall_mat,
                    wpt(0, -0.02, ground_z), wpt(seg_len, -0.02, ground_z),
                    wpt(seg_len, -0.02, top_z + parapet_h), wpt(0, -0.02, top_z + parapet_h),
                    wall_uv, 0.82, 0.96,
                )
                continue

            # 1. Base Plinth + Stepped Water-Table Top Ledge
            self.quad_enu(
                plaster_plinth_mat,
                wpt(0, 0.055, ground_z), wpt(seg_len, 0.055, ground_z),
                wpt(seg_len, 0.055, ground_z + plinth_h), wpt(0, 0.055, ground_z + plinth_h),
                plaster_plinth_uv, 0.72, 0.90,
            )
            self.quad_enu(
                plaster_plinth_mat,
                wpt(0, 0.055, ground_z + plinth_h), wpt(seg_len, 0.055, ground_z + plinth_h),
                wpt(seg_len, 0.0, ground_z + plinth_h + 0.025), wpt(0, 0.0, ground_z + plinth_h + 0.025),
                plaster_plinth_uv, 0.88, 0.96,
            )

            # 2. If short wall (< 2.5m), treat as solid corner/pilaster wall without broken windows
            n_bays = max(0, int(seg_len // bay_w)) if seg_len >= 2.8 else 0
            if n_bays == 0:
                self.quad_enu(
                    wall_mat,
                    wpt(0, 0.0, ground_z + plinth_h), wpt(seg_len, 0.0, ground_z + plinth_h),
                    wpt(seg_len, 0.0, top_z + parapet_h), wpt(0, 0.0, top_z + parapet_h),
                    wall_uv, 0.86, 0.98,
                )
                # Also close parapet inner wall & coping on short walls so rooftops never leak
                self.quad_enu(
                    wall_mat,
                    wpt(seg_len, -0.22, top_z + 0.24), wpt(0, -0.22, top_z + 0.24),
                    wpt(0, -0.22, top_z + parapet_h), wpt(seg_len, -0.22, top_z + parapet_h),
                    wall_uv, 0.78, 0.92,
                )
                self.quad_enu(
                    mullion_mat,
                    wpt(0, -0.24, top_z + parapet_h), wpt(seg_len, -0.24, top_z + parapet_h),
                    wpt(seg_len, 0.12, top_z + parapet_h), wpt(0, 0.12, top_z + parapet_h),
                    (0.1, 0.1, 0.9, 0.9), 0.94, 1.0,
                )
                continue

            pilaster_w = min(0.55, seg_len * 0.08)
            actual_bay = seg_len / n_bays

            for st in range(stories):
                sz0 = ground_z + plinth_h + st * story_h
                sz1 = sz0 + story_h
                sp_h = 0.88
                win_z0 = sz0 + sp_h
                win_z1 = sz1 - 0.36
                # Spandrel band across bay
                self.quad_enu(
                    band_mat,
                    wpt(0, 0.03, sz0), wpt(seg_len, 0.03, sz0),
                    wpt(seg_len, 0.03, win_z0), wpt(0, 0.03, win_z0),
                    band_uv, 0.88, 0.96,
                )
                # Top lintel band
                self.quad_enu(
                    wall_mat,
                    wpt(0, 0.04, win_z1), wpt(seg_len, 0.04, win_z1),
                    wpt(seg_len, 0.04, sz1), wpt(0, 0.04, sz1),
                    wall_uv, 0.86, 0.98,
                )

                for bi in range(n_bays):
                    b0 = bi * actual_bay
                    b1 = (bi + 1) * actual_bay
                    pw = pilaster_w * 0.5
                    w0 = b0 + pw
                    w1 = b1 - pw
                    # Left/right pilaster cheeks protruding
                    self.quad_enu(
                        wall_mat,
                        wpt(b0, 0.06, sz0), wpt(w0, 0.06, sz0),
                        wpt(w0, 0.06, sz1), wpt(b0, 0.06, sz1),
                        wall_uv, 0.88, 0.98,
                    )
                    self.quad_enu(
                        wall_mat,
                        wpt(w1, 0.06, sz0), wpt(b1, 0.06, sz0),
                        wpt(b1, 0.06, sz1), wpt(w1, 0.06, sz1),
                        wall_uv, 0.88, 0.98,
                    )
                    # Window recess reveal jambs + sill + head
                    if not simple_recess:
                        self.quad_enu(
                            wall_mat,
                            wpt(w0, -recess, win_z0), wpt(w0, 0.06, win_z0),
                            wpt(w0, 0.06, win_z1), wpt(w0, -recess, win_z1),
                            wall_uv, 0.72, 0.80,
                        )
                        self.quad_enu(
                            wall_mat,
                            wpt(w1, 0.06, win_z0), wpt(w1, -recess, win_z0),
                            wpt(w1, -recess, win_z1), wpt(w1, 0.06, win_z1),
                            wall_uv, 0.72, 0.80,
                        )
                        # Projecting drip window sill (3D top + front lip on campus; clean single sill on context)
                        self.quad_enu(
                            mullion_mat,
                            wpt(w0 - 0.03, -recess, win_z0), wpt(w1 + 0.03, -recess, win_z0),
                            wpt(w1 + 0.03, 0.10, win_z0 - 0.01), wpt(w0 - 0.03, 0.10, win_z0 - 0.01),
                            (0.1, 0.1, 0.9, 0.9), 0.95, 1.0,
                        )
                        if not is_context_bldg:
                            self.quad_enu(
                                mullion_mat,
                                wpt(w0 - 0.03, 0.10, win_z0 - 0.06), wpt(w1 + 0.03, 0.10, win_z0 - 0.06),
                                wpt(w1 + 0.03, 0.10, win_z0 - 0.01), wpt(w0 - 0.03, 0.10, win_z0 - 0.01),
                                (0.1, 0.1, 0.9, 0.9), 0.82, 0.92,
                            )
                        self.quad_enu(
                            wall_mat,
                            wpt(w0, 0.04, win_z1), wpt(w1, 0.04, win_z1),
                            wpt(w1, -recess, win_z1), wpt(w0, -recess, win_z1),
                            wall_uv, 0.65, 0.72,
                        )
                    # Procedural 3D shallow interior room + ceiling LED fixtures behind campus glass
                    w_plane = 0.01 if simple_recess else -recess
                    if use_phys_glass and interior_mode != "none" and not simple_recess:
                        add_shallow_room(
                            self,
                            wpt,
                            w0,
                            w1,
                            recess,
                            win_z0,
                            win_z1,
                            sz0,
                            sz1,
                            self.mats,
                            room_key=f"{self.name}_{i}_{st}_{bi}",
                            room_type=interior_mode,
                            depth=2.85,
                        )
                    # Recessed window glass pane (physical translucent glazing on campus; parallax shader on context)
                    self.quad_enu(
                        resolved_win_mat,
                        wpt(w0, w_plane, win_z0), wpt(w1, w_plane, win_z0),
                        wpt(w1, w_plane, win_z1), wpt(w0, w_plane, win_z1),
                        resolved_win_uv, 0.90, 1.0,
                    )
                    # Crisp 3D Aluminum mullions & transom on campus buildings (lightweight flat mullions on context)
                    if not simple_recess:
                        md_back = -recess + 0.008
                        md_front = -recess + 0.052
                        if is_context_bldg:
                            for mx in (w0 + (w1 - w0) * 0.5,):
                                self.quad_enu(mullion_mat, wpt(mx - 0.03, md_front, win_z0), wpt(mx + 0.03, md_front, win_z0), wpt(mx + 0.03, md_front, win_z1), wpt(mx - 0.03, md_front, win_z1), (0.1, 0.1, 0.9, 0.9), 0.92, 1.0)
                        else:
                            for mx in (w0 + (w1 - w0) * 0.34, w0 + (w1 - w0) * 0.66):
                                self.quad_enu(mullion_mat, wpt(mx - 0.028, md_front, win_z0), wpt(mx + 0.028, md_front, win_z0), wpt(mx + 0.028, md_front, win_z1), wpt(mx - 0.028, md_front, win_z1), (0.1, 0.1, 0.9, 0.9), 0.94, 1.0)
                                self.quad_enu(mullion_mat, wpt(mx - 0.028, md_back, win_z0), wpt(mx - 0.028, md_front, win_z0), wpt(mx - 0.028, md_front, win_z1), wpt(mx - 0.028, md_back, win_z1), (0.1, 0.1, 0.9, 0.9), 0.78, 0.88)
                                self.quad_enu(mullion_mat, wpt(mx + 0.028, md_front, win_z0), wpt(mx + 0.028, md_back, win_z0), wpt(mx + 0.028, md_back, win_z1), wpt(mx + 0.028, md_front, win_z1), (0.1, 0.1, 0.9, 0.9), 0.78, 0.88)
                            hz = win_z0 + (win_z1 - win_z0) * 0.72
                            self.quad_enu(mullion_mat, wpt(w0 + 0.02, md_front + 0.004, hz - 0.026), wpt(w1 - 0.02, md_front + 0.004, hz - 0.026), wpt(w1 - 0.02, md_front + 0.004, hz + 0.026), wpt(w0 + 0.02, md_front + 0.004, hz + 0.026), (0.1, 0.1, 0.9, 0.9), 0.94, 1.0)
                            self.quad_enu(mullion_mat, wpt(w0 + 0.02, md_back, hz + 0.026), wpt(w1 - 0.02, md_back, hz + 0.026), wpt(w1 - 0.02, md_front + 0.004, hz + 0.026), wpt(w0 + 0.02, md_front + 0.004, hz + 0.026), (0.1, 0.1, 0.9, 0.9), 0.90, 0.98)
                    # Ground-floor (1F) exterior 3D window security grille on campus buildings (upper floors stay clean & authentic!)
                    if window_grille and (not is_context_bldg) and st == 0:
                        gm = grille_mat if grille_mat is not None else mullion_mat
                        gz_bot = win_z0 + 0.05
                        gz_top = win_z0 + (win_z1 - win_z0) * 0.50
                        g_out = 0.095
                        add_rect_beam(self, gm, wpt(w0 + 0.03, g_out, gz_top), wpt(w1 - 0.03, g_out, gz_top), 0.030, 0.030, caps=False)
                        add_rect_beam(self, gm, wpt(w0 + 0.03, g_out, gz_bot), wpt(w1 - 0.03, g_out, gz_bot), 0.026, 0.026, caps=False)
                        n_vbars = max(3, min(6, int(round((w1 - w0) / 0.52))))
                        for vi in range(n_vbars):
                            vx = (w0 + 0.12) + ((w1 - w0 - 0.24) * vi / max(1, n_vbars - 1))
                            add_rect_beam(self, gm, wpt(vx, g_out, gz_bot), wpt(vx, g_out, gz_top), 0.018, 0.018, caps=False)

            # 3. Cornice + Closed Parapet Wall (outer + inner + projecting beveled coping) + 3D Rooftop Railing
            self.quad_enu(
                wall_mat,
                wpt(0, 0.10, top_z), wpt(seg_len, 0.10, top_z),
                wpt(seg_len, 0.10, top_z + parapet_h), wpt(0, 0.10, top_z + parapet_h),
                wall_uv, 0.90, 1.0,
            )
            # Inner parapet wall facing inward across rooftop (eliminates hollow see-through parapet from above!)
            self.quad_enu(
                wall_mat,
                wpt(seg_len, -0.22, top_z + 0.24), wpt(0, -0.22, top_z + 0.24),
                wpt(0, -0.22, top_z + parapet_h), wpt(seg_len, -0.22, top_z + parapet_h),
                wall_uv, 0.78, 0.92,
            )
            # Projecting coping stone lip (front drip edge + top cap)
            self.quad_enu(
                mullion_mat,
                wpt(0, 0.135, top_z + parapet_h - 0.06), wpt(seg_len, 0.135, top_z + parapet_h - 0.06),
                wpt(seg_len, 0.135, top_z + parapet_h + 0.02), wpt(0, 0.135, top_z + parapet_h + 0.02),
                (0.1, 0.1, 0.9, 0.9), 0.88, 0.98,
            )
            self.quad_enu(
                mullion_mat,
                wpt(0, -0.25, top_z + parapet_h + 0.02), wpt(seg_len, -0.25, top_z + parapet_h + 0.02),
                wpt(seg_len, 0.135, top_z + parapet_h + 0.02), wpt(0, 0.135, top_z + parapet_h + 0.02),
                (0.1, 0.1, 0.9, 0.9), 0.95, 1.0,
            )
            if add_rail:
                rm = rail_mat if rail_mat is not None else mullion_mat
                rz0 = top_z + parapet_h + 0.02
                rz1 = rz0 + 0.95
                # 3D square-tube top & mid handrails + 3D square posts every 2.4m
                add_rect_beam(self, rm, wpt(0, 0.04, rz1 - 0.025), wpt(seg_len, 0.04, rz1 - 0.025), 0.046, 0.046, caps=False)
                add_rect_beam(self, rm, wpt(0, 0.04, rz0 + 0.46), wpt(seg_len, 0.04, rz0 + 0.46), 0.034, 0.034, caps=False)
                n_posts = max(2, int(seg_len // 2.4) + 1)
                for pi in range(n_posts):
                    pa = seg_len * pi / (n_posts - 1)
                    add_rect_beam(self, rm, wpt(pa, 0.04, rz0), wpt(pa, 0.04, rz1), 0.044, 0.044, caps=False)

            # 4. Subtle vertical rainwater downspout near wall corner on campus multi-story facades
            if add_downspouts and seg_len >= 7.5:
                dp_a = 0.45
                dp_p = wpt(dp_a, 0.11, ground_z + 0.12)
                self.add_smooth_cylinder(mullion_mat, dp_p[0], dp_p[1], ground_z + 0.12, 0.048, 0.048, total_h - 0.12, segs=6, ao_bot=0.76, ao_top=0.95)

        # Roof Cap
        self.add_polygon_patch(pts, top_z + 0.25, roof_mat, roof_uv, scale_m=12.0, ao=0.98)

    def add_pitched_gable_building(
        self,
        cx: float, cy_n: float,
        w: float, d: float,
        eave_h: float, ridge_h: float,
        yaw_rad: float,
        wall_mat: int, wall_uv: UVBox,
        roof_mat: int, roof_uv: UVBox,
        win_mat: int, win_uv: UVBox,
        wood_mat: int,
        stories: int = 1,
        ridge_along_x: bool = True,
        balcony_south: bool = False,
        balcony_mat: Optional[int] = None,
        ground_z: float = 0.0,
        window_frame_mat: Optional[int] = None,
        gable_vent: bool = False,
    ) -> None:
        """Traditional Beijing 青砖/灰瓦 gable building with stone plinth, thick overhanging eaves, ridge/verge trims & framed windows."""
        cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

        def wp(lx: float, ly: float, lz: float) -> Vec3:
            return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs, ground_z + lz)

        hw, hd = w * 0.5, d * 0.5
        zt = eave_h
        frame_m = window_frame_mat if window_frame_mat is not None else wood_mat
        # Base masonry stone apron plinth + main wall box
        self.add_box(wall_mat, cx, cy_n, ground_z, w + 0.14, d + 0.14, min(0.45, eave_h * 0.16), yaw_rad, wall_uv, ao_bot=0.68, ao_top=0.84)
        self.add_box(wall_mat, cx, cy_n, ground_z, w, d, eave_h, yaw_rad, wall_uv, ao_bot=0.75, ao_top=0.90)

        # Windows along front/back long walls with 3D frames, center mullions & projecting sills
        n_win = max(2, int((w if ridge_along_x else d) // 3.0))
        is_ctx = self.name.startswith("Context_")
        use_phys = (not self.classic_mode) and (not is_ctx) and ("glass_phys" in self.mats)
        w_glass = (
            self.mats["context_window"]
            if ((not self.classic_mode) and is_ctx and "context_window" in self.mats)
            else (self.mats["glass_phys"] if use_phys else win_mat)
        )
        w_uv = (0.0, 0.0, 1.0, 1.0) if ((not self.classic_mode) and (is_ctx or use_phys)) else win_uv
        w_glow = self.mats.get("int_glow_warm0", self.mats.get("int_wall", wall_mat))
        w_lamp = self.mats.get("int_light_warm0", win_mat)
        if ridge_along_x:
            for side in (-1.0, 1.0):
                y_face = side * (hd + 0.04)
                y_back = side * (hd + 0.015)
                for st in range(stories):
                    z0 = st * (eave_h / stories) + 0.85
                    z1 = z0 + (eave_h / stories) * 0.52
                    for wi in range(n_win):
                        wx = -hw + (wi + 0.5) * (w / n_win)
                        ww = (w / n_win) * 0.54
                        # Projecting sill, head lintel, left/right jambs & center sash mullion
                        fc = wp(wx, side * (hd + 0.06), 0.0)
                        self.add_box(frame_m, fc[0], fc[1], ground_z + z0 - 0.075, ww + 0.16, 0.14, 0.075, yaw_rad)
                        self.add_box(frame_m, fc[0], fc[1], ground_z + z1, ww + 0.12, 0.10, 0.065, yaw_rad)
                        for jx in (-ww * 0.5 - 0.025, 0.0, ww * 0.5 + 0.025):
                            jp = wp(wx + jx, side * (hd + 0.05), 0.0)
                            self.add_box(frame_m, jp[0], jp[1], ground_z + z0, 0.055 if jx != 0 else 0.04, 0.08, z1 - z0, yaw_rad)
                        tp = wp(wx, side * (hd + 0.05), 0.0)
                        self.add_box(frame_m, tp[0], tp[1], ground_z + z0 + (z1 - z0) * 0.68, ww, 0.075, 0.04, yaw_rad)
                        if side < 0:
                            if use_phys:
                                self.quad_enu(w_glow, wp(wx - ww * 0.48, y_back, z0 + 0.02), wp(wx + ww * 0.48, y_back, z0 + 0.02), wp(wx + ww * 0.48, y_back, z1 - 0.02), wp(wx - ww * 0.48, y_back, z1 - 0.02), (0.0, 0.0, 1.0, 1.0), 0.82, 0.98)
                                self.quad_enu(w_lamp, wp(wx - ww * 0.32, y_back - 0.008, z1 - 0.16), wp(wx + ww * 0.32, y_back - 0.008, z1 - 0.16), wp(wx + ww * 0.32, y_back - 0.008, z1 - 0.06), wp(wx - ww * 0.32, y_back - 0.008, z1 - 0.06), (0.0, 0.0, 1.0, 1.0), 1.0, 1.0)
                            self.quad_enu(w_glass, wp(wx - ww * 0.5, y_face, z0), wp(wx + ww * 0.5, y_face, z0), wp(wx + ww * 0.5, y_face, z1), wp(wx - ww * 0.5, y_face, z1), w_uv, 0.90, 1.0)
                        else:
                            if use_phys:
                                self.quad_enu(w_glow, wp(wx + ww * 0.48, y_back, z0 + 0.02), wp(wx - ww * 0.48, y_back, z0 + 0.02), wp(wx - ww * 0.48, y_back, z1 - 0.02), wp(wx + ww * 0.48, y_back, z1 - 0.02), (0.0, 0.0, 1.0, 1.0), 0.82, 0.98)
                                self.quad_enu(w_lamp, wp(wx + ww * 0.32, y_back + 0.008, z1 - 0.16), wp(wx - ww * 0.32, y_back + 0.008, z1 - 0.16), wp(wx - ww * 0.32, y_back + 0.008, z1 - 0.06), wp(wx + ww * 0.32, y_back + 0.008, z1 - 0.06), (0.0, 0.0, 1.0, 1.0), 1.0, 1.0)
                            self.quad_enu(w_glass, wp(wx + ww * 0.5, y_face, z0), wp(wx - ww * 0.5, y_face, z0), wp(wx - ww * 0.5, y_face, z1), wp(wx + ww * 0.5, y_face, z1), w_uv, 0.90, 1.0)
        else:
            # Windows along East/West long walls when ridge runs North-South
            for side in (-1.0, 1.0):
                x_face = side * (hw + 0.04)
                for st in range(stories):
                    z0 = st * (eave_h / stories) + 0.85
                    z1 = z0 + (eave_h / stories) * 0.52
                    for wi in range(n_win):
                        wy = -hd + (wi + 0.5) * (d / n_win)
                        ww = (d / n_win) * 0.54
                        fc = wp(side * (hw + 0.06), wy, 0.0)
                        self.add_box(frame_m, fc[0], fc[1], ground_z + z0 - 0.075, 0.14, ww + 0.16, 0.075, yaw_rad)
                        self.add_box(frame_m, fc[0], fc[1], ground_z + z1, 0.10, ww + 0.12, 0.065, yaw_rad)
                        for jy in (-ww * 0.5 - 0.025, 0.0, ww * 0.5 + 0.025):
                            jp = wp(side * (hw + 0.05), wy + jy, 0.0)
                            self.add_box(frame_m, jp[0], jp[1], ground_z + z0, 0.08, 0.055 if jy != 0 else 0.04, z1 - z0, yaw_rad)
                        if side < 0:
                            self.quad_enu(w_glass, wp(x_face, wy + ww * 0.5, z0), wp(x_face, wy - ww * 0.5, z0), wp(x_face, wy - ww * 0.5, z1), wp(x_face, wy + ww * 0.5, z1), w_uv, 0.90, 1.0)
                        else:
                            self.quad_enu(w_glass, wp(x_face, wy - ww * 0.5, z0), wp(x_face, wy + ww * 0.5, z0), wp(x_face, wy + ww * 0.5, z1), wp(x_face, wy - ww * 0.5, z1), w_uv, 0.90, 1.0)

        # Optional 2F green-rail balcony corridor
        if balcony_south and stories >= 2 and balcony_mat is not None:
            by = -hd - 1.4
            bz = eave_h * 0.48
            self.quad_enu(wall_mat, wp(-hw, by, bz), wp(hw, by, bz), wp(hw, -hd, bz), wp(-hw, -hd, bz), wall_uv, 0.80, 0.85, double_sided=True)
            for ci in range(max(3, n_win + 1)):
                px = -hw + ci * (w / max(2, n_win))
                self.add_cylinder(wood_mat, wp(px, by + 0.15, 0)[0], wp(px, by + 0.15, 0)[1], ground_z, 0.14, 0.14, eave_h, 8)
            self.quad_enu(balcony_mat, wp(-hw, by - 0.03, bz), wp(hw, by - 0.03, bz), wp(hw, by - 0.03, bz + 1.05), wp(-hw, by - 0.03, bz + 1.05), (0.1, 0.1, 0.9, 0.9), 0.92, 1.0, double_sided=True)

        # Overhanging pitched roof with 3D fascia eaves, gable bargeboards (博风板) & molded ridge cap
        ov = 0.65
        wu0, wv0, wu1, wv1 = wall_uv
        wum = (wu0 + wu1) * 0.5
        rh = zt + ridge_h
        if ridge_along_x:
            self.quad_enu(roof_mat, wp(-hw - ov, -hd - ov, zt - 0.12), wp(hw + ov, -hd - ov, zt - 0.12), wp(hw + ov, 0, rh), wp(-hw - ov, 0, rh), roof_uv, 0.88, 1.0, double_sided=True)
            self.quad_enu(roof_mat, wp(hw + ov, hd + ov, zt - 0.12), wp(-hw - ov, hd + ov, zt - 0.12), wp(-hw - ov, 0, rh), wp(hw + ov, 0, rh), roof_uv, 0.88, 1.0, double_sided=True)
            # 3D Eave fascia boards along South & North overhangs
            add_rect_beam(self, wood_mat, wp(-hw - ov, -hd - ov, zt - 0.16), wp(hw + ov, -hd - ov, zt - 0.16), 0.09, 0.14)
            add_rect_beam(self, wood_mat, wp(-hw - ov, hd + ov, zt - 0.16), wp(hw + ov, hd + ov, zt - 0.16), 0.09, 0.14)
            # Sloped gable bargeboard verge trims (博风板 / 垂脊) at West & East ends
            for gx in (-hw - ov + 0.04, hw + ov - 0.04):
                add_rect_beam(self, roof_mat, wp(gx, -hd - ov, zt - 0.10), wp(gx, 0.0, rh + 0.04), 0.14, 0.16, roof_uv)
                add_rect_beam(self, roof_mat, wp(gx, hd + ov, zt - 0.10), wp(gx, 0.0, rh + 0.04), 0.14, 0.16, roof_uv)
            # Gable end triangles
            self.tri_enu(wall_mat, wp(-hw, hd, zt), wp(-hw, -hd, zt), wp(-hw, 0, rh), (wu0, wv1), (wu1, wv1), (wum, wv0), 0.86, 0.86, 0.96)
            self.tri_enu(wall_mat, wp(hw, -hd, zt), wp(hw, hd, zt), wp(hw, 0, rh), (wu0, wv1), (wu1, wv1), (wum, wv0), 0.86, 0.86, 0.96)
            # Optional recessed louvered gable vents on West & East gable triangles (e.g. East Campus E-B4 blue annex!)
            if gable_vent:
                vz = zt + ridge_h * 0.42
                for gx_s in (-1.0, 1.0):
                    vp = wp(gx_s * (hw + 0.05), 0.0, 0.0)
                    self.add_box(frame_m, vp[0], vp[1], ground_z + vz - 0.36, 0.10, 1.32, 0.72, yaw_rad)
                    vp_in = wp(gx_s * (hw + 0.07), 0.0, 0.0)
                    self.add_box(wood_mat, vp_in[0], vp_in[1], ground_z + vz - 0.28, 0.07, 1.12, 0.56, yaw_rad)
                    for li in range(4):
                        sl_z = ground_z + vz - 0.22 + li * 0.13
                        self.add_box(frame_m, wp(gx_s * (hw + 0.095), 0.0, 0.0)[0], wp(gx_s * (hw + 0.095), 0.0, 0.0)[1], sl_z, 0.04, 1.08, 0.035, yaw_rad)
            # Stepped ridge roll cap + ridge end blocks
            self.add_box(roof_mat, cx, cy_n, ground_z + rh - 0.04, w + ov * 2 + 0.12, 0.32, 0.22, yaw_rad, roof_uv)
            self.add_box(wood_mat, cx, cy_n, ground_z + rh + 0.16, w + ov * 2 + 0.16, 0.16, 0.09, yaw_rad)
        else:
            self.quad_enu(roof_mat, wp(-hw - ov, hd + ov, zt - 0.12), wp(-hw - ov, -hd - ov, zt - 0.12), wp(0, -hd - ov, rh), wp(0, hd + ov, rh), roof_uv, 0.88, 1.0, double_sided=True)
            self.quad_enu(roof_mat, wp(hw + ov, -hd - ov, zt - 0.12), wp(hw + ov, hd + ov, zt - 0.12), wp(0, hd + ov, rh), wp(0, -hd - ov, rh), roof_uv, 0.88, 1.0, double_sided=True)
            add_rect_beam(self, wood_mat, wp(-hw - ov, -hd - ov, zt - 0.16), wp(-hw - ov, hd + ov, zt - 0.16), 0.09, 0.14)
            add_rect_beam(self, wood_mat, wp(hw + ov, -hd - ov, zt - 0.16), wp(hw + ov, hd + ov, zt - 0.16), 0.09, 0.14)
            for gy in (-hd - ov + 0.04, hd + ov - 0.04):
                add_rect_beam(self, roof_mat, wp(-hw - ov, gy, zt - 0.10), wp(0.0, gy, rh + 0.04), 0.14, 0.16, roof_uv)
                add_rect_beam(self, roof_mat, wp(hw + ov, gy, zt - 0.10), wp(0.0, gy, rh + 0.04), 0.14, 0.16, roof_uv)
            self.tri_enu(wall_mat, wp(-hw, -hd, zt), wp(hw, -hd, zt), wp(0, -hd, rh), (wu0, wv1), (wu1, wv1), (wum, wv0), 0.86, 0.86, 0.96)
            self.tri_enu(wall_mat, wp(hw, hd, zt), wp(-hw, hd, zt), wp(0, hd, rh), (wu0, wv1), (wu1, wv1), (wum, wv0), 0.86, 0.86, 0.96)
            self.add_box(roof_mat, cx, cy_n, ground_z + rh - 0.04, 0.32, d + ov * 2 + 0.12, 0.22, yaw_rad, roof_uv)
            self.add_box(wood_mat, cx, cy_n, ground_z + rh + 0.16, 0.16, d + ov * 2 + 0.16, 0.09, yaw_rad)

    def add_tree(
        self,
        cx: float, cy_n: float, species: str, h: float,
        trunk_mat: int, leaf_mat: int,
        accent_mat: Optional[int] = None,
        z_base: float = 0.0,
    ) -> None:
        """Species-aware botanical tree (alpha-cutout clusters in Enhanced; multi-lobe sculpted crowns in Classic)."""
        if (not self.classic_mode) and self.mats and "foliage_broad" in self.mats:
            add_botanical_tree(self, cx, cy_n, species, h, self.mats, enu_to_gltf, z_base=z_base)
            return
        # Classic self-contained mode (zero external textures needed): smooth multi-segment trunk + organic layered crowns
        if species == "rose":
            for k in range(4):
                a = 2.0 * math.pi * k / 4.0
                self.add_sphere(leaf_mat, cx + 0.25 * math.cos(a), cy_n + 0.25 * math.sin(a), z_base + h * 0.42, h * 0.36, h * 0.34, h * 0.36, 7, 4, UV_FOLIAGE, 0.92)
            if accent_mat is not None:
                for k in range(3):
                    a = 2.0 * math.pi * k / 3.0 + 0.4
                    self.add_sphere(accent_mat, cx + 0.22 * math.cos(a), cy_n + 0.22 * math.sin(a), z_base + h * 0.72, 0.09, 0.08, 0.09, 6, 3, (0.0, 0.0, 1.0, 1.0), 1.0)
            return
        r_b = max(0.14, h * 0.028)
        th = h * (0.28 if species in ("cedar", "pine") else 0.40)
        self.add_smooth_cylinder(trunk_mat, cx, cy_n, z_base, r_b, r_b * 0.52, th, 8, ao_bot=0.65, ao_top=0.88)
        if species == "cedar":
            c_mat = self.mats.get("leaf_pine", leaf_mat)
            for ti in range(6):
                fz = 0.26 + ti * 0.115
                tr = h * 0.22 * (1.0 - ti * 0.13)
                self.add_sphere(c_mat, cx, cy_n, z_base + h * fz, tr, h * 0.09, tr, 9, 4, (0.0, 0.0, 1.0, 1.0), 0.88 + ti * 0.02)
            return
        if species == "pine":
            p_mat = self.mats.get("leaf_pine", leaf_mat)
            for ox, oy, fz, rr in ((-0.16, -0.08, 0.52, 0.22), (0.18, 0.08, 0.62, 0.21), (-0.06, 0.16, 0.74, 0.20), (0.10, -0.10, 0.84, 0.17)):
                self.add_sphere(p_mat, cx + ox * h, cy_n + oy * h, z_base + h * fz, h * rr, h * 0.11, h * rr, 8, 4, (0.0, 0.0, 1.0, 1.0), 0.92)
            return
        crown_mat = accent_mat if (species == "ginkgo" and accent_mat is not None) else leaf_mat
        c_uv = UV_FOLIAGE if crown_mat == self.mats.get("leaf") else (0.0, 0.0, 1.0, 1.0)
        for ox, oy, fz, rr in ((0.0, 0.0, 0.70, 0.28), (-0.17, 0.06, 0.62, 0.21), (0.17, -0.06, 0.64, 0.20), (0.03, 0.16, 0.60, 0.19), (-0.04, -0.15, 0.62, 0.19), (0.01, 0.01, 0.85, 0.18)):
            self.add_sphere(crown_mat, cx + ox * h, cy_n + oy * h, z_base + h * fz, h * rr, h * rr * 0.84, h * rr, 8, 5, c_uv, 0.94)
        if species in ("magnolia", "persimmon") and accent_mat is not None:
            for k in range(6):
                a = 2.0 * math.pi * k / 6.0
                self.add_sphere(accent_mat, cx + h * 0.22 * math.cos(a), cy_n + h * 0.22 * math.sin(a), z_base + h * (0.64 + (k % 3) * 0.08), 0.13, 0.11, 0.13, 6, 3, (0.0, 0.0, 1.0, 1.0), 1.0)


# ---------------------------------------------------------------------------
# glTF Binary (.glb) Serializer
# ---------------------------------------------------------------------------
class GLBExporter:
    def __init__(self, classic_mode: bool = False):
        self.textures: List[Tuple[str, bytes]] = []
        self.materials: List[dict] = []
        self.nodes: List[NodeBuilder] = []
        self.metric_tiles: Dict[int, float] = {}
        self.legacy_redirects: Dict[Tuple[int, UVBox], Tuple[int, float]] = {}
        self.mats_ref: dict = {}
        self.classic_mode: bool = classic_mode
        self.double_sided_mats: Set[int] = set()

    def bind_archviz_registry(
        self,
        mats: dict,
        metric_tiles: Dict[int, float],
        legacy_redirects: Dict[Tuple[int, UVBox], Tuple[int, float]],
    ) -> None:
        self.mats_ref = mats
        self.metric_tiles = metric_tiles
        self.legacy_redirects = legacy_redirects

    def add_png_texture(self, name: str, path: str) -> int:
        data = Path(path).read_bytes()
        idx = len(self.textures)
        self.textures.append((name, data))
        return idx

    def add_mat(
        self,
        name: str,
        base_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        metallic: float = 0.0,
        roughness: float = 0.78,
        tex_idx: Optional[int] = None,
        emissive: Optional[Tuple[float, float, float]] = None,
        double_sided: bool = False,
        alpha_mode: Optional[str] = None,
    ) -> int:
        pbr: dict = {
            "baseColorFactor": list(base_color),
            "metallicFactor": metallic,
            "roughnessFactor": roughness,
        }
        if tex_idx is not None:
            pbr["baseColorTexture"] = {"index": tex_idx}
        m: dict = {"name": name, "pbrMetallicRoughness": pbr}
        if emissive is not None:
            m["emissiveFactor"] = list(emissive)
        if double_sided:
            m["doubleSided"] = True
        if alpha_mode is not None:
            m["alphaMode"] = alpha_mode
            if alpha_mode == "MASK":
                m["alphaCutoff"] = 0.45
        idx = len(self.materials)
        self.materials.append(m)
        if double_sided:
            self.double_sided_mats.add(idx)
        return idx

    def add_node(self, name: str) -> NodeBuilder:
        nb = NodeBuilder(
            name, self.metric_tiles, self.legacy_redirects, self.mats_ref,
            classic_mode=self.classic_mode, double_sided_mats=self.double_sided_mats,
        )
        self.nodes.append(nb)
        return nb

    def write_glb(self, out_path: str) -> Tuple[int, int]:
        bin_buf = bytearray()
        buffer_views: List[dict] = []
        accessors: List[dict] = []
        images: List[dict] = []
        textures_gltf: List[dict] = []
        samplers = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}]

        def append_bytes(raw: bytes, target: Optional[int] = None) -> int:
            while len(bin_buf) % 4 != 0:
                bin_buf.append(0)
            offset = len(bin_buf)
            bin_buf.extend(raw)
            bv: dict = {"buffer": 0, "byteOffset": offset, "byteLength": len(raw)}
            if target is not None:
                bv["target"] = target
            idx = len(buffer_views)
            buffer_views.append(bv)
            return idx

        # 1. Embed PNG images
        for tname, png_bytes in self.textures:
            bv_idx = append_bytes(png_bytes)
            img_idx = len(images)
            images.append({"name": tname, "bufferView": bv_idx, "mimeType": "image/png"})
            textures_gltf.append({"sampler": 0, "source": img_idx})

        # 2. Pack Meshes & Nodes
        meshes: List[dict] = []
        gltf_nodes: List[dict] = []
        root_children: List[int] = []
        total_tris = 0
        total_verts = 0

        for nb in self.nodes:
            prims: List[dict] = []
            for mat_idx, b in sorted(nb.buckets.items()):
                if not b.idx:
                    continue
                nv = len(b.pos)
                total_verts += nv
                total_tris += len(b.idx) // 3

                min_p = [min(p[k] for p in b.pos) for k in range(3)]
                max_p = [max(p[k] for p in b.pos) for k in range(3)]

                pos_bytes = b"".join(struct.pack("<fff", *p) for p in b.pos)
                norm_bytes = b"".join(struct.pack("<fff", *n) for n in b.norm)
                uv_bytes = b"".join(struct.pack("<ff", *u) for u in b.uv)
                col_bytes = b"".join(struct.pack("<fff", *c) for c in b.col)
                idx_bytes = b"".join(struct.pack("<I", i) for i in b.idx)

                bv_pos = append_bytes(pos_bytes, 34962)
                bv_norm = append_bytes(norm_bytes, 34962)
                bv_uv = append_bytes(uv_bytes, 34962)
                bv_col = append_bytes(col_bytes, 34962)
                bv_idx = append_bytes(idx_bytes, 34963)

                acc_pos = len(accessors)
                accessors.append({"bufferView": bv_pos, "componentType": 5126, "count": nv, "type": "VEC3", "min": min_p, "max": max_p})
                acc_norm = len(accessors)
                accessors.append({"bufferView": bv_norm, "componentType": 5126, "count": nv, "type": "VEC3"})
                acc_uv = len(accessors)
                accessors.append({"bufferView": bv_uv, "componentType": 5126, "count": nv, "type": "VEC2"})
                acc_col = len(accessors)
                accessors.append({"bufferView": bv_col, "componentType": 5126, "count": nv, "type": "VEC3"})
                acc_idx = len(accessors)
                accessors.append({"bufferView": bv_idx, "componentType": 5125, "count": len(b.idx), "type": "SCALAR"})

                prims.append({
                    "attributes": {"POSITION": acc_pos, "NORMAL": acc_norm, "TEXCOORD_0": acc_uv, "COLOR_0": acc_col},
                    "indices": acc_idx,
                    "material": mat_idx,
                })

            if not prims:
                continue
            mesh_idx = len(meshes)
            meshes.append({"name": nb.name, "primitives": prims})
            node_idx = len(gltf_nodes)
            gltf_nodes.append({"name": nb.name, "mesh": mesh_idx})
            root_children.append(node_idx)

        while len(bin_buf) % 4 != 0:
            bin_buf.append(0)

        gltf = {
            "asset": {"version": "2.0", "generator": "ibb-school-map procedural glb builder"},
            "scene": 0,
            "scenes": [{"name": "CampusScene", "nodes": root_children}],
            "nodes": gltf_nodes,
            "meshes": meshes,
            "materials": self.materials,
            "textures": textures_gltf,
            "images": images,
            "samplers": samplers,
            "accessors": accessors,
            "bufferViews": buffer_views,
            "buffers": [{"byteLength": len(bin_buf)}],
        }

        json_bytes = json.dumps(gltf, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        while len(json_bytes) % 4 != 0:
            json_bytes += b" "

        total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_buf)
        header = struct.pack("<III", 0x46546C67, 2, total_len)
        json_hdr = struct.pack("<II", len(json_bytes), 0x4E4F534A)
        bin_hdr = struct.pack("<II", len(bin_buf), 0x004E4942)

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(header + json_hdr + json_bytes + bin_hdr + bytes(bin_buf))
        return total_verts, total_tris


UV_CONSTS: Dict[str, UVBox] = {
    "UV_TERRACOTTA_BRICK": UV_TERRACOTTA_BRICK,
    "UV_RED_BRICK_WALK": UV_RED_BRICK_WALK,
    "UV_GREY_RIB": UV_GREY_RIB,
    "UV_QINGZHUAN": UV_QINGZHUAN,
    "UV_STUCCO": UV_STUCCO,
    "UV_GREY_TILE": UV_GREY_TILE,
    "UV_RED_TILE": UV_RED_TILE,
    "UV_GREEN_ROOF": UV_GREEN_ROOF,
    "UV_TRACK_EPDM": UV_TRACK_EPDM,
    "UV_COURT_GREEN": UV_COURT_GREEN,
    "UV_PLAZA_TILE": UV_PLAZA_TILE,
    "UV_GRASS": UV_GRASS,
    "UV_ASPHALT": UV_ASPHALT,
    "UV_GLASS_WINDOW": UV_GLASS_WINDOW,
    "UV_MARBLE": UV_MARBLE,
    "UV_BURGUNDY": UV_BURGUNDY,
    "UV_SHENDU_GRANITE": UV_SHENDU_GRANITE,
    "UV_DARK_SLATE_PODIUM": UV_DARK_SLATE_PODIUM,
    "UV_BLUE_TILE_ROOF": UV_BLUE_TILE_ROOF,
    "UV_HARD_COURT_APRON": UV_HARD_COURT_APRON,
    "UV_GLASS_BACKBOARD": UV_GLASS_BACKBOARD,
    "UV_PINGPONG_TOP": UV_PINGPONG_TOP,
    "UV_AC_UNIT_FRONT": UV_AC_UNIT_FRONT,
}


def init_materials(exp: GLBExporter, tex_dir: str, include_west_details: bool = False, classic_mode: bool = False) -> dict:
    t_gates = exp.add_png_texture("SignageGates", f"{tex_dir}/tex_signage_gates.png")
    t_stage = exp.add_png_texture("PlaquesStage", f"{tex_dir}/tex_plaques_stage.png")
    t_surf = exp.add_png_texture("Surfaces", f"{tex_dir}/tex_surfaces.png")

    mats = {
        "gates": exp.add_mat("Mat_Gates", roughness=0.55, tex_idx=t_gates),
        "led": exp.add_mat("Mat_LED", roughness=0.30, tex_idx=t_gates, emissive=(0.66, 0.035, 0.02)),
        "stage_led": exp.add_mat("Mat_StageLED", roughness=0.35, tex_idx=t_stage, emissive=(0.14, 0.16, 0.22)),
        "stage": exp.add_mat("Mat_StagePlaques", roughness=0.62, tex_idx=t_stage),
        "surf": exp.add_mat("Mat_Surfaces", roughness=0.82, tex_idx=t_surf),
        "roof_gloss": exp.add_mat("Mat_RoofCoat", roughness=0.48, metallic=0.12, tex_idx=t_surf),
        "glass": exp.add_mat("Mat_Glass", roughness=0.18, metallic=0.25, tex_idx=t_surf),
        "skylight": exp.add_mat("Mat_Skylight", base_color=(0.88, 0.93, 0.98, 0.85), roughness=0.22, tex_idx=t_surf, alpha_mode="BLEND", double_sided=True),
        "white_alu": exp.add_mat("Mat_WhiteAlu", base_color=(0.91, 0.92, 0.93, 1.0), metallic=0.35, roughness=0.38),
        "dark_steel": exp.add_mat("Mat_DarkSteel", base_color=(0.18, 0.21, 0.25, 1.0), metallic=0.65, roughness=0.40),
        "blue_steel": exp.add_mat("Mat_BlueSteel", base_color=(0.24, 0.34, 0.45, 1.0), metallic=0.55, roughness=0.42),
        "tensile": exp.add_mat("Mat_TensileMembrane", base_color=(0.94, 0.95, 0.97, 1.0), roughness=0.45, double_sided=True),
        "trunk": exp.add_mat("Mat_Bark", base_color=(0.35, 0.27, 0.20, 1.0), roughness=0.92),
        "leaf": exp.add_mat("Mat_Foliage", base_color=(0.86, 0.94, 0.84, 1.0), roughness=0.85, tex_idx=t_surf),
        "leaf_pine": exp.add_mat("Mat_PineFoliage", base_color=(0.10, 0.26, 0.16, 1.0), roughness=0.88),
        "leaf_ginkgo": exp.add_mat("Mat_GinkgoGold", base_color=(0.68, 0.64, 0.18, 1.0), roughness=0.86),
        "leaf_magnolia": exp.add_mat("Mat_MagnoliaLeaf", base_color=(0.18, 0.34, 0.19, 1.0), roughness=0.86),
        "leaf_persimmon": exp.add_mat("Mat_PersimmonLeaf", base_color=(0.25, 0.38, 0.17, 1.0), roughness=0.86),
        "flower_rose": exp.add_mat("Mat_RoseFlower", base_color=(0.74, 0.07, 0.12, 1.0), roughness=0.62),
        "flower_white": exp.add_mat("Mat_MagnoliaFlower", base_color=(0.96, 0.94, 0.88, 1.0), roughness=0.60),
        "fruit_orange": exp.add_mat("Mat_PersimmonFruit", base_color=(0.88, 0.38, 0.06, 1.0), roughness=0.55),
        "bronze": exp.add_mat("Mat_BronzeStatue", base_color=(0.23, 0.15, 0.09, 1.0), metallic=0.62, roughness=0.38),
        "stainless": exp.add_mat("Mat_StainlessGate", base_color=(0.72, 0.74, 0.76, 1.0), metallic=0.82, roughness=0.28),
        "pavilion_wood": exp.add_mat("Mat_PavilionWood", base_color=(0.40, 0.11, 0.09, 1.0), roughness=0.62),
        "crimson": exp.add_mat("Mat_CrimsonWood", base_color=(0.68, 0.14, 0.14, 1.0), roughness=0.55),
        "orange_hoop": exp.add_mat("Mat_OrangeHoop", base_color=(0.92, 0.35, 0.08, 1.0), roughness=0.35),
        "green_rail": exp.add_mat("Mat_GreenRail", base_color=(0.12, 0.36, 0.22, 1.0), roughness=0.48),
        "yellow_hatch": exp.add_mat("Mat_YellowHatch", base_color=(0.94, 0.68, 0.10, 1.0), roughness=0.75),
        "gold_trim": exp.add_mat("Mat_GoldTrim", base_color=(0.82, 0.68, 0.28, 1.0), metallic=0.75, roughness=0.30),
        "context": exp.add_mat("Mat_ContextHutong", base_color=(0.76, 0.77, 0.79, 1.0), roughness=0.92),
        "context_blue": exp.add_mat("Mat_ContextNeighborBlue", base_color=(0.38, 0.56, 0.78, 1.0), roughness=0.65),
    }
    if include_west_details:
        t_det = exp.add_png_texture("WestDetails", f"{tex_dir}/tex_west_details.png")
        mats["details"] = exp.add_mat("Mat_WestDetails", roughness=0.66, tex_idx=t_det)
        mats["details_alpha"] = exp.add_mat(
            "Mat_WestDetailsAlpha", roughness=0.24, tex_idx=t_det, alpha_mode="BLEND", double_sided=True
        )
        mats["hard_court"] = exp.add_mat("Mat_HardCourtApron", roughness=0.42, metallic=0.04, tex_idx=t_det)
        mats["pool_water"] = exp.add_mat(
            "Mat_RockeryWater", roughness=0.08, metallic=0.18, tex_idx=t_det, alpha_mode="BLEND", double_sided=True
        )
        mats["waterfall"] = exp.add_mat(
            "Mat_WaterfallStream", base_color=(0.86, 0.96, 1.0, 0.72), roughness=0.10, metallic=0.05,
            alpha_mode="BLEND", double_sided=True,
        )
        mats["rockery_stone"] = exp.add_mat(
            "Mat_RockeryStone", base_color=(0.50, 0.47, 0.44, 1.0), roughness=0.76, tex_idx=t_gates
        )
        mats["hoop_green"] = exp.add_mat("Mat_HoopGreen", base_color=(0.09, 0.52, 0.23, 1.0), metallic=0.28, roughness=0.38)
        mats["hoop_pad"] = exp.add_mat("Mat_HoopPad", base_color=(0.08, 0.44, 0.20, 1.0), roughness=0.72)
        mats["yellow_pole"] = exp.add_mat("Mat_YellowPole", base_color=(0.95, 0.79, 0.15, 1.0), roughness=0.45)
        mats["fitness_blue"] = exp.add_mat("Mat_FitnessBlue", base_color=(0.14, 0.36, 0.76, 1.0), metallic=0.35, roughness=0.42)
        mats["floodlight"] = exp.add_mat(
            "Mat_Floodlight", base_color=(0.98, 0.97, 0.90, 1.0), roughness=0.20, emissive=(0.45, 0.43, 0.36)
        )
        mats["warm_glass"] = exp.add_mat(
            "Mat_WarmSunroom", base_color=(0.96, 0.89, 0.70, 0.88), roughness=0.22, emissive=(0.26, 0.20, 0.10),
            alpha_mode="BLEND", double_sided=True,
        )
        mats["wall_grey_render"] = exp.add_mat("Mat_WallGreyRender", base_color=(0.66, 0.68, 0.71, 1.0), roughness=0.88)
        mats["context_dark"] = exp.add_mat("Mat_ContextDark", base_color=(0.32, 0.35, 0.40, 1.0), roughness=0.78)
    mats["led_off"] = exp.add_mat("Mat_LEDOff", base_color=(0.13, 0.14, 0.15, 1.0), metallic=0.10, roughness=0.30, emissive=(0.03, 0.03, 0.035))
    mats["stainless"] = exp.add_mat("Mat_Stainless", base_color=(0.80, 0.81, 0.82, 1.0), metallic=0.85, roughness=0.25)
    mats["bare_soil"] = exp.add_mat("Mat_BareSoil", base_color=(0.36, 0.29, 0.22, 1.0), roughness=1.0)
    mats["fence_mesh"] = exp.add_mat("Mat_FenceMesh", base_color=(0.55, 0.58, 0.60, 0.34), roughness=0.55, double_sided=True, alpha_mode="BLEND")
    mats["sign_red"] = exp.add_mat("Mat_SignRed", base_color=(0.62, 0.12, 0.12, 1.0), roughness=0.60)
    mats["sign_blue"] = exp.add_mat("Mat_SignBlue", base_color=(0.10, 0.30, 0.55, 1.0), roughness=0.55)
    mats["plaque_white"] = exp.add_mat("Mat_PlaqueWhite", base_color=(0.92, 0.92, 0.89, 1.0), roughness=0.45)

    if classic_mode:
        # Self-contained Classic GLB: keep embedded PNG atlases active (zero external /textures/* fetches),
        # alias direct PBR/lamp keys to clean embedded/standard materials so every geometry upgrade renders crisply.
        mats["pbr_rockery"] = exp.add_mat("Mat_RockeryGranite", base_color=(0.56, 0.56, 0.54, 1.0), roughness=0.84)
        mats["pbr_bark"] = mats["trunk"]
        mats["pbr_wood"] = exp.add_mat("Mat_WoodClassic", base_color=(0.58, 0.42, 0.28, 1.0), roughness=0.64)
        mats["pbr_dark_slate"] = exp.add_mat("Mat_DarkSlateClassic", base_color=(0.28, 0.30, 0.34, 1.0), roughness=0.72)
        mats["glass_phys"] = exp.add_mat(
            "Mat_ClassicGlass", base_color=(0.30, 0.44, 0.56, 1.0), metallic=0.28, roughness=0.18
        )
        mats["lamp_warm"] = exp.add_mat("Mat_Lamp_Warm", base_color=(1.0, 0.95, 0.82, 1.0), roughness=0.22, emissive=(0.12, 0.09, 0.04))
        mats["int_light_warm0"] = mats["lamp_warm"]
        mats["int_light_warm1"] = mats["lamp_warm"]
        mats["int_glow_warm0"] = exp.add_mat("Mat_IntClassic0", base_color=(0.88, 0.84, 0.76, 1.0), roughness=0.90)
        mats["int_glow_warm1"] = mats["int_glow_warm0"]
        mats["int_floor"] = exp.add_mat("Mat_IntFloorClassic", base_color=(0.52, 0.50, 0.48, 1.0), roughness=0.80)
        mats["int_books"] = exp.add_mat("Mat_IntBooksClassic", base_color=(0.46, 0.28, 0.20, 1.0), roughness=0.82)
        exp.bind_archviz_registry(mats, {}, {})
        return mats

    # Enhanced ArchViz mode: register semantic PBR slots, physical transparent glass, shallow interiors & foliage cards
    metric_tiles, _ = register_archviz_materials(exp, mats)
    legacy_redirects = populate_legacy_redirects(mats, UV_CONSTS, metric_tiles)
    exp.bind_archviz_registry(mats, metric_tiles, legacy_redirects)
    return mats


def add_basketball_hoop(nb: NodeBuilder, cx: float, cy_n: float, yaw_face_rad: float, mats: dict, z_base: float = 0.04) -> None:
    """East Campus upgraded gooseneck basketball hoop with tempered glass backboard, hollow orange rim & braided net."""
    add_realistic_basketball_hoop(nb, cx, cy_n, yaw_face_rad, mats, UV_CONSTS, z_base=z_base, style="east_dark")


def add_basketball_hoop_west(nb: NodeBuilder, cx: float, cy_n: float, yaw_face_rad: float, mats: dict, z_base: float = 0.06) -> None:
    """West Campus photo-accurate Kelly-green 3D truss hoop + tempered glass backboard, hollow orange rim & braided net."""
    add_realistic_basketball_hoop(nb, cx, cy_n, yaw_face_rad, mats, UV_CONSTS, z_base=z_base, style="west_green")


def add_double_basketball_hoop_west(nb: NodeBuilder, cx: float, cy_n: float, yaw_axis_rad: float, mats: dict, z_base: float = 0.06) -> None:
    """West Campus back-to-back connected twin Kelly-green 3D truss basketball hoops sharing one central column."""
    add_realistic_double_basketball_hoop(nb, cx, cy_n, yaw_axis_rad, mats, UV_CONSTS, z_base=z_base)


def add_ac_unit(nb: NodeBuilder, cx: float, cy: float, z_bot: float, yaw_face_rad: float, mats: dict) -> None:
    """Split AC outdoor condenser unit on braced wall L-brackets with insulated refrigerant conduit."""
    add_detailed_ac_unit(nb, cx, cy, z_bot, yaw_face_rad, mats, UV_CONSTS)


def add_pingpong_table(nb: NodeBuilder, cx: float, cy: float, yaw_rad: float, mats: dict, z_base: float = 0.028) -> None:
    """Standard outdoor ping-pong table with beveled blue top, tubular crimson undercarriage & fine mesh net."""
    add_realistic_pingpong_table(nb, cx, cy, yaw_rad, mats, UV_CONSTS, z_base=z_base)


def add_taihu_rockery_basin(nb: NodeBuilder, cx: float, cy: float, mats: dict, z_base: float = 0.0) -> None:
    """Water-filled dark-slate octagonal basin with vertical-fluted rockery & cascading waterfall (supports elevated z_base)."""
    segs = 8
    r_out, r_in = 2.28, 1.98
    z0, z1 = z_base + 0.02, z_base + 0.54
    inner_ring: List[Vec2] = []
    for i in range(segs):
        a0 = (2.0 * math.pi * i) / segs + math.pi / 8
        a1 = (2.0 * math.pi * (i + 1)) / segs + math.pi / 8
        o0 = (cx + r_out * math.cos(a0), cy + r_out * math.sin(a0))
        o1 = (cx + r_out * math.cos(a1), cy + r_out * math.sin(a1))
        co0 = (cx + (r_out + 0.04) * math.cos(a0), cy + (r_out + 0.04) * math.sin(a0))
        co1 = (cx + (r_out + 0.04) * math.cos(a1), cy + (r_out + 0.04) * math.sin(a1))
        i0 = (cx + r_in * math.cos(a0), cy + r_in * math.sin(a0))
        i1 = (cx + r_in * math.cos(a1), cy + r_in * math.sin(a1))
        inner_ring.append(i0)
        # Outer & inner dark-slate pool curb walls + slightly overhanging stone coping lip
        nb.quad_enu(mats["details"], (o0[0], o0[1], z0), (o1[0], o1[1], z0), (o1[0], o1[1], z1 - 0.06), (o0[0], o0[1], z1 - 0.06), UV_DARK_SLATE_PODIUM, 0.76, 0.94)
        nb.quad_enu(mats["surf"], (co0[0], co0[1], z1 - 0.06), (co1[0], co1[1], z1 - 0.06), (co1[0], co1[1], z1), (co0[0], co0[1], z1), UV_PLAZA_TILE, 0.88, 0.98)
        nb.quad_enu(mats["details"], (i1[0], i1[1], z_base + 0.12), (i0[0], i0[1], z_base + 0.12), (i0[0], i0[1], z1), (i1[0], i1[1], z1), UV_DARK_SLATE_PODIUM, 0.68, 0.88)
        nb.quad_enu(mats["surf"], (i0[0], i0[1], z1), (co0[0], co0[1], z1), (co1[0], co1[1], z1), (i1[0], i1[1], z1), UV_PLAZA_TILE, 0.94, 0.99)
    # Submerged dark-slate pool floor + south-right silver inscription plaque on curb
    nb.add_polygon_patch(inner_ring, z_base + 0.12, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.72)
    nb.quad_enu(
        mats["white_alu"],
        (cx + 0.10, cy - r_out * 0.925, z_base + 0.22), (cx + 0.56, cy - r_out * 0.925, z_base + 0.22),
        (cx + 0.56, cy - r_out * 0.925, z_base + 0.37), (cx + 0.10, cy - r_out * 0.925, z_base + 0.37),
    )
    # Reflective translucent emerald-blue pool water surface
    nb.add_polygon_patch(inner_ring, z_base + 0.44, mats["pool_water"], UV_ROCKERY_WATER, ao=0.98)
    # Sculpted vertical-fluted craggy Taihu mountain rockery (smooth-normal organic crags)
    spire_specs = [
        (-0.46, 0.10, 3.36, 0.72, 0.58, 11),
        (-1.02, -0.14, 2.38, 0.44, 0.40, 23),
        (0.56, 0.08, 2.78, 0.60, 0.48, 37),
        (0.06, -0.22, 1.68, 0.56, 0.46, 49),
        (-0.56, -0.58, 1.88, 0.42, 0.34, 61),
        (0.68, -0.48, 2.02, 0.44, 0.36, 73),
        (-0.48, 0.62, 2.12, 0.46, 0.38, 89),
        (0.54, 0.60, 1.94, 0.44, 0.36, 97),
    ]
    for dx, dy, sh, rx, ry, seed in spire_specs:
        add_sculpted_rockery_spire(nb, cx + dx, cy + dy, z_base + 0.12, sh, rx, ry, seed, mats["pbr_rockery"], enu_to_gltf)
    # Cascading waterfall stream sheets (upper cleft -> central ledge -> pool surface) + white splash foam collar
    nb.quad_enu(
        mats["waterfall"],
        (cx - 0.14, cy - 0.10, z_base + 1.70), (cx + 0.22, cy - 0.10, z_base + 1.70),
        (cx + 0.16, cy + 0.02, z_base + 2.28), (cx - 0.10, cy + 0.02, z_base + 2.28),
        (0.1, 0.1, 0.9, 0.9), 0.95, 1.0, double_sided=True,
    )
    nb.quad_enu(
        mats["waterfall"],
        (cx - 0.24, cy - 0.82, z_base + 0.445), (cx + 0.32, cy - 0.82, z_base + 0.445),
        (cx + 0.24, cy - 0.48, z_base + 1.70), (cx - 0.18, cy - 0.48, z_base + 1.70),
        (0.1, 0.1, 0.9, 0.9), 0.96, 1.0, double_sided=True,
    )
    splash_pts = [
        (cx + 0.04 + 0.52 * math.cos(2 * math.pi * k / 12), cy - 0.86 + 0.34 * math.sin(2 * math.pi * k / 12))
        for k in range(12)
    ]
    nb.add_polygon_patch(splash_pts, z_base + 0.452, mats["waterfall"], (0.1, 0.1, 0.9, 0.9), ao=1.0)
    # Organic rock-crevice bonsai sprig on upper-right crag (replaces crude cylinder shrub!)
    nb.add_limb(mats["trunk"], (cx + 0.84, cy + 0.04, z_base + 1.92), (cx + 0.96, cy + 0.04, z_base + 2.40), 0.036, 0.018, segs=6)
    add_planter_foliage(nb, cx + 0.98, cy + 0.04, z_base + 2.34, 0.56, 0.46, 0.3, mats, plant_kind="hedge", height=0.45, seed=91)


def add_parked_bicycle_row(
    nb: NodeBuilder,
    x_start: float, y_start: float,
    count: int, step_x: float, step_y: float,
    yaw_rad: float, mats: dict,
    z_base: float = 0.03,
) -> None:
    """High-detail parked student bicycles with circular tires, alloy rims, spokes, tubular frames & hollow wire baskets."""
    add_realistic_bicycle_row(nb, x_start, y_start, count, step_x, step_y, yaw_rad, mats, z_base=z_base)


def add_pullup_rack_and_mats(nb: NodeBuilder, mats: dict, z_base: float = 0.0) -> None:
    """West wall tubular blue chin-up / fitness bar rack (5 bars) + segmented crimson crash mats flush to NW planter & midline."""
    x_bar = -93.25
    # 5 horizontal bars (6 vertical posts) from playground N-S midline (y=107.60) up to NW tree planter (y=122.20)
    y_bays = [108.10 + i * 2.70 for i in range(6)]
    # Segmented beveled gymnastics crash mats hugging west wall (y=107.60..122.15, zero gap to NW tree planter)
    n_mats = 6
    mat_y0, mat_y1 = 107.60, 122.15
    mat_seg = (mat_y1 - mat_y0) / n_mats
    for mi in range(n_mats):
        my_c = mat_y0 + (mi + 0.5) * mat_seg
        nb.add_beveled_box(mats["crimson"], -93.12, my_c, z_base + 0.056, 1.08, mat_seg - 0.04, 0.11, 0.0, bevel=0.02, ao_bot=0.76, ao_top=0.96)
    for idx, py in enumerate(y_bays):
        # Bolted steel base flange + cylindrical blue fitness upright + dome cap
        nb.add_smooth_cylinder(mats["dark_steel"], x_bar, py, z_base + 0.16, 0.09, 0.08, 0.04, segs=8)
        nb.add_smooth_cylinder(mats["fitness_blue"], x_bar, py, z_base + 0.20, 0.045, 0.045, 2.28, segs=8, ao_bot=0.78, ao_top=0.98)
        nb.add_sphere(mats["fitness_blue"], x_bar, py, z_base + 2.48, 0.052, 0.048, 0.052, segs=8, rings=4, ao=1.0)
        if idx < len(y_bays) - 1:
            ny = y_bays[idx + 1]
            bar_z = z_base + (2.36 if idx % 2 == 0 else 2.18)
            nb.add_limb(mats["stainless"] if "stainless" in mats else mats["white_alu"], (x_bar, py, bar_z), (x_bar, ny, bar_z), 0.020, 0.020, segs=6)
            # Hanging blue exercise straps + grip rings
            for sy in (py + 0.85, ny - 0.85):
                nb.add_limb(mats["fitness_blue"], (x_bar, sy, bar_z), (x_bar, sy, bar_z - 0.48), 0.012, 0.012, segs=4)
                add_torus_ring(nb, mats["white_alu"], (x_bar, sy, bar_z - 0.54), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), 0.06, 0.012, major_segs=8, minor_segs=4)


def add_high_ball_fence_and_floodlights(nb: NodeBuilder, mats: dict, z_base: float = 0.0) -> None:
    """Tall sports perimeter ball-stop fence (tubular frame + translucent chain-link mesh) & angled stadium LED masts."""
    # West wall high ball-stop fence (x = -93.92, y = 89.5..124.5, rising above elevated perimeter wall)
    y0, y1 = 89.5, 124.5
    n_bays = 10
    z_bot, z_top = z_base + 2.35, z_base + 5.65
    nb.add_limb(mats["blue_steel"], (-93.92, y0, z_top - 0.04), (-93.92, y1, z_top - 0.04), 0.032, 0.032, segs=6)
    nb.add_limb(mats["blue_steel"], (-93.92, y0, (z_bot + z_top) * 0.5), (-93.92, y1, (z_bot + z_top) * 0.5), 0.026, 0.026, segs=6)
    nb.add_limb(mats["blue_steel"], (-93.92, y0, z_bot + 0.04), (-93.92, y1, z_bot + 0.04), 0.026, 0.026, segs=6)
    # Translucent chain-link mesh sheet across entire ball-stop fence
    nb.quad_enu(
        mats["fence_mesh"],
        (-93.92, y0, z_bot + 0.06), (-93.92, y1, z_bot + 0.06),
        (-93.92, y1, z_top - 0.06), (-93.92, y0, z_top - 0.06),
        (0.0, 0.0, 1.0, 1.0), 0.94, 0.98, double_sided=True,
    )
    for i in range(n_bays + 1):
        fy = y0 + (y1 - y0) * (i / n_bays)
        nb.add_smooth_cylinder(mats["blue_steel"], -93.92, fy, z_bot, 0.042, 0.042, z_top - z_bot, segs=6)
        if i < n_bays:
            ny = y0 + (y1 - y0) * ((i + 1) / n_bays)
            # Slender tension cable cross-braces
            nb.add_limb(mats["blue_steel"], (-93.92, fy, z_bot + 0.08), (-93.92, ny, z_top - 0.08), 0.009, 0.009, segs=4)
            nb.add_limb(mats["blue_steel"], (-93.92, ny, z_bot + 0.08), (-93.92, fy, z_top - 0.08), 0.009, 0.009, segs=4)

    # 4 Multi-head angled stadium floodlight masts (3 along elevated west track boundary + 1 at east lower forecourt)
    for lx, ly, zb_m, ph_m, yaw_in in [
        (-93.65, 92.2, z_base, 7.25, 0.0),
        (-93.65, 107.6, z_base, 7.25, 0.0),
        (-93.65, 121.8, z_base, 7.25, 0.0),
        (-13.15, 107.6, 0.0, 7.25 + z_base, math.pi),
    ]:
        add_detailed_stadium_floodlight(nb, lx, ly, zb_m, yaw_in, ph_m, mats, n_heads=2)


def add_pa_speaker_stack(
    nb: NodeBuilder, sx: float, sy: float, yaw_rad: float, mats: dict, z_base: float = 0.0
) -> None:
    """Ground-stacked 2-tier outdoor PA speaker system: bottom horizontal beveled subwoofer + top vertical full-range cabinet."""
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

    def rot(lx: float, ly: float) -> Vec2:
        return (sx + lx * cs - ly * sn, sy + lx * sn + ly * cs)

    # 4 low rubber feet directly on ground
    for fx in (-0.44, 0.44):
        for fy in (-0.28, 0.28):
            rx, ry = rot(fx, fy)
            nb.add_box(mats["dark_steel"], rx, ry, z_base + 0.0, 0.08, 0.08, 0.04, yaw_rad, ao_bot=0.68, ao_top=0.82)

    # Tier 1: Bottom HORIZONTAL beveled subwoofer cabinet (w=1.06m E-W, d=0.72m N-S, h=0.62m)
    nb.add_beveled_box(mats["dark_steel"], sx, sy, z_base + 0.04, 1.06, 0.72, 0.62, yaw_rad, bevel=0.02, ao_bot=0.72, ao_top=0.92)
    # Recessed horizontal dual-woofer grille facing -ly (south toward playground), UV rotated 90 deg for side-by-side cones
    sub_f0 = rot(-0.48, -0.368)
    sub_f1 = rot(0.48, -0.368)
    u0, _, u1, _ = UV_PA_SPEAKER
    v_sub0, v_sub1 = 0.390, 0.505
    nb.bucket(mats["stage"]).add_quad_uvs(
        enu_to_gltf(sub_f0[0], sub_f0[1], z_base + 0.09),
        enu_to_gltf(sub_f1[0], sub_f1[1], z_base + 0.09),
        enu_to_gltf(sub_f1[0], sub_f1[1], z_base + 0.61),
        enu_to_gltf(sub_f0[0], sub_f0[1], z_base + 0.61),
        (u0, v_sub0), (u0, v_sub1), (u1, v_sub1), (u1, v_sub0),
        0.88, 0.98,
    )
    # Thin isolation bumper pad between Tier 1 & Tier 2
    nb.add_box(mats["dark_steel"], sx, sy, z_base + 0.66, 0.62, 0.54, 0.03, yaw_rad, ao_bot=0.76, ao_top=0.88)

    # Tier 2: Top VERTICAL beveled full-range main speaker cabinet (w=0.58m, d=0.52m, h=1.02m) + slim weather cap
    nb.add_beveled_box(mats["dark_steel"], sx, sy, z_base + 0.69, 0.58, 0.52, 1.02, yaw_rad, bevel=0.02, ao_bot=0.82, ao_top=0.96)
    hood_xy = rot(0.0, -0.02)
    nb.add_beveled_box(mats["dark_steel"], hood_xy[0], hood_xy[1], z_base + 1.71, 0.62, 0.58, 0.04, yaw_rad, bevel=0.012, ao_bot=0.88, ao_top=1.0)
    # Front vertical speaker grille & horn/drivers facing -ly (toward playground)
    top_f0 = rot(-0.25, -0.268)
    top_f1 = rot(0.25, -0.268)
    nb.quad_enu(
        mats["stage"],
        (top_f0[0], top_f0[1], z_base + 0.73),
        (top_f1[0], top_f1[1], z_base + 0.73),
        (top_f1[0], top_f1[1], z_base + 1.67),
        (top_f0[0], top_f0[1], z_base + 1.67),
        UV_PA_SPEAKER, 0.92, 1.0,
    )


def add_tapered_monolith(
    nb: NodeBuilder,
    cx: float, cy_n: float,
    tiers: List[Tuple[float, float, float, float, float, float]],
    mat: int, uv_box: UVBox,
) -> None:
    """Stacked tapered granite tiers (z0, z1, w0, d0, w1, d1) forming natural stone monolith."""
    for idx, (z0, z1, w0, d0, w1, d1) in enumerate(tiers):
        b = [
            (cx - w0 * 0.5, cy_n - d0 * 0.5),
            (cx + w0 * 0.5, cy_n - d0 * 0.5),
            (cx + w0 * 0.5, cy_n + d0 * 0.5),
            (cx - w0 * 0.5, cy_n + d0 * 0.5),
        ]
        t = [
            (cx - w1 * 0.5, cy_n - d1 * 0.5),
            (cx + w1 * 0.5, cy_n - d1 * 0.5),
            (cx + w1 * 0.5, cy_n + d1 * 0.5),
            (cx - w1 * 0.5, cy_n + d1 * 0.5),
        ]
        ao0 = 0.78 + idx * 0.04
        ao1 = min(1.0, 0.84 + idx * 0.04)
        for k in range(4):
            kn = (k + 1) % 4
            nb.quad_enu(
                mat,
                (b[k][0], b[k][1], z0), (b[kn][0], b[kn][1], z0),
                (t[kn][0], t[kn][1], z1), (t[k][0], t[k][1], z1),
                uv_box, ao0, ao1,
            )
        if idx == len(tiers) - 1:
            nb.quad_enu(
                mat,
                (t[0][0], t[0][1], z1), (t[1][0], t[1][1], z1),
                (t[2][0], t[2][1], z1), (t[3][0], t[3][1], z1),
                uv_box, ao1, ao1,
            )


# ---------------------------------------------------------------------------
# WEST CAMPUS (同福夹道3号 校本部)
# ---------------------------------------------------------------------------
def build_west_campus(data_path: str, tex_dir: str, out_glb: str, classic_mode: bool = False) -> Tuple[int, int, List[dict]]:
    west = json.loads(Path(data_path).read_text())
    ways = {w["id"]: w for w in west["ways"]}
    exp = GLBExporter(classic_mode=classic_mode)
    mats = init_materials(exp, tex_dir, include_west_details=True, classic_mode=classic_mode)
    west_lights: List[dict] = []
    # Real-world 40 cm elevation step: northern playground plateau (W-P1, W-P2, W-H1, W-B5 & NE ping-pong/rockery)
    # sits +0.40m above the southern plaza, bicycle parking zone & cafeteria south/west forecourt, with zero north drop.
    PG_Z = 0.40

    # ---- Campus_Ground_West ----
    gnd = exp.add_node("Campus_Ground_West")
    gnd.add_polygon_patch(ways["352521262"]["pts"], 0.0, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    # Surrounding road base (below y=0 slightly)
    gnd.add_box(mats["surf"], -35.0, 60.0, -0.18, 290.0, 270.0, 0.16, 0.0, UV_ASPHALT, ao_bot=0.92, ao_top=0.92)
    # East entry driveway stone pavement leading to 1F bike portal (W-ST1) & Cafeteria (W-B6) + 同福夹道 alley strip
    gnd.add_polygon_patch([(-4.5, 5.2), (3.6, 5.2), (3.6, 75.2), (-5.2, 75.2)], 0.02, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    gnd.add_polygon_patch([(-5.2, 87.3), (3.6, 87.3), (3.6, 96.5), (-5.2, 96.5)], 0.02, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    gnd.add_polygon_patch([(-4.2, -55.0), (4.2, -55.0), (4.2, 5.2), (-4.2, 5.2)], -0.01, mats["surf"], UV_ASPHALT, ao=0.95)

    # Elevated Northern Campus Plateau Slab (z = 0.0 .. PG_Z = 0.40m, seamless zero drop on north side!)
    north_plateau_pts = [
        (-94.0, 90.40), (-13.50, 90.40), (-13.50, 120.30),
        (-9.20, 120.30), (-9.20, 124.80), (-5.80, 124.80),
        (-5.80, 132.50), (-6.80, 132.50), (-6.80, 142.60), (-94.0, 142.60),
    ]
    gnd.add_polygon_slab(
        north_plateau_pts, 0.0, PG_Z,
        mats["surf"], mats["surf"],
        UV_QINGZHUAN, UV_PLAZA_TILE,
        ao_bot=0.72, ao_top=0.95,
    )
    # Stone-paved passage east of 校史馆 (W-H1), north alley & straight W-B5 south veranda walk (on +0.40m terrace)
    gnd.add_polygon_patch([(-70.2, 124.6), (-65.0, 124.6), (-65.0, 136.85), (-70.2, 136.85)], PG_Z + 0.025, mats["surf"], UV_PLAZA_TILE, ao=0.96)
    gnd.add_polygon_patch([(-93.6, 133.1), (-70.0, 133.1), (-70.0, 136.85), (-93.6, 136.85)], PG_Z + 0.028, mats["surf"], UV_PLAZA_TILE, ao=0.94)
    gnd.add_polygon_patch([(-70.2, 134.3), (-6.8, 134.3), (-6.8, 136.85), (-70.2, 136.85)], PG_Z + 0.027, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    # Decorative crazy-paving stone medallion in north alley east entry (Photo 1 foreground, on +0.40m terrace)
    gnd.quad_enu(
        mats["details"],
        (-72.0, 133.75, PG_Z + 0.036), (-70.35, 133.75, PG_Z + 0.036),
        (-70.35, 135.15, PG_Z + 0.036), (-72.0, 135.15, PG_Z + 0.036),
        UV_CRAZY_PAVING, 0.95, 0.98,
    )

    # Playground South Plaza Strip (lower grade z = 0.025..0.032m, 40cm below playground)
    gnd.add_polygon_patch(
        [
            (-93.75, 81.5), (-89.15, 81.5), (-89.8, 76.2), (-69.8, 77.2),
            (-69.5, 66.8), (-55.2, 66.8), (-55.2, 77.2), (-46.8, 77.4),
            (-46.8, 90.4), (-93.75, 90.4),
        ],
        0.025, mats["surf"], UV_PLAZA_TILE, ao=0.96,
    )
    # East forecourt stone-brick walkway in front of Student Cafeteria (W-B6, lower grade up to y=124.80)
    gnd.add_polygon_patch(
        [(-13.50, 90.4), (-5.60, 90.4), (-5.60, 124.80), (-9.20, 124.80), (-9.20, 120.30), (-13.50, 120.30)],
        0.026, mats["surf"], UV_PLAZA_TILE, ao=0.97,
    )
    # East side: 自行车停放区（无车棚） + 外置楼梯东侧一层推车穿堂连接道 (lower grade z = 0.032m)
    gnd.add_polygon_patch(
        [(-46.8, 68.2), (-37.5, 68.4), (-11.5, 84.5), (-11.5, 90.4), (-46.8, 90.4)],
        0.032, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.92,
    )
    gnd.add_polygon_patch(
        [(-11.5, 84.5), (-9.5, 83.2), (-0.45, 83.2), (-0.45, 90.4), (-11.5, 90.4)],
        0.032, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.92,
    )
    gnd.add_polygon_patch(
        [(-0.45, 74.8), (3.35, 74.8), (3.35, 90.4), (-0.45, 90.4)],
        0.032, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.91,
    )

    # 40 cm Qingzhuan Brick Retaining Wall + Overhanging Granite Coping along South & East Playground Drop
    # Cleanly gapped for 3 granite staircases + 1 accessible ramp descending to lower bike zone & cafeteria forecourt!
    ret_h = PG_Z + 0.055  # coping rises slightly above track edge (exact match to west-stairway-2024.webp!)
    add_stone_curb_polyline(gnd, [(-93.75, 90.36), (-53.10, 90.36)], 0.02, ret_h, 0.28, mats, UV_CONSTS)
    add_stone_curb_polyline(gnd, [(-48.90, 90.36), (-26.80, 90.36)], 0.02, ret_h, 0.28, mats, UV_CONSTS)
    add_stone_curb_polyline(gnd, [(-23.20, 90.36), (-21.40, 90.36)], 0.02, ret_h, 0.28, mats, UV_CONSTS)
    add_stone_curb_polyline(gnd, [(-19.50, 90.36), (-13.50, 90.36), (-13.50, 111.70)], 0.02, ret_h, 0.28, mats, UV_CONSTS)
    add_stone_curb_polyline(gnd, [(-13.50, 115.30), (-13.50, 120.30), (-9.20, 120.30), (-9.20, 124.80)], 0.02, ret_h, 0.28, mats, UV_CONSTS)
    # 4 Granite Staircases & 1 Accessible Ramp bridging the 40 cm elevation difference
    add_granite_stairs(gnd, -51.0, 90.38, 0.025, PG_Z + 0.05, 4.10, 1.15, math.pi, 3, mats, UV_CONSTS, cheek_walls=True)
    add_granite_stairs(gnd, -25.0, 90.38, 0.032, PG_Z + 0.05, 3.50, 1.10, math.pi, 3, mats, UV_CONSTS, cheek_walls=True)
    add_accessible_ramp_wedge(gnd, -20.45, 90.38, 0.032, PG_Z + 0.05, 1.80, 2.40, math.pi, mats, UV_CONSTS)
    add_granite_stairs(gnd, -13.50, 113.50, 0.026, PG_Z + 0.05, 3.50, 1.10, -math.pi * 0.5, 3, mats, UV_CONSTS, cheek_walls=True)
    add_granite_stairs(gnd, -7.50, 124.80, 0.026, PG_Z + 0.03, 3.10, 1.10, math.pi, 3, mats, UV_CONSTS, cheek_walls=True)

    for lx0, ly0, lx1, ly1 in [
        (-44.6, 78.2, -14.5, 78.34),
        (-44.6, 81.6, -14.5, 81.74),
        (-44.6, 85.4, -14.5, 85.54),
        (-44.6, 78.2, -44.45, 85.54),
        (-29.5, 78.2, -29.35, 85.54),
        (-14.65, 78.2, -14.5, 85.54),
        # Parking bay stripes north of W-ST1 & 1F push-bike lane guide lines through east portal
        (-9.2, 83.55, -2.0, 83.67),
        (-9.2, 83.55, -9.08, 85.15),
        (-6.8, 83.55, -6.68, 85.15),
        (-4.4, 83.55, -4.28, 85.15),
        (-2.12, 83.55, -2.0, 85.15),
        (-0.22, 74.9, -0.10, 85.4),
        (3.00, 74.9, 3.12, 85.4),
        (1.39, 75.7, 1.51, 77.3),
        (1.39, 78.5, 1.51, 80.1),
        (1.39, 81.3, 1.51, 82.9),
        (-14.5, 85.4, 1.51, 85.52),
    ]:
        gnd.quad_enu(mats["white_alu"], (lx0, ly0, 0.042), (lx1, ly0, 0.042), (lx1, ly1, 0.042), (lx0, ly1, 0.042))
    # Two rows of inverted-U tubular steel wheel racks + realistic circular-wheel student bicycles (strictly unroofed)
    for rack_y in (79.8, 83.8):
        add_detailed_bicycle_rack(gnd, -29.5, rack_y, 0.034, 28.0, 18, 0.0, mats)
    add_parked_bicycle_row(gnd, -41.8, 79.85, 16, 1.62, 0.0, 0.28, mats, z_base=0.034)
    add_parked_bicycle_row(gnd, -41.2, 83.85, 15, 1.68, 0.0, -0.24, mats, z_base=0.034)

    # North-east water-rockery & 5 ping-pong tables apron in front of W-B5 east section (elevated +0.40m, no drop!)
    gnd.add_polygon_patch(
        [(-31.4, 124.8), (-7.0, 124.8), (-7.0, 134.35), (-31.4, 134.35)],
        PG_Z + 0.028, mats["surf"], UV_TRACK_EPDM, ao=0.96,
    )
    add_taihu_rockery_basin(gnd, -20.6, 131.5, mats, z_base=PG_Z)
    # 5 outdoor ping-pong tables oriented North-South (yaw=pi/2) & aligned parallel to rockery center (y=131.5, PR #18 + PG_Z)
    for ppx, ppy, ppyaw in [
        (-28.6, 131.5, math.pi * 0.5),  # Left 1
        (-25.2, 131.5, math.pi * 0.5),  # Left 2
        (-16.2, 131.5, math.pi * 0.5),  # Right 1
        (-13.2, 131.5, math.pi * 0.5),  # Right 2
        (-10.2, 131.5, math.pi * 0.5),  # Right 3
    ]:
        add_pingpong_table(gnd, ppx, ppy, ppyaw, mats, z_base=PG_Z + 0.028)

    # Green lawn south of B-Wing & C-Wing junction + forecourt stone strip in front of B座 SE corner
    gnd.add_polygon_patch(
        [(-41.5, 42.5), (-5.2, 42.5), (-5.2, 68.0), (-10.2, 68.0), (-35.5, 55.6), (-41.5, 55.6)],
        0.025, mats["surf"], UV_GRASS, ao=0.94,
    )
    gnd.add_polygon_patch(
        [(-35.5, 55.6), (-10.2, 68.0), (-5.2, 68.0), (-5.2, 72.8), (-5.8, 72.8), (-35.5, 57.5)],
        0.025, mats["surf"], UV_PLAZA_TILE, ao=0.97,
    )
    # Masonry Stone-Brick Retaining Curbs & Granite Coping separating the West Entry Driveway from the Lawn!
    # 1. East border along entry driveway (x = -5.20, from y = 42.50 northward to y = 68.0, with gap at y=57.6..60.2 for Bing Xin path)
    add_stone_curb_polyline(gnd, [(-5.20, 42.50), (-5.20, 57.60)], 0.02, 0.30, 0.24, mats, UV_CONSTS)
    add_stone_curb_polyline(gnd, [(-5.20, 60.20), (-5.20, 68.00), (-10.20, 68.00)], 0.02, 0.30, 0.24, mats, UV_CONSTS)
    # 2. South & West borders of B-Wing lawn (leaving clean ramp landing apron around (-9.5, 38.0) & path gap)
    add_stone_curb_polyline(gnd, [(-5.20, 42.50), (-18.50, 42.50)], 0.02, 0.28, 0.24, mats, UV_CONSTS)
    add_stone_curb_polyline(gnd, [(-21.20, 42.50), (-41.50, 42.50), (-41.50, 55.60), (-35.50, 55.60)], 0.02, 0.28, 0.24, mats, UV_CONSTS)
    # 3. Sloped North border separating lawn from B-Wing forecourt stone strip (with gap facing B-Wing south entrance!)
    add_stone_curb_polyline(gnd, [(-35.50, 55.60), (-26.80, 59.88)], 0.02, 0.26, 0.22, mats, UV_CONSTS)
    add_stone_curb_polyline(gnd, [(-22.20, 62.12), (-10.20, 68.00)], 0.02, 0.26, 0.22, mats, UV_CONSTS)
    # 4. West edge of entry road between South Gate Annex (y=24.2) and W-R1 ramp landing plaza (y=33.8): stone curb + hedge bed
    #    (Leaves y=34.0..42.5 completely open so W-R1 wheelchair ramp at (-9.5, 38.0) flows unobstructed onto the main driveway!)
    add_stone_curb_polyline(gnd, [(-5.45, 24.20), (-5.45, 33.80), (-8.60, 33.80)], 0.02, 0.30, 0.24, mats, UV_CONSTS)
    add_planter_box(gnd, -6.30, 29.0, 0.02, 8.2, 1.35, 0.30, math.pi * 0.5, mats, UV_CONSTS, style="qingzhuan", plant_kind="hedge", plant_h=0.50, seed=41)
    # Low granite kerb edging along East wall side of entry driveway (x = +3.55, y = 8.0..74.8)
    add_stone_curb_polyline(gnd, [(3.55, 8.00), (3.55, 74.80)], 0.02, 0.16, 0.18, mats, UV_CONSTS, wall_uv_key="UV_PLAZA_TILE")

    # Campus Perimeter Rendered Wall with Structural Pilasters, Plinth & Coping (raised +0.40m around elevated north zone!)
    bound = ensure_ccw(ways["352521262"]["pts"])
    for i in range(len(bound)):
        a, b = bound[i], bound[(i + 1) % len(bound)]
        if a[1] < 8.0 and b[1] < 8.0 and -11.5 <= a[0] <= 5.0 and -11.5 <= b[0] <= 5.0:
            continue  # Open for West Gate & Guardhouse facade
        if min(a[1], b[1]) >= 96.4 and max(a[1], b[1]) <= 138.3 and min(a[0], b[0]) >= -6.9:
            continue  # W-B6 Cafeteria & its northern school annex exterior walls form the campus boundary here
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 0.5:
            continue
        yaw = math.atan2(dy, dx)
        mx, my = (a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5
        wall_h = (2.30 + PG_Z) if max(a[1], b[1]) > 90.4 else 2.30
        gnd.add_box(mats["surf"], mx, my, 0.0, L, 0.40, 0.34, yaw, UV_QINGZHUAN, ao_bot=0.70, ao_top=0.88)
        gnd.add_box(mats["wall_grey_render"], mx, my, 0.34, L, 0.34, wall_h - 0.34, yaw, ao_bot=0.78, ao_top=0.95)
        gnd.add_beveled_box(mats["surf"], mx, my, wall_h, L + 0.06, 0.46, 0.11, yaw, UV_QINGZHUAN, bevel=0.02, ao_bot=0.86, ao_top=0.98)
        n_pil = max(2, int(L // 4.2) + 1)
        for pi in range(n_pil):
            t_p = pi / (n_pil - 1)
            px = a[0] + dx * t_p
            py = a[1] + dy * t_p
            gnd.add_box(mats["surf"], px, py, 0.0, 0.42, 0.46, wall_h + 0.08, yaw, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.96)
            gnd.add_beveled_box(mats["surf"], px, py, wall_h + 0.08, 0.48, 0.52, 0.07, yaw, UV_PLAZA_TILE, bevel=0.015, ao_bot=0.90, ao_top=1.0)

    # West wall fitness pull-up bars + segmented red mats & high ball-stop fence + multi-head floodlights (on +0.40m terrace)
    add_pullup_rack_and_mats(gnd, mats, z_base=PG_Z)
    add_high_ball_fence_and_floodlights(gnd, mats, z_base=PG_Z)

    # ---- W-G1: 同福夹道3号正门 + 左侧大理石保安厅（含转角观察窗、东侧出入门、真实浅室内与门廊筒灯） ----
    gate = exp.add_node("W-G1")
    # Twin beveled marble gate piers
    gate.add_beveled_box(mats["gates"], -4.2, 5.2, 0.0, 1.2, 1.5, 4.4, 0.0, UV_MARBLE, bevel=0.04, ao_bot=0.76, ao_top=0.98)
    gate.add_beveled_box(mats["gates"], 3.2, 5.2, 0.0, 1.4, 1.5, 4.4, 0.0, UV_MARBLE, bevel=0.04, ao_bot=0.76, ao_top=0.98)
    # Guardhouse Tier-1 true 3D shallow interior (visible through physical glass corner windows in Enhanced mode)
    if not classic_mode:
        add_hero_room_box(
            gate, cx=-8.25, cy=7.60, z_floor=0.14, w=4.65, d=4.85, h=3.10,
            mats=mats, light_key="int_light_warm0", glow_key="int_glow_warm0", furnish="guardhouse",
        )
        # Recessed warm soffit downlights under the West Gate overhanging canopy + red LED banner glow
        for gx_dl in (-2.9, -1.2, 0.5, 2.0):
            add_wall_sconce(gate, gx_dl, 5.15, 4.32, mats, west_lights, color="#ffd59c", intensity=14.0, distance=13.0)
    west_lights.append({
        "kind": "gate_led",
        "pos": [-0.45, 5.05, -3.75],
        "color": "#ff5522",
        "intensity": 10.0,
        "distance": 12.0,
    })
    west_lights.append({
        "kind": "window_spill",
        "pos": [-6.8, 2.1, -4.4],
        "color": "#ffd296",
        "intensity": 12.0,
        "distance": 11.0,
    })
    # Guardhouse (left/west of gate: x -10.90..-5.65, y 4.80..10.40) with recessed doors & physical windows
    gate.add_box(mats["gates"], -8.275, 7.60, 0.0, 5.25, 5.60, 0.10, 0.0, UV_MARBLE, ao_bot=0.74, ao_top=0.90)
    gate.add_box(mats["gates"], -8.275, 7.60, 3.32, 5.25, 5.60, 0.28, 0.0, UV_MARBLE, ao_bot=0.86, ao_top=0.96, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    # White aluminum overhanging canopy extending east to join left gate pier
    gate.add_beveled_box(mats["white_alu"], -7.875, 7.60, 3.58, 6.35, 5.80, 0.30, 0.0, bevel=0.03, ao_bot=0.88, ao_top=1.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    # South marble wall (SW solid pier + window apron) + recessed SE corner service window
    gate.add_box(mats["gates"], -9.875, 4.98, 0.10, 2.05, 0.36, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    gate.quad_enu(mats["gates"], (-10.35, 4.78, 2.25), (-9.35, 4.78, 2.25), (-9.35, 4.78, 2.85), (-10.35, 4.78, 2.85), UV_EAST_SIGN, 0.92, 1.0)
    gate.quad_enu(mats["crimson"], (-10.08, 4.77, 1.82), (-9.62, 4.77, 1.82), (-9.62, 4.77, 2.12), (-10.08, 4.77, 2.12), (0.1, 0.1, 0.9, 0.9), 0.94, 1.0)
    gate.add_box(mats["gates"], -7.25, 4.98, 0.10, 3.20, 0.36, 0.95, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94)
    gate.add_box(mats["gates"], -7.25, 4.93, 1.01, 3.24, 0.44, 0.05, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.98)
    gate.quad_enu(mats["glass_phys"], (-8.85, 4.94, 1.05), (-5.79, 4.94, 1.05), (-5.79, 4.94, 3.32), (-8.85, 4.94, 3.32))
    gate.add_box(mats["dark_steel"], -8.81, 4.90, 1.05, 0.08, 0.10, 2.27, 0.0)
    gate.add_box(mats["dark_steel"], -7.25, 4.90, 1.05, 0.07, 0.10, 2.27, 0.0)
    gate.add_box(mats["dark_steel"], -7.32, 4.90, 2.18, 3.06, 0.10, 0.08, 0.0)
    gate.add_box(mats["dark_steel"], -7.32, 4.90, 3.27, 3.06, 0.10, 0.08, 0.0)
    gate.add_box(mats["dark_steel"], -7.32, 4.90, 1.06, 3.06, 0.10, 0.06, 0.0)
    gate.add_box(mats["dark_steel"], -6.52, 4.91, 1.09, 0.05, 0.08, 1.08, 0.0)  # Sliding service sash divider
    # Corner steel post joining South & East glass corner window
    gate.add_box(mats["dark_steel"], -5.72, 4.88, 1.05, 0.18, 0.18, 2.27, 0.0)
    # East wall (facing main entry driveway: SE corner window + entrance glass door + north window)
    gate.add_box(mats["gates"], -5.83, 6.145, 0.10, 0.36, 2.41, 0.95, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94)
    gate.add_box(mats["gates"], -5.79, 6.145, 1.01, 0.44, 2.45, 0.05, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.98)
    gate.quad_enu(mats["glass_phys"], (-5.79, 4.94, 1.05), (-5.79, 7.35, 1.05), (-5.79, 7.35, 3.32), (-5.79, 4.94, 3.32))
    gate.add_box(mats["dark_steel"], -5.75, 7.31, 1.05, 0.10, 0.08, 2.27, 0.0)
    gate.add_box(mats["dark_steel"], -5.75, 6.15, 1.05, 0.10, 0.07, 2.27, 0.0)
    gate.add_box(mats["dark_steel"], -5.75, 6.145, 2.18, 0.10, 2.41, 0.08, 0.0)
    gate.add_box(mats["dark_steel"], -5.75, 6.145, 3.27, 0.10, 2.41, 0.08, 0.0)
    gate.add_box(mats["dark_steel"], -5.75, 6.145, 1.06, 0.10, 2.41, 0.06, 0.0)
    # Pier between corner window & guardhouse door
    gate.add_box(mats["gates"], -5.83, 7.50, 0.10, 0.36, 0.30, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    # Guardhouse East Entrance Doorway (y: 7.65..8.85) with granite step, door frame, transom & handle
    gate.add_box(mats["surf"], -5.465, 8.25, 0.0, 0.37, 1.40, 0.10, 0.0, UV_QINGZHUAN, ao_bot=0.78, ao_top=0.94)
    gate.add_box(mats["gates"], -5.83, 8.25, 2.35, 0.36, 1.20, 0.97, 0.0, UV_MARBLE, ao_bot=0.82, ao_top=0.95)
    gate.add_box(mats["dark_steel"], -5.77, 7.69, 0.10, 0.12, 0.08, 2.25, 0.0)
    gate.add_box(mats["dark_steel"], -5.77, 8.81, 0.10, 0.12, 0.08, 2.25, 0.0)
    gate.add_box(mats["dark_steel"], -5.77, 8.25, 2.29, 0.12, 1.20, 0.06, 0.0)
    gate.add_box(mats["dark_steel"], -5.77, 8.25, 2.02, 0.12, 1.16, 0.06, 0.0)
    gate.add_box(mats["dark_steel"], -5.80, 8.25, 0.10, 0.06, 1.06, 0.82, 0.0)
    gate.quad_enu(mats["glass_phys"], (-5.79, 7.72, 0.92), (-5.79, 8.78, 0.92), (-5.79, 8.78, 2.29), (-5.79, 7.72, 2.29))
    gate.add_box(mats["white_alu"], -5.73, 7.84, 0.96, 0.05, 0.05, 0.38, 0.0)
    # Pier & East North-bay window (y: 8.85..10.40)
    gate.add_box(mats["gates"], -5.83, 8.975, 0.10, 0.36, 0.25, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    gate.add_box(mats["gates"], -5.83, 9.625, 0.10, 0.36, 1.05, 1.05, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94)
    gate.add_box(mats["gates"], -5.83, 9.625, 2.95, 0.36, 1.05, 0.37, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.95)
    gate.add_box(mats["gates"], -5.79, 9.625, 1.11, 0.44, 1.08, 0.05, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.98)
    gate.quad_enu(mats["glass_phys"], (-5.79, 9.10, 1.15), (-5.79, 10.15, 1.15), (-5.79, 10.15, 2.95), (-5.79, 9.10, 2.95))
    gate.add_box(mats["dark_steel"], -5.75, 9.625, 1.15, 0.09, 0.06, 1.80, 0.0)
    gate.add_box(mats["dark_steel"], -5.75, 9.625, 2.90, 0.09, 1.05, 0.06, 0.0)
    gate.add_box(mats["dark_steel"], -5.75, 9.625, 1.16, 0.09, 1.05, 0.05, 0.0)
    gate.add_box(mats["gates"], -5.83, 10.275, 0.10, 0.36, 0.25, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    # West wall with recessed daylight window + North solid wall
    gate.add_box(mats["gates"], -10.72, 5.68, 0.10, 0.36, 1.04, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    gate.add_box(mats["gates"], -10.72, 7.60, 0.10, 0.36, 2.80, 1.05, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94)
    gate.add_box(mats["gates"], -10.72, 7.60, 2.95, 0.36, 2.80, 0.37, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.95)
    gate.quad_enu(mats["glass_phys"], (-10.76, 9.00, 1.15), (-10.76, 6.20, 1.15), (-10.76, 6.20, 2.95), (-10.76, 9.00, 2.95))
    gate.add_box(mats["dark_steel"], -10.80, 7.60, 1.15, 0.08, 0.06, 1.80, 0.0)
    gate.add_box(mats["dark_steel"], -10.80, 7.60, 2.90, 0.08, 2.80, 0.06, 0.0)
    gate.add_box(mats["dark_steel"], -10.80, 7.60, 1.16, 0.08, 2.80, 0.05, 0.0)
    gate.add_box(mats["gates"], -10.72, 9.70, 0.10, 0.36, 1.40, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    gate.add_box(mats["gates"], -8.275, 10.22, 0.10, 4.53, 0.36, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    # Pedestrian passage lintel & glazed doorway frame between guardhouse and left gate pier
    gate.add_box(mats["gates"], -5.225, 5.375, 3.35, 0.85, 1.15, 1.00, 0.0, UV_MARBLE, ao_bot=0.80, ao_top=0.96)
    gate.add_box(mats["dark_steel"], -5.60, 5.05, 0.0, 0.07, 0.09, 2.25, 0.0)
    gate.add_box(mats["dark_steel"], -4.85, 5.05, 0.0, 0.07, 0.09, 2.25, 0.0)
    gate.add_box(mats["dark_steel"], -5.225, 5.05, 2.20, 0.85, 0.09, 0.08, 0.0)
    gate.add_box(mats["dark_steel"], -5.60, 5.35, 0.05, 0.05, 0.58, 2.12, 0.0)
    # Overhead fascia header (segmented vertical joints + overhanging cornice trim + soffit), centered LED & East pier plaque
    gate.add_box(
        mats["gates"], -2.05, 5.15, 4.35, 13.0, 1.95, 1.35, 0.0,
        UV_WEST_FASCIA_PLAIN, ao_bot=0.82, ao_top=0.98,
        top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
    )
    # Vertical panel seam ribs & crisp overhanging metal roof drip trim matching west-gate-2024.webp
    gate.add_beveled_box(mats["gates"], -2.05, 5.15, 5.68, 13.18, 2.10, 0.09, 0.0, UV_BURGUNDY, bevel=0.02, ao_bot=0.88, ao_top=1.0)
    for seam_x in (-8.0, -6.9, -5.8, -4.7, 3.6, 4.4):
        gate.add_box(mats["dark_steel"], seam_x, 4.17, 4.37, 0.03, 0.03, 1.31, 0.0)
    gate.add_box(mats["white_alu"], -2.05, 5.15, 4.32, 12.92, 1.88, 0.03, 0.0, ao_bot=0.86, ao_top=0.94)
    gate.add_box(mats["dark_steel"], -0.45, 4.21, 4.52, 7.80, 0.10, 1.02, 0.0, ao_bot=0.82, ao_top=0.98)
    gate.quad_enu(
        mats["led"],
        (-4.25, 4.15, 4.58), (3.35, 4.15, 4.58),
        (3.35, 4.15, 5.48), (-4.25, 4.15, 5.48),
        UV_WEST_LED_ONLY, 1.0, 1.0,
    )
    gate.quad_enu(mats["gates"], (2.68, 4.42, 0.9), (3.72, 4.42, 0.9), (3.72, 4.42, 3.45), (2.68, 4.42, 3.45), UV_WEST_PLAQUE, 0.95, 1.0)

    # Ornate Openwork Black Wrought-Iron Double Swing Gates (opened inward, matching west-gate-2024.webp!)
    for wing_x in (-3.28, 2.02):
        y_hinge, y_tip = 5.28, 8.28
        # Solid lower kick panel (z=0.14..0.68) + outer vertical stiles + mid/upper horizontal rails
        gate.add_box(mats["dark_steel"], wing_x, (y_hinge + y_tip) * 0.5, 0.14, 0.075, 3.00, 0.54, 0.0, ao_bot=0.72, ao_top=0.92)
        gate.add_box(mats["dark_steel"], wing_x, y_hinge, 0.12, 0.09, 0.09, 2.08, 0.0)
        gate.add_box(mats["dark_steel"], wing_x, y_tip, 0.12, 0.09, 0.09, 2.52, 0.0)
        gate.add_box(mats["dark_steel"], wing_x, (y_hinge + y_tip) * 0.5, 1.88, 0.065, 3.00, 0.055, 0.0)
        # Gracefully arched rising top cresting rail + 11 openwork slim pickets with spear tips
        n_pick = 11
        prev_arch: Optional[Vec3] = None
        for pi in range(n_pick):
            u = pi / (n_pick - 1)
            py = y_hinge + u * (y_tip - y_hinge)
            z_arch = 2.16 + 0.44 * math.sin(u * math.pi * 0.5)
            gate.add_box(mats["dark_steel"], wing_x, py, 0.68, 0.032, 0.032, z_arch - 0.68, 0.0)
            gate.add_smooth_cylinder(mats["gold_trim"], wing_x, py, z_arch, 0.022, 0.004, 0.09, segs=6)
            cur_arch = (wing_x, py, z_arch)
            if prev_arch is not None:
                add_rect_beam(gate, mats["dark_steel"], prev_arch, cur_arch, 0.06, 0.055)
            prev_arch = cur_arch
            # Decorative diamond scroll rings between upper rail & curved arch
            if pi < n_pick - 1 and pi % 2 == 0:
                py_m = py + (y_tip - y_hinge) / (n_pick - 1) * 0.5
                add_torus_ring(gate, mats["dark_steel"], (wing_x, py_m, 2.02), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), 0.095, 0.014, major_segs=8, minor_segs=4)

    # Low stainless floor track & neatly retracted retractable-gate stack beside west inner jamb (no doorway collision!)
    gate.add_box(mats["stainless"], -0.45, 5.10, 0.015, 7.10, 0.05, 0.015, 0.0)
    # Pedestrian turnstile stanchion inside left passage (west-gate-2024.webp)
    gate.add_beveled_box(mats["stainless"], -5.22, 5.45, 0.0, 0.22, 0.95, 0.96, 0.0, bevel=0.02)
    # Left guardhouse utility awning & blue anti-riot cabinet silhouette (west-gate-2024.webp far left)
    gate.add_box(mats["blue_steel"], -10.30, 4.45, 0.02, 1.25, 0.55, 1.48, 0.0, ao_bot=0.76, ao_top=0.96)
    add_rect_beam(gate, mats["dark_steel"], (-11.65, 4.15, 2.85), (-8.90, 4.15, 3.05), 0.09, 0.09)
    gate.add_smooth_cylinder(mats["blue_steel"], -11.45, 4.15, 0.0, 0.045, 0.045, 2.85, segs=8)
    gate.quad_enu(mats["skylight"], (-11.65, 4.05, 2.86), (-8.90, 4.05, 3.06), (-8.90, 4.88, 3.12), (-11.65, 4.88, 2.92), UV_SKYLIGHT, 0.94, 1.0, double_sided=True)

    # Photo-accurate 45° Diagonal Yellow Cross-Hatched No-Parking Box + Outer Border + 2 Manhole Covers (west-gate-2024.webp!)
    hx0, hx1, hy0, hy1 = -3.95, 2.95, -2.20, 3.60
    # Crisp outer yellow border frame
    for bx0, by0, bx1, by1 in [
        (hx0, hy0, hx1, hy0 + 0.14), (hx0, hy1 - 0.14, hx1, hy1),
        (hx0, hy0, hx0 + 0.14, hy1), (hx1 - 0.14, hy0, hx1, hy1),
    ]:
        gate.quad_enu(mats["yellow_hatch"], (bx0, by0, 0.015), (bx1, by0, 0.015), (bx1, by1, 0.015), (bx0, by1, 0.015))

    def _clip_diag_stripe(c_val: float, slope: float) -> Optional[Tuple[Vec2, Vec2]]:
        # Line y = slope * x + c_val clipped to [hx0, hx1] x [hy0, hy1]
        pts_hit: List[Vec2] = []
        for x_e in (hx0, hx1):
            y_e = slope * x_e + c_val
            if hy0 - 1e-4 <= y_e <= hy1 + 1e-4:
                pts_hit.append((x_e, max(hy0, min(hy1, y_e))))
        for y_e in (hy0, hy1):
            x_e = (y_e - c_val) / slope
            if hx0 + 1e-4 < x_e < hx1 - 1e-4:
                pts_hit.append((x_e, y_e))
        if len(pts_hit) < 2:
            return None
        pts_hit.sort()
        return pts_hit[0], pts_hit[-1]

    for slope_s in (1.0, -1.0):
        c_min = (hy0 - slope_s * hx1) if slope_s > 0 else (hy0 - slope_s * hx0)
        c_max = (hy1 - slope_s * hx0) if slope_s > 0 else (hy1 - slope_s * hx1)
        c_cur = c_min + 0.65
        while c_cur < c_max - 0.35:
            seg = _clip_diag_stripe(c_cur, slope_s)
            if seg is not None:
                pA_h, pB_h = seg
                dx_h, dy_h = pB_h[0] - pA_h[0], pB_h[1] - pA_h[1]
                ll_h = max(math.hypot(dx_h, dy_h), 0.01)
                nx_h, ny_h = (dy_h / ll_h) * 0.06, (-dx_h / ll_h) * 0.06
                gate.quad_enu(
                    mats["yellow_hatch"],
                    (pA_h[0] + nx_h, pA_h[1] + ny_h, 0.016), (pB_h[0] + nx_h, pB_h[1] + ny_h, 0.016),
                    (pB_h[0] - nx_h, pB_h[1] - ny_h, 0.016), (pA_h[0] - nx_h, pA_h[1] - ny_h, 0.016),
                )
            c_cur += 1.25
    for mhx, mhy in ((-1.75, -1.45), (1.35, -1.35)):
        gate.add_cylinder(mats["dark_steel"], mhx, mhy, 0.006, 0.36, 0.36, 0.016, 12)

    # Five yellow/black safety bollards with domed caps & reflective collars in front of the gate
    for bi in range(5):
        bxp = -3.55 + bi * 1.50
        gate.add_smooth_cylinder(mats["dark_steel"], bxp, 2.45, 0.0, 0.12, 0.11, 0.04, segs=10)
        gate.add_smooth_cylinder(mats["yellow_hatch"], bxp, 2.45, 0.04, 0.09, 0.085, 0.80, segs=10, ao_bot=0.78, ao_top=1.0)
        gate.add_smooth_cylinder(mats["dark_steel"], bxp, 2.45, 0.44, 0.094, 0.094, 0.12, segs=10, ao_bot=0.86, ao_top=1.0)
        gate.add_sphere(mats["yellow_hatch"], bxp, 2.45, 0.84, 0.086, 0.06, 0.086, segs=10, rings=4, ao=1.0)

    # Gold-framed glass honours/notice case with rain canopy & divided display plaques on east wall
    dcx, dcy = 5.54, 2.20
    gate.add_beveled_box(mats["gold_trim"], dcx, dcy, 0.98, 0.12, 2.15, 1.52, 0.0, bevel=0.015, ao_bot=0.86, ao_top=1.0)
    gate.add_beveled_box(mats["gold_trim"], dcx - 0.10, dcy, 2.50, 0.34, 2.28, 0.08, 0.0, bevel=0.015)
    gate.add_box(mats["white_alu"], dcx - 0.02, dcy, 1.08, 0.06, 1.95, 1.32, 0.0, ao_bot=0.88, ao_top=1.0)
    for div_y in (dcy - 0.35, dcy + 0.35):
        gate.add_box(mats["gold_trim"], dcx - 0.055, div_y, 1.08, 0.03, 0.035, 1.32, 0.0)
    gate.quad_enu(
        mats["glass_phys"],
        (dcx - 0.07, dcy - 0.96, 1.10), (dcx - 0.07, dcy + 0.96, 1.10),
        (dcx - 0.07, dcy + 0.96, 2.38), (dcx - 0.07, dcy - 0.96, 2.38),
    )

    # ---- W-L1: 慎独石 (entry axis, ~N30, facing south; sculpted granite monolith in stone planter bed) ----
    shendu = exp.add_node("W-L1")
    shendu.add_beveled_box(mats["surf"], -2.6, 30.0, 0.025, 2.50, 1.75, 0.16, 0.0, UV_QINGZHUAN, bevel=0.025, ao_bot=0.72, ao_top=0.90, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    add_sculpted_shendu_boulder(shendu, -2.6, 30.0, 0.16, 2.48, mats["pbr_rockery"], enu_to_gltf)
    # 3-strip subtly curved inscription face hugging the granite boulder south facet cleanly
    s_u0, s_v0, s_u1, s_v1 = UV_SHENDU_STONE
    for si_s in range(3):
        t0, t1 = si_s / 3.0, (si_s + 1) / 3.0
        x0_b, x1_b = -3.02 + 0.84 * t0, -3.02 + 0.84 * t1
        x0_t, x1_t = -2.92 + 0.64 * t0, -2.92 + 0.64 * t1
        y0_c = 29.59 + 0.035 * abs(t0 - 0.5) * 2.0
        y1_c = 29.59 + 0.035 * abs(t1 - 0.5) * 2.0
        su0 = s_u0 + (s_u1 - s_u0) * t0
        su1 = s_u0 + (s_u1 - s_u0) * t1
        shendu.quad_enu(
            mats["gates"],
            (x0_b, y0_c, 0.36), (x1_b, y1_c, 0.36),
            (x1_t, y1_c + 0.07, 2.08), (x0_t, y0_c + 0.07, 2.08),
            (su0, s_v0, su1, s_v1), 0.92, 1.0,
        )
    # Warm ground uplight housing illuminating the carved "慎獨" motto stone at night
    if not classic_mode:
        add_wall_sconce(shendu, -2.6, 28.95, 0.24, mats, west_lights, color="#ffd8a0", intensity=8.5, distance=8.0)
    # Continuous hollow Qingzhuan stone planter beds with natural clipped boxwood/rose hedges flanking Shendu stone
    add_planter_box(shendu, -4.15, 29.35, 0.025, 1.45, 0.72, 0.36, 0.0, mats, UV_CONSTS, style="qingzhuan", plant_kind="hedge", plant_h=0.46, seed=11)
    add_planter_box(shendu, -1.05, 29.35, 0.025, 1.45, 0.72, 0.36, 0.0, mats, UV_CONSTS, style="qingzhuan", plant_kind="hedge", plant_h=0.46, seed=17)
    # Teaching-building front pines (校方供稿：教学楼前青松)
    gnd.add_tree(-4.55, 33.6, "pine", 7.6, mats["trunk"], mats["leaf_pine"])
    gnd.add_tree(-4.30, 41.0, "pine", 6.8, mats["trunk"], mats["leaf_pine"])

    # ---- W-L3: 冰心像 (sculpted bronze portrait bust on classically molded marble pedestal + stone flower border) ----
    bx_node = exp.add_node("W-L3")
    bx_node.add_beveled_box(mats["surf"], -16.5, 58.8, 0.03, 3.20, 3.20, 0.16, 0.0, UV_QINGZHUAN, bevel=0.03, ao_bot=0.76, ao_top=0.92, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    bx_node.add_beveled_box(mats["surf"], -16.5, 58.8, 0.19, 2.20, 2.20, 0.16, 0.0, UV_PLAZA_TILE, bevel=0.025, ao_bot=0.80, ao_top=0.96)
    bx_node.add_beveled_box(mats["gates"], -16.5, 58.8, 0.35, 1.24, 1.24, 0.18, 0.0, UV_MARBLE, bevel=0.025)
    bx_node.add_beveled_box(mats["gates"], -16.5, 58.8, 0.53, 0.88, 0.88, 1.15, 0.0, UV_MARBLE, bevel=0.03, ao_bot=0.82, ao_top=0.98)
    # Molded classical cornice crown cap under bust
    bx_node.add_beveled_box(mats["gates"], -16.5, 58.8, 1.68, 1.06, 1.06, 0.12, 0.0, UV_MARBLE, bevel=0.025, ao_bot=0.90, ao_top=1.0)
    # Framed bronze inscription plaque on the south face of the pedestal
    bx_node.add_box(mats["bronze"], -16.5, 58.35, 0.72, 1.08, 0.04, 0.44, 0.0)
    bx_node.quad_enu(mats["gold_trim"], (-17.00, 58.32, 0.75), (-16.00, 58.32, 0.75), (-16.00, 58.32, 1.13), (-17.00, 58.32, 1.13), (0.1, 0.1, 0.9, 0.9), 0.92, 1.0)
    # Flanking low stone flower planters at NW & NE edges of statue terrace
    add_planter_box(bx_node, -17.65, 59.90, 0.03, 0.95, 0.48, 0.30, 0.0, mats, UV_CONSTS, style="stone", plant_kind="rose", plant_h=0.35, seed=31)
    add_planter_box(bx_node, -15.35, 59.90, 0.03, 0.95, 0.48, 0.30, 0.0, mats, UV_CONSTS, style="stone", plant_kind="rose", plant_h=0.35, seed=37)
    if not classic_mode:
        add_wall_sconce(bx_node, -16.5, 57.55, 0.22, mats, west_lights, color="#ffdba8", intensity=7.5, distance=7.5)
    # High-subdivision smoothly contoured bronze bust (~2.75 m total height)
    add_sculpted_bingxin_bust(bx_node, -16.5, 58.8, 1.80, mats["bronze"], enu_to_gltf)
    # Magnolia beside the statue (white flowers)
    bx_node.add_tree(-19.35, 58.15, "magnolia", 8.6, mats["trunk"], mats["leaf_magnolia"], mats["flower_white"])

    # ---- Connected 6-Story Complex: W-B1 (C座) + W-B2 (中部北凸枢纽) + W-B3 (B座) ----
    # Exact north stepped profile verified from OSM `way 398697589` + Photos 2, 4 & 6:
    #   - W-B1 north wing (x=-89.8..-69.8, y≈76.7) + north recessed slot (x=-69.5..-55.2, y=66.8)
    #   - W-B2 grey-ribbed 90° north projection (x=-55.2..-46.8, y=68.2..77.4)
    #   - W-B3 terracotta/white obtuse bend bay (x=-46.8..-37.5, y≈68.3) + ~150° NE wing (to -11.5, 84.5)

    # ---- W-B3: B座教学主楼 (6层 · 红白立面 + 150°钝角折弯 + 南北双面 B 教学楼牌) ----
    wb3 = exp.add_node("W-B3")
    wb3_pts = [(-46.8, 68.2), (-37.5, 68.4), (-11.5, 84.5), (-5.8, 72.8), (-35.5, 57.5), (-46.8, 57.6)]
    wb3.add_detailed_building(
        wb3_pts, stories=6, story_h=3.45, plinth_h=0.80,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_TERRACOTTA_BRICK,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        solid_x_planes=[-46.8],
        rail_mat=mats["dark_steel"],
        window_grille=True, grille_mat=mats["white_alu"],
        bay_w=4.4,
    )
    # Projecting balconies on the south facade (white vertical-baluster rails + terracotta cheeks + hollow molded planters!)
    ba = (-35.5, 57.5)
    bb = (-5.8, 72.8)
    bl = math.hypot(bb[0] - ba[0], bb[1] - ba[1])
    btx, bty = (bb[0] - ba[0]) / bl, (bb[1] - ba[1]) / bl
    bnx, bny = bty, -btx
    byaw = math.atan2(bty, btx)
    for fl in range(1, 6):
        bz = 0.80 + fl * 3.45
        for bi in range(7):
            along = 2.4 + bi * 4.30
            if along > bl - 1.2:
                continue
            px = ba[0] + btx * along + bnx * 0.58
            py = ba[1] + bty * along + bny * 0.58
            wb3.add_box(mats["white_alu"], px, py, bz, 3.70, 1.14, 0.14, byaw, ao_bot=0.84, ao_top=0.98)
            for s in (-1, 1):
                sx = px + btx * s * 1.82
                sy = py + bty * s * 1.82
                wb3.add_box(mats["surf"], sx, sy, bz + 0.14, 0.14, 1.05, 0.55, byaw, UV_TERRACOTTA_BRICK, 0.84, 0.98)
                # Corner vertical steel rail posts on balcony outer edge
                cp_x = sx + bnx * 0.52
                cp_y = sy + bny * 0.52
                wb3.add_box(mats["white_alu"], cp_x, cp_y, bz + 0.14, 0.055, 0.055, 0.98, byaw)
            # Top & bottom white steel balcony rails + 9 crisp vertical balusters (eliminates floating horizontal bars!)
            rx = px + bnx * 0.52
            ry = py + bny * 0.52
            wb3.add_box(mats["white_alu"], rx, ry, bz + 1.08, 3.64, 0.055, 0.05, byaw, ao_bot=0.90, ao_top=1.0)
            wb3.add_box(mats["white_alu"], rx, ry, bz + 0.22, 3.64, 0.045, 0.04, byaw, ao_bot=0.88, ao_top=0.98)
            for bvi in range(9):
                u_bv = -1.62 + bvi * (3.24 / 8.0)
                wb3.add_box(mats["white_alu"], rx + btx * u_bv, ry + bty * u_bv, bz + 0.22, 0.025, 0.025, 0.86, byaw)
            # Hollow molded terracotta-stone balcony planter trough with dark soil & botanical rose foliage (NO red blocks!)
            fx = px + bnx * 0.50
            fy = py + bty * 0.0 + bny * 0.50
            add_planter_box(
                wb3, fx, fy, bz + 0.82,
                length=2.45, width=0.25, height=0.22, yaw_rad=byaw,
                mats=mats, uv_consts=UV_CONSTS,
                style="terracotta", plant_kind="rose", plant_h=0.28, seed=fl * 31 + bi * 7,
            )
    for aac, zac in ((6.0, 11.5), (18.5, 14.9), (28.0, 18.3)):
        acx = ba[0] + btx * aac + bnx * 0.18
        acy = ba[1] + bty * aac + bny * 0.18
        add_ac_unit(wb3, acx, acy, zac, byaw, mats)
    # Rooftop stair/elevator penthouse on B-Wing
    add_rooftop_penthouse(wb3, -24.5, 70.5, 0.80 + 6 * 3.45 + 0.25, 5.2, 4.4, 2.35, byaw, mats, UV_CONSTS, wall_uv_key="UV_STUCCO")

    # East gable vertical calligraphy ("北京市第一六六中学（原贝满女中、女十二中）") south of W-ST1
    wb3.quad_enu(mats["stage"], (-6.02, 74.15, 6.2), (-7.52, 77.25, 6.2), (-7.52, 77.25, 19.8), (-6.02, 74.15, 19.8), UV_B_WALL_SIGN, 0.92, 1.0)
    # South-east facing red "B 教学楼" open-book plaque
    wb3.quad_enu(mats["stage"], (-30.68, 59.82, 16.5), (-27.71, 61.35, 16.5), (-27.71, 61.35, 20.4), (-30.68, 59.82, 20.4), UV_BOOK_B, 0.95, 1.0)
    # North-northwest facing red "B 教学楼" open-book plaque facing the playground (Photo 4!)
    wb3_n_dx, wb3_n_dy = -37.5 - (-11.5), 68.4 - 84.5
    wb3_n_len = math.hypot(wb3_n_dx, wb3_n_dy)
    wb3_ntx, wb3_nty = wb3_n_dx / wb3_n_len, wb3_n_dy / wb3_n_len
    wb3_nnx, wb3_nny = wb3_nty, -wb3_ntx  # outward NNW normal (-0.526, +0.850)
    wb3_n_yaw = math.atan2(wb3_nny, wb3_nnx) - math.pi * 0.5
    p_nb0 = (-11.5 + wb3_ntx * 13.6 + wb3_nnx * 0.14, 84.5 + wb3_nty * 13.6 + wb3_nny * 0.14)
    p_nb1 = (-11.5 + wb3_ntx * 16.9 + wb3_nnx * 0.14, 84.5 + wb3_nty * 16.9 + wb3_nny * 0.14)
    wb3.quad_enu(mats["stage"], (p_nb0[0], p_nb0[1], 17.2), (p_nb1[0], p_nb1[1], 17.2), (p_nb1[0], p_nb1[1], 20.9), (p_nb0[0], p_nb0[1], 20.9), UV_BOOK_B, 0.95, 1.0)
    # Ground-floor North-facing classroom/corridor double doors (physical glass + aluminum frames + granite threshold + mini eaves)
    for door_along in (10.5, 21.8):
        nd_c = (-11.5 + wb3_ntx * door_along + wb3_nnx * 0.10, 84.5 + wb3_nty * door_along + wb3_nny * 0.10)
        nd_yaw = math.atan2(-wb3_nnx, wb3_nny)
        add_building_entrance_portal(wb3, nd_c[0], nd_c[1], 0.03, nd_yaw, mats, UV_CONSTS, width=2.85, steps=1)
    add_parked_bicycle_row(
        wb3,
        -15.2 + wb3_nnx * 0.95, 82.2 + wb3_nny * 0.95,
        13, wb3_ntx * 1.55, wb3_nty * 1.55,
        wb3_n_yaw, mats, z_base=0.032,
    )
    # Split AC outdoor units on B座 south & north walls
    for ac_along, ac_st in [(6.2, 1), (6.2, 2), (15.0, 2), (15.0, 3), (24.2, 1), (24.2, 4)]:
        ac_p = (-11.5 + wb3_ntx * ac_along + wb3_nnx * 0.20, 84.5 + wb3_nty * ac_along + wb3_nny * 0.20)
        add_ac_unit(wb3, ac_p[0], ac_p[1], 0.95 + ac_st * 3.45, wb3_n_yaw, mats)

    # Ground-floor SSE courtyard entrance portal on bay bi=3 (facing South-Southeast lawn)
    wb3_ax, wb3_ay = -35.5, 57.5
    wb3_dx, wb3_dy = 29.7, 15.3
    wb3_len = math.hypot(wb3_dx, wb3_dy)
    wb3_tx, wb3_ty = wb3_dx / wb3_len, wb3_dy / wb3_len
    wb3_nx, wb3_ny = wb3_ty, -wb3_tx  # outward SSE normal
    wb3_yaw = math.atan2(wb3_dy, wb3_dx)
    wb3_along_c = 3.5 * (wb3_len / 9.0)

    def wb3_dpt(along_d: float, out_d: float) -> Vec2:
        a = wb3_along_c + along_d
        return (wb3_ax + wb3_tx * a + wb3_nx * out_d, wb3_ay + wb3_ty * a + wb3_ny * out_d)

    for s_along, s_st in [(22.5, 1), (22.5, 2), (26.2, 1), (26.2, 2), (26.2, 3)]:
        sap = (wb3_ax + wb3_tx * s_along + wb3_nx * 0.20, wb3_ay + wb3_ty * s_along + wb3_ny * 0.20)
        add_ac_unit(wb3, sap[0], sap[1], 0.95 + s_st * 3.45, wb3_yaw - math.pi * 0.5, mats)

    # Granite entry step + protruding marble portal frame (covers 1F window opening up to z=3.95)
    st_c = wb3_dpt(0.0, 0.52)
    wb3.add_box(mats["gates"], st_c[0], st_c[1], 0.0, 3.70, 1.04, 0.14, wb3_yaw, UV_MARBLE, ao_bot=0.76, ao_top=0.95, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for jamb_s in (-1.48, 1.48):
        jc = wb3_dpt(jamb_s, 0.16)
        wb3.add_box(mats["gates"], jc[0], jc[1], 0.14, 0.48, 0.36, 3.81, wb3_yaw, UV_MARBLE, ao_bot=0.78, ao_top=0.96, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    hc = wb3_dpt(0.0, 0.16)
    wb3.add_box(mats["surf"], hc[0], hc[1], 3.05, 3.44, 0.36, 0.90, wb3_yaw, UV_STUCCO, ao_bot=0.84, ao_top=0.96)
    # Recessed double aluminum-framed glass entrance doors + glazed transom
    dc_back = wb3_dpt(0.0, 0.08)
    wb3.add_box(mats["dark_steel"], dc_back[0], dc_back[1], 0.14, 2.52, 0.24, 2.92, wb3_yaw, ao_bot=0.78, ao_top=0.94)
    p_dl0, p_dl1 = wb3_dpt(-1.18, 0.21), wb3_dpt(1.18, 0.21)
    wb3.quad_enu(mats["glass"], (p_dl0[0], p_dl0[1], 0.22), (p_dl1[0], p_dl1[1], 0.22), (p_dl1[0], p_dl1[1], 2.42), (p_dl0[0], p_dl0[1], 2.42), UV_GLASS_WINDOW, 0.90, 1.0)
    wb3.quad_enu(mats["glass"], (p_dl0[0], p_dl0[1], 2.52), (p_dl1[0], p_dl1[1], 2.52), (p_dl1[0], p_dl1[1], 2.98), (p_dl0[0], p_dl0[1], 2.98), UV_GLASS_WINDOW, 0.90, 1.0)
    for mul_s, w_m, z0_m, z1_m in [(-1.22, 0.08, 0.14, 3.05), (0.0, 0.07, 0.14, 3.05), (1.22, 0.08, 0.14, 3.05), (-0.14, 0.04, 0.92, 1.42), (0.14, 0.04, 0.92, 1.42)]:
        mc = wb3_dpt(mul_s, 0.23)
        wb3.add_box(mats["white_alu"], mc[0], mc[1], z0_m, w_m, 0.06, z1_m - z0_m, wb3_yaw)
    mc_bar = wb3_dpt(0.0, 0.23)
    wb3.add_box(mats["white_alu"], mc_bar[0], mc_bar[1], 2.43, 2.52, 0.06, 0.08, wb3_yaw)
    # Cantilevered entrance canopy + 3D cylindrical steel tie rods
    canc = wb3_dpt(0.0, 0.72)
    wb3.add_beveled_box(mats["white_alu"], canc[0], canc[1], 3.12, 3.90, 1.44, 0.18, wb3_yaw, bevel=0.02, ao_bot=0.86, ao_top=1.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for tie_s in (-1.65, 1.65):
        tw = wb3_dpt(tie_s, 0.20)
        tf = wb3_dpt(tie_s, 1.28)
        wb3.add_limb(mats["dark_steel"], (tw[0], tw[1], 3.86), (tf[0], tf[1], 3.30), 0.020, 0.020, segs=6)

    # ---- W-B2: 中部楼梯间枢纽 (6层 · 90°北凸灰横肋翼 + 空调外机 + 屋顶机房) ----
    wb2 = exp.add_node("W-B2")
    wb2_pts = [(-55.2, 77.1), (-46.8, 77.4), (-46.82, 68.2), (-46.8, 57.6), (-55.2, 58.0), (-55.22, 66.8)]
    wb2.add_detailed_building(
        wb2_pts, stories=6, story_h=3.60, plinth_h=0.82,
        wall_mat=mats["surf"], wall_uv=UV_GREY_RIB,
        band_mat=mats["surf"], band_uv=UV_GREY_RIB,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        solid_x_planes=[-55.2, -46.8],
        party_max_y_on_x={-55.2: 67.0, -46.8: 68.4},
        rail_mat=mats["dark_steel"],
        window_grille=True, grille_mat=mats["dark_steel"],
        bay_w=4.1,
        interior_mode="hallway",
    )
    # Split AC units along W-B2's exposed 90° East return wall (Photo 6 right side!)
    for st_ac in (1, 2, 3, 4):
        add_ac_unit(wb2, -46.62, 70.1, 0.92 + st_ac * 3.60, -math.pi * 0.5, mats)
    # Rooftop stair/elevator penthouse bulkhead (with steel door, vent louvers & exhaust cowls)
    add_rooftop_penthouse(wb2, -51.0, 71.8, 22.65, 6.8, 6.4, 2.55, 0.0, mats, UV_CONSTS, wall_uv_key="UV_GREY_RIB")
    # North ground-floor glazed doorway portal exiting onto south plaza (real glass, aluminum frame, steps & canopy)
    sconce_fn = None if classic_mode else add_wall_sconce
    add_building_entrance_portal(wb2, -51.0, 77.35, 0.025, 0.0, mats, UV_CONSTS, width=4.40, steps=2, light_records=west_lights, add_wall_sconce_fn=sconce_fn)
    # South 2F doorway exit connecting W-B2/W-B3 junction onto the curved stone ramp W-R1 (at z = 4.40m)
    add_building_entrance_portal(wb2, -45.0, 57.55, 4.40, math.pi, mats, UV_CONSTS, width=2.80, steps=0)

    # ---- W-B1: C座教学实验楼 (6层 · 20m北立面 + 五层巨幅白色柱式人物浮雕 + 北/南 C座红牌 + 深色钢构屋顶架) ----
    wb1 = exp.add_node("W-B1")
    wb1_pts = [
        (-89.8, 76.2), (-69.8, 77.2), (-69.5, 66.8), (-55.2, 66.8),
        (-55.2, 58.0), (-68.2, 58.0), (-68.2, 34.2), (-79.9, 34.0),
        (-81.0, 49.8), (-87.8, 53.5),
    ]
    wb1.add_detailed_building(
        wb1_pts, stories=6, story_h=3.80, plinth_h=0.85,
        wall_mat=mats["surf"], wall_uv=UV_GREY_RIB,
        band_mat=mats["surf"], band_uv=UV_GREY_RIB,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        solid_x_planes=[-55.2],
        rail_mat=mats["dark_steel"],
        window_grille=True, grille_mat=mats["dark_steel"],
        bay_w=6.2,
    )
    # Hero 5-Story White Classical Column & Portrait Bas-Relief Wall on C座 North Facade (with molded classical surround!)
    c_n_yaw = math.atan2(77.2 - 76.2, -69.8 - (-89.8))  # ~ +0.05 rad along (-89.8,76.2)->(-69.8,77.2)
    c_nnx, c_nny = -math.sin(c_n_yaw), math.cos(c_n_yaw)  # outward North normal (-0.05, +0.9988)
    rel_cx, rel_cy = -79.8 + c_nnx * 0.22, 76.7 + c_nny * 0.22
    wb1.add_beveled_box(mats["white_alu"], rel_cx, rel_cy, 1.10, 5.65, 0.44, 18.25, c_n_yaw, bevel=0.03, ao_bot=0.86, ao_top=0.99)
    # Classical projecting pedestal base & pediment cornice molding framing the 5-story relief
    wb1.add_beveled_box(mats["gates"], rel_cx + c_nnx * 0.08, rel_cy + c_nny * 0.08, 0.85, 6.05, 0.58, 0.32, c_n_yaw, UV_MARBLE, bevel=0.025)
    wb1.add_beveled_box(mats["gates"], rel_cx + c_nnx * 0.10, rel_cy + c_nny * 0.10, 19.32, 6.15, 0.62, 0.34, c_n_yaw, UV_MARBLE, bevel=0.025)
    cs_c, sn_c = math.cos(c_n_yaw), math.sin(c_n_yaw)
    for pil_dx in (-2.76, 2.76):
        wb1.add_box(mats["gates"], rel_cx + pil_dx * cs_c + c_nnx * 0.14, rel_cy + pil_dx * sn_c + c_nny * 0.14, 1.15, 0.28, 0.24, 18.18, c_n_yaw, UV_MARBLE)
    # Relief textured front face (looking South from playground: Left is East +2.74, Right is West -2.74)
    r_p0 = (rel_cx + 2.66 * cs_c + c_nnx * 0.24, rel_cy + 2.66 * sn_c + c_nny * 0.24)
    r_p1 = (rel_cx - 2.66 * cs_c + c_nnx * 0.24, rel_cy - 2.66 * sn_c + c_nny * 0.24)
    wb1.quad_enu(
        mats["details"],
        (r_p0[0], r_p0[1], 1.22), (r_p1[0], r_p1[1], 1.22),
        (r_p1[0], r_p1[1], 19.25), (r_p0[0], r_p0[1], 19.25),
        UV_C_WHITE_RELIEF, 0.94, 1.0,
    )
    # North-facing red "C 教学楼" plaque at 6F above the white relief (Photo 2!)
    c_s0 = (rel_cx - 0.15 * cs_c + c_nnx * 0.16, rel_cy - 0.15 * sn_c + c_nny * 0.16)
    c_s1 = (rel_cx - 3.15 * cs_c + c_nnx * 0.16, rel_cy - 3.15 * sn_c + c_nny * 0.16)
    wb1.quad_enu(mats["stage"], (c_s0[0], c_s0[1], 19.85), (c_s1[0], c_s1[1], 19.85), (c_s1[0], c_s1[1], 22.90), (c_s0[0], c_s0[1], 22.90), UV_BOOK_C, 0.96, 1.0)
    # Split AC outdoor units flanking the north facade windows (Photo 2!)
    for ac_dx in (-6.6, 6.6):
        for st_c_ac in range(6):
            acp = (rel_cx + ac_dx * cs_c + c_nnx * 0.04, rel_cy + ac_dx * sn_c + c_nny * 0.04)
            add_ac_unit(wb1, acp[0], acp[1], 1.05 + st_c_ac * 3.80, c_n_yaw, mats)
    # Rooftop Open Dark-Steel Pergola Frame + Secondary Louver Joists + Machine Bulkhead on C座 north block
    wb1_roof_z = 0.85 + 6 * 3.80 + 0.25
    for px_r in (-87.8, -82.4, -77.0, -71.6):
        for py_r in (60.6, 68.0, 75.2):
            wb1.add_box(mats["dark_steel"], px_r, py_r, wb1_roof_z, 0.26, 0.26, 1.65, c_n_yaw)
    for ly in (60.6, 64.3, 68.0, 71.6, 75.2):
        wb1.add_box(mats["dark_steel"], -79.7, ly, wb1_roof_z + 1.55, 17.0, 0.22, 0.26, c_n_yaw, ao_bot=0.86, ao_top=1.0)
    for lx in (-87.8, -82.4, -77.0, -71.6):
        wb1.add_box(mats["dark_steel"], lx, 67.9, wb1_roof_z + 1.55, 0.22, 15.0, 0.26, 0.0, ao_bot=0.86, ao_top=1.0)
    for sx_j in range(11):
        jx = -87.0 + sx_j * 1.46
        wb1.add_box(mats["dark_steel"], jx, 67.9, wb1_roof_z + 1.68, 0.08, 14.6, 0.12, 0.0)
    add_rooftop_penthouse(wb1, -74.0, 46.5, wb1_roof_z, 5.4, 5.0, 2.40, 0.0, mats, UV_CONSTS, wall_uv_key="UV_GREY_RIB")
    # C座 South-West Exterior Return Staircase (upgraded from solid blue box to real sloped flights + openwork safety grille!)
    wb1.add_box(mats["surf"], -82.6, 42.0, 0.0, 4.4, 9.6, 0.85, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.90)
    for cx_p in (-84.65, -80.55):
        for cy_p in (37.35, 46.65):
            wb1.add_box(mats["white_alu"], cx_p, cy_p, 0.85, 0.28, 0.28, 19.2, 0.0)
    for lvl in range(5):
        sz = 0.85 + lvl * 3.80
        zm = sz + 1.90
        zt = sz + 3.80
        # Floor & mid-landing slabs
        wb1.add_box(mats["white_alu"], -82.6, 38.4, sz, 4.1, 2.2, 0.24, 0.0)
        wb1.add_box(mats["white_alu"], -82.6, 45.6, zm, 4.1, 2.2, 0.24, 0.0)
        # Solid sloped concrete stair stringer beams & flights
        add_rect_beam(wb1, mats["surf"], (-83.55, 39.4, sz + 0.12), (-83.55, 44.6, zm + 0.12), 1.85, 0.22, UV_STUCCO)
        add_rect_beam(wb1, mats["surf"], (-81.65, 44.6, zm + 0.12), (-81.65, 39.4, zt + 0.12), 1.85, 0.22, UV_STUCCO)
        # Solid white sloped side balustrades
        add_rect_beam(wb1, mats["surf"], (-84.55, 39.4, sz + 0.65), (-84.55, 44.6, zm + 0.65), 0.16, 1.05, UV_STUCCO)
        wb1.add_box(mats["surf"], -82.6, 37.38, sz, 4.1, 0.16, 1.05, 0.0, UV_STUCCO)
        wb1.add_box(mats["surf"], -82.6, 46.62, zm, 4.1, 0.16, 1.05, 0.0, UV_STUCCO)
        # Openwork blue-grey vertical safety cage bars & top/mid horizontal rails (replaces opaque blue wall slabs!)
        for ly_i in range(13):
            ly_bar = 37.55 + ly_i * (8.90 / 12.0)
            wb1.add_box(mats["blue_steel"], -84.62, ly_bar, sz, 0.04, 0.04, 3.80, 0.0)
        for lx_i in range(7):
            lx_bar = -84.45 + lx_i * (3.70 / 6.0)
            wb1.add_box(mats["blue_steel"], lx_bar, 37.35, sz, 0.04, 0.04, 3.80, 0.0)
            wb1.add_box(mats["blue_steel"], lx_bar, 46.65, sz, 0.04, 0.04, 3.80, 0.0)
        wb1.add_box(mats["blue_steel"], -84.62, 42.0, zm, 0.05, 9.25, 0.05, 0.0)
    wb1.add_box(mats["white_alu"], -82.6, 42.0, 20.05, 4.5, 9.7, 0.26, 0.0)
    # Red "C 教学楼" book plaque on C座 south wing south wall
    wb1.quad_enu(mats["stage"], (-75.8, 33.86, 17.5), (-72.5, 33.91, 17.5), (-72.5, 33.91, 21.2), (-75.8, 33.86, 21.2), UV_BOOK_C, 0.95, 1.0)

    # ---- W-R1: 室外弧形无障碍大坡道 + 方案A全石质护栏 + 镂空石质花槽 + 大雪松 ----
    # Exits 2F of W-B2 (楼梯间) going south, curving smoothly down to ground z = 0.03m
    wr1 = exp.add_node("W-R1")
    ramp_pts: List[Vec3] = []
    segs_r = 28
    pA, pB, pC, pD = (-45.0, 57.5), (-43.5, 44.5), (-24.0, 41.5), (-9.5, 38.0)
    for k in range(segs_r + 1):
        t = k / segs_r
        mt = 1.0 - t
        e = mt**3 * pA[0] + 3 * mt**2 * t * pB[0] + 3 * mt * t**2 * pC[0] + t**3 * pD[0]
        n = mt**3 * pA[1] + 3 * mt**2 * t * pB[1] + 3 * mt * t**2 * pC[1] + t**3 * pD[1]
        h = 4.40 * (1.0 - t) + 0.03
        ramp_pts.append((e, n, h))

    add_stone_curved_ramp(wr1, ramp_pts, half_w=1.55, mats=mats, uv_consts=UV_CONSTS)
    # Hero Snow Cedar in NE concave pocket beside the ramp
    wr1.add_tree(-27.5, 50.5, "cedar", 14.5, mats["trunk"], mats["leaf"])

    # ---- W-B4: 南院 A 座综合楼与图书馆（圆弧鼓楼转角真凹窗 + 北向图书馆出入口 + 1层南门接建） ----
    wb4 = exp.add_node("W-B4")
    # Replace coarse faceted NE corner with a smooth 7-chord semicircular drum (center (-20.0, 31.7), R=6.5m)
    # Each chord is ~2.89m >= 2.8m so add_detailed_building creates genuine curved-array recessed windows, grilles & interiors!
    wb4_pts_smooth: List[Vec2] = [(-56.0, 25.5), (-30.0, 25.2), (-20.0, 25.2)]
    for ai in range(1, 7):
        ang = -math.pi * 0.5 + (math.pi * ai) / 7.0
        wb4_pts_smooth.append((-20.0 + 6.5 * math.cos(ang), 31.7 + 6.5 * math.sin(ang)))
    wb4_pts_smooth.extend([(-20.0, 38.2), (-56.0, 38.2)])
    wb4.add_detailed_building(
        wb4_pts_smooth, stories=3, story_h=3.6, plinth_h=0.85,
        wall_mat=mats["surf"], wall_uv=UV_GREY_RIB,
        band_mat=mats["surf"], band_uv=UV_TERRACOTTA_BRICK,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        window_grille=True, grille_mat=mats["dark_steel"],
        bay_w=2.85,
    )
    add_rooftop_penthouse(wb4, -42.0, 31.7, 0.85 + 3 * 3.6 + 0.25, 4.8, 4.2, 2.25, 0.0, mats, UV_CONSTS, wall_uv_key="UV_GREY_RIB")
    # North-facing 1F Library Entrance Portal on bay bi=3 (cx=-32.275, y=38.20, facing +Y North) + Tier-1 Library Interior
    lib_cx = -32.275
    if not classic_mode:
        add_hero_room_box(
            wb4, cx=lib_cx, cy=35.4, z_floor=0.16, w=7.2, d=4.8, h=3.15,
            mats=mats, light_key="int_light_warm1", glow_key="int_glow_warm1", furnish="library",
        )
        add_wall_sconce(wb4, lib_cx, 38.88, 3.10, mats, west_lights, color="#ffd8a4", intensity=12.0, distance=11.0)
    wb4.add_box(mats["gates"], lib_cx, 38.75, 0.0, 3.90, 1.10, 0.16, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wb4.add_box(mats["gates"], lib_cx, 39.30, 0.0, 4.10, 0.50, 0.08, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for lx_off in (-1.52, 1.52):
        wb4.add_box(mats["gates"], lib_cx + lx_off, 38.36, 0.16, 0.50, 0.40, 4.02, 0.0, UV_MARBLE, ao_bot=0.78, ao_top=0.96, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wb4.add_box(mats["surf"], lib_cx, 38.36, 3.06, 3.54, 0.40, 1.12, 0.0, UV_STUCCO, ao_bot=0.84, ao_top=0.96)
    wb4.add_box(mats["dark_steel"], lib_cx, 38.28, 0.16, 2.58, 0.26, 2.92, 0.0, ao_bot=0.78, ao_top=0.94)
    wb4.quad_enu(mats["glass_phys"], (lib_cx + 1.22, 38.43, 0.24), (lib_cx - 1.22, 38.43, 0.24), (lib_cx - 1.22, 38.43, 2.48), (lib_cx + 1.22, 38.43, 2.48))
    wb4.quad_enu(mats["glass_phys"], (lib_cx + 1.22, 38.43, 2.56), (lib_cx - 1.22, 38.43, 2.56), (lib_cx - 1.22, 38.43, 3.00), (lib_cx + 1.22, 38.43, 3.00))
    for mx_off, mw, mz0, mz1 in [(-1.24, 0.08, 0.16, 3.06), (0.0, 0.07, 0.16, 3.06), (1.24, 0.08, 0.16, 3.06), (-0.14, 0.04, 0.94, 1.46), (0.14, 0.04, 0.94, 1.46)]:
        wb4.add_box(mats["white_alu"], lib_cx + mx_off, 38.45, mz0, mw, 0.06, mz1 - mz0, 0.0)
    wb4.add_box(mats["white_alu"], lib_cx, 38.45, 2.48, 2.56, 0.06, 0.08, 0.0)
    # Library canopy + 3D cylindrical steel tie rods + flanking stone planters + "图书馆 / LIBRARY" signboard facing North
    wb4.add_beveled_box(mats["white_alu"], lib_cx, 38.92, 3.12, 3.90, 1.48, 0.18, 0.0, bevel=0.02, ao_bot=0.86, ao_top=1.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for tie_x in (lib_cx - 1.65, lib_cx + 1.65):
        wb4.add_limb(mats["dark_steel"], (tie_x, 38.42, 3.94), (tie_x, 39.48, 3.30), 0.020, 0.020, segs=6)
    for pl_dx in (-2.45, 2.45):
        add_planter_box(wb4, lib_cx + pl_dx, 38.85, 0.02, 0.72, 0.72, 0.48, 0.0, mats, UV_CONSTS, style="stone", plant_kind="hedge", plant_h=0.45, seed=int(abs(pl_dx * 10)))
    wb4.add_box(mats["dark_steel"], lib_cx, 38.58, 3.36, 2.75, 0.08, 0.86, 0.0, ao_bot=0.84, ao_top=0.98)
    wb4.quad_enu(mats["stage"], (lib_cx + 1.33, 38.63, 3.40), (lib_cx - 1.33, 38.63, 3.40), (lib_cx - 1.33, 38.63, 4.18), (lib_cx + 1.33, 38.63, 4.18), UV_LIBRARY_SIGN, 0.96, 1.0)
    # 1-story south entrance service annex behind West Gate guardhouse (with windows & east doorway)
    wb4.add_detailed_building(
        [(-10.9, 10.4), (-5.65, 10.4), (-5.65, 24.2), (-10.9, 24.2)],
        stories=1, story_h=2.95, plinth_h=0.55,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["dark_steel"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.32, add_rail=False, bay_w=3.4,
    )
    # East entry doorway, granite step, physical glass door & braced canopy facing main driveway
    wb4.add_box(mats["surf"], -5.41, 17.25, 0.0, 0.48, 1.56, 0.12, 0.0, UV_QINGZHUAN, ao_bot=0.78, ao_top=0.94, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wb4.add_box(mats["dark_steel"], -5.54, 17.25, 0.12, 0.14, 1.36, 2.25, 0.0, ao_bot=0.78, ao_top=0.95)
    wb4.quad_enu(mats["glass_phys"], (-5.46, 16.65, 0.18), (-5.46, 17.85, 0.18), (-5.46, 17.85, 2.26), (-5.46, 16.65, 2.26))
    wb4.add_limb(mats["white_alu"], (-5.42, 16.76, 0.94), (-5.42, 16.76, 1.32), 0.015, 0.015, segs=6)
    wb4.add_beveled_box(mats["dark_steel"], -5.16, 17.25, 2.45, 0.96, 1.68, 0.14, 0.0, bevel=0.015, ao_bot=0.84, ao_top=1.0)
    for ty_a in (16.55, 17.95):
        wb4.add_limb(mats["dark_steel"], (-5.60, ty_a, 2.98), (-4.78, ty_a, 2.55), 0.016, 0.016, segs=5)

    # ---- W-ST1: 东北外挂折返楼梯塔 & "尚美" 艺术浮雕壁 (实体厚白斜梯梁 + 蓝灰菱形防坠网 + 倾斜双头喇叭, west-stairway-2024.webp) ----
    wst1 = exp.add_node("W-ST1")
    wst1.add_beveled_box(mats["surf"], -6.8, 80.5, 0.0, 5.45, 5.45, 1.05, 0.0, UV_QINGZHUAN, bevel=0.025, ao_bot=0.72, ao_top=0.92, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for pi_st in ((-9.25, 78.05), (-4.35, 78.05), (-9.25, 82.95), (-4.35, 82.95)):
        wst1.add_box(mats["white_alu"], pi_st[0], pi_st[1], 1.05, 0.36, 0.36, 18.6, 0.0)
    for lvl in range(5):
        z0 = 1.05 + lvl * 3.55
        zm = z0 + 1.77
        zt = z0 + 3.55
        # Landing slabs & solid white horizontal landing parapets (with real coping thickness)
        wst1.add_box(mats["white_alu"], -6.8, 79.1, z0, 4.9, 2.0, 0.24, 0.0)
        wst1.add_box(mats["white_alu"], -6.8, 81.9, zm, 4.9, 2.0, 0.24, 0.0)
        wst1.add_box(mats["surf"], -6.8, 78.02, z0, 5.05, 0.20, 1.08, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.99)
        wst1.add_box(mats["surf"], -6.8, 82.98, zm, 5.05, 0.20, 1.08, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.99)
        # Solid 3D thick white concrete sloped Z-shaped stair stringer balustrades & stepped flights (NO paper quads!)
        add_rect_beam(wst1, mats["surf"], (-9.32, 78.8, z0 + 0.52), (-9.32, 82.2, zm + 0.52), 0.18, 1.05, UV_STUCCO, ao_bot=0.88, ao_top=0.99)
        add_rect_beam(wst1, mats["surf"], (-4.28, 82.2, zm + 0.52), (-4.28, 78.8, zt + 0.52), 0.18, 1.05, UV_STUCCO, ao_bot=0.88, ao_top=0.99)
        add_rect_beam(wst1, mats["surf"], (-4.60, 83.02, zm + 0.52), (-9.00, 83.02, z0 + 0.96), 0.18, 1.04, UV_STUCCO, ao_bot=0.88, ao_top=0.99)
        # Inner sloped concrete stair slabs visible through the blue-grey cage
        add_rect_beam(wst1, mats["white_alu"], (-8.10, 79.2, z0 + 0.12), (-8.10, 81.8, zm + 0.12), 1.95, 0.20)
        add_rect_beam(wst1, mats["white_alu"], (-5.50, 81.8, zm + 0.12), (-5.50, 79.2, zt + 0.12), 1.95, 0.20)
        # Dense blue-grey vertical safety cage bars + iconic diagonal chevron struts & yellow diamond accents (west-stairway-2024.webp!)
        for bx_o in (-2.54, 2.54):
            for li in range(11):
                ly = 78.15 + li * 0.47
                wst1.add_box(mats["blue_steel"], -6.8 + bx_o, ly, z0, 0.038, 0.042, 3.55, 0.0)
            wst1.add_limb(mats["blue_steel"], (-6.8 + bx_o, 78.2, z0 + 1.2), (-6.8 + bx_o, 80.5, z0 + 2.4), 0.024, 0.024, segs=4)
            wst1.add_limb(mats["blue_steel"], (-6.8 + bx_o, 80.5, z0 + 2.4), (-6.8 + bx_o, 82.8, z0 + 1.2), 0.024, 0.024, segs=4)
        for by_o in (-2.54, 2.54):
            for li in range(11):
                lx = -9.15 + li * 0.47
                wst1.add_box(mats["blue_steel"], lx, 80.5 + by_o, z0, 0.042, 0.038, 3.55, 0.0)
            wst1.add_limb(mats["blue_steel"], (-9.1, 80.5 + by_o, z0 + 1.2), (-6.8, 80.5 + by_o, z0 + 2.4), 0.024, 0.024, segs=4)
            wst1.add_limb(mats["blue_steel"], (-6.8, 80.5 + by_o, z0 + 2.4), (-4.5, 80.5 + by_o, z0 + 1.2), 0.024, 0.024, segs=4)
            # Signature subtle yellow accent diamond tabs in the safety grille
            if lvl < 4:
                wst1.add_box(mats["yellow_pole"], -7.95, 80.5 + by_o, z0 + 1.75, 0.09, 0.045, 0.14, 0.0)
                wst1.add_box(mats["yellow_pole"], -5.65, 80.5 + by_o, z0 + 2.15, 0.09, 0.045, 0.14, 0.0)
    wst1.add_beveled_box(mats["white_alu"], -6.8, 80.5, 19.35, 5.45, 5.45, 0.34, 0.0, bevel=0.03)
    # Photo-accurate T-pole with Twin Downward-Tilted White Trapezoidal PA Speakers (west-stairway-2024.webp right!)
    wst1.add_smooth_cylinder(mats["blue_steel"], -7.8, 83.68, 0.0, 0.075, 0.062, 2.95, segs=10)
    add_rect_beam(wst1, mats["blue_steel"], (-8.38, 83.68, 2.82), (-7.22, 83.68, 2.82), 0.055, 0.055)
    for sp_dx in (-0.36, 0.36):
        # Tilted horn speaker housing angled forward & downward toward bike plaza
        add_rect_beam(wst1, mats["white_alu"], (-7.8 + sp_dx, 83.66, 2.74), (-7.8 + sp_dx, 83.98, 2.52), 0.28, 0.24)
        add_rect_beam(wst1, mats["dark_steel"], (-7.8 + sp_dx, 83.97, 2.53), (-7.8 + sp_dx, 84.01, 2.50), 0.24, 0.19)

    # 1-Story Covered Bike Pass-Through Building east of W-ST1 (spanning to East Campus Wall, y=75.20..83.40)
    west_room_pts = [
        (-6.97, 75.20), (-0.45, 75.20), (-0.45, 83.40),
        (-4.08, 83.40), (-4.08, 77.78), (-8.22, 77.78),
    ]
    wst1.add_polygon_slab(
        west_room_pts, 0.0, 3.44,
        mats["surf"], mats["surf"],
        UV_QINGZHUAN, UV_PLAZA_TILE,
        ao_bot=0.75, ao_top=0.94,
    )
    # South-facing glazed duty/service window on west bay (upgraded to physical transparent glass + 3D frame)
    wst1.add_box(mats["dark_steel"], -3.70, 75.18, 1.15, 2.80, 0.12, 1.50, 0.0, ao_bot=0.78, ao_top=0.94)
    wst1.add_box(mats["surf"], -3.70, 75.13, 1.07, 2.98, 0.18, 0.08, 0.0, UV_PLAZA_TILE)
    wst1.quad_enu(
        mats["glass_phys"],
        (-5.02, 75.12, 1.22), (-2.38, 75.12, 1.22),
        (-2.38, 75.12, 2.58), (-5.02, 75.12, 2.58),
    )
    wst1.add_box(mats["white_alu"], -3.70, 75.11, 1.20, 0.06, 0.06, 1.40, 0.0)
    wst1.add_box(mats["white_alu"], -3.70, 75.11, 2.22, 2.66, 0.06, 0.05, 0.0)
    # North-facing "尚美 · 美育浮雕" bronze relief on west bay north wall (west-stairway-2024.webp left!)
    wst1.add_beveled_box(mats["dark_steel"], -2.275, 83.42, 0.46, 3.40, 0.08, 2.62, 0.0, bevel=0.015)
    wst1.quad_enu(
        mats["stage"],
        (-0.65, 83.47, 0.52), (-3.90, 83.47, 0.52),
        (-3.90, 83.47, 2.98), (-0.65, 83.47, 2.98),
        UV_RELIEF_WALL, 0.92, 1.0,
    )
    # East Qingzhuan structural pier along East Campus Wall & hollow 1F bike tunnel (x = -0.45..+3.35, h = 3.02m)
    wst1.add_box(mats["surf"], 3.65, 79.30, 0.0, 0.60, 8.20, 3.44, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.94)
    wst1.add_box(mats["surf"], 1.45, 79.30, 3.02, 3.84, 8.20, 0.42, 0.0, UV_QINGZHUAN, ao_bot=0.84, ao_top=0.95)
    # Bright white ceiling soffit, light stucco upper tunnel walls, corner yellow-black bumper guards & dome lights
    wst1.add_box(mats["surf"], -0.43, 79.30, 1.05, 0.04, 8.08, 1.96, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.96)
    wst1.add_box(mats["surf"], 3.33, 79.30, 1.05, 0.04, 8.08, 1.96, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.96)
    wst1.add_box(mats["white_alu"], 1.45, 79.30, 2.99, 3.78, 8.12, 0.04, 0.0, ao_bot=0.92, ao_top=0.98)
    for bump_x in (-0.42, 3.32):
        for bump_y in (75.32, 83.28):
            wst1.add_box(mats["yellow_hatch"], bump_x, bump_y, 0.12, 0.09, 0.09, 0.85, 0.0)
    for cly in (77.3, 81.3):
        wst1.add_smooth_cylinder(mats["dark_steel"], 1.45, cly, 2.95, 0.28, 0.28, 0.04, segs=12)
        wst1.add_smooth_cylinder(mats["floodlight"], 1.45, cly, 2.92, 0.23, 0.21, 0.04, segs=12, ao_bot=0.98, ao_top=1.0)
    # Crisp white portal jambs & lintel frames on both South entrance (y=75.18) and North exit (y=83.42)
    for py_port in (75.18, 83.42):
        wst1.add_box(mats["white_alu"], -0.52, py_port, 0.03, 0.16, 0.14, 3.08, 0.0, ao_bot=0.82, ao_top=0.98)
        wst1.add_box(mats["white_alu"], 3.42, py_port, 0.03, 0.16, 0.14, 3.08, 0.0, ao_bot=0.82, ao_top=0.98)
        wst1.add_box(mats["white_alu"], 1.45, py_port, 2.97, 4.10, 0.16, 0.16, 0.0, ao_bot=0.88, ao_top=1.0)
    # Continuous 1-story flat roof & overhanging white moulded cornice (z = 3.44..3.66m)
    pass_roof_pts = [
        (-7.05, 75.06), (4.06, 75.06), (4.06, 83.54),
        (-4.06, 83.54), (-4.06, 77.74), (-8.30, 77.74),
    ]
    wst1.add_polygon_slab(
        pass_roof_pts, 3.44, 3.66,
        mats["white_alu"], mats["surf"],
        (0.1, 0.1, 0.9, 0.9), UV_PLAZA_TILE,
        ao_bot=0.90, ao_top=0.98,
    )

    # Ginkgo on the west side of the corner stair (校方供稿：转角楼梯一侧银杏)
    wst1.add_tree(-8.2, 86.0, "ginkgo", 9.2, mats["trunk"], mats["leaf"], mats["leaf_ginkgo"])

    # ---- W-MC: 音乐长廊（钢构采光骨架 + 石材柱墩 + 斜撑牛腿 + 牌楼立体门框 + 廊内条凳） ----
    wmc = exp.add_node("W-MC")
    # Archway / glazed entrance portal at south edge of track southwest plaza (y=76.25..81.45)
    portal_bays = [
        (81.45, -93.50, -89.15),
        (78.85, -93.42, -89.55),
        (76.25, -93.35, -89.95),
    ]
    for py, xw, xe in portal_bays:
        for col_x in (xw, xe):
            wmc.add_beveled_box(mats["surf"], col_x, py, 0.0, 0.42, 0.42, 0.34, 0.0, UV_PLAZA_TILE, bevel=0.02)
            wmc.add_box(mats["dark_steel"], col_x, py, 0.34, 0.24, 0.24, 4.31, 0.0)
        wmc.add_box(mats["dark_steel"], (xw + xe) * 0.5, py, 4.55, (xe - xw) + 0.44, 0.24, 0.24, 0.0)
        # Diagonal knee braces at column tops
        wmc.add_limb(mats["dark_steel"], (xw, py, 3.92), (xw + 0.65, py, 4.58), 0.032, 0.032, segs=5)
        wmc.add_limb(mats["dark_steel"], (xe, py, 3.92), (xe - 0.65, py, 4.58), 0.032, 0.032, segs=5)
    wmc.add_box(mats["dark_steel"], -93.42, 78.85, 4.55, 0.22, 5.45, 0.22, -math.atan2(-0.15, 5.20))
    wmc.add_box(mats["dark_steel"], -89.55, 78.85, 4.55, 0.22, 5.45, 0.22, -math.atan2(0.80, 5.20))
    # Aluminum skylight mullion ribs over portal
    for r_i in range(5):
        u_r = r_i / 4.0
        ry_p = 76.25 + u_r * 5.20
        rx_w = -93.35 - u_r * 0.15
        rx_e = -89.95 + u_r * 0.80
        add_rect_beam(wmc, mats["white_alu"], (rx_w, ry_p, 4.79), (rx_e, ry_p, 4.79), 0.07, 0.07)
    wmc.quad_enu(
        mats["skylight"],
        (-93.45, 76.25, 4.78),
        (-89.88, 76.25, 4.78),
        (-89.08, 81.45, 4.78),
        (-93.58, 81.45, 4.78),
        UV_SKYLIGHT, 0.96, 1.0, double_sided=True,
    )
    # 3D Framed North & South header boards ("音乐长廊 / MUSIC CORRIDOR") with cap moldings
    wmc.add_beveled_box(mats["dark_steel"], -91.325, 81.46, 3.82, 4.46, 0.14, 1.14, 0.0, bevel=0.015)
    wmc.quad_enu(mats["stage"], (-89.15, 81.55, 3.87), (-93.50, 81.55, 3.87), (-93.50, 81.55, 4.92), (-89.15, 81.55, 4.92), UV_MUSIC_SIGN, 0.95, 1.0)
    wmc.add_beveled_box(mats["dark_steel"], -91.65, 76.24, 3.82, 3.52, 0.14, 1.14, 0.0, bevel=0.015)
    wmc.quad_enu(mats["stage"], (-93.35, 76.15, 3.87), (-89.95, 76.15, 3.87), (-89.95, 76.15, 4.92), (-93.35, 76.15, 4.92), UV_MUSIC_SIGN, 0.95, 1.0)
    # Covered corridor extending south from archway along C-Wing west side (with stone plinths, skylight purlins & benches!)
    for pi in range(6):
        t = pi / 5.0
        py = 76.25 - t * 22.25
        xw = -93.35 + t * 1.95
        xe = -89.95 + t * 1.75
        for col_x in (xw, xe):
            wmc.add_beveled_box(mats["surf"], col_x, py, 0.0, 0.36, 0.36, 0.28, 0.0, UV_PLAZA_TILE, bevel=0.02)
            wmc.add_box(mats["dark_steel"], col_x, py, 0.28, 0.20, 0.20, 3.72, 0.0)
        wmc.add_box(mats["dark_steel"], (xw + xe) * 0.5, py, 3.94, (xe - xw) + 0.32, 0.18, 0.20, 0.0)
        wmc.add_limb(mats["dark_steel"], (xw, py, 3.45), (xw + 0.52, py, 3.96), 0.026, 0.026, segs=5)
        wmc.add_limb(mats["dark_steel"], (xe, py, 3.45), (xe - 0.52, py, 3.96), 0.026, 0.026, segs=5)
        if pi < 5:
            # Intermediate skylight mullion purlin + timber corridor bench along west edge
            tm = (pi + 0.5) / 5.0
            py_m = 76.25 - tm * 22.25
            xw_m = -93.35 + tm * 1.95
            xe_m = -89.95 + tm * 1.75
            add_rect_beam(wmc, mats["white_alu"], (xw_m, py_m, 4.15), (xe_m, py_m, 4.15), 0.06, 0.06)
            if pi % 2 == 0:
                bx_b = xw_m + 0.42
                wmc.add_box(mats["pbr_wood"], bx_b, py_m, 0.44, 0.46, 1.85, 0.06, 0.0)
                wmc.add_box(mats["dark_steel"], bx_b, py_m - 0.72, 0.02, 0.40, 0.08, 0.42, 0.0)
                wmc.add_box(mats["dark_steel"], bx_b, py_m + 0.72, 0.02, 0.40, 0.08, 0.42, 0.0)
    wmc.add_box(mats["dark_steel"], -92.375, 65.125, 3.94, 0.18, 22.35, 0.18, -math.atan2(-1.95, 22.25))
    wmc.add_box(mats["dark_steel"], -89.075, 65.125, 3.94, 0.18, 22.35, 0.18, -math.atan2(-1.75, 22.25))
    # Longitudinal center glass skylight ridge mullion
    add_rect_beam(wmc, mats["white_alu"], (-91.65, 76.25, 4.16), (-89.80, 54.00, 4.16), 0.065, 0.065)
    wmc.quad_enu(
        mats["skylight"],
        (-91.50, 54.00, 4.14),
        (-88.12, 54.00, 4.14),
        (-89.88, 76.25, 4.14),
        (-93.45, 76.25, 4.14),
        UV_SKYLIGHT, 0.94, 1.0, double_sided=True,
    )

    # ---- W-L2: 百草园内庭绿地（花岗岩园路路缘 + 飞檐起翘中式四角攒尖亭 + 镂空砌筑花坛与月季槽） ----
    wl2 = exp.add_node("W-L2")
    wl2.add_polygon_patch([(-67.2, 39.0), (-45.5, 39.0), (-45.5, 57.2), (-67.2, 57.2)], 0.04, mats["surf"], UV_GRASS, ao=0.94)
    # Granite perimeter curb separating Baicao Garden lawn from surrounding walkways
    add_stone_curb_polyline(wl2, [(-67.2, 39.0), (-57.6, 39.0)], 0.02, 0.18, 0.18, mats, UV_CONSTS)
    add_stone_curb_polyline(wl2, [(-55.2, 39.0), (-45.5, 39.0), (-45.5, 46.8)], 0.02, 0.18, 0.18, mats, UV_CONSTS)
    add_stone_curb_polyline(wl2, [(-45.5, 49.2), (-45.5, 57.2), (-55.2, 57.2)], 0.02, 0.18, 0.18, mats, UV_CONSTS)
    add_stone_curb_polyline(wl2, [(-57.6, 57.2), (-67.2, 57.2), (-67.2, 49.2)], 0.02, 0.18, 0.18, mats, UV_CONSTS)
    add_stone_curb_polyline(wl2, [(-67.2, 46.8), (-67.2, 39.0)], 0.02, 0.18, 0.18, mats, UV_CONSTS)
    # Stone garden cross paths & granite path edging curbs
    wl2.add_polygon_patch([(-66.8, 47.0), (-45.8, 47.0), (-45.8, 49.0), (-66.8, 49.0)], 0.06, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    wl2.add_polygon_patch([(-57.4, 39.2), (-55.4, 39.2), (-55.4, 57.0), (-57.4, 57.0)], 0.06, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    for px0, py0, px1, py1 in [
        (-66.8, 46.92, -58.6, 46.92), (-54.2, 46.92, -45.8, 46.92),
        (-66.8, 49.08, -58.6, 49.08), (-54.2, 49.08, -45.8, 49.08),
        (-57.48, 39.2, -57.48, 45.8), (-57.48, 50.2, -57.48, 57.0),
        (-55.32, 39.2, -55.32, 45.8), (-55.32, 50.2, -55.32, 57.0),
    ]:
        add_stone_curb_polyline(wl2, [(px0, py0), (px1, py1)], 0.04, 0.11, 0.12, mats, UV_CONSTS, wall_uv_key="UV_PLAZA_TILE")
    # Hollow circular brick flower bed with granite coping ring, dark soil & lush blooming roses
    add_hollow_round_planter(wl2, -56.4, 48.0, 0.05, r_out=2.25, height=0.34, mats=mats, uv_consts=UV_CONSTS, segs=16, plant_kind="rose", plant_h=0.58)
    # Authentic upturned flying-eave Chinese square pavilion (四角攒尖起翘灰瓦亭 + 美人靠 + 鼓形柱础 + 葫芦宝顶!)
    add_chinese_pavilion(wl2, -52.4, 43.2, z0=0.05, mats=mats, uv_consts=UV_CONSTS)
    # Hollow Qingzhuan masonry rose planters flanking the east-west garden path
    for r_idx, (rx, ry, rw, rd) in enumerate(((-63.4, 49.65, 3.6, 0.85), (-49.4, 49.65, 3.6, 0.85))):
        add_planter_box(wl2, rx, ry, 0.05, rw, rd, 0.36, 0.0, mats, UV_CONSTS, style="qingzhuan", plant_kind="rose", plant_h=0.55, seed=71 + r_idx * 13)
    # Species mix: 青松 / 银杏 / 柿树 / 玉兰
    wl2.add_tree(-61.5, 43.6, "pine", 8.5, mats["trunk"], mats["leaf_pine"])
    wl2.add_tree(-46.4, 38.2, "ginkgo", 7.4, mats["trunk"], mats["leaf"], mats["leaf_ginkgo"])
    wl2.add_tree(-63.0, 53.6, "persimmon", 7.8, mats["trunk"], mats["leaf_persimmon"], mats["fruit_orange"])
    wl2.add_tree(-48.2, 54.0, "magnolia", 7.2, mats["trunk"], mats["leaf_magnolia"], mats["flower_white"])

    # ---- W-P1: 北区 200m 环形塑胶操场 + 红绿双色篮球场 + 绿色桁架球架 + 排球网 + 道次号 ----
    wp1 = exp.add_node("W-P1")

    def rounded_rect_pts(x0: float, y0: float, x1: float, y1: float, rad: float, n_arc: int = 16) -> List[Vec2]:
        pts: List[Vec2] = []
        centers = [
            (x1 - rad, y0 + rad, -math.pi / 2, 0.0),
            (x1 - rad, y1 - rad, 0.0, math.pi / 2),
            (x0 + rad, y1 - rad, math.pi / 2, math.pi),
            (x0 + rad, y0 + rad, math.pi, 1.5 * math.pi),
        ]
        for ccx, ccy, a_s, a_e in centers:
            for k in range(n_arc + 1):
                a = a_s + (a_e - a_s) * k / n_arc
                pts.append((ccx + rad * math.cos(a), ccy + rad * math.sin(a)))
        return clean_ring(pts)

    # Full rectangular EPDM playground base (elevated +0.40m above south bicycle zone & cafeteria forecourt; clean 10-15mm Z stratification!)
    wp1.add_polygon_patch(
        [
            (-93.75, 90.40),
            (-13.50, 90.40),
            (-13.50, 120.30),
            (-9.20, 120.30),
            (-9.20, 124.80),
            (-93.75, 124.80),
        ],
        PG_Z + 0.050, mats["surf"], UV_TRACK_EPDM, ao=0.98,
    )
    # Inner slotted concrete drainage curb ring separating porous EPDM track from harder oval infield
    drain_pts = rounded_rect_pts(-88.20, 94.70, -18.40, 120.50, 12.90, n_arc=16)
    for i in range(len(drain_pts)):
        a, b = drain_pts[i], drain_pts[(i + 1) % len(drain_pts)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = max(math.hypot(dx, dy), 0.01)
        nx, ny = (dy / L) * 0.12, (-dx / L) * 0.12
        wp1.quad_enu(mats["surf"], (a[0] + nx, a[1] + ny, PG_Z + 0.084), (b[0] + nx, b[1] + ny, PG_Z + 0.084), (b[0] - nx, b[1] - ny, PG_Z + 0.084), (a[0] - nx, a[1] - ny, PG_Z + 0.084), UV_PLAZA_TILE, 0.88, 0.94)
    # 5 white oval lane boundary rings
    for lane_r in (12.90, 13.925, 14.95, 15.975, 17.00):
        inset = 17.00 - lane_r
        lane_pts = rounded_rect_pts(-92.30 + inset, 90.60 + inset, -14.30 - inset, 124.60 - inset, lane_r, n_arc=16)
        for i in range(len(lane_pts)):
            a, b = lane_pts[i], lane_pts[(i + 1) % len(lane_pts)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = max(math.hypot(dx, dy), 0.01)
            nx, ny = (dy / L) * 0.05, (-dx / L) * 0.05
            wp1.quad_enu(mats["white_alu"], (a[0] + nx, a[1] + ny, PG_Z + 0.088), (b[0] + nx, b[1] + ny, PG_Z + 0.088), (b[0] - nx, b[1] - ny, PG_Z + 0.088), (a[0] - nx, a[1] - ny, PG_Z + 0.088))
    # NE 50m sprint straightaway lane stripes & Start (x=-9.80) / Finish (x=-59.80) markings
    for ly in (120.50, 121.525, 122.55, 123.575, 124.60):
        wp1.quad_enu(mats["white_alu"], (-31.30, ly - 0.05, PG_Z + 0.098), (-9.50, ly - 0.05, PG_Z + 0.098), (-9.50, ly + 0.05, PG_Z + 0.098), (-31.30, ly + 0.05, PG_Z + 0.098))
    wp1.quad_enu(mats["white_alu"], (-9.86, 120.48, PG_Z + 0.106), (-9.74, 120.48, PG_Z + 0.106), (-9.74, 124.62, PG_Z + 0.106), (-9.86, 124.62, PG_Z + 0.106))
    wp1.quad_enu(mats["white_alu"], (-59.86, 120.48, PG_Z + 0.106), (-59.74, 120.48, PG_Z + 0.106), (-59.74, 124.62, PG_Z + 0.106), (-59.86, 124.62, PG_Z + 0.106))
    # Painted white track lane numbers "1" "2" "3" "4" on North straightaway & 50m sprint start
    for idx_ln, lane_mid_y in enumerate((121.01, 122.04, 123.06, 124.09)):
        uv_ln = UV_LANE_NUMS[idx_ln]
        for nx_pos in (-72.0, -10.8):
            wp1.quad_enu(
                mats["details_alpha"],
                (nx_pos + 0.48, lane_mid_y - 0.32, PG_Z + 0.114),
                (nx_pos + 0.48, lane_mid_y + 0.32, PG_Z + 0.114),
                (nx_pos - 0.48, lane_mid_y + 0.32, PG_Z + 0.114),
                (nx_pos - 0.48, lane_mid_y - 0.32, PG_Z + 0.114),
                uv_ln, 0.98, 1.0,
            )

    # Smooth harder acrylic/silicon-PU oval infield apron + 3 green/red basketball courts & 6 upgraded hoops
    wp1.add_polygon_patch(rounded_rect_pts(-88.08, 94.82, -18.52, 120.38, 12.78, n_arc=16), PG_Z + 0.070, mats["hard_court"], UV_HARD_COURT_APRON, ao=0.99)
    court_xs = [(-74.8, -61.8), (-59.8, -46.8), (-44.8, -31.8)]
    for cx0, cx1 in court_xs:
        cy0, cy1 = 96.1, 119.1
        cmid_x = (cx0 + cx1) * 0.5
        cmid_y = (cy0 + cy1) * 0.5
        wp1.add_polygon_patch([(cx0 - 0.5, cy0 - 0.45), (cx1 + 0.5, cy0 - 0.45), (cx1 + 0.5, cy1 + 0.45), (cx0 - 0.5, cy1 + 0.45)], PG_Z + 0.095, mats["surf"], UV_COURT_GREEN, ao=1.0)
        kw, kd = 2.40, 5.50
        wp1.add_polygon_patch([(cmid_x - kw, cy0), (cmid_x + kw, cy0), (cmid_x + kw, cy0 + kd), (cmid_x - kw, cy0 + kd)], PG_Z + 0.110, mats["hard_court"], UV_HARD_COURT_APRON, ao=0.99)
        wp1.add_polygon_patch([(cmid_x - kw, cy1 - kd), (cmid_x + kw, cy1 - kd), (cmid_x + kw, cy1), (cmid_x - kw, cy1)], PG_Z + 0.110, mats["hard_court"], UV_HARD_COURT_APRON, ao=0.99)
        c_jump_pts = [(cmid_x + 1.8 * math.cos(2 * math.pi * k / 16), cmid_y + 1.8 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
        wp1.add_polygon_patch(c_jump_pts, PG_Z + 0.110, mats["hard_court"], UV_HARD_COURT_APRON, ao=0.99)
        for x0, y0, x1, y1 in [
            (cx0, cy0, cx1, cy0 + 0.11),
            (cx0, cy1 - 0.11, cx1, cy1),
            (cx0, cy0, cx0 + 0.11, cy1),
            (cx1 - 0.11, cy0, cx1, cy1),
            (cx0, cmid_y - 0.055, cx1, cmid_y + 0.055),
            (cmid_x - kw, cy0, cmid_x - kw + 0.10, cy0 + kd),
            (cmid_x + kw - 0.10, cy0, cmid_x + kw, cy0 + kd),
            (cmid_x - kw, cy0 + kd - 0.10, cmid_x + kw, cy0 + kd),
            (cmid_x - kw, cy1 - kd, cmid_x - kw + 0.10, cy1),
            (cmid_x + kw - 0.10, cy1 - kd, cmid_x + kw, cy1),
            (cmid_x - kw, cy1 - kd, cmid_x + kw, cy1 - kd + 0.10),
        ]:
            wp1.quad_enu(mats["white_alu"], (x0, y0, PG_Z + 0.125), (x1, y0, PG_Z + 0.125), (x1, y1, PG_Z + 0.125), (x0, y1, PG_Z + 0.125))
        for k in range(16):
            a0 = 2 * math.pi * k / 16
            a1 = 2 * math.pi * (k + 1) / 16
            p0 = (cmid_x + 1.8 * math.cos(a0), cmid_y + 1.8 * math.sin(a0))
            p1 = (cmid_x + 1.8 * math.cos(a1), cmid_y + 1.8 * math.sin(a1))
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            ll = max(math.hypot(dx, dy), 0.01)
            nx, ny = (dy / ll) * 0.045, (-dx / ll) * 0.045
            wp1.quad_enu(mats["white_alu"], (p0[0] + nx, p0[1] + ny, PG_Z + 0.125), (p1[0] + nx, p1[1] + ny, PG_Z + 0.125), (p1[0] - nx, p1[1] - ny, PG_Z + 0.125), (p0[0] - nx, p0[1] - ny, PG_Z + 0.125))
        for end_y, dir_s in ((cy0 + 1.50, 1.0), (cy1 - 1.50, -1.0)):
            for k in range(12):
                a0 = 0.20 + (math.pi - 0.40) * (k / 12)
                a1 = 0.20 + (math.pi - 0.40) * ((k + 1) / 12)
                p0 = (cmid_x + 6.00 * math.cos(a0), end_y + dir_s * 6.00 * math.sin(a0))
                p1 = (cmid_x + 6.00 * math.cos(a1), end_y + dir_s * 6.00 * math.sin(a1))
                dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                ll = max(math.hypot(dx, dy), 0.01)
                nx, ny = (dy / ll) * 0.045, (-dx / ll) * 0.045
                wp1.quad_enu(mats["white_alu"], (p0[0] + nx, p0[1] + ny, PG_Z + 0.125), (p1[0] + nx, p1[1] + ny, PG_Z + 0.125), (p1[0] - nx, p1[1] - ny, PG_Z + 0.125), (p0[0] - nx, p0[1] - ny, PG_Z + 0.125))
        add_basketball_hoop_west(wp1, cmid_x, cy0 - 0.72, 0.0, mats, z_base=PG_Z + 0.06)
        add_basketball_hoop_west(wp1, cmid_x, cy1 + 0.72, math.pi, mats, z_base=PG_Z + 0.06)

    # Two North-South green volleyball courts tucked neatly inside West & East semicircular infield arcs (PR #18 + PG_Z!)
    for vx0, vx1 in ((-83.55, -76.15), (-30.45, -23.05)):
        vy0, vy1 = 100.20, 115.00
        vy_mid = (vy0 + vy1) * 0.5  # 107.60 (playground N-S midline)
        atk_off = 2.47  # proportional 3m attack line offset (7.4m x 14.8m court)
        wp1.add_polygon_patch(
            [(vx0 - 0.35, vy0 - 0.35), (vx1 + 0.35, vy0 - 0.35), (vx1 + 0.35, vy1 + 0.35), (vx0 - 0.35, vy1 + 0.35)],
            PG_Z + 0.095, mats["surf"], UV_COURT_GREEN, ao=1.0,
        )
        for x0, y0, x1, y1 in [
            (vx0, vy0, vx1, vy0 + 0.09),
            (vx0, vy1 - 0.09, vx1, vy1),
            (vx0, vy0, vx0 + 0.09, vy1),
            (vx1 - 0.09, vy0, vx1, vy1),
            (vx0, vy_mid - 0.045, vx1, vy_mid + 0.045),
            (vx0, vy_mid - atk_off - 0.04, vx1, vy_mid - atk_off + 0.04),
            (vx0, vy_mid + atk_off - 0.04, vx1, vy_mid + atk_off + 0.04),
        ]:
            wp1.quad_enu(mats["white_alu"], (x0, y0, PG_Z + 0.125), (x1, y0, PG_Z + 0.125), (x1, y1, PG_Z + 0.125), (x0, y1, PG_Z + 0.125))
        px_w, px_e = vx0 - 0.35, vx1 + 0.35
        for px_v in (px_w, px_e):
            wp1.add_smooth_cylinder(mats["hoop_pad"], px_v, vy_mid, PG_Z + 0.08, 0.068, 0.068, 1.40, segs=6)
            wp1.add_smooth_cylinder(mats["orange_hoop"], px_v, vy_mid, PG_Z + 0.08, 0.050, 0.046, 2.45, segs=6)
        add_rect_beam(wp1, mats["white_alu"], (px_w + 0.05, vy_mid, PG_Z + 2.43), (px_e - 0.05, vy_mid, PG_Z + 2.43), 0.022, 0.055)
        add_rect_beam(wp1, mats["white_alu"], (px_w + 0.05, vy_mid, PG_Z + 1.42), (px_e - 0.05, vy_mid, PG_Z + 1.42), 0.018, 0.038)
        wp1.quad_enu(
            mats["details_alpha"],
            (px_w + 0.05, vy_mid, PG_Z + 1.42), (px_e - 0.05, vy_mid, PG_Z + 1.42),
            (px_e - 0.05, vy_mid, PG_Z + 2.43), (px_w + 0.05, vy_mid, PG_Z + 2.43),
            UV_VOLLEY_NET, 0.96, 1.0, double_sided=True,
        )

    # Back-to-back connected twin hoops on N-S midline (y=107.60), facing North & South on BOTH West & East sides (PR #18 + PG_Z)
    add_double_basketball_hoop_west(wp1, -86.05, 107.60, 0.0, mats, z_base=PG_Z + 0.06)
    add_double_basketball_hoop_west(wp1, -20.55, 107.60, 0.0, mats, z_base=PG_Z + 0.06)

    # Two diagonal practice hoops on West side INSIDE the running track (NW facing SE, SW facing NE; East side has none)
    add_basketball_hoop_west(wp1, -82.27, 117.55, -3.0 * math.pi / 4.0, mats, z_base=PG_Z + 0.06)
    add_basketball_hoop_west(wp1, -82.27, 97.65, -math.pi / 4.0, mats, z_base=PG_Z + 0.06)

    # Signature leaning deciduous tree + hollow granite curb tree pit + 3D tubular metal ladder (on +0.40m terrace!)
    lt_x, lt_y = -22.0, 120.25
    add_planter_box(wp1, lt_x, lt_y, PG_Z + 0.04, 1.32, 1.22, 0.16, 0.0, mats, UV_CONSTS, style="stone", plant_kind="hedge", plant_h=0.0, seed=55)
    for ti_seg in range(5):
        z_b = PG_Z + ti_seg * 0.92
        z_t = PG_Z + (ti_seg + 1) * 0.92
        r_b = 0.31 - ti_seg * 0.025
        r_t = 0.31 - (ti_seg + 1) * 0.025
        ox_b, ox_t = ti_seg * 0.13, (ti_seg + 1) * 0.13
        wp1.add_limb(mats["trunk"], (lt_x + ox_b, lt_y, z_b), (lt_x + ox_t, lt_y, z_t), r_b, r_t, segs=8)
    wp1.add_tree(lt_x + 0.65, lt_y, "broad", 10.6, mats["trunk"], mats["leaf"], z_base=PG_Z)
    # 3D tubular steel ladder leaning against tree fork
    for lad_y in (lt_y - 0.18, lt_y + 0.18):
        wp1.add_limb(mats["dark_steel"], (lt_x + 1.55, lad_y, PG_Z + 0.08), (lt_x + 0.68, lad_y, PG_Z + 4.45), 0.018, 0.018, segs=6)
    for ri in range(11):
        rt = (ri + 0.5) / 11.0
        rx = (lt_x + 1.55) * (1.0 - rt) + (lt_x + 0.68) * rt
        rz = (PG_Z + 0.08) * (1.0 - rt) + (PG_Z + 4.45) * rt
        wp1.add_limb(mats["white_alu"], (rx, lt_y - 0.18, rz), (rx, lt_y + 0.18, rz), 0.013, 0.013, segs=5)

    # ---- W-P2: 北侧悬挑三跨拱形张拉膜主席台与升旗台（与操场齐平 +0.40m 无北落差 + 立体管桁架与微飘国旗） ----
    wp2 = exp.add_node("W-P2")
    st_cx, st_cy = -44.0, 128.5
    # Raised dark-slate stone podium deck with projecting granite coping rim
    wp2.add_box(
        mats["details"], st_cx, st_cy, PG_Z, 22.0, 6.0, 0.85, 0.0,
        UV_DARK_SLATE_PODIUM, ao_bot=0.74, ao_top=0.95,
        top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
    )
    wp2.add_beveled_box(mats["surf"], st_cx, st_cy, PG_Z + 0.82, 22.14, 6.14, 0.06, 0.0, UV_PLAZA_TILE, bevel=0.015, ao_bot=0.90, ao_top=1.0)
    # Left (West) & Right (East) side 3-step dark-slate staircases ONLY (no steps in front)
    for side_sign, x_edge in ((-1.0, -55.0), (1.0, -33.0)):
        for si, h_step in enumerate((0.64, 0.43, 0.22)):
            xc = x_edge + side_sign * (0.28 + si * 0.56)
            wp2.add_box(
                mats["details"], xc, 128.7, PG_Z, 0.56, 2.80, h_step, 0.0,
                UV_DARK_SLATE_PODIUM, ao_bot=0.76, ao_top=0.95,
                top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
            )
    # 3D Tubular Stainless steel deck guardrails & sloped stair handrails ONLY on West & East sides
    rail_st_mat = mats["stainless"] if "stainless" in mats else mats["white_alu"]
    for side_sign, x_rail, x_bot in ((-1.0, -54.92, -56.60), (1.0, -33.08, -31.40)):
        for y0_r, y1_r in ((125.58, 127.30), (130.10, 131.42)):
            wp2.add_limb(rail_st_mat, (x_rail, y0_r, PG_Z + 1.77), (x_rail, y1_r, PG_Z + 1.77), 0.024, 0.024, segs=6)
            wp2.add_limb(rail_st_mat, (x_rail, y0_r, PG_Z + 1.34), (x_rail, y1_r, PG_Z + 1.34), 0.018, 0.018, segs=6)
            for ry_post in (y0_r, (y0_r + y1_r) * 0.5, y1_r):
                wp2.add_smooth_cylinder(rail_st_mat, x_rail, ry_post, PG_Z + 0.85, 0.024, 0.024, 0.94, segs=6)
        for hy in (127.30, 130.10):
            wp2.add_smooth_cylinder(rail_st_mat, x_bot, hy, PG_Z + 0.22, 0.024, 0.024, 0.78, segs=6)
            wp2.add_smooth_cylinder(rail_st_mat, (x_rail + x_bot) * 0.5, hy, PG_Z + 0.43, 0.022, 0.022, 0.94, segs=6)
            wp2.add_limb(rail_st_mat, (x_rail, hy, PG_Z + 1.77), (x_bot, hy, PG_Z + 0.98), 0.024, 0.024, segs=6)
            wp2.add_limb(rail_st_mat, (x_rail, hy, PG_Z + 1.34), (x_bot, hy, PG_Z + 0.60), 0.018, 0.018, segs=6)
    # Unified beige stone backdrop wall with cornice cap, flush motto pilasters & crimson-framed LED
    wp2.add_box(
        mats["gates"], st_cx, 130.765, PG_Z + 0.85, 13.6, 0.83, 4.90, 0.0,
        UV_MARBLE, ao_bot=0.78, ao_top=0.96,
        top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
    )
    wp2.add_beveled_box(
        mats["gates"], st_cx, 130.755, PG_Z + 5.75, 14.08, 1.06, 0.24, 0.0,
        UV_MARBLE, bevel=0.025, ao_bot=0.84, ao_top=0.98,
        top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
    )
    wp2.add_box(mats["gates"], st_cx - 5.65, 130.33, PG_Z + 1.15, 1.65, 0.08, 4.30, 0.0, UV_MARBLE, ao_bot=0.82, ao_top=0.96)
    wp2.quad_enu(mats["stage"], (st_cx - 6.45, 130.28, PG_Z + 1.15), (st_cx - 4.85, 130.28, PG_Z + 1.15), (st_cx - 4.85, 130.28, PG_Z + 5.45), (st_cx - 6.45, 130.28, PG_Z + 5.45), UV_PILLAR_LEFT, 0.94, 1.0)
    wp2.add_box(mats["gates"], st_cx + 5.65, 130.33, PG_Z + 1.15, 1.65, 0.08, 4.30, 0.0, UV_MARBLE, ao_bot=0.82, ao_top=0.96)
    wp2.quad_enu(mats["stage"], (st_cx + 4.85, 130.28, PG_Z + 1.15), (st_cx + 6.45, 130.28, PG_Z + 1.15), (st_cx + 6.45, 130.28, PG_Z + 5.45), (st_cx + 4.85, 130.28, PG_Z + 5.45), UV_PILLAR_RIGHT, 0.94, 1.0)
    wp2.add_box(mats["gates"], st_cx, 130.31, PG_Z + 1.38, 8.70, 0.12, 3.94, 0.0, UV_BURGUNDY, ao_bot=0.82, ao_top=0.98)
    wp2.add_box(mats["dark_steel"], st_cx, 130.27, PG_Z + 1.52, 8.36, 0.08, 3.66, 0.0)
    wp2.quad_enu(mats["stage_led"], (st_cx - 4.10, 130.22, PG_Z + 1.58), (st_cx + 4.10, 130.22, PG_Z + 1.58), (st_cx + 4.10, 130.22, PG_Z + 5.12), (st_cx - 4.10, 130.22, PG_Z + 5.12), UV_STAGE_LED, 1.0, 1.0)
    # Ground-stacked 2-tier PA speakers below stage on West & East sides (south of side stairs, north of track; PR #18 + PG_Z)
    add_pa_speaker_stack(wp2, -55.90, 126.05, 0.08, mats, z_base=PG_Z + 0.02)
    add_pa_speaker_stack(wp2, -32.10, 126.05, -0.08, mats, z_base=PG_Z + 0.02)
    # Twin tall deciduous trees flanking East end of Chairman Stage (clear of East stairs & ground PA speaker, on +0.40m terrace)
    wp2.add_tree(-30.5, 127.8, "broad", 11.2, mats["trunk"], mats["leaf"], z_base=PG_Z)
    wp2.add_tree(-26.9, 126.8, "broad", 9.6, mats["trunk"], mats["leaf"], z_base=PG_Z)
    # 4 Rear structural steel masts + 3D box cantilevered valley ribs & tubular diagonal struts
    mast_xs = [-54.4, -47.47, -40.53, -33.6]
    for mx in mast_xs:
        wp2.add_smooth_cylinder(mats["dark_steel"], mx, 131.38, PG_Z, 0.19, 0.17, 6.22, segs=10, ao_bot=0.74, ao_top=0.96)
        add_rect_beam(wp2, mats["dark_steel"], (mx, 131.65, PG_Z + 5.93), (mx, 124.75, PG_Z + 6.19), 0.19, 0.19)
        wp2.add_limb(mats["dark_steel"], (mx, 131.38, PG_Z + 3.90), (mx, 128.25, PG_Z + 6.08), 0.065, 0.055, segs=8)
    # 3 Smooth double-curved tensile membrane arches + 3D tubular curved steel space-truss chords
    y_rear, y_front = 131.65, 124.75

    def stage_arch_z(t: float, y: float) -> float:
        s = (y_rear - y) / (y_rear - y_front)
        z_v = PG_Z + 6.02 + 0.28 * s + 0.10 * math.sin(math.pi * s)
        return z_v + 1.14 * math.sin(math.pi * t)

    for span in range(3):
        xA = -54.6 + span * 7.067
        xB = xA + 7.067
        n_seg = 16
        n_y = 6
        b_ten = wp2.bucket(mats["tensile"])
        for ai in range(n_seg):
            t0, t1 = ai / n_seg, (ai + 1) / n_seg
            x0, x1 = xA + (xB - xA) * t0, xA + (xB - xA) * t1
            for yi in range(n_y):
                ya = y_front + (y_rear - y_front) * (yi / n_y)
                yb = y_front + (y_rear - y_front) * ((yi + 1) / n_y)
                p00 = enu_to_gltf(x0, ya, stage_arch_z(t0, ya))
                p10 = enu_to_gltf(x1, ya, stage_arch_z(t1, ya))
                p11 = enu_to_gltf(x1, yb, stage_arch_z(t1, yb))
                p01 = enu_to_gltf(x0, yb, stage_arch_z(t0, yb))
                def _arch_n(tt: float) -> Vec3:
                    dzdx = (1.14 * math.pi * math.cos(math.pi * tt)) / 7.067
                    return vnorm((-dzdx, 1.0, 0.04))
                na, nb_v = _arch_n(t0), _arch_n(t1)
                b_ten.add_smooth_quad(
                    p00, p10, p11, p01, na, nb_v, nb_v, na,
                    [(t0, yi / n_y), (t1, yi / n_y), (t1, (yi + 1) / n_y), (t0, (yi + 1) / n_y)],
                    [(0.95, 0.95, 0.95), (0.95, 0.95, 0.95), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)],
                    double_sided=False,
                )
            for y_tr in (124.82, 128.22):
                zt0 = stage_arch_z(t0, y_tr) - 0.04
                zt1 = stage_arch_z(t1, y_tr) - 0.04
                zb0 = zt0 - 0.30 * math.sin(math.pi * t0) - 0.07
                zb1 = zt1 - 0.30 * math.sin(math.pi * t1) - 0.07
                wp2.add_limb(mats["dark_steel"], (x0, y_tr, zt0), (x1, y_tr, zt1), 0.036, 0.036, segs=6)
                wp2.add_limb(mats["dark_steel"], (x0, y_tr, zb0), (x1, y_tr, zb1), 0.032, 0.032, segs=6)
                if ai > 0 and ai % 2 == 0:
                    wp2.add_limb(mats["dark_steel"], (x0, y_tr, zb0), (x0, y_tr, zt0), 0.020, 0.020, segs=5)
                wp2.add_limb(mats["dark_steel"], (x0, y_tr, zb0), (x1, y_tr, zt1), 0.018, 0.018, segs=5)
        if not classic_mode:
            add_wall_sconce(wp2, (xA + xB) * 0.5, 128.2, PG_Z + 6.22, mats, west_lights, color="#ffe2b5", intensity=15.0, distance=15.0)
    # Flagpole & Multi-Segment Gently Waving Red Flag on Stepped Dark-Slate Terrace (West side of stage)
    fx, fy = -58.8, 126.4
    wp2.add_box(mats["details"], fx, fy, PG_Z, 2.75, 2.75, 0.22, 0.0, UV_DARK_SLATE_PODIUM, ao_bot=0.74, ao_top=0.94, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wp2.add_box(mats["details"], fx, fy, PG_Z + 0.22, 2.20, 2.20, 0.26, 0.0, UV_DARK_SLATE_PODIUM, ao_bot=0.78, ao_top=0.96, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for px_off in (-1.0, 1.0):
        for py_off in (-1.0, 1.0):
            wp2.add_smooth_cylinder(rail_st_mat, fx + px_off, fy + py_off, PG_Z + 0.48, 0.026, 0.026, 0.58, segs=6)
    wp2.add_limb(rail_st_mat, (fx - 1.0, fy - 1.0, PG_Z + 1.04), (fx + 1.0, fy - 1.0, PG_Z + 1.04), 0.022, 0.022, segs=6)
    wp2.add_limb(rail_st_mat, (fx - 1.0, fy + 1.0, PG_Z + 1.04), (fx + 1.0, fy + 1.0, PG_Z + 1.04), 0.022, 0.022, segs=6)
    wp2.add_limb(rail_st_mat, (fx - 1.0, fy - 1.0, PG_Z + 1.04), (fx - 1.0, fy + 1.0, PG_Z + 1.04), 0.022, 0.022, segs=6)
    wp2.add_limb(rail_st_mat, (fx + 1.0, fy - 1.0, PG_Z + 1.04), (fx + 1.0, fy + 1.0, PG_Z + 1.04), 0.022, 0.022, segs=6)
    wp2.add_smooth_cylinder(rail_st_mat, fx, fy, PG_Z + 0.48, 0.10, 0.045, 14.5, segs=12)
    wp2.add_sphere(mats["gold_trim"], fx, fy, PG_Z + 15.05, 0.10, 0.11, 0.10, segs=10, rings=5, ao=1.0)
    # 6-segment organically rippling fabric flag (replaces rigid flat board!)
    fu0, fv0, fu1, fv1 = UV_FLAG
    for fi in range(6):
        t0, t1 = fi / 6.0, (fi + 1) / 6.0
        x0_f, x1_f = fx + 0.06 + 2.42 * t0, fx + 0.06 + 2.42 * t1
        y0_f = fy - 0.16 * t0 + 0.12 * math.sin(t0 * math.pi * 2.2) * t0
        y1_f = fy - 0.16 * t1 + 0.12 * math.sin(t1 * math.pi * 2.2) * t1
        dz0 = -0.08 * t0 + 0.04 * math.sin(t0 * math.pi * 2.0)
        dz1 = -0.08 * t1 + 0.04 * math.sin(t1 * math.pi * 2.0)
        wp2.quad_enu(
            mats["gates"],
            (x0_f, y0_f, PG_Z + 13.15 + dz0), (x1_f, y1_f, PG_Z + 13.15 + dz1),
            (x1_f, y1_f, PG_Z + 14.75 + dz1), (x0_f, y0_f, PG_Z + 14.75 + dz0),
            (fu0 + (fu1 - fu0) * t0, fv0, fu0 + (fu1 - fu0) * t1, fv1),
            0.94, 1.0, double_sided=True,
        )

    # ---- W-B5: 高二平房区（+0.40m 北台地齐平 + 南向连续悬挑檐廊 + 规律教室门与落水管） ----
    wb5 = exp.add_node("W-B5")
    wb5_pts = [(-92.2, 136.8), (-6.8, 136.8), (-6.8, 142.1), (-92.2, 142.1)]
    wb5.add_detailed_building(
        wb5_pts, stories=1, story_h=3.15, plinth_h=0.50,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["warm_glass"], win_uv=(0.0, 0.0, 1.0, 1.0),
        mullion_mat=mats["dark_steel"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.45, add_rail=False, bay_w=3.6,
        ground_z=PG_Z,
        solid_x_planes=[-6.8],
        interior_mode="warm0",
    )
    # Rhythmic south-facing classroom doorways along the 85m veranda (with thresholds, steel frames, upper glazing & handles)
    for cd_x in (-67.5, -56.7, -45.9, -35.1, -24.3, -13.5):
        wb5.add_box(mats["surf"], cd_x, 136.58, PG_Z + 0.02, 1.48, 0.44, 0.10, 0.0, UV_PLAZA_TILE)
        wb5.add_box(mats["dark_steel"], cd_x, 136.75, PG_Z + 0.10, 1.24, 0.16, 2.28, 0.0)
        wb5.add_box(mats["white_alu"], cd_x, 136.68, PG_Z + 0.12, 1.12, 0.07, 1.15, 0.0)
        wb5.quad_enu(mats["glass_phys"], (cd_x - 0.50, 136.65, PG_Z + 1.28), (cd_x + 0.50, 136.65, PG_Z + 1.28), (cd_x + 0.50, 136.65, PG_Z + 2.30), (cd_x - 0.50, 136.65, PG_Z + 2.30))
        wb5.add_limb(mats["dark_steel"], (cd_x - 0.40, 136.62, PG_Z + 0.96), (cd_x - 0.40, 136.62, PG_Z + 1.24), 0.015, 0.015, segs=5)
    # Continuous straight south cantilevered eave from W-H1 north alley portal (x=-72.52) to NE annex gable (x=-6.8)
    wb5.add_box(mats["surf"], -39.66, 135.96, PG_Z + 3.25, 65.72, 1.72, 0.52, 0.0, UV_STUCCO, ao_bot=0.84, ao_top=0.98, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wb5.add_box(mats["wall_grey_render"], -39.66, 135.88, PG_Z + 3.74, 65.84, 1.92, 0.14, 0.0, ao_bot=0.88, ao_top=1.0)
    # Rainwater downspouts along veranda fascia
    for dsp_x in (-64.8, -43.2, -21.6, -7.2):
        wb5.add_smooth_cylinder(mats["white_alu"], dsp_x, 136.68, PG_Z + 0.06, 0.045, 0.045, 3.25, segs=6)
    # Warm veranda ceiling lights spaced evenly along the 65m north classroom veranda
    if not classic_mode:
        for vlx in (-66.0, -56.0, -44.0, -32.0, -22.0, -12.0):
            add_wall_sconce(wb5, vlx, 135.95, PG_Z + 3.22, mats, west_lights, color="#ffd89c", intensity=10.0, distance=11.0)
    for col_i in range(5):
        vc_x = -72.52 + col_i * 3.85
        col_h = 2.72 if col_i == 0 else 3.25
        wb5.add_box(mats["surf"], vc_x, 135.28, PG_Z, 0.34, 0.34, col_h, 0.0, UV_STUCCO, ao_bot=0.76, ao_top=0.94)
    wb5.add_cylinder(mats["floodlight"], -69.8, 135.95, PG_Z + 3.20, 0.22, 0.22, 0.05, 12, ao_bot=0.98, ao_top=1.0)
    wb5.add_box(mats["crimson"], -71.50, 136.66, PG_Z + 0.03, 0.72, 0.24, 0.62, 0.0, ao_bot=0.78, ao_top=0.96)
    wb5.quad_enu(
        mats["details"],
        (-71.84, 136.53, PG_Z + 0.05), (-71.16, 136.53, PG_Z + 0.05),
        (-71.16, 136.53, PG_Z + 0.63), (-71.84, 136.53, PG_Z + 0.63),
        UV_FIRE_BOX, 0.94, 1.0,
    )

    # ---- W-H1: 校史馆（D座 · +0.40m 北台地 + 厚檐立体硬山屋面 + 南廊朱红大门 + 镂空树池 + 圆柱训练杆） ----
    wh1 = exp.add_node("W-H1")
    for ti_p, (in_d, z_b, h_t) in enumerate([(0.0, PG_Z + 0.02, 0.14), (0.32, PG_Z + 0.16, 0.14), (0.64, PG_Z + 0.30, 0.14)]):
        wh1.add_box(
            mats["surf"], -81.0, 128.92 + in_d * 0.35, z_b,
            22.8 - in_d * 0.4, 8.78 - in_d * 0.7, h_t, 0.0,
            UV_PLAZA_TILE, ao_bot=0.74 + ti_p * 0.04, ao_top=0.94,
        )
    wh1_base_z = PG_Z + 0.44
    wh1_eave_z = PG_Z + 7.12
    wh1_mid_z = PG_Z + 3.78
    wh1.add_box(mats["surf"], -81.0, 129.79, wh1_base_z, 22.0, 6.82, wh1_eave_z - wh1_base_z, 0.0, UV_QINGZHUAN, ao_bot=0.75, ao_top=0.90)
    wh1.add_box(mats["white_alu"], -81.0, 129.15, wh1_mid_z - 0.09, 22.24, 8.26, 0.18, 0.0, ao_bot=0.88, ao_top=1.0)
    wh1.add_box(mats["surf"], -81.0, 125.75, wh1_mid_z - 0.12, 22.0, 1.30, 0.18, 0.0, UV_PLAZA_TILE, ao_bot=0.80, ao_top=0.94)
    wh1.add_box(mats["crimson"], -81.0, 125.22, wh1_eave_z - 0.32, 22.0, 0.32, 0.30, 0.0, ao_bot=0.82, ao_top=0.96)
    n_col_bays = 7
    bay_span_h1 = 21.48 / n_col_bays
    for ci in range(n_col_bays + 1):
        px = -91.74 + ci * bay_span_h1
        wh1.add_box(mats["surf"], px, 125.24, wh1_base_z, 0.52, 0.52, wh1_eave_z - wh1_base_z, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.94)
        wh1.add_box(mats["white_alu"], px, 125.24, wh1_mid_z - 0.24, 0.64, 0.64, 0.14, 0.0)
        wh1.add_box(mats["white_alu"], px, 125.24, wh1_eave_z - 0.44, 0.64, 0.64, 0.14, 0.0)
        if ci < n_col_bays:
            bx0 = px + 0.26
            bx1 = px + bay_span_h1 - 0.26
            b_mid = (bx0 + bx1) * 0.5
            b_w = bx1 - bx0
            # Bay ci==2 on 1F: traditional crimson double wooden entrance doors instead of a window!
            for is_1f_w, (st_z0, st_z1) in ((True, (wh1_base_z + 0.72, wh1_mid_z - 0.45)), (False, (wh1_mid_z + 0.75, wh1_eave_z - 0.55))):
                if is_1f_w and ci == 2:
                    wh1.add_box(mats["crimson"], b_mid, 126.32, wh1_base_z, 1.92, 0.14, 2.55, 0.0)
                    wh1.add_box(mats["pavilion_wood"], b_mid, 126.27, wh1_base_z + 0.06, 1.72, 0.07, 1.08, 0.0)
                    wh1.quad_enu(mats["glass_phys"], (b_mid - 0.80, 126.24, wh1_base_z + 1.18), (b_mid + 0.80, 126.24, wh1_base_z + 1.18), (b_mid + 0.80, 126.24, wh1_base_z + 2.46), (b_mid - 0.80, 126.24, wh1_base_z + 2.46))
                    wh1.add_box(mats["crimson"], b_mid, 126.23, wh1_base_z + 0.06, 0.07, 0.06, 2.44, 0.0)
                    for hx_d in (-0.12, 0.12):
                        wh1.add_limb(mats["gold_trim"], (b_mid + hx_d, 126.18, wh1_base_z + 0.96), (b_mid + hx_d, 126.18, wh1_base_z + 1.32), 0.014, 0.014, segs=5)
                    continue
                wh1.add_box(mats["crimson"], b_mid, 126.34, st_z0, b_w * 0.72, 0.10, st_z1 - st_z0, 0.0)
                if not classic_mode:
                    wh1.quad_enu(
                        mats["int_glow_warm1"],
                        (b_mid - b_w * 0.32, 126.42, st_z0 + 0.08),
                        (b_mid + b_w * 0.32, 126.42, st_z0 + 0.08),
                        (b_mid + b_w * 0.32, 126.42, st_z1 - 0.08),
                        (b_mid - b_w * 0.32, 126.42, st_z1 - 0.08),
                        (0.0, 0.0, 1.0, 1.0), 0.85, 1.0,
                    )
                    wh1.quad_enu(
                        mats["int_light_warm1"],
                        (b_mid - b_w * 0.22, 126.40, st_z1 - 0.24),
                        (b_mid + b_w * 0.22, 126.40, st_z1 - 0.24),
                        (b_mid + b_w * 0.22, 126.40, st_z1 - 0.12),
                        (b_mid - b_w * 0.22, 126.40, st_z1 - 0.12),
                        (0.0, 0.0, 1.0, 1.0), 1.0, 1.0,
                    )
                wh1.quad_enu(
                    mats["glass_phys"],
                    (b_mid - b_w * 0.33, 126.28, st_z0 + 0.08),
                    (b_mid + b_w * 0.33, 126.28, st_z0 + 0.08),
                    (b_mid + b_w * 0.33, 126.28, st_z1 - 0.08),
                    (b_mid - b_w * 0.33, 126.28, st_z1 - 0.08),
                )
                for m_off in (-b_w * 0.11, b_w * 0.11):
                    wh1.add_box(mats["crimson"], b_mid + m_off, 126.26, st_z0, 0.045, 0.06, st_z1 - st_z0, 0.0)
                wh1.add_box(mats["crimson"], b_mid, 126.26, (st_z0 + st_z1) * 0.5, b_w * 0.68, 0.06, 0.045, 0.0)
            if not classic_mode and ci in (1, 3, 5):
                add_wall_sconce(wh1, b_mid, 125.75, wh1_mid_z - 0.14, mats, west_lights, color="#ffd08a", intensity=10.0, distance=10.0)
                add_wall_sconce(wh1, b_mid, 125.75, wh1_eave_z - 0.26, mats, west_lights, color="#ffd08a", intensity=9.0, distance=10.0)
            for is_1f, rz_b in ((True, wh1_base_z), (False, wh1_mid_z + 0.06)):
                if is_1f and ci == 2:
                    continue
                wh1.add_box(mats["green_rail"], b_mid, 125.24, rz_b + 0.96, b_w, 0.06, 0.055, 0.0)
                wh1.add_box(mats["green_rail"], b_mid, 125.24, rz_b + 0.10, b_w, 0.05, 0.045, 0.0)
                for pk_i in range(9):
                    pk_x = bx0 + 0.12 + (b_w - 0.24) * (pk_i / 8.0)
                    wh1.add_box(mats["green_rail"], pk_x, 125.24, rz_b + 0.10, 0.032, 0.032, 0.88, 0.0)

    # 3. Overhanging traditional grey barrel-tile hard-gable roof with 3D fascia eaves, gable bargeboards & ridge trim
    wh1_ridge_z = PG_Z + 9.08
    wh1_ry_mid = 129.15
    q_u0, q_v0, q_u1, q_v1 = UV_QINGZHUAN
    q_um = (q_u0 + q_u1) * 0.5
    wh1.quad_enu(mats["surf"], (-92.55, 124.55, wh1_eave_z - 0.12), (-69.45, 124.55, wh1_eave_z - 0.12), (-69.45, wh1_ry_mid, wh1_ridge_z), (-92.55, wh1_ry_mid, wh1_ridge_z), UV_GREY_TILE, 0.88, 1.0, double_sided=True)
    wh1.quad_enu(mats["surf"], (-69.45, 133.75, wh1_eave_z - 0.12), (-92.55, 133.75, wh1_eave_z - 0.12), (-92.55, wh1_ry_mid, wh1_ridge_z), (-69.45, wh1_ry_mid, wh1_ridge_z), UV_GREY_TILE, 0.88, 1.0, double_sided=True)
    # 3D Eave fascia & gable verge bargeboards (博风板 / 垂脊)
    add_rect_beam(wh1, mats["crimson"], (-92.55, 124.55, wh1_eave_z - 0.16), (-69.45, 124.55, wh1_eave_z - 0.16), 0.10, 0.16)
    add_rect_beam(wh1, mats["dark_steel"], (-92.55, 133.75, wh1_eave_z - 0.16), (-69.45, 133.75, wh1_eave_z - 0.16), 0.10, 0.16)
    for gx_h in (-92.50, -69.50):
        add_rect_beam(wh1, mats["surf"], (gx_h, 124.55, wh1_eave_z - 0.08), (gx_h, wh1_ry_mid, wh1_ridge_z + 0.06), 0.16, 0.18, UV_GREY_TILE)
        add_rect_beam(wh1, mats["surf"], (gx_h, 133.75, wh1_eave_z - 0.08), (gx_h, wh1_ry_mid, wh1_ridge_z + 0.06), 0.16, 0.18, UV_GREY_TILE)
    wh1.tri_enu(mats["surf"], (-92.0, 133.20, wh1_eave_z), (-92.0, 125.10, wh1_eave_z), (-92.0, wh1_ry_mid, wh1_ridge_z), (q_u0, q_v1), (q_u1, q_v1), (q_um, q_v0), 0.86, 0.86, 0.96)
    wh1.tri_enu(mats["surf"], (-70.0, 125.10, wh1_eave_z), (-70.0, 133.20, wh1_eave_z), (-70.0, wh1_ry_mid, wh1_ridge_z), (q_u0, q_v1), (q_u1, q_v1), (q_um, q_v0), 0.86, 0.86, 0.96)
    wh1.add_box(mats["surf"], -81.0, wh1_ry_mid, wh1_ridge_z - 0.04, 23.25, 0.34, 0.24, 0.0, UV_GREY_TILE)
    wh1.add_box(mats["dark_steel"], -81.0, wh1_ry_mid, wh1_ridge_z + 0.18, 23.35, 0.18, 0.10, 0.0)
    wh1.quad_enu(mats["stage"], (-69.88, 127.6, PG_Z + 3.9), (-69.88, 130.4, PG_Z + 3.9), (-69.88, 130.4, PG_Z + 6.5), (-69.88, 127.6, PG_Z + 6.5), UV_BOOK_D, 0.95, 1.0)
    # West end hollow raised stone tree planter + twin tall deciduous trees (on +0.40m terrace!)
    add_planter_box(wh1, -92.3, 124.8, PG_Z + 0.02, 5.2, 2.9, 0.48, math.pi * 0.5, mats, UV_CONSTS, style="stone", plant_kind="hedge", plant_h=0.35, seed=83)
    wh1.add_tree(-91.8, 123.6, "broad", 11.4, mats["trunk"], mats["leaf"], z_base=PG_Z + 0.40)
    wh1.add_tree(-92.4, 126.2, "broad", 9.6, mats["trunk"], mats["leaf"], z_base=PG_Z + 0.40)

    # 4. North Facade Details & Semi-Open Skywell Courtyard Entrance (on +0.40m terrace!)
    for nwx in (-71.05, -74.55, -79.2, -83.8, -88.4):
        for nwz0, nwz1 in ((PG_Z + 1.38, PG_Z + 2.68), (PG_Z + 4.62, PG_Z + 5.92)):
            if nwx == -79.2 and nwz0 < PG_Z + 3.0:
                continue
            wh1.add_box(mats["crimson"], nwx, 133.22, nwz0, 1.08, 0.12, nwz1 - nwz0, 0.0)
            wh1.quad_enu(mats["glass_phys"], (nwx + 0.46, 133.29, nwz0 + 0.08), (nwx - 0.46, 133.29, nwz0 + 0.08), (nwx - 0.46, 133.29, nwz1 - 0.08), (nwx + 0.46, 133.29, nwz1 - 0.08))
            wh1.add_box(mats["surf"], nwx, 133.26, nwz0 - 0.09, 1.20, 0.16, 0.09, 0.0, UV_QINGZHUAN)
    for ac_hx, ac_hz in ((-70.65, PG_Z + 4.95), (-71.75, PG_Z + 4.78), (-73.45, PG_Z + 4.62), (-74.55, PG_Z + 4.48)):
        add_ac_unit(wh1, ac_hx, 133.38, ac_hz, 0.0, mats)
    # Cluster of upright 3D cylindrical yellow training/hurdle poles along 1F north wall
    for py_i in range(20):
        px_pole = -72.18 + (py_i % 10) * 0.21 + (0.07 if py_i >= 10 else 0.0)
        py_pole = 133.36 + (0.14 if py_i >= 10 else 0.0)
        tilt_x = ((py_i * 7) % 5 - 2) * 0.03
        wh1.add_smooth_cylinder(mats["yellow_pole"], px_pole, py_pole, PG_Z + 0.03, 0.07, 0.07, 0.03, segs=6)
        wh1.add_limb(mats["yellow_pole"], (px_pole, py_pole, PG_Z + 0.05), (px_pole + tilt_x, py_pole + 0.02, PG_Z + 1.36), 0.015, 0.015, segs=5)
    # Grey-brick flat-lintel portal frame spanning alley from W-H1 pilaster to W-B5 pier
    wh1.add_box(mats["surf"], -72.52, 133.48, PG_Z + 0.03, 0.62, 0.56, 3.16, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.95)
    wh1.add_box(mats["surf"], -72.52, 134.35, PG_Z + 2.72, 0.62, 2.35, 0.46, 0.0, UV_QINGZHUAN, ao_bot=0.84, ao_top=0.98, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wh1.add_box(mats["white_alu"], -72.52, 134.35, PG_Z + 2.68, 0.58, 1.72, 0.04, 0.0)
    # Semi-open skywell courtyard (x = -77.35..-72.52, y = 133.2..136.8)
    wh1.add_box(mats["white_alu"], -74.95, 136.32, PG_Z + 2.92, 4.86, 0.96, 0.24, 0.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wh1.add_box(mats["white_alu"], -76.85, 134.55, PG_Z + 2.92, 1.00, 2.70, 0.24, 0.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    pit_x, pit_y = -75.05, 134.55
    wh1.add_box(mats["surf"], pit_x, pit_y, PG_Z + 0.03, 2.25, 1.48, 0.14, 0.0, UV_PLAZA_TILE, ao_bot=0.78, ao_top=0.95, top_mat=mats["details"], top_uv=UV_WHITE_PEBBLES)
    wh1.add_tree(pit_x, pit_y, "broad", 10.4, mats["trunk"], mats["leaf"], z_base=PG_Z + 0.14)
    wh1.add_box(mats["crimson"], -73.08, 133.42, PG_Z + 0.03, 0.56, 0.22, 0.58, 0.0)
    wh1.quad_enu(mats["details"], (-72.80, 133.54, PG_Z + 0.05), (-73.36, 133.54, PG_Z + 0.05), (-73.36, 133.54, PG_Z + 0.59), (-72.80, 133.54, PG_Z + 0.59), UV_FIRE_BOX, 0.90, 0.98)
    for sb_i in range(6):
        sb_x = -73.68 - sb_i * 0.46
        wh1.add_box(mats["surf"], sb_x, 133.56, PG_Z + 0.03, 0.40, 0.42, 0.11, 0.0, UV_PLAZA_TILE)
        wh1.add_smooth_cylinder(mats["dark_steel"], sb_x, 133.56, PG_Z + 0.14, 0.03, 0.03, 0.36, segs=6)
    gx_ent = -77.35
    if not classic_mode:
        add_hero_room_box(
            wh1, cx=-79.45, cy=135.0, z_floor=PG_Z + 0.08, w=4.0, d=3.35, h=2.92,
            mats=mats, light_key="int_light_warm1", glow_key="int_glow_warm1", furnish="museum",
        )
        add_wall_sconce(wh1, -76.55, 134.55, PG_Z + 2.90, mats, west_lights, color="#ffd594", intensity=12.0, distance=10.0)
    wh1.add_box(mats["surf"], -79.45, 135.0, PG_Z + 3.04, 4.25, 3.62, 0.24, 0.0, UV_PLAZA_TILE, ao_bot=0.84, ao_top=0.98)
    wh1.add_box(mats["surf"], -81.52, 135.0, PG_Z + 0.03, 0.30, 3.62, 3.05, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.94)
    for gy_m in (133.26, 134.35, 135.65, 136.74):
        wh1.add_box(mats["dark_steel"], gx_ent, gy_m, PG_Z + 0.03, 0.08, 0.08, 3.02, 0.0)
    for gz_m in (0.06, 2.28, 3.00):
        wh1.add_box(mats["dark_steel"], gx_ent, 135.0, PG_Z + gz_m, 0.08, 3.56, 0.07, 0.0)
    wh1.quad_enu(
        mats["details_alpha"],
        (gx_ent + 0.02, 133.30, PG_Z + 0.08), (gx_ent + 0.02, 136.70, PG_Z + 0.08),
        (gx_ent + 0.02, 136.70, PG_Z + 2.98), (gx_ent + 0.02, 133.30, PG_Z + 2.98),
        UV_HISTORY_GLASS_DOOR, 0.94, 1.0, double_sided=True,
    )
    wh1.quad_enu(mats["stage"], (gx_ent + 0.06, 135.72, PG_Z + 1.95), (gx_ent + 0.06, 136.66, PG_Z + 1.95), (gx_ent + 0.06, 136.66, PG_Z + 2.34), (gx_ent + 0.06, 135.72, PG_Z + 2.34), UV_HISTORY_SIGN, 0.95, 1.0)

    # Persimmon outside the history museum (on +0.40m terrace!)
    wh1.add_tree(-68.6, 137.4, "persimmon", 7.6, mats["trunk"], mats["leaf_persimmon"], mats["fruit_orange"], z_base=PG_Z)

    # ---- W-B6: 学生食堂（操场东侧 1层圆拱顶建筑 + 真实大厅浅室内餐桌吊灯） ----
    wb6 = exp.add_node("W-B6")
    caf_cx, caf_cy, caf_w, caf_d = 0.2, 112.0, 11.6, 31.0
    caf_eave, caf_crown = 4.55, 6.35
    caf_hw, caf_hd = caf_w * 0.5, caf_d * 0.5
    # Tier-1 true 3D cafeteria dining hall interior (visible through transparent high-bay windows & glass vestibule in Enhanced)
    if not classic_mode:
        add_hero_room_box(
            wb6, cx=caf_cx, cy=caf_cy, z_floor=0.14, w=caf_w - 0.65, d=caf_d - 0.85, h=caf_eave - 0.22,
            mats=mats, light_key="int_light_warm0", glow_key="int_glow_warm0", furnish="cafeteria",
        )
    # Lower plinth + hollow wall piers framing transparent high-bay dining windows
    wb6.add_box(mats["surf"], caf_cx, caf_cy, 0.0, caf_w, caf_d, 1.15, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.90)
    # Upper spandrel lintel band above windows (z=3.85..4.55) + solid north/south end walls
    wb6.add_box(mats["surf"], caf_cx, caf_cy, 3.85, caf_w, caf_d, caf_eave - 3.85, 0.0, UV_STUCCO, ao_bot=0.86, ao_top=0.96)
    wb6.add_box(mats["surf"], caf_cx, caf_cy + caf_hd - 0.16, 1.15, caf_w, 0.32, 2.70, 0.0, UV_STUCCO, ao_bot=0.82, ao_top=0.96)
    wb6.add_box(mats["surf"], caf_cx - 3.9, caf_cy - caf_hd + 0.16, 1.15, 3.8, 0.32, 2.70, 0.0, UV_STUCCO, ao_bot=0.82, ao_top=0.96)
    wb6.add_box(mats["surf"], caf_cx + 3.9, caf_cy - caf_hd + 0.16, 1.15, 3.8, 0.32, 2.70, 0.0, UV_STUCCO, ao_bot=0.82, ao_top=0.96)
    # West & East high-bay dining hall windows (physical transparent glass + 3D piers & mullions)
    for side in (-1.0, 1.0):
        x_w = caf_cx + side * (caf_hw - 0.08)
        # Corner & between-window structural piers so glass opens directly into the 3D dining hall
        pier_ys = [caf_cy - caf_hd + 1.25] + [(caf_cy - caf_hd + 2.5) + wi * 3.8 + 3.2 for wi in range(7)]
        for py_c in pier_ys:
            wb6.add_box(mats["surf"], x_w, py_c, 1.15, 0.32, 1.22, 2.70, 0.0, UV_STUCCO, ao_bot=0.82, ao_top=0.96)
        for wi in range(7):
            wy0 = (caf_cy - caf_hd + 2.5) + wi * 3.8
            wy1 = wy0 + 2.6
            if side < 0:
                wb6.quad_enu(mats["glass_phys"], (x_w - 0.04, wy1, 1.20), (x_w - 0.04, wy0, 1.20), (x_w - 0.04, wy0, 3.85), (x_w - 0.04, wy1, 3.85))
            else:
                wb6.quad_enu(mats["glass_phys"], (x_w + 0.04, wy0, 1.20), (x_w + 0.04, wy1, 1.20), (x_w + 0.04, wy1, 3.85), (x_w + 0.04, wy0, 3.85))
            wb6.add_box(mats["white_alu"], x_w, (wy0 + wy1) * 0.5, 1.18, 0.08, 2.62, 0.06, 0.0)
            wb6.add_box(mats["white_alu"], x_w, (wy0 + wy1) * 0.5, 3.05, 0.08, 2.62, 0.06, 0.0)
            wb6.add_box(mats["white_alu"], x_w, (wy0 + wy1) * 0.5, 1.20, 0.08, 0.06, 2.65, 0.0)
    # Warm dining hall window spill + south entrance canopy light
    if not classic_mode:
        add_wall_sconce(wb6, caf_cx, caf_cy - caf_hd - 0.55, 2.92, mats, west_lights, color="#ffd89e", intensity=15.0, distance=14.0)
        add_wall_sconce(wb6, -6.12, 121.8, 3.02, mats, west_lights, color="#ffd89e", intensity=14.0, distance=14.0)
    west_lights.append({
        "kind": "window_spill",
        "pos": [-6.6, 2.4, -112.0],
        "color": "#ffd496",
        "intensity": 14.0,
        "distance": 14.0,
    })
    # Barrel-vaulted arched roof with 3D curved gable trim ribs & radial fanlight aluminum mullions
    y_s, y_n = caf_cy - caf_hd - 0.3, caf_cy + caf_hd + 0.3
    arc_segs = 12
    arch_rise = caf_crown - caf_eave
    span_hw = caf_hw + 0.35
    for ai in range(arc_segs):
        a0 = math.pi * (1.0 - ai / arc_segs)
        a1 = math.pi * (1.0 - (ai + 1) / arc_segs)
        x0 = caf_cx + span_hw * math.cos(a0)
        z0 = caf_eave + arch_rise * math.sin(a0)
        x1 = caf_cx + span_hw * math.cos(a1)
        z1 = caf_eave + arch_rise * math.sin(a1)
        wb6.quad_enu(mats["surf"], (x0, y_s, z0), (x1, y_s, z1), (x1, y_n, z1), (x0, y_n, z0), UV_GREY_TILE, 0.88, 1.0, double_sided=True)
        # 3D arched metal fascia edge trims at South & North ends
        add_rect_beam(wb6, mats["dark_steel"], (x0, y_s, z0), (x1, y_s, z1), 0.14, 0.16, caps=False)
        add_rect_beam(wb6, mats["dark_steel"], (x0, y_n, z0), (x1, y_n, z1), 0.14, 0.16, caps=False)
        wb6.tri_enu(mats["glass_phys"], (caf_cx, y_s + 0.25, caf_eave), (x1 * 0.94 + caf_cx * 0.06, y_s + 0.25, z1 - 0.05), (x0 * 0.94 + caf_cx * 0.06, y_s + 0.25, z0 - 0.05), (0.5, 0.9), (0.8, 0.2), (0.2, 0.2), double_sided=True)
        if ai > 0 and ai % 2 == 0:
            wb6.add_limb(mats["white_alu"], (caf_cx, y_s + 0.23, caf_eave), (x0 * 0.95 + caf_cx * 0.05, y_s + 0.23, z0 - 0.04), 0.028, 0.028, segs=5)
        wb6.tri_enu(mats["surf"], (caf_cx, y_n - 0.25, caf_eave), (x0 * 0.96 + caf_cx * 0.04, y_n - 0.25, z0), (x1 * 0.96 + caf_cx * 0.04, y_n - 0.25, z1), (0.5, 0.8), (0.2, 0.2), (0.8, 0.2), double_sided=True)
    # South main entrance canopy with 3D steel tie rods, granite step, framed glass double doors & "学生食堂" sign
    wb6.add_box(mats["surf"], caf_cx, y_s - 0.15, 0.0, 5.2, 0.85, 0.12, 0.0, UV_PLAZA_TILE)
    wb6.add_beveled_box(mats["dark_steel"], caf_cx, y_s - 0.5, 2.95, 5.8, 1.45, 0.22, 0.0, bevel=0.02)
    for tx_c in (caf_cx - 2.35, caf_cx + 2.35):
        wb6.add_limb(mats["dark_steel"], (tx_c, y_s + 0.18, 3.85), (tx_c, y_s - 1.05, 3.12), 0.022, 0.022, segs=6)
    wb6.quad_enu(mats["glass_phys"], (caf_cx - 2.3, y_s + 0.22, 0.12), (caf_cx + 2.3, y_s + 0.22, 0.12), (caf_cx + 2.3, y_s + 0.22, 2.90), (caf_cx - 2.3, y_s + 0.22, 2.90))
    for mx_c in (-2.30, -1.15, 0.0, 1.15, 2.30):
        wb6.add_box(mats["white_alu"], caf_cx + mx_c, y_s + 0.20, 0.12, 0.07, 0.07, 2.78, 0.0)
    for hx_c in (-0.16, 0.16):
        wb6.add_limb(mats["stainless"] if "stainless" in mats else mats["white_alu"], (caf_cx + hx_c, y_s + 0.14, 0.92), (caf_cx + hx_c, y_s + 0.14, 1.42), 0.016, 0.016, segs=6)
    wb6.quad_enu(mats["stage"], (caf_cx - 2.6, y_s + 0.14, 3.25), (caf_cx + 2.2, y_s + 0.14, 3.25), (caf_cx + 2.2, y_s + 0.14, 4.50), (caf_cx - 2.6, y_s + 0.14, 4.50), UV_CAFETERIA_SIGN, 0.95, 1.0)
    # West playground-facing glazed entrance vestibule + granite steps + canopy & AC units
    wb6.add_box(mats["surf"], -6.40, 121.8, 0.02, 0.72, 4.20, 0.10, 0.0, UV_PLAZA_TILE)
    wb6.add_beveled_box(mats["white_alu"], -6.12, 121.8, 3.05, 1.12, 4.44, 0.28, 0.0, bevel=0.02, ao_bot=0.86, ao_top=1.0)
    wb6.add_box(mats["surf"], -5.82, 121.8, 2.92, 0.48, 3.90, 0.14, 0.0, UV_STUCCO, ao_bot=0.80, ao_top=0.96)
    wb6.quad_enu(
        mats["glass_phys"],
        (-6.08, 123.55, 0.12), (-6.08, 120.05, 0.12),
        (-6.08, 120.05, 2.92), (-6.08, 123.55, 2.92),
    )
    for wmy in (120.05, 121.15, 121.80, 122.45, 123.55):
        wb6.add_box(mats["white_alu"], -6.10, wmy, 0.08, 0.06, 0.07, 2.90, 0.0)
    wb6.add_box(mats["white_alu"], -6.10, 121.8, 2.32, 0.06, 3.55, 0.07, 0.0)
    wb6.quad_enu(mats["warm_glass"], (-5.66, 126.9, 1.05), (-5.66, 124.5, 1.05), (-5.66, 124.5, 2.75), (-5.66, 126.9, 2.75), (0.0, 0.0, 1.0, 1.0), 0.94, 1.0)
    add_ac_unit(wb6, -5.80, 119.1, 0.45, math.pi * 0.5, mats)
    add_ac_unit(wb6, -5.80, 115.6, 0.45, math.pi * 0.5, mats)
    add_ac_unit(wb6, -5.80, 115.6, 1.25, math.pi * 0.5, mats)

    # 1F Flat-Eaved Connecting Bay north of Cafeteria + West-Facing White Double-Leaf Small Door (aligned to +0.40m north terrace!)
    wb6.add_box(mats["surf"], 0.10, 129.95, 0.0, 11.80, 4.90, PG_Z + 0.85, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.90)
    wb6.add_box(mats["wall_grey_render"], 0.10, 129.95, PG_Z + 0.85, 11.80, 4.90, 2.62, 0.0, ao_bot=0.80, ao_top=0.95)
    wb6.add_beveled_box(mats["surf"], -0.02, 129.95, PG_Z + 3.45, 12.15, 5.05, 0.22, 0.0, UV_STUCCO, bevel=0.02, ao_bot=0.88, ao_top=1.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    # White double-leaf small door with molded door surround & mini rain hood facing West (-X) onto the +0.40m terrace!
    wb6.add_box(mats["surf"], -5.96, 131.35, PG_Z + 0.02, 0.38, 1.62, 0.08, 0.0, UV_PLAZA_TILE, ao_bot=0.78, ao_top=0.95)
    wb6.add_box(mats["white_alu"], -5.83, 131.35, PG_Z + 0.08, 0.12, 1.48, 2.18, 0.0, ao_bot=0.84, ao_top=0.99)
    wb6.add_beveled_box(mats["white_alu"], -6.04, 131.35, PG_Z + 2.28, 0.44, 1.72, 0.09, 0.0, bevel=0.015)
    for dy_pane in (130.98, 131.72):
        wb6.quad_enu(
            mats["warm_glass"],
            (-5.90, dy_pane + 0.24, PG_Z + 1.18), (-5.90, dy_pane - 0.24, PG_Z + 1.18),
            (-5.90, dy_pane - 0.24, PG_Z + 2.06), (-5.90, dy_pane + 0.24, PG_Z + 2.06),
            (0.0, 0.0, 1.0, 1.0), 0.94, 1.0,
        )
    wb6.add_box(mats["dark_steel"], -5.91, 131.35, PG_Z + 0.10, 0.04, 0.04, 2.10, 0.0)
    wb6.add_box(mats["dark_steel"], -5.92, 131.26, PG_Z + 0.98, 0.04, 0.03, 0.18, 0.0)
    wb6.add_box(mats["dark_steel"], -5.92, 131.44, PG_Z + 0.98, 0.04, 0.03, 0.18, 0.0)
    add_ac_unit(wb6, -6.00, 129.05, PG_Z + 0.32, math.pi * 0.5, mats)
    wb6.add_box(mats["white_alu"], -5.84, 129.15, PG_Z + 1.92, 0.10, 0.38, 0.48, 0.0)

    # 1F Qingzhuan Pitched-Gable School Building immediately north of Cafeteria (sits on +0.40m north terrace!)
    wb6.add_pitched_gable_building(
        cx=-0.4, cy_n=135.3, w=12.8, d=5.8, eave_h=3.45, ridge_h=1.65, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["warm_glass"], win_uv=(0.0, 0.0, 1.0, 1.0),
        wood_mat=mats["dark_steel"], stories=1, ridge_along_x=True,
        ground_z=PG_Z,
    )
    wb6.add_box(mats["surf"], -0.4, 135.3, 0.0, 12.95, 5.95, PG_Z, 0.0, UV_QINGZHUAN, ao_bot=0.70, ao_top=0.84)
    wb6.add_box(mats["surf"], -6.96, 133.55, PG_Z + 0.02, 0.34, 1.08, 0.08, 0.0, UV_PLAZA_TILE)
    wb6.add_box(mats["dark_steel"], -6.82, 133.55, PG_Z + 0.08, 0.09, 0.94, 2.12, 0.0, ao_bot=0.68, ao_top=0.86)
    wb6.add_tree(-8.2, 128.2, "broad", 10.6, mats["trunk"], mats["leaf"], z_base=PG_Z)

    # ---- Context_West: Photo-Detailed Surrounding Buildings Visible from Campus + Hutong Context ----
    ctx_w = exp.add_node("Context_West")

    # 1. NW Neighbor: 灯市口小学北楼 (way 479455921) — 4F warm ochre facade + black Juliet grilles + glowing barrel-vaulted glass roof (Photos 3 & 7!)
    dsk_n_pts = ways["479455921"]["pts"]
    ctx_w.add_detailed_building(
        dsk_n_pts, stories=4, story_h=3.65, plinth_h=0.80,
        wall_mat=mats["details"], wall_uv=UV_NEIGHBOR_OCHRE,
        band_mat=mats["details"], band_uv=UV_NEIGHBOR_OCHRE,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["crimson"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.65, add_rail=True, rail_mat=mats["dark_steel"],
        bay_w=4.4, window_grille=True, grille_mat=mats["dark_steel"],
        interior_mode="context",
    )
    # East gable chimney/flue shaft & stepped south-east triangular gable fin (Photos 3 & 7!)
    ctx_w.add_box(mats["crimson"], -94.42, 120.8, 0.0, 0.52, 0.65, 15.9, 0.0, ao_bot=0.72, ao_top=0.92)
    ctx_w.tri_enu(mats["details"], (-94.60, 104.33, 15.8), (-94.60, 108.2, 15.8), (-94.60, 105.6, 17.85), (0.05, 0.95), (0.22, 0.95), (0.12, 0.78), 0.90, 0.90, 0.98, double_sided=True)
    # Signature illuminated semicircular barrel-vaulted glass rooftop atrium (x = -132..-94.8, y = 105.5..121.0, Photo 7!)
    sun_x0, sun_x1 = -132.0, -94.85
    sun_cy, sun_hw, sun_z0, sun_rise = 113.25, 7.65, 15.95, 2.75
    sun_segs = 12
    for si in range(sun_segs):
        a0 = math.pi * (si / sun_segs)
        a1 = math.pi * ((si + 1) / sun_segs)
        y0_s = sun_cy - sun_hw * math.cos(a0)
        z0_s = sun_z0 + sun_rise * math.sin(a0)
        y1_s = sun_cy - sun_hw * math.cos(a1)
        z1_s = sun_z0 + sun_rise * math.sin(a1)
        ctx_w.quad_enu(mats["warm_glass"], (sun_x0, y0_s, z0_s), (sun_x1, y0_s, z0_s), (sun_x1, y1_s, z1_s), (sun_x0, y1_s, z1_s), (0.0, 0.0, 1.0, 1.0), 0.95, 1.0, double_sided=True)
        # East & West glazed semicircular end gables + smoothly tilted 3D arch mullion ribs (fixed staircase bug!)
        ctx_w.tri_enu(mats["warm_glass"], (sun_x1, sun_cy, sun_z0), (sun_x1, y0_s, z0_s), (sun_x1, y1_s, z1_s), (0.5, 0.9), (0.2, 0.2), (0.8, 0.2), 0.96, 1.0, 1.0, double_sided=True)
        add_rect_beam(ctx_w, mats["white_alu"], (sun_x1 + 0.04, y0_s, z0_s), (sun_x1 + 0.04, y1_s, z1_s), 0.09, 0.09, caps=False)
        if si > 0 and si % 3 == 0:
            ctx_w.add_limb(mats["white_alu"], (sun_x1 + 0.03, sun_cy, sun_z0), (sun_x1 + 0.03, y0_s, z0_s), 0.032, 0.032, segs=5)
    # White rooftop balustrade along East gable below glass arch (Photo 7!)
    ctx_w.add_box(mats["white_alu"], -94.70, sun_cy, sun_z0 + 0.72, 0.08, sun_hw * 1.96, 0.07, 0.0)
    for bal_i in range(15):
        by_b = (sun_cy - sun_hw * 0.95) + bal_i * (sun_hw * 1.90 / 14.0)
        ctx_w.add_box(mats["white_alu"], -94.70, by_b, sun_z0, 0.07, 0.07, 0.75, 0.0)
    # 4-story beige NE wing behind NW playground trees (visible in Photo 3 center background!)
    ctx_w.add_detailed_building(
        [(-116.0, 123.2), (-96.2, 123.2), (-96.2, 134.5), (-116.0, 134.5)],
        stories=4, story_h=3.40, plinth_h=0.65,
        wall_mat=mats["details"], wall_uv=UV_NEIGHBOR_OCHRE,
        band_mat=mats["surf"], band_uv=UV_STUCCO,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["warm_glass"], win_uv=(0.0, 0.0, 1.0, 1.0),
        mullion_mat=mats["dark_steel"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.55, add_rail=True, rail_mat=mats["dark_steel"], bay_w=4.2,
        interior_mode="context",
    )

    # 2. SW Neighbor: 灯市口小学南配楼 / 景山北邻教学楼 (way 398697588) — 2F cream wall w/ red diamonds + bright blue pitched roof (Photo 2 right!)
    dsk_s_pts = ways["398697588"]["pts"]
    ctx_w.add_detailed_building(
        dsk_s_pts, stories=2, story_h=3.95, plinth_h=0.65,
        wall_mat=mats["details"], wall_uv=UV_NEIGHBOR_DIAMOND,
        band_mat=mats["details"], band_uv=UV_NEIGHBOR_DIAMOND,
        roof_mat=mats["details"], roof_uv=UV_BLUE_TILE_ROOF,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.25, add_rail=False, bay_w=4.6,
        interior_mode="context",
    )
    # Overhanging bright cobalt-blue pitched hipped/gable tile roof over eastern main block (-167..-92, 30.2..63.4)
    br_x0, br_x1, br_y0, br_y1 = -167.4, -91.6, 29.8, 63.8
    br_ymid, br_z0, br_z1 = (br_y0 + br_y1) * 0.5, 8.75, 11.35
    ctx_w.quad_enu(mats["details"], (br_x0, br_y0, br_z0), (br_x1, br_y0, br_z0), (br_x1 - 5.0, br_ymid, br_z1), (br_x0 + 5.0, br_ymid, br_z1), UV_BLUE_TILE_ROOF, 0.90, 1.0, double_sided=True)
    ctx_w.quad_enu(mats["details"], (br_x1, br_y1, br_z0), (br_x0, br_y1, br_z0), (br_x0 + 5.0, br_ymid, br_z1), (br_x1 - 5.0, br_ymid, br_z1), UV_BLUE_TILE_ROOF, 0.90, 1.0, double_sided=True)
    ctx_w.tri_enu(mats["details"], (br_x1, br_y0, br_z0), (br_x1, br_y1, br_z0), (br_x1 - 5.0, br_ymid, br_z1), (0.53, 0.98), (0.74, 0.98), (0.63, 0.78), 0.90, 0.90, 1.0, double_sided=True)
    ctx_w.tri_enu(mats["details"], (br_x0, br_y1, br_z0), (br_x0, br_y0, br_z0), (br_x0 + 5.0, br_ymid, br_z1), (0.53, 0.98), (0.74, 0.98), (0.63, 0.78), 0.90, 0.90, 1.0, double_sided=True)

    # 3. NE External Hutong Courtyard Cluster (north 2F grey-brick building way 636389213 + east red-tile roofs outside x=6.0!)
    ctx_w.add_pitched_gable_building(
        cx=2.1, cy_n=142.4, w=18.6, d=6.8, eave_h=6.85, ridge_h=1.85, yaw_rad=0.03,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=2, ridge_along_x=True,
    )
    # East-boundary purple-red corrugated tile pitched-roof annexes outside school east wall (visible behind W-ST1 & Photo 1 skyline!)
    ctx_w.add_pitched_gable_building(
        cx=10.2, cy_n=86.5, w=8.2, d=14.5, eave_h=3.6, ridge_h=1.45, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        roof_mat=mats["surf"], roof_uv=UV_RED_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=1, ridge_along_x=False,
    )
    ctx_w.add_pitched_gable_building(
        cx=12.6, cy_n=133.2, w=10.8, d=8.2, eave_h=6.2, ridge_h=1.95, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_RED_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=2, ridge_along_x=True,
    )

    # 4. South Gate East Neighbor 5-Story White & Salmon Apartment Building (way 636389225 + north wing, west-gate-2024.webp right!)
    ctx_w.add_detailed_building(
        [(6.4, 4.2), (21.4, 4.0), (21.6, 28.5), (6.6, 28.5)],
        stories=5, story_h=2.95, plinth_h=0.65,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_STUCCO,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.55, add_rail=False, bay_w=3.8,
        window_grille=True, grille_mat=mats["gold_trim"],
        interior_mode="context",
    )
    # Salmon-pink corner bay with 3D framed windows + projecting Beijing residential security window cages (west-gate-2024.webp right!)
    ctx_w.add_box(mats["details"], 7.45, 5.65, 3.6, 2.5, 3.2, 11.8, 0.0, UV_SALMON_WALL, ao_bot=0.84, ao_top=0.98)
    for wy in (4.75, 6.55):
        for wz in (4.55, 7.10, 9.65, 12.20):
            ctx_w.quad_enu(
                mats["glass"],
                (6.18, wy - 0.52, wz), (6.18, wy + 0.52, wz),
                (6.18, wy + 0.52, wz + 1.55), (6.18, wy - 0.52, wz + 1.55),
                UV_GLASS_WINDOW, 0.92, 1.0, double_sided=True,
            )
            ctx_w.add_box(mats["white_alu"], 6.16, wy, wz - 0.06, 0.10, 1.18, 0.08, 0.0, ao_bot=0.90, ao_top=1.0)
            ctx_w.add_box(mats["white_alu"], 6.16, wy, wz + 1.55, 0.10, 1.18, 0.07, 0.0)
            # Projecting wrought-iron security window cage
            for cz_bar in (wz + 0.04, wz + 0.78, wz + 1.50):
                add_rect_beam(ctx_w, mats["gold_trim"], (5.92, wy - 0.56, cz_bar), (5.92, wy + 0.56, cz_bar), 0.024, 0.024, caps=False)
            for cy_bar in (wy - 0.54, wy - 0.18, wy + 0.18, wy + 0.54):
                add_rect_beam(ctx_w, mats["gold_trim"], (5.92, cy_bar, wz + 0.02), (5.92, cy_bar, wz + 1.52), 0.022, 0.022, caps=False)
    for wx in (6.95, 8.05):
        for wz in (4.55, 7.10, 9.65, 12.20):
            ctx_w.quad_enu(
                mats["glass"],
                (wx - 0.40, 4.03, wz), (wx + 0.40, 4.03, wz),
                (wx + 0.40, 4.03, wz + 1.55), (wx - 0.40, 4.03, wz + 1.55),
                UV_GLASS_WINDOW, 0.92, 1.0, double_sided=True,
            )
            ctx_w.add_box(mats["white_alu"], wx, 4.01, wz - 0.06, 0.96, 0.10, 0.08, 0.0, ao_bot=0.90, ao_top=1.0)
            for cz_bar in (wz + 0.04, wz + 1.50):
                add_rect_beam(ctx_w, mats["gold_trim"], (wx - 0.44, 3.80, cz_bar), (wx + 0.44, 3.80, cz_bar), 0.024, 0.024, caps=False)
            for cx_bar in (wx - 0.42, wx, wx + 0.42):
                add_rect_beam(ctx_w, mats["gold_trim"], (cx_bar, 3.80, wz + 0.02), (cx_bar, 3.80, wz + 1.52), 0.022, 0.022, caps=False)
    for st_e_ac in (1, 2, 3):
        add_ac_unit(ctx_w, 6.22, 9.8, 0.8 + st_e_ac * 2.95, math.pi * 0.5, mats)
    # Ground-floor alley courtyard wall & cream display cabinet east of gate
    ctx_w.add_box(mats["gates"], 5.8, 1.2, 0.0, 0.45, 6.8, 2.55, 0.0, UV_MARBLE, ao_bot=0.78, ao_top=0.96)

    # 5. East & South Residential Towers & Remaining Hutong Context (Photo 4 left skyline & Photo 7 west skyline!)
    # East 12-story light-grey stepped residential apartment tower (way 352521260, Photo 4 left skyline!)
    ctx_w.add_detailed_building(
        ways["352521260"]["pts"], stories=12, story_h=2.95, plinth_h=0.85,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_GREY_RIB,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.90, add_rail=False, bay_w=5.0, simple_recess=True,
        interior_mode="context",
    )
    # Closer East 7-story residential block (way 263035038) & South 5-story residential blocks (27号楼 263035030, 263035031)
    for res_wid, res_st in (("263035038", 7), ("352521261", 6), ("263035030", 5), ("263035031", 5)):
        ctx_w.add_detailed_building(
            ways[res_wid]["pts"], stories=res_st, story_h=2.95, plinth_h=0.65,
            wall_mat=mats["surf"], wall_uv=UV_STUCCO,
            band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
            roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
            win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
            mullion_mat=mats["white_alu"],
            plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
            parapet_h=0.60, add_rail=False, bay_w=4.8, simple_recess=True,
            interior_mode="context",
        )
    # Far-west Wangfujing / Capital Theatre modern mid-rises visible in Photo 7 left skyline
    ctx_w.add_detailed_building(
        [(-198.0, 74.0), (-168.0, 74.0), (-168.0, 102.0), (-198.0, 102.0)],
        stories=6, story_h=3.55, plinth_h=0.80,
        wall_mat=mats["surf"], wall_uv=UV_GREY_RIB,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["warm_glass"], win_uv=(0.0, 0.0, 1.0, 1.0),
        mullion_mat=mats["dark_steel"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.85, add_rail=False, bay_w=5.2, simple_recess=True,
        interior_mode="context",
    )

    custom_modeled_w = {
        "352521262", "398697589", "636389217", "636389213",
        "479455921", "398697588", "636389225", "352521260",
        "263035038", "352521261", "263035030", "263035031",
    }
    for w in west["ways"]:
        if w["id"] in custom_modeled_w or "building" not in w.get("tags", {}):
            continue
        pts = w["pts"]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if max(xs) < -180 or min(xs) > 95 or max(ys) < -70 or min(ys) > 195:
            continue
        cx_w = sum(xs) / len(xs)
        cy_w = sum(ys) / len(ys)
        if -93.8 <= cx_w <= 7.8 and 5.2 <= cy_w <= 143.0:
            continue  # Skip any external OSM slice falling inside the updated campus perimeter
        lv_str = w["tags"].get("building:levels", "")
        if lv_str == "1":
            # First-ring visible hutong houses upgraded from flat slabs to pitched grey-tile gable houses!
            bw_h, bd_h = max(xs) - min(xs), max(ys) - min(ys)
            if -120.0 <= cx_w <= 42.0 and -25.0 <= cy_w <= 165.0 and bw_h >= 3.5 and bd_h >= 3.5 and bw_h <= 42.0 and bd_h <= 42.0:
                add_hutong_house(
                    ctx_w, (min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5,
                    bw_h, bd_h, 3.45, 0.0,
                    mats["surf"], UV_QINGZHUAN, mats["surf"], UV_GREY_TILE,
                    ridge=min(1.45, min(bw_h, bd_h) * 0.16), ridge_along_x=(bw_h >= bd_h),
                )
            else:
                ctx_w.add_polygon_slab(pts, 0.0, 3.65, mats["surf"], mats["surf"], UV_QINGZHUAN, UV_GREY_TILE, ao_bot=0.74, ao_top=0.94)
        else:
            h = 11.5 if w["tags"].get("building") == "school" else 9.5
            ctx_w.add_polygon_slab(pts, 0.0, h, mats["surf"], mats["surf"], UV_STUCCO, UV_PLAZA_TILE, ao_bot=0.74, ao_top=0.95)
    # Campus, east passage & surrounding hutong trees (elevated z_base for north-terrace tree!)
    for tx, ty, sp, th, tzb in [
        (-22, 52, "broad", 8.5, 0.0), (-35, 51, "broad", 8.0, 0.0),
        (5.0, 34, "broad", 7.5, 0.0), (5.2, 48, "broad", 8.0, 0.0),
        (5.0, 62, "broad", 7.6, 0.0), (5.2, 76, "broad", 8.2, 0.0),
        (-89.5, 134.8, "broad", 7.8, PG_Z),
        (-102.0, 92.0, "broad", 9.5, 0.0), (-118.0, 90.0, "broad", 10.2, 0.0),
    ]:
        ctx_w.add_tree(tx, ty, sp, th, mats["trunk"], mats["leaf"], z_base=tzb)

    # West Campus modern courtyard lamp posts & stadium floodlight anchors
    for lx, ly in [
        (2.4, 18.0), (2.4, 38.0), (2.4, 58.0), (2.4, 72.0),
        (-13.5, 45.0), (-26.0, 39.5), (-40.5, 48.0),
        (-54.8, 43.2), (-62.5, 50.0),
        (-74.0, 86.0), (-51.0, 86.5), (-26.0, 88.0), (-8.5, 96.0),
    ]:
        add_courtyard_lamp(gnd, lx, ly, mats, west_lights, pole_h=3.75)

    # 4 Stadium LED floodlight masts (aligned to +0.40m elevated playground terrace!)
    for fx, fy, tx, ty in [
        (-93.2, 92.2, -68.0, 103.0),
        (-93.2, 107.6, -65.0, 107.6),
        (-93.2, 121.8, -68.0, 112.0),
        (-13.6, 107.6, -42.0, 107.6),
    ]:
        west_lights.append({
            "kind": "floodlight",
            "pos": [round(fx, 2), round(7.45 + PG_Z, 2), round(-fy, 2)],
            "target": [round(tx, 2), round(PG_Z, 2), round(-ty, 2)],
            "color": "#eef5ff",
            "intensity": 62.0,
            "distance": 46.0,
        })
    # C-Wing white relief uplight & exterior stair spotlight & bike tunnel ceiling lights
    west_lights.append({"kind": "sconce", "pos": [-79.8, 2.5, -78.6], "color": "#fff0d6", "intensity": 16.0, "distance": 18.0})
    west_lights.append({"kind": "sconce", "pos": [-7.8, 2.85, -83.8], "color": "#ffecd0", "intensity": 12.0, "distance": 12.0})
    west_lights.append({"kind": "sconce", "pos": [1.45, 2.85, -79.3], "color": "#ffdfb0", "intensity": 12.0, "distance": 11.0})

    verts, tris = exp.write_glb(out_glb)
    return verts, tris, west_lights


# ---------------------------------------------------------------------------
# EAST CAMPUS (东四六条甲44号 毕业年级校区)
# ---------------------------------------------------------------------------
def add_grid_patch(nb: NodeBuilder, x0: float, y0: float, x1: float, y1: float, z: float,
                   mat: int, uv: UVBox, cell: float = 2.0, ao: float = 1.0) -> None:
    """Axis-aligned paving patch with a 1:1 texture tile per grid cell (no long stretch)."""
    u0, v0, u1, v1 = uv
    nx = max(1, int(math.ceil((x1 - x0) / cell)))
    ny = max(1, int(math.ceil((y1 - y0) / cell)))
    dx = (x1 - x0) / nx
    dy = (y1 - y0) / ny
    for ix in range(nx):
        for iy in range(ny):
            ax = x0 + ix * dx
            ay = y0 + iy * dy
            nb.quad_enu(
                mat,
                (ax, ay, z), (ax + dx, ay, z), (ax + dx, ay + dy, z), (ax, ay + dy, z),
                (u0, v0, u1, v1), ao, ao,
            )


def add_wall_run(nb: NodeBuilder, a: Vec2, b: Vec2, h: float, thick: float,
                 mat: int, uv: UVBox, cap_mat: Optional[int] = None, cap_uv: Optional[UVBox] = None) -> None:
    """Wall segment with an optional tiled coping cap."""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L < 0.05:
        return
    yaw = math.atan2(b[1] - a[1], b[0] - a[0])
    cx = (a[0] + b[0]) * 0.5
    cy = (a[1] + b[1]) * 0.5
    nb.add_box(mat, cx, cy, 0.0, L, thick, h, yaw, uv, ao_bot=0.78, ao_top=0.97)
    if cap_mat is not None:
        nb.add_box(cap_mat, cx, cy, h, L + 0.10, thick + 0.16, 0.10, yaw, cap_uv or uv)


def add_ribbon(nb: NodeBuilder, mat: int, p0: Vec3, p1: Vec3, width: float,
               uv: UVBox = (0.0, 0.0, 1.0, 1.0), ao: float = 1.0) -> None:
    """Flat double-sided bar in a vertical plane (for X-braces / A-frame legs)."""
    x0, y0, z0 = p0
    x1, y1, z1 = p1
    dx, dz = x1 - x0, z1 - z0
    L = math.hypot(dx, dz) or 1.0
    nx, nz = -dz / L * width * 0.5, dx / L * width * 0.5
    nb.quad_enu(
        mat,
        (x0 + nx, y0, z0 + nz), (x0 - nx, y0, z0 - nz),
        (x1 - nx, y1, z1 - nz), (x1 + nx, y1, z1 + nz),
        uv, ao, ao, double_sided=True,
    )


def add_ground_line(nb: NodeBuilder, mat: int, x0: float, y0: float, x1: float, y1: float,
                    width: float, z: float) -> None:
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 0.02:
        return
    nb.add_box(mat, (x0 + x1) * 0.5, (y0 + y1) * 0.5, z, L, width, 0.02,
               math.atan2(y1 - y0, x1 - x0))


def add_ground_circle(nb: NodeBuilder, mat: int, cx: float, cy: float, r: float,
                      width: float, z: float, segs: int = 16,
                      a0: float = 0.0, a1: float = math.pi * 2.0) -> None:
    prev: Optional[Vec2] = None
    for i in range(segs + 1):
        a = a0 + (a1 - a0) * i / segs
        p = (cx + r * math.cos(a), cy + r * math.sin(a))
        if prev is not None:
            add_ground_line(nb, mat, prev[0], prev[1], p[0], p[1], width, z)
        prev = p


def add_hutong_house(nb: NodeBuilder, cx: float, cy: float, w: float, d: float, h: float,
                     yaw: float, wall_mat: int, wall_uv: UVBox, roof_mat: int, roof_uv: UVBox,
                     ridge: float = 1.3, ridge_along_x: bool = True) -> None:
    """Beijing traditional gable hutong house with stone base plinth, thick eaves, ridge roll, bargeboards & framed windows."""
    cs, sn = math.cos(yaw), math.sin(yaw)

    def wp(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, lz)

    nb.add_box(wall_mat, cx, cy, 0.0, w + 0.10, d + 0.10, 0.34, yaw, wall_uv, ao_bot=0.68, ao_top=0.84)
    nb.add_box(wall_mat, cx, cy, 0.0, w, d, h, yaw, wall_uv, ao_bot=0.76, ao_top=0.95)

    # Lightweight traditional dark-framed windows & doorway along front/back long walls
    win_m = nb.mats.get("context_window", nb.mats.get("glass", wall_mat)) if not nb.classic_mode else nb.mats.get("glass", wall_mat)
    win_uv = (0.0, 0.0, 1.0, 1.0) if (not nb.classic_mode and "context_window" in nb.mats) else UV_GLASS_WINDOW
    frame_m = nb.mats.get("dark_steel", wall_mat)
    span_long = w if ridge_along_x else d
    n_win = max(2, min(5, int(span_long // 3.4)))
    if h >= 2.8 and span_long >= 4.2:
        for side_s in (-1.0, 1.0):
            for wi in range(n_win):
                u_w = -0.36 + (0.72 * wi / max(1, n_win - 1))
                if ridge_along_x:
                    wx = u_w * w
                    wy = side_s * (d * 0.5 + 0.03)
                    if side_s < 0:
                        nb.quad_enu(win_m, wp(wx - 0.52, wy, 1.05), wp(wx + 0.52, wy, 1.05), wp(wx + 0.52, wy, 2.35), wp(wx - 0.52, wy, 2.35), win_uv, 0.88, 0.98)
                    else:
                        nb.quad_enu(win_m, wp(wx + 0.52, wy, 1.05), wp(wx - 0.52, wy, 1.05), wp(wx - 0.52, wy, 2.35), wp(wx + 0.52, wy, 2.35), win_uv, 0.88, 0.98)
                    fp = wp(wx, side_s * (d * 0.5 + 0.04), 0.0)
                    nb.add_box(frame_m, fp[0], fp[1], 0.98, 1.16, 0.08, 0.07, yaw)
                else:
                    wy = u_w * d
                    wx = side_s * (w * 0.5 + 0.03)
                    if side_s < 0:
                        nb.quad_enu(win_m, wp(wx, wy + 0.52, 1.05), wp(wx, wy - 0.52, 1.05), wp(wx, wy - 0.52, 2.35), wp(wx, wy + 0.52, 2.35), win_uv, 0.88, 0.98)
                    else:
                        nb.quad_enu(win_m, wp(wx, wy - 0.52, 1.05), wp(wx, wy + 0.52, 1.05), wp(wx, wy + 0.52, 2.35), wp(wx, wy - 0.52, 2.35), win_uv, 0.88, 0.98)
                    fp = wp(side_s * (w * 0.5 + 0.04), wy, 0.0)
                    nb.add_box(frame_m, fp[0], fp[1], 0.98, 0.08, 1.16, 0.07, yaw)

    ov = 0.48
    rh = h + ridge
    if ridge_along_x:
        nb.quad_enu(roof_mat, wp(-w / 2 - ov, -d / 2 - ov, h - 0.08), wp(w / 2 + ov, -d / 2 - ov, h - 0.08),
                    wp(w / 2 + ov, 0, rh), wp(-w / 2 - ov, 0, rh), roof_uv, 0.88, 1.0, double_sided=True)
        nb.quad_enu(roof_mat, wp(w / 2 + ov, d / 2 + ov, h - 0.08), wp(-w / 2 - ov, d / 2 + ov, h - 0.08),
                    wp(-w / 2 - ov, 0, rh), wp(w / 2 + ov, 0, rh), roof_uv, 0.88, 1.0, double_sided=True)
        nb.tri_enu(wall_mat, wp(-w / 2, d / 2, h), wp(-w / 2, -d / 2, h), wp(-w / 2, 0, rh),
                   (0.05, 0.95), (0.95, 0.95), (0.5, 0.05), 0.85, 0.85, 0.95)
        nb.tri_enu(wall_mat, wp(w / 2, -d / 2, h), wp(w / 2, d / 2, h), wp(w / 2, 0, rh),
                   (0.05, 0.95), (0.95, 0.95), (0.5, 0.05), 0.85, 0.85, 0.95)
        # Ridge roll & eave fascia thickness
        nb.add_box(roof_mat, cx, cy, rh - 0.03, w + ov * 2 + 0.08, 0.26, 0.18, yaw, roof_uv)
        add_rect_beam(nb, frame_m, wp(-w / 2 - ov, -d / 2 - ov, h - 0.11), wp(w / 2 + ov, -d / 2 - ov, h - 0.11), 0.07, 0.10)
        add_rect_beam(nb, frame_m, wp(-w / 2 - ov, d / 2 + ov, h - 0.11), wp(w / 2 + ov, d / 2 + ov, h - 0.11), 0.07, 0.10)
    else:
        nb.quad_enu(roof_mat, wp(-w / 2 - ov, d / 2 + ov, h - 0.08), wp(-w / 2 - ov, -d / 2 - ov, h - 0.08),
                    wp(0, -d / 2 - ov, rh), wp(0, d / 2 + ov, rh), roof_uv, 0.88, 1.0, double_sided=True)
        nb.quad_enu(roof_mat, wp(w / 2 + ov, -d / 2 - ov, h - 0.08), wp(w / 2 + ov, d / 2 + ov, h - 0.08),
                    wp(0, d / 2 + ov, rh), wp(0, -d / 2 - ov, rh), roof_uv, 0.88, 1.0, double_sided=True)
        nb.tri_enu(wall_mat, wp(-w / 2, -d / 2, h), wp(w / 2, -d / 2, h), wp(0, -d / 2, rh),
                   (0.05, 0.95), (0.95, 0.95), (0.5, 0.05), 0.85, 0.85, 0.95)
        nb.tri_enu(wall_mat, wp(w / 2, d / 2, h), wp(-w / 2, d / 2, h), wp(0, d / 2, rh),
                   (0.05, 0.95), (0.95, 0.95), (0.5, 0.05), 0.85, 0.85, 0.95)
        nb.add_box(roof_mat, cx, cy, rh - 0.03, 0.26, d + ov * 2 + 0.08, 0.18, yaw, roof_uv)
        add_rect_beam(nb, frame_m, wp(-w / 2 - ov, -d / 2 - ov, h - 0.11), wp(-w / 2 - ov, d / 2 + ov, h - 0.11), 0.07, 0.10)
        add_rect_beam(nb, frame_m, wp(w / 2 + ov, -d / 2 - ov, h - 0.11), wp(w / 2 + ov, d / 2 + ov, h - 0.11), 0.07, 0.10)


def add_court_markings(nb: NodeBuilder, cx: float, cy: float, w: float, l: float,
                       mat: int, z: float = 0.09) -> None:
    """White FIBA-style markings scaled to the measured court (w x l)."""
    t = 0.06
    hw, hl = w * 0.5 - 0.18, l * 0.5 - 0.18
    add_ground_line(nb, mat, cx - hw, cy - hl, cx + hw, cy - hl, t, z)
    add_ground_line(nb, mat, cx + hw, cy - hl, cx + hw, cy + hl, t, z)
    add_ground_line(nb, mat, cx + hw, cy + hl, cx - hw, cy + hl, t, z)
    add_ground_line(nb, mat, cx - hw, cy + hl, cx - hw, cy - hl, t, z)
    add_ground_line(nb, mat, cx - hw, cy, cx + hw, cy, t, z)
    add_ground_circle(nb, mat, cx, cy, 1.75, t, z, 16)
    for sgn in (-1.0, 1.0):
        base = cy + sgn * hl
        lane_end = base - sgn * 5.8
        add_ground_line(nb, mat, cx - 2.45, base, cx - 2.45, lane_end, t, z)
        add_ground_line(nb, mat, cx + 2.45, base, cx + 2.45, lane_end, t, z)
        add_ground_line(nb, mat, cx - 2.45, lane_end, cx + 2.45, lane_end, t, z)
        add_ground_circle(nb, mat, cx, lane_end, 1.75, t, z, 14)
        hoop = base - sgn * 1.35
        add_ground_circle(nb, mat, cx, hoop, 6.55, t, z, 18,
                          a0=(math.pi * 0.5 - 1.12) if sgn > 0 else (-math.pi * 0.5 - 1.12),
                          a1=(math.pi * 0.5 + 1.12) if sgn > 0 else (-math.pi * 0.5 + 1.12))


def build_east_campus(data_path: str, tex_dir: str, out_glb: str, classic_mode: bool = False) -> Tuple[int, int, List[dict]]:
    east = json.loads(Path(data_path).read_text())
    ways = {w["id"]: w for w in east["ways"]}
    exp = GLBExporter(classic_mode=classic_mode)
    mats = init_materials(exp, tex_dir, include_west_details=True, classic_mode=classic_mode)
    east_lights: List[dict] = []

    # --- Layout constants (metres, ENU) : read from the measured truth block -
    d = east.get("derived", {})
    lane_cfg = d.get("north_lane", {})
    gate_cfg = d.get("gate", {})
    GX = float(gate_cfg.get("center_x", -6.55))     # gate centre line
    OPEN = float(gate_cfg.get("opening", 4.80))     # clear opening between piers
    PIER = float(gate_cfg.get("pier", 0.85))        # pier section
    GATE_Y = 80.50                                   # gate plane (street line)
    LANE_W = float(lane_cfg.get("w", -9.40))
    LANE_E = float(lane_cfg.get("e", -3.30))
    WALL_H = 2.60
    WEST_PIER = GX - OPEN * 0.5 - PIER * 0.5
    EAST_PIER = GX + OPEN * 0.5 + PIER * 0.5

    # ---- Campus_Ground_East : real boundary + lane + street + curbs + bikes ---
    gnd = exp.add_node("Campus_Ground_East")
    gnd.add_polygon_patch(ways["398694728"]["pts"], 0.0, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    # 6 m red-brick entrance lane with granite side kerbs along both walls
    add_grid_patch(gnd, LANE_W, 23.9, LANE_E, 76.4, 0.03, mats["surf"], UV_RED_BRICK_WALK, cell=1.6)
    add_grid_patch(gnd, LANE_W, 76.4, LANE_E, 80.1, 0.03, mats["surf"], UV_PLAZA_TILE, cell=1.6)
    add_grid_patch(gnd, -10.2, 54.0, LANE_W, 68.0, 0.03, mats["surf"], UV_PLAZA_TILE, cell=1.6)
    add_stone_curb_polyline(gnd, [(LANE_W + 0.14, 24.1), (LANE_W + 0.14, 53.8)], 0.02, 0.13, 0.16, mats, UV_CONSTS, wall_uv_key="UV_PLAZA_TILE")
    add_stone_curb_polyline(gnd, [(LANE_W + 0.14, 68.2), (LANE_W + 0.14, 76.2)], 0.02, 0.13, 0.16, mats, UV_CONSTS, wall_uv_key="UV_PLAZA_TILE")
    add_stone_curb_polyline(gnd, [(LANE_E - 0.14, 24.1), (LANE_E - 0.14, 76.2)], 0.02, 0.13, 0.16, mats, UV_CONSTS, wall_uv_key="UV_PLAZA_TILE")
    # Bare/gravel yard north of the courts with granite edging curb & parked student bicycles
    add_grid_patch(gnd, -12.0, 18.0, 32.0, 24.0, 0.02, mats["bare_soil"], (0.0, 0.0, 1.0, 1.0), cell=4.0)
    add_stone_curb_polyline(gnd, [(-12.0, 18.0), (-12.0, 24.0)], 0.015, 0.12, 0.16, mats, UV_CONSTS, wall_uv_key="UV_PLAZA_TILE")
    add_stone_curb_polyline(gnd, [(32.0, 18.0), (32.0, 24.0)], 0.015, 0.12, 0.16, mats, UV_CONSTS, wall_uv_key="UV_PLAZA_TILE")
    add_detailed_bicycle_rack(gnd, 8.0, 22.4, 0.025, 13.0, 9, 0.0, mats)
    add_parked_bicycle_row(gnd, 2.2, 22.45, 8, 1.62, 0.0, -0.18, mats, z_base=0.025)
    # East Si Liu Tiao roadway + south sidewalk + granite street kerbs + gate apron
    add_grid_patch(gnd, -62.0, 81.0, 66.0, 89.0, -0.02, mats["surf"], UV_ASPHALT, cell=4.0)
    add_grid_patch(gnd, -62.0, 80.1, 66.0, 81.0, 0.0, mats["surf"], UV_PLAZA_TILE, cell=1.5)
    add_grid_patch(gnd, -11.2, 80.1, -1.6, 82.6, 0.01, mats["surf"], UV_PLAZA_TILE, cell=1.2)
    add_stone_curb_polyline(gnd, [(-62.0, 81.0), (-11.4, 81.0)], -0.02, 0.16, 0.18, mats, UV_CONSTS, wall_uv_key="UV_PLAZA_TILE")
    add_stone_curb_polyline(gnd, [(-1.4, 81.0), (66.0, 81.0)], -0.02, 0.16, 0.18, mats, UV_CONSTS, wall_uv_key="UV_PLAZA_TILE")

    # ---- Walls: Beijing Hutong Qingzhuan walls with plinths, pilasters & two-slope grey tile wall caps ----
    for wa, wb, wt_w in [
        ((-35.5, -40.6), (55.3, -39.3), 0.35),
        ((55.3, -39.3), (54.3, 24.1), 0.35),
        ((-35.5, -40.6), (-35.5, 24.0), 0.35),
        ((-35.5, 24.0), (LANE_W, 24.0), 0.35),
        ((LANE_E, 24.0), (54.3, 24.1), 0.35),
        ((LANE_W, 24.0), (LANE_W, 54.0), 0.30),
        ((LANE_W, 68.0), (LANE_W, 76.2), 0.30),
        ((LANE_E, 24.0), (LANE_E, 76.2), 0.30),
    ]:
        add_detailed_wall_run(gnd, wa, wb, WALL_H, wt_w, mats, UV_CONSTS, wall_uv_key="UV_QINGZHUAN", hutong_tile_cap=True)

    # ---- E-G1 : Photo-Faithful North Gate (east-gate-2023.webp), Guardhouse, Plaques & Wheeled A-Frame Barricades ----
    eg1 = exp.add_node("E-G1")
    for px_idx, px in enumerate((WEST_PIER, EAST_PIER)):
        # Polished dark granite plinth base (east-gate-2023.webp) + beveled burgundy steel pier shaft + corner trim
        eg1.add_beveled_box(mats["details"], px, GATE_Y, 0.0, PIER + 0.10, PIER + 0.10, 0.34, 0.0, UV_DARK_SLATE_PODIUM, bevel=0.02, ao_bot=0.70, ao_top=0.92)
        eg1.add_beveled_box(mats["gates"], px, GATE_Y, 0.34, PIER, PIER, 4.21, 0.0, UV_BURGUNDY, bevel=0.03, ao_bot=0.74, ao_top=0.98)
        # Signature horizontal-louver stainless wall sconce lantern on North face (east-gate-2023.webp!)
        eg1.add_box(mats["stainless"], px, GATE_Y + 0.45, 3.30, 0.34, 0.14, 0.56, 0.0, ao_bot=0.84, ao_top=0.98)
        eg1.add_box(mats["lamp_warm"], px, GATE_Y + 0.47, 3.35, 0.28, 0.12, 0.46, 0.0)
        for lv_i in range(6):
            eg1.add_box(mats["stainless"], px, GATE_Y + 0.53, 3.35 + lv_i * 0.088, 0.34, 0.04, 0.025, 0.0)
        east_lights.append({
            "kind": "sconce",
            "pos": [round(px, 2), 3.58, round(-(GATE_Y + 0.58), 2)],
            "color": "#ffd89c", "intensity": 12.0, "distance": 12.0,
        })
        # Photo-signature silver-white openwork intersecting diamond lattice panel on the INNER jamb of both piers!
        in_dir = 1.0 if px_idx == 0 else -1.0  # west pier faces +X east; east pier faces -X west
        ix_lat = px + in_dir * (PIER * 0.5 + 0.035)
        eg1.add_box(mats["white_alu"], ix_lat, GATE_Y - 0.36, 0.36, 0.045, 0.045, 3.52, 0.0)
        eg1.add_box(mats["white_alu"], ix_lat, GATE_Y + 0.36, 0.36, 0.045, 0.045, 3.52, 0.0)
        for di in range(6):
            z_lo = 0.42 + di * 0.56
            z_hi = z_lo + 0.56
            eg1.add_limb(mats["white_alu"], (ix_lat, GATE_Y - 0.34, z_lo), (ix_lat, GATE_Y + 0.34, z_hi), 0.016, 0.016, segs=4)
            eg1.add_limb(mats["white_alu"], (ix_lat, GATE_Y + 0.34, z_lo), (ix_lat, GATE_Y - 0.34, z_hi), 0.016, 0.016, segs=4)
    # Gate soffit downlight
    e_sconce_fn = None if classic_mode else add_wall_sconce
    if not classic_mode:
        add_wall_sconce(eg1, GX, GATE_Y, 4.48, mats, east_lights, color="#ffd496", intensity=14.0, distance=13.0)
    # Beam + vertically fluted deep maroon fascia + sloped mini Chinese barrel-tile eave with white drip tiles (瓦当) + twin stone end-posts!
    eg1.add_box(mats["gates"], GX, GATE_Y, 4.55, OPEN + 2 * PIER + 0.10, PIER + 0.06, 0.42, 0.0, UV_BURGUNDY)
    eg1.add_box(mats["gates"], GX, GATE_Y, 4.97, OPEN + 2 * PIER + 0.38, PIER + 0.22, 0.78, 0.0, UV_BURGUNDY, ao_bot=0.84, ao_top=1.0)
    # Vertical fluted ribs across maroon fascia (east-gate-2023.webp!)
    n_ribs = 28
    span_f = OPEN + 2 * PIER + 0.20
    for ri in range(n_ribs):
        rx_f = (GX - span_f * 0.5) + ri * (span_f / (n_ribs - 1))
        eg1.add_box(mats["gates"], rx_f, GATE_Y + PIER * 0.5 + 0.13, 5.00, 0.065, 0.055, 0.72, 0.0, UV_BURGUNDY)
    # Sloped mini Chinese grey-tile eave roof + 21 cylindrical barrel-tile rolls + circular white drip discs (瓦当)
    eg1.quad_enu(
        mats["surf"],
        (GX - 3.55, GATE_Y + 0.74, 5.72), (GX + 3.55, GATE_Y + 0.74, 5.72),
        (GX + 3.55, GATE_Y + 0.15, 6.08), (GX - 3.55, GATE_Y + 0.15, 6.08),
        UV_GREY_TILE, 0.88, 1.0, double_sided=True,
    )
    eg1.quad_enu(
        mats["surf"],
        (GX + 3.55, GATE_Y - 0.74, 5.72), (GX - 3.55, GATE_Y - 0.74, 5.72),
        (GX - 3.55, GATE_Y - 0.15, 6.08), (GX + 3.55, GATE_Y - 0.15, 6.08),
        UV_GREY_TILE, 0.88, 1.0, double_sided=True,
    )
    for i in range(21):
        tx = GX - 3.30 + i * (6.60 / 20.0)
        eg1.add_limb(mats["surf"], (tx, GATE_Y + 0.76, 5.74), (tx, GATE_Y + 0.16, 6.10), 0.055, 0.055, segs=6)
        eg1.add_limb(mats["surf"], (tx, GATE_Y - 0.76, 5.74), (tx, GATE_Y - 0.16, 6.10), 0.055, 0.055, segs=6)
        # Crisp circular white ceramic drip-tile face (瓦当) at each barrel tile eave end!
        eg1.add_box(mats["white_alu"], tx, GATE_Y + 0.77, 5.69, 0.11, 0.04, 0.11, 0.0)
    # Twin upper grey stone end-posts & horizontal upper lintel crest bar (east-gate-2023.webp top!)
    for px_top in (GX - 3.05, GX + 3.05):
        eg1.add_beveled_box(mats["surf"], px_top, GATE_Y, 5.95, 0.34, 0.36, 0.82, 0.0, UV_PLAZA_TILE, bevel=0.02)
    eg1.add_beveled_box(mats["surf"], GX, GATE_Y, 6.22, 6.00, 0.28, 0.32, 0.0, UV_PLAZA_TILE, bevel=0.02)

    # LED screen (off, dark recessed bezel) on the beam's north face
    eg1.add_box(mats["dark_steel"], GX, GATE_Y + 0.46, 3.83, 4.72, 0.08, 0.70, 0.0)
    eg1.quad_enu(mats["led_off"], (GX - 2.30, GATE_Y + 0.51, 3.88), (GX + 2.30, GATE_Y + 0.51, 3.88),
                 (GX + 2.30, GATE_Y + 0.51, 4.50), (GX - 2.30, GATE_Y + 0.51, 4.50),
                 (0.0, 0.0, 1.0, 1.0), 1.0, 1.0, double_sided=True)
    # Vertical white plaque on the WEST pier (north face)
    eg1.add_box(mats["dark_steel"], WEST_PIER, GATE_Y + 0.44, 1.10, 0.34, 0.04, 2.10, 0.0)
    eg1.quad_enu(mats["gates"], (WEST_PIER - 0.15, GATE_Y + 0.47, 1.20), (WEST_PIER + 0.15, GATE_Y + 0.47, 1.20),
                 (WEST_PIER + 0.15, GATE_Y + 0.47, 3.10), (WEST_PIER - 0.15, GATE_Y + 0.47, 3.10),
                 UV_WEST_PLAQUE, 1.0, 1.0, double_sided=True)
    # Stainless steel school plaque + address plate + security sign on guardhouse wall
    eg1.add_box(mats["stainless"], -2.05, GATE_Y + 0.42, 1.93, 1.42, 0.04, 0.56, 0.0)
    eg1.quad_enu(mats["gates"], (-2.72, GATE_Y + 0.45, 1.97), (-1.38, GATE_Y + 0.45, 1.97),
                 (-1.38, GATE_Y + 0.45, 2.49), (-2.72, GATE_Y + 0.45, 2.49),
                 UV_EAST_SIGN, 1.0, 1.0, double_sided=True)
    eg1.add_box(mats["sign_red"], -3.02, GATE_Y + 0.42, 1.44, 0.52, 0.03, 0.34, 0.0)
    eg1.add_box(mats["plaque_white"], -3.02, GATE_Y + 0.44, 1.47, 0.44, 0.03, 0.28, 0.0)
    eg1.add_box(mats["sign_blue"], -1.95, GATE_Y + 0.42, 2.78, 0.56, 0.03, 0.38, 0.0)
    # Side stainless pedestrian grille gates flanking outer sides of both piers (east-gate-2023.webp!)
    for side_gx0, side_gx1 in ((EAST_PIER + 0.46, -3.35), (-9.85, WEST_PIER - 0.46)):
        if side_gx1 - side_gx0 > 0.20:
            sg_mid = (side_gx0 + side_gx1) * 0.5
            eg1.add_box(mats["stainless"], sg_mid, GATE_Y - 0.12, 2.10, side_gx1 - side_gx0, 0.05, 0.05, 0.0)
            eg1.add_box(mats["stainless"], sg_mid, GATE_Y - 0.12, 0.14, side_gx1 - side_gx0, 0.05, 0.05, 0.0)
            for sgi in range(5):
                px_sg = side_gx0 + (side_gx1 - side_gx0) * (sgi / 4.0)
                eg1.add_box(mats["stainless"], px_sg, GATE_Y - 0.12, 0.14, 0.025, 0.025, 1.96, 0.0)

    # Upgraded Motorized Stainless Folding Accordion Gate: controller head cabinet + 3D X-bars + horizontal wheels!
    bays = 12
    bw = OPEN / bays
    yb_gate = GATE_Y - 0.30
    # Motorized silver controller head cabinet on the east end of the opening (east-gate-2023.webp left of gate!)
    eg1.add_beveled_box(mats["stainless"], GX + OPEN * 0.5 - 0.22, yb_gate, 0.12, 0.46, 0.48, 1.66, 0.0, bevel=0.025)
    eg1.add_box(mats["dark_steel"], GX + OPEN * 0.5 - 0.22, yb_gate + 0.25, 1.05, 0.32, 0.04, 0.34, 0.0)
    eg1.add_box(mats["led"], GX + OPEN * 0.5 - 0.22, yb_gate + 0.275, 1.15, 0.26, 0.02, 0.12, 0.0)
    for i in range(bays + 1):
        bx = GX - OPEN * 0.5 + i * bw
        eg1.add_box(mats["stainless"], bx, yb_gate, 0.12, 0.05, 0.06, 1.62, 0.0)
        eg1.add_box(mats["gold_trim"], bx, yb_gate, 1.74, 0.065, 0.075, 0.05, 0.0)  # picket finial cap
        if i % 2 == 0:
            # Horizontal rolling wheels in forks (replaces vertical floating orange cylinders!)
            for wy_w in (yb_gate - 0.16, yb_gate + 0.16):
                add_torus_ring(eg1, mats["dark_steel"], (bx, wy_w, 0.065), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.048, 0.018, major_segs=8, minor_segs=4)
                eg1.add_limb(mats["orange_hoop"], (bx, wy_w - 0.02, 0.065), (bx, wy_w + 0.02, 0.065), 0.024, 0.024, segs=6)
    for i in range(bays):
        x0 = GX - OPEN * 0.5 + i * bw
        x1 = x0 + bw
        eg1.add_limb(mats["stainless"], (x0, yb_gate, 0.22), (x1, yb_gate, 1.56), 0.016, 0.016, segs=4)
        eg1.add_limb(mats["stainless"], (x0, yb_gate, 1.56), (x1, yb_gate, 0.22), 0.016, 0.016, segs=4)
    for ty in (GATE_Y - 0.46, GATE_Y - 0.14):
        eg1.add_box(mats["stainless"], GX, ty, 0.01, OPEN + 0.3, 0.05, 0.02, 0.0)
    # Card reader pillar (west side of the opening)
    eg1.add_beveled_box(mats["stainless"], GX - OPEN * 0.5 - 0.28, GATE_Y - 0.75, 0.0, 0.26, 0.26, 1.18, 0.0, bevel=0.02)
    eg1.add_box(mats["led"], GX - OPEN * 0.5 - 0.28, GATE_Y - 0.88, 0.80, 0.16, 0.02, 0.12, 0.0)
    # Guardhouse (east of gate): Qingzhuan grey brick with thick grey-tile eaves & crisp white-framed windows
    eg1.add_pitched_gable_building(
        cx=0.20, cy_n=78.55, w=7.0, d=4.7, eave_h=3.05, ridge_h=0.75, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=1, ridge_along_x=True,
        window_frame_mat=mats["white_alu"],
    )
    # Photo-faithful 3D Wheeled Steel-Pipe A-Frame Barricades (拒马, east-gate-2023.webp foreground!)
    add_wheeled_aframe_barricade(eg1, -10.8, 83.25, 0.0, 0.26, mats)
    add_wheeled_aframe_barricade(eg1, -2.0, 83.25, 0.0, -0.26, mats)
    # White/red "5" roundel + two manhole covers
    eg1.quad_enu(mats["gates"], (GX - 1.15, 83.55, 0.03), (GX + 1.15, 83.55, 0.03),
                 (GX + 1.15, 85.85, 0.03), (GX - 1.15, 85.85, 0.03), UV_SPEED_5, 1.0, 1.0, double_sided=True)
    for hx, hy in ((GX - 1.9, 82.9), (GX + 1.7, 83.2)):
        eg1.add_cylinder(mats["dark_steel"], hx, hy, 0.01, 0.34, 0.34, 0.02, 12)

    # ---- E-N1 : 56 m brick lane + sloped-tile west veranda annex + curbed east tree court ----
    en1 = exp.add_node("E-N1")
    en1.add_pitched_gable_building(
        cx=-13.50, cy_n=61.0, w=7.0, d=14.0, eave_h=3.30, ridge_h=1.05, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=1, ridge_along_x=False,
        window_frame_mat=mats["white_alu"],
    )
    # Sloped traditional grey-tile lean-to veranda + granite plinth step + crimson columns, architrave & entrance door
    en1.add_box(mats["surf"], -9.52, 61.0, 0.02, 1.18, 13.8, 0.16, 0.0, UV_PLAZA_TILE, ao_bot=0.76, ao_top=0.96)
    en1.quad_enu(
        mats["surf"],
        (-10.02, 54.0, 3.30), (-8.88, 54.0, 2.86),
        (-8.88, 68.0, 2.86), (-10.02, 68.0, 3.30),
        UV_GREY_TILE, 0.86, 1.0, double_sided=True,
    )
    add_rect_beam(en1, mats["crimson"], (-8.92, 54.0, 2.84), (-8.92, 68.0, 2.84), 0.11, 0.14)
    for py in (54.9, 58.9, 62.9, 66.9):
        en1.add_box(mats["surf"], -9.15, py, 0.18, 0.28, 0.28, 0.12, 0.0, UV_PLAZA_TILE)
        en1.add_smooth_cylinder(mats["crimson"], -9.15, py, 0.30, 0.09, 0.085, 2.55, segs=8)
    # Veranda doorway facing east onto north lane
    en1.add_box(mats["pavilion_wood"], -9.98, 61.0, 0.18, 0.12, 1.38, 2.25, 0.0)
    en1.quad_enu(mats["glass_phys"], (-9.91, 60.45, 1.15), (-9.91, 61.55, 1.15), (-9.91, 61.55, 2.30), (-9.91, 60.45, 2.30))
    # East side: walled tree courtyard with green lawn & stone edging curb (replaces bare tile!)
    en1.add_polygon_patch([(-2.9, 48.0), (8.2, 48.0), (8.2, 75.8), (-2.9, 75.8)], 0.03, mats["surf"], UV_GRASS, ao=0.94)
    add_stone_curb_polyline(en1, [(-2.9, 48.0), (8.2, 48.0), (8.2, 75.8), (-2.9, 75.8)], 0.02, 0.16, 0.18, mats, UV_CONSTS, closed=True)
    for tx, ty, sp, th in ((0.6, 74.0, "cedar", 9.0), (3.6, 68.0, "broad", 11.0),
                           (1.4, 62.0, "cedar", 8.2), (4.6, 56.0, "broad", 10.0),
                           (2.2, 50.5, "broad", 9.0)):
        en1.add_tree(tx, ty, sp, th, mats["trunk"], mats["leaf"])
    en1.add_tree(-14.2, 72.0, "broad", 10.0, mats["trunk"], mats["leaf"])
    en1.add_tree(-15.5, 45.0, "broad", 9.0, mats["trunk"], mats["leaf"])

    # ---- E-P1 : Two measured courts + curbed buffer + braced fence + upgraded hoops & multi-head floodlights ----
    ep1 = exp.add_node("E-P1")
    add_grid_patch(ep1, -6.0, -16.0, 31.0, 19.0, 0.04, mats["surf"], UV_TRACK_EPDM, cell=2.2, ao=0.98)
    for wid in ("838569683", "838569684"):
        pts = ways[wid]["pts"]
        ep1.add_polygon_patch(pts, 0.07, mats["surf"], UV_COURT_GREEN, ao=1.0)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        cx = (min(xs) + max(xs)) * 0.5
        cy = (min(ys) + max(ys)) * 0.5
        add_court_markings(ep1, cx, cy, max(xs) - min(xs), max(ys) - min(ys), mats["white_alu"], 0.09)
        add_basketball_hoop(ep1, cx, min(ys) - 0.6, 0.0, mats, z_base=0.04)
        add_basketball_hoop(ep1, cx, max(ys) + 0.6, math.pi, mats, z_base=0.04)
    # Chain-link fence around the sports pad with granite bottom curb, top/mid rails, corner braces & west gate frame
    fx0, fy0, fx1, fy1 = -6.0, -16.0, 31.0, 19.0
    fence_runs = [((fx0, fy0), (fx1, fy0)), ((fx1, fy0), (fx1, fy1)),
                  ((fx1, fy1), (fx0, fy1)), ((fx0, 2.0), (fx0, fy0)),
                  ((fx0, fy1), (fx0, 4.6))]
    post_mat = mats["dark_steel"]
    for a, b in fence_runs:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        yaw = math.atan2(b[1] - a[1], b[0] - a[0])
        add_stone_curb_polyline(ep1, [a, b], 0.02, 0.16, 0.18, mats, UV_CONSTS, wall_uv_key="UV_PLAZA_TILE")
        n = max(2, int(L / 3.0) + 1)
        for i in range(n):
            t = i / (n - 1)
            px = a[0] + (b[0] - a[0]) * t
            py = a[1] + (b[1] - a[1]) * t
            ep1.add_smooth_cylinder(post_mat, px, py, 0.16, 0.048, 0.048, 3.06, segs=6)
        ep1.add_limb(post_mat, (a[0], a[1], 3.20), (b[0], b[1], 3.20), 0.032, 0.032, segs=6)
        ep1.add_limb(post_mat, (a[0], a[1], 1.65), (b[0], b[1], 1.65), 0.026, 0.026, segs=6)
        ep1.quad_enu(mats["fence_mesh"],
                     (a[0], a[1], 0.16), (b[0], b[1], 0.16), (b[0], b[1], 3.18), (a[0], a[1], 3.18),
                     (0.0, 0.0, 1.0, 1.0), 1.0, 1.0, double_sided=True)
    # West fence gateway overhead transom portal frame (y=2.0..4.6)
    ep1.add_limb(post_mat, (fx0, 2.0, 2.55), (fx0, 4.6, 2.55), 0.04, 0.04, segs=6)
    # Four multi-head angled stadium floodlight masts (replaces pole + cube!)
    for lx, ly, lyaw in (
        (fx0 + 0.6, fy0 + 0.6, math.pi * 0.25),
        (fx1 - 0.6, fy0 + 0.6, math.pi * 0.75),
        (fx0 + 0.6, fy1 - 0.6, -math.pi * 0.25),
        (fx1 - 0.6, fy1 - 0.6, -math.pi * 0.75),
    ):
        add_detailed_stadium_floodlight(ep1, lx, ly, 0.04, lyaw, 7.85, mats, n_heads=3)
        east_lights.append({
            "kind": "floodlight",
            "pos": [round(lx, 2), 7.90, round(-ly, 2)],
            "target": [12.5, 0.0, -1.5],
            "color": "#eef5ff",
            "intensity": 64.0,
            "distance": 46.0,
        })

    # ---- E-B1 : south main teaching building (4F green roof + north entrance portal, penthouse & AC units) ----
    eb1 = exp.add_node("E-B1")
    eb1.add_detailed_building(
        ways["477977123"]["pts"], stories=4, story_h=3.6, plinth_h=0.85,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREEN_ROOF,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
    )
    add_building_entrance_portal(eb1, 8.6, -17.88, 0.0, 0.020, mats, UV_CONSTS, width=4.20, steps=2, light_records=east_lights, add_wall_sconce_fn=e_sconce_fn)
    add_rooftop_penthouse(eb1, -4.5, -24.8, 0.85 + 4 * 3.6 + 0.25, 4.6, 4.2, 2.30, 0.020, mats, UV_CONSTS)
    add_rooftop_penthouse(eb1, 21.5, -24.4, 0.85 + 4 * 3.6 + 0.25, 4.6, 4.2, 2.30, 0.020, mats, UV_CONSTS)
    for ax_e1 in (-6.0, 2.0, 15.0, 23.0):
        ay_e1 = -18.33 + ((ax_e1 + 13.91) / 44.98) * 0.90 + 0.16
        for st_e1 in (1, 2, 3):
            add_ac_unit(eb1, ax_e1, ay_e1, 0.95 + st_e1 * 3.6, 0.020, mats)

    # ---- E-B2 : south-west L building (4F green roof + east entrance portal, penthouse & AC units) ----
    eb2 = exp.add_node("E-B2")
    eb2.add_detailed_building(
        ways["477977122"]["pts"], stories=4, story_h=3.6, plinth_h=0.85,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREEN_ROOF,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
    )
    add_building_entrance_portal(eb2, -16.56, -24.5, 0.0, -math.pi * 0.5, mats, UV_CONSTS, width=3.50, steps=2, light_records=east_lights, add_wall_sconce_fn=e_sconce_fn)
    add_rooftop_penthouse(eb2, -24.4, -27.2, 0.85 + 4 * 3.6 + 0.25, 4.5, 4.2, 2.25, 0.0, mats, UV_CONSTS)
    for ay_e2, ax_e2 in ((-19.5, -16.38), (-29.5, -16.42)):
        for st_e2 in (1, 2):
            add_ac_unit(eb2, ax_e2, ay_e2, 0.95 + st_e2 * 3.6, -math.pi * 0.5, mats)

    # ---- E-B3 : south-east annex block (3F + north entrance portal, penthouse & AC units) ----
    eb3 = exp.add_node("E-B3")
    eb3.add_detailed_building(
        ways["477977121"]["pts"], stories=3, story_h=3.5, plinth_h=0.75,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
    )
    add_building_entrance_portal(eb3, 46.8, -17.08, 0.0, 0.015, mats, UV_CONSTS, width=3.40, steps=2, light_records=east_lights, add_wall_sconce_fn=e_sconce_fn)
    add_rooftop_penthouse(eb3, 43.2, -24.5, 0.75 + 3 * 3.5 + 0.25, 4.2, 3.8, 2.15, 0.015, mats, UV_CONSTS)
    for ax_e3 in (42.2, 51.0):
        ay_e3 = -17.18 + ((ax_e3 - 39.96) / 14.32) * 0.21 + 0.16
        add_ac_unit(eb3, ax_e3, ay_e3, 0.85 + 3.5, 0.015, mats)

    # ---- E-B4 : west mid building + blue-tile 2F annex (with white window frames, gable louver vents & east doors!) ----
    eb4 = exp.add_node("E-B4")
    eb4.add_detailed_building(
        ways["477977120"]["pts"], stories=3, story_h=3.5, plinth_h=0.75,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
    )
    add_building_entrance_portal(eb4, -14.62, -3.30, 0.0, -math.pi * 0.5, mats, UV_CONSTS, width=3.40, steps=2, light_records=east_lights, add_wall_sconce_fn=e_sconce_fn)
    add_rooftop_penthouse(eb4, -23.5, -3.4, 0.75 + 3 * 3.5 + 0.25, 4.2, 3.8, 2.15, 0.0, mats, UV_CONSTS)
    # North annex with blue tile roof + red diamond plaster + WHITE window frames + gable louver vents + east entrance!
    eb4.add_pitched_gable_building(
        cx=-22.0, cy_n=8.0, w=16.0, d=12.0, eave_h=6.60, ridge_h=2.10, yaw_rad=0.0,
        wall_mat=mats["details"], wall_uv=UV_NEIGHBOR_DIAMOND,
        roof_mat=mats["details"], roof_uv=UV_BLUE_TILE_ROOF,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=2, ridge_along_x=True,
        window_frame_mat=mats["white_alu"], gable_vent=True,
    )
    add_building_entrance_portal(eb4, -14.00, 8.0, 0.0, -math.pi * 0.5, mats, UV_CONSTS, width=2.80, steps=2)

    # ---- E-B5 : east edge green-roof building (2F + west entrance portal, penthouse & AC units) ----
    eb5 = exp.add_node("E-B5")
    eb5.add_detailed_building(
        [(37.0, -14.0), (49.0, -14.0), (49.0, 16.0), (37.0, 16.0)],
        stories=2, story_h=3.6, plinth_h=0.55,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREEN_ROOF,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
    )
    add_building_entrance_portal(eb5, 37.0, 1.0, 0.0, math.pi * 0.5, mats, UV_CONSTS, width=3.50, steps=2, light_records=east_lights, add_wall_sconce_fn=e_sconce_fn)
    add_rooftop_penthouse(eb5, 43.0, 7.5, 0.55 + 2 * 3.6 + 0.25, 4.2, 4.0, 2.15, 0.0, mats, UV_CONSTS)
    for ay_e5 in (-8.0, -3.5, 6.5, 11.5):
        add_ac_unit(eb5, 36.84, ay_e5, 0.70 + 3.6, math.pi * 0.5, mats)

    # ---- Context_East : hutong neighbours around the lane ------------------
    ctx_e = exp.add_node("Context_East")
    # neutral ground under the surrounding hutong blocks (avoids floating houses)
    add_grid_patch(gnd, -36.0, 24.2, 56.0, 95.5, -0.01, mats["surf"], UV_ASPHALT, cell=6.0, ao=0.92)
    add_grid_patch(gnd, -36.0, -64.0, 56.0, -40.8, -0.01, mats["surf"], UV_ASPHALT, cell=6.0, ao=0.92)
    # lane-side houses: west row (outside the campus wall) and east row beyond x=10
    houses = [
        (-14.5, 73.0, 9.0, 9.0, 3.4), (-14.5, 47.0, 9.0, 12.0, 3.6),
        (-16.0, 33.5, 10.0, 11.0, 3.4),
        (-26.0, 70.0, 12.0, 12.0, 3.8), (-27.0, 54.0, 12.0, 12.0, 3.6),
        (-27.0, 38.0, 12.0, 12.0, 3.6), (-26.0, 28.5, 12.0, 8.0, 3.4),
        (14.0, 72.0, 10.0, 10.0, 3.6), (14.0, 58.0, 10.0, 10.0, 3.4),
        (16.0, 42.0, 12.0, 12.0, 3.8), (18.0, 32.0, 12.0, 10.0, 3.4),
        (30.0, 66.0, 14.0, 12.0, 3.8), (32.0, 48.0, 14.0, 14.0, 4.0),
        (33.0, 30.0, 14.0, 12.0, 3.6),
        (46.0, 72.0, 12.0, 12.0, 3.6), (47.0, 54.0, 12.0, 14.0, 3.8),
        (47.0, 36.0, 12.0, 14.0, 3.6),
    ]
    for hx, hy, hw, hd, hh in houses:
        add_hutong_house(ctx_e, hx, hy, hw, hd, hh, 0.0, mats["surf"], UV_QINGZHUAN,
                         mats["surf"], UV_GREY_TILE, ridge=1.25, ridge_along_x=True)
    # 2-storey volume at the south end of the lane (upgraded from blank cube to real recessed-window context building!)
    ctx_e.add_detailed_building(
        [(0.0, 34.0), (9.0, 34.0), (9.0, 48.0), (0.0, 48.0)],
        stories=2, story_h=3.20, plinth_h=0.50,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.45, add_rail=False, bay_w=3.5, simple_recess=True,
        interior_mode="context",
    )
    # Street-facing hutong row directly across Dongsi 6th Alley (pitched grey-tile houses facing the school gate!)
    for hx_n, hw_n, hd_n in ((-52, 34, 14), (2, 38, 16), (48, 36, 14)):
        add_hutong_house(ctx_e, hx_n, 102.0, hw_n, hd_n, 3.6, 0.0, mats["surf"], UV_QINGZHUAN, mats["surf"], UV_GREY_TILE, ridge=1.45, ridge_along_x=True)
    # Remaining distant perimeter hutong blocks
    for bx, by, bw, bd in [(-52, 48, 22, 38), (68, 46, 22, 36),
                           (-52, -16, 20, 48), (68, -14, 22, 46),
                           (-10, -56, 48, 14), (42, -56, 36, 14)]:
        ctx_e.add_box(mats["context"], bx, by, 0.0, bw, bd, 3.6, 0.0, (0.0, 0.0, 1.0, 1.0), ao_bot=0.72, ao_top=0.92)
    ctx_e.add_tree(-30, 26, "broad", 9.0, mats["trunk"], mats["leaf"])
    ctx_e.add_tree(36, 22, "broad", 8.5, mats["trunk"], mats["leaf"])
    # south yard trees (west wall, north edge, east corner)
    for tx, ty, th in ((-33.0, -33.0, 10.0), (-33.0, -24.0, 9.0), (-22.0, 22.0, 11.0),
                       (12.0, 22.0, 10.0), (52.0, 10.0, 9.0)):
        ctx_e.add_tree(tx, ty, "broad", th, mats["trunk"], mats["leaf"])

    # Warm hutong lane sconces along the 56m brick alley + veranda soffit lights + south yard courtyard lamps
    if not classic_mode:
        for ly_lane in (72.0, 62.0, 50.0, 38.0, 28.0):
            add_wall_sconce(gnd, LANE_E - 0.22, ly_lane, 2.35, mats, east_lights, color="#ffd18c", intensity=11.0, distance=12.0)
        for ly_ver in (56.5, 61.0, 65.5):
            add_wall_sconce(en1, -9.45, ly_ver, 2.88, mats, east_lights, color="#ffd696", intensity=10.0, distance=10.0)
    for lx_s, ly_s in [(-11.0, 12.0), (-11.0, -8.0), (-10.0, -18.0), (10.0, -18.0), (34.0, -16.0), (34.0, 12.0)]:
        add_courtyard_lamp(gnd, lx_s, ly_s, mats, east_lights, pole_h=3.75)

    verts, tris = exp.write_glb(out_glb)
    return verts, tris, east_lights


def resolve_tex_dir(repo: Path) -> str:
    env_dir = os.environ.get("MAP_TEX_DIR", "").strip()
    if env_dir:
        tex_path = Path(env_dir)
    else:
        scratch_root = Path(os.environ.get("BUILD_SCRATCH_ROOT", str(Path.home() / ".build")))
        tex_path = scratch_root / "校园地图" / "glb_textures"

    required = ("tex_signage_gates.png", "tex_plaques_stage.png", "tex_surfaces.png", "tex_west_details.png")
    if not all((tex_path / f).exists() for f in required):
        swift_bin = shutil.which("swift")
        renderer = repo / "blender" / "scripts" / "render_textures.swift"
        if swift_bin and renderer.exists():
            tex_path.mkdir(parents=True, exist_ok=True)
            subprocess.run([swift_bin, str(renderer), str(tex_path)], check=True)
        else:
            missing = [f for f in required if not (tex_path / f).exists()]
            raise FileNotFoundError(
                f"Missing texture atlas(es) {missing} in {tex_path}. "
                "Set MAP_TEX_DIR or run `swift blender/scripts/render_textures.swift <out_dir>` on macOS."
            )
    return str(tex_path)


def sync_campuses_model_version(repo: Path, filename: str, mb_field: Optional[str] = None) -> str:
    """Update `?v=<sha8>` query param (and optionally MB size) on modelUrl in src/data/campuses.ts after rebuilding a GLB."""
    file_path = repo / "public" / "models" / filename
    raw_bytes = file_path.read_bytes()
    sha8 = hashlib.sha256(raw_bytes).hexdigest()[:8]
    size_mb = round(len(raw_bytes) / (1024 * 1024), 1)
    campuses_ts = repo / "src" / "data" / "campuses.ts"
    if campuses_ts.exists():
        text = campuses_ts.read_text()
        updated = re.sub(
            rf"/models/{re.escape(filename)}(?:\?v=[0-9a-f]+)?",
            f"/models/{filename}?v={sha8}",
            text,
        )
        if mb_field is not None:
            # Update the matching *ModelMB line immediately following this filename's URL
            updated = re.sub(
                rf"(/models/{re.escape(filename)}\?v=[0-9a-f]+\",\s*\n\s*{re.escape(mb_field)}:\s*)[0-9.]+",
                rf"\g<1>{size_mb}",
                updated,
            )
        if updated != text:
            campuses_ts.write_text(updated)
    return sha8


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate procedural campus GLB models (Enhanced + Classic)")
    parser.add_argument(
        "--campus",
        choices=("west", "east", "all"),
        default="all",
        help="Which campus GLB to rebuild (default: all)",
    )
    parser.add_argument(
        "--variant",
        "--mode",
        dest="variant",
        choices=("enhanced", "classic", "all"),
        default="all",
        help="Which model variant(s) to rebuild: enhanced, classic, or all (default: all)",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    data_dir = repo / "blender" / "data"
    out_dir = repo / "public" / "models"
    tex_dir = resolve_tex_dir(repo)

    west_lights: Optional[List[dict]] = None
    east_lights: Optional[List[dict]] = None
    enhanced_targets: List[str] = []
    classic_targets: List[str] = []
    version_syncs: List[Tuple[str, str]] = []

    build_enhanced = args.variant in ("enhanced", "all")
    build_classic = args.variant in ("classic", "all")

    if args.campus in ("west", "all"):
        if build_enhanced:
            west_out = out_dir / "west-campus.glb"
            wv, wt, west_lights = build_west_campus(str(data_dir / "west_metric.json"), tex_dir, str(west_out), classic_mode=False)
            enhanced_targets.append(str(west_out))
            version_syncs.append(("west-campus.glb", "enhancedModelMB"))
            print(f"west-campus.glb raw: {wv} verts, {wt} tris, {west_out.stat().st_size:,} bytes, {len(west_lights)} lights")
        if build_classic:
            west_cls = out_dir / "west-campus-classic.glb"
            wv_c, wt_c, _ = build_west_campus(str(data_dir / "west_metric.json"), tex_dir, str(west_cls), classic_mode=True)
            classic_targets.append(str(west_cls))
            version_syncs.append(("west-campus-classic.glb", "classicModelMB"))
            print(f"west-campus-classic.glb raw: {wv_c} verts, {wt_c} tris, {west_cls.stat().st_size:,} bytes")

    if args.campus in ("east", "all"):
        if build_enhanced:
            east_out = out_dir / "east-campus.glb"
            ev, et, east_lights = build_east_campus(str(data_dir / "east_metric.json"), tex_dir, str(east_out), classic_mode=False)
            enhanced_targets.append(str(east_out))
            version_syncs.append(("east-campus.glb", "enhancedModelMB"))
            print(f"east-campus.glb raw: {ev} verts, {et} tris, {east_out.stat().st_size:,} bytes, {len(east_lights)} lights")
        if build_classic:
            east_cls = out_dir / "east-campus-classic.glb"
            ev_c, et_c, _ = build_east_campus(str(data_dir / "east_metric.json"), tex_dir, str(east_cls), classic_mode=True)
            classic_targets.append(str(east_cls))
            version_syncs.append(("east-campus-classic.glb", "classicModelMB"))
            print(f"east-campus-classic.glb raw: {ev_c} verts, {et_c} tris, {east_cls.stat().st_size:,} bytes")

    # Run gltf-transform weld + dedup + prune + quantization (Classic preserves lossless FLOAT32 POSITION per PR #19!)
    node_bin = shutil.which("node")
    opt_script = Path(__file__).resolve().parent / "optimize_glb.mjs"
    if node_bin and opt_script.exists():
        if enhanced_targets:
            try:
                subprocess.run([node_bin, str(opt_script), *enhanced_targets], check=True)
            except Exception as exc:
                print(f"[warn] optimize_glb (enhanced) skipped: {exc}")
        if classic_targets:
            try:
                subprocess.run([node_bin, str(opt_script), "--preserve-positions", *classic_targets], check=True)
            except Exception as exc:
                print(f"[warn] optimize_glb (classic) skipped: {exc}")

    for fname, mb_field in version_syncs:
        ver = sync_campuses_model_version(repo, fname, mb_field=mb_field)
        print(f"{fname} final (v={ver}): {(out_dir / fname).stat().st_size:,} bytes")

    if west_lights is not None and east_lights is not None:
        write_campus_lights_ts(repo, west_lights, east_lights)
        print(f"Exported src/data/campusLights.ts (west={len(west_lights)}, east={len(east_lights)})")


if __name__ == "__main__":
    main()

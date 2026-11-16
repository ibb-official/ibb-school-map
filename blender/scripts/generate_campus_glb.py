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
UV_WHITE_PEBBLES: UVBox = (0.5918, 0.2754, 0.7676, 0.5137)
UV_FIRE_BOX: UVBox = (0.7930, 0.2734, 0.9883, 0.3984)
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


class NodeBuilder:
    def __init__(self, name: str):
        self.name = name
        self.buckets: Dict[int, PrimitiveBucket] = {}

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
        self.bucket(mat).add_quad(p0, p1, p2, p3, uv_box, c_bot, c_top, flip_uv_x, double_sided)

    def tri_enu(
        self,
        mat: int,
        e0: Vec3, e1: Vec3, e2: Vec3,
        uv0: Vec2, uv1: Vec2, uv2: Vec2,
        c0: float = 1.0, c1: float = 1.0, c2: float = 1.0,
        double_sided: bool = False,
    ) -> None:
        self.bucket(mat).add_tri(
            enu_to_gltf(*e0), enu_to_gltf(*e1), enu_to_gltf(*e2),
            uv0, uv1, uv2, (c0, c0, c0), (c1, c1, c1), (c2, c2, c2), double_sided=double_sided
        )

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
        tu0, tv0, tu1, tv1 = top_uv
        du, dv = tu1 - tu0, tv1 - tv0
        for ia, ib, ic in tris:
            pa, pb, pc = pts[ia], pts[ib], pts[ic]
            # Scale planar UV cleanly within tile box (modulate subtly so it stays within cell!)
            def map_uv(p: Vec2) -> Vec2:
                fu = (p[0] / tile_m) % 1.0
                fv = (-p[1] / tile_m) % 1.0
                return (tu0 + fu * du * 0.85 + du * 0.075, tv0 + fv * dv * 0.85 + dv * 0.075)
            # Single quad cell map without wrap artifacts: use bounded normalization for patterned patches
            # Actually clamp inside tile bounds directly using triangle bounding normalization or local tile
            self.tri_enu(
                top_mat,
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
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        spanx = max(maxx - minx, 0.1)
        spany = max(maxy - miny, 0.1)
        u0, v0, u1, v1 = uv_box
        tris = ear_clip_2d(pts)
        for ia, ib, ic in tris:
            pa, pb, pc = pts[ia], pts[ib], pts[ic]
            uva = (u0 + ((pa[0] - minx) / spanx) * (u1 - u0), v1 - ((pa[1] - miny) / spany) * (v1 - v0))
            uvb = (u0 + ((pb[0] - minx) / spanx) * (u1 - u0), v1 - ((pb[1] - miny) / spany) * (v1 - v0))
            uvc = (u0 + ((pc[0] - minx) / spanx) * (u1 - u0), v1 - ((pc[1] - miny) / spany) * (v1 - v0))
            self.tri_enu(
                mat,
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
    ) -> None:
        """
        Extrudes a multi-story building polygon with structural pilasters, spandrel bands,
        deep -0.22m window recesses, mullions, lower sills, overhanging parapet & roof rail.
        Edges aligned with `solid_x_planes` render as clean setback party walls without windows.
        """
        pts = ensure_ccw(poly_raw)
        n = len(pts)
        if n < 3:
            return
        total_h = plinth_h + stories * story_h
        top_z = ground_z + total_h

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

            # 1. Base Plinth
            self.quad_enu(
                plaster_plinth_mat,
                wpt(0, 0.04, ground_z), wpt(seg_len, 0.04, ground_z),
                wpt(seg_len, 0.04, ground_z + plinth_h), wpt(0, 0.04, ground_z + plinth_h),
                plaster_plinth_uv, 0.72, 0.90,
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
                        self.quad_enu(
                            mullion_mat,
                            wpt(w0, -recess, win_z0), wpt(w1, -recess, win_z0),
                            wpt(w1, 0.07, win_z0), wpt(w0, 0.07, win_z0),
                            (0.1, 0.1, 0.9, 0.9), 0.94, 0.98,
                        )
                        self.quad_enu(
                            wall_mat,
                            wpt(w0, 0.04, win_z1), wpt(w1, 0.04, win_z1),
                            wpt(w1, -recess, win_z1), wpt(w0, -recess, win_z1),
                            wall_uv, 0.65, 0.72,
                        )
                    # Recessed window glass pane (with safety bars in texture)
                    w_plane = 0.01 if simple_recess else -recess
                    self.quad_enu(
                        win_mat,
                        wpt(w0, w_plane, win_z0), wpt(w1, w_plane, win_z0),
                        wpt(w1, w_plane, win_z1), wpt(w0, w_plane, win_z1),
                        win_uv, 0.85, 1.0,
                    )
                    # Vertical aluminum mullions (outer frame + center 2 splits)
                    if not simple_recess:
                        for mx in [w0 + 0.05, w0 + (w1 - w0) * 0.34, w0 + (w1 - w0) * 0.66, w1 - 0.05]:
                            self.quad_enu(
                                mullion_mat,
                                wpt(mx - 0.03, -recess + 0.03, win_z0),
                                wpt(mx + 0.03, -recess + 0.03, win_z0),
                                wpt(mx + 0.03, -recess + 0.03, win_z1),
                                wpt(mx - 0.03, -recess + 0.03, win_z1),
                                (0.1, 0.1, 0.9, 0.9), 0.95, 1.0,
                            )
                    # Optional exterior window security guardrail bars (top & mid rail, crisp & low-poly)
                    if window_grille:
                        gm = grille_mat if grille_mat is not None else mullion_mat
                        gz_top = win_z0 + (win_z1 - win_z0) * 0.46
                        gz_mid = win_z0 + (win_z1 - win_z0) * 0.23
                        for gz_b in (gz_top, gz_mid):
                            self.quad_enu(
                                gm,
                                wpt(w0 + 0.04, 0.09, gz_b - 0.035),
                                wpt(w1 - 0.04, 0.09, gz_b - 0.035),
                                wpt(w1 - 0.04, 0.09, gz_b),
                                wpt(w0 + 0.04, 0.09, gz_b),
                                (0.1, 0.1, 0.9, 0.9), 0.88, 0.98, double_sided=True,
                            )

            # 3. Cornice + Parapet Wall + Rooftop Safety Railing
            self.quad_enu(
                wall_mat,
                wpt(0, 0.10, top_z), wpt(seg_len, 0.10, top_z),
                wpt(seg_len, 0.10, top_z + parapet_h), wpt(0, 0.10, top_z + parapet_h),
                wall_uv, 0.90, 1.0,
            )
            self.quad_enu(
                mullion_mat,
                wpt(0, -0.25, top_z + parapet_h), wpt(seg_len, -0.25, top_z + parapet_h),
                wpt(seg_len, 0.12, top_z + parapet_h), wpt(0, 0.12, top_z + parapet_h),
                (0.1, 0.1, 0.9, 0.9), 0.95, 1.0,
            )
            if add_rail:
                rm = rail_mat if rail_mat is not None else mullion_mat
                rz0 = top_z + parapet_h
                rz1 = rz0 + 0.95
                # Top handrail bar + mid bar + posts every 2.4m
                for bar_z, bar_h in ((rz1 - 0.05, 0.05), (rz0 + 0.46, 0.035)):
                    self.quad_enu(
                        rm,
                        wpt(0, 0.05, bar_z), wpt(seg_len, 0.05, bar_z),
                        wpt(seg_len, 0.05, bar_z + bar_h), wpt(0, 0.05, bar_z + bar_h),
                        (0.1, 0.1, 0.9, 0.9), 0.94, 1.0, double_sided=True,
                    )
                n_posts = max(2, int(seg_len // 2.4) + 1)
                for pi in range(n_posts):
                    pa = seg_len * pi / (n_posts - 1)
                    self.quad_enu(
                        rm,
                        wpt(max(0, pa - 0.03), 0.05, rz0),
                        wpt(min(seg_len, pa + 0.03), 0.05, rz0),
                        wpt(min(seg_len, pa + 0.03), 0.05, rz1),
                        wpt(max(0, pa - 0.03), 0.05, rz1),
                        (0.1, 0.1, 0.9, 0.9), 0.90, 1.0, double_sided=True,
                    )

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
    ) -> None:
        """Traditional Beijing 青砖/灰瓦 gable building with overhanging eaves & ridge."""
        cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

        def wp(lx: float, ly: float, lz: float) -> Vec3:
            return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs, ground_z + lz)

        hw, hd = w * 0.5, d * 0.5
        zt = eave_h
        # Main wall box
        self.add_box(wall_mat, cx, cy_n, ground_z, w, d, eave_h, yaw_rad, wall_uv, ao_bot=0.75, ao_top=0.88)

        # Windows along front/back long walls
        n_win = max(2, int((w if ridge_along_x else d) // 3.0))
        if ridge_along_x:
            for side in (-1.0, 1.0):
                y_face = side * (hd + 0.04)
                for st in range(stories):
                    z0 = st * (eave_h / stories) + 0.85
                    z1 = z0 + (eave_h / stories) * 0.52
                    for wi in range(n_win):
                        wx = -hw + (wi + 0.5) * (w / n_win)
                        ww = (w / n_win) * 0.54
                        if side < 0:
                            self.quad_enu(win_mat, wp(wx - ww * 0.5, y_face, z0), wp(wx + ww * 0.5, y_face, z0), wp(wx + ww * 0.5, y_face, z1), wp(wx - ww * 0.5, y_face, z1), win_uv, 0.86, 0.96)
                        else:
                            self.quad_enu(win_mat, wp(wx + ww * 0.5, y_face, z0), wp(wx - ww * 0.5, y_face, z0), wp(wx - ww * 0.5, y_face, z1), wp(wx + ww * 0.5, y_face, z1), win_uv, 0.86, 0.96)

        # Optional 2F green-rail balcony corridor (for D座 校史馆!)
        if balcony_south and stories >= 2 and balcony_mat is not None:
            by = -hd - 1.4
            bz = eave_h * 0.48
            # Floor slab
            self.quad_enu(wall_mat, wp(-hw, by, bz), wp(hw, by, bz), wp(hw, -hd, bz), wp(-hw, -hd, bz), wall_uv, 0.80, 0.85, double_sided=True)
            # Support columns
            for ci in range(max(3, n_win + 1)):
                px = -hw + ci * (w / max(2, n_win))
                self.add_cylinder(wood_mat, wp(px, by + 0.15, 0)[0], wp(px, by + 0.15, 0)[1], ground_z, 0.14, 0.14, eave_h, 8)
            # Dark green balcony railing
            self.quad_enu(balcony_mat, wp(-hw, by - 0.03, bz), wp(hw, by - 0.03, bz), wp(hw, by - 0.03, bz + 1.05), wp(-hw, by - 0.03, bz + 1.05), (0.1, 0.1, 0.9, 0.9), 0.92, 1.0, double_sided=True)

        # Overhanging pitched roof (ridge_along_x -> ridge runs East-West, gables on W/E)
        ov = 0.65
        wu0, wv0, wu1, wv1 = wall_uv
        wum = (wu0 + wu1) * 0.5
        if ridge_along_x:
            rh = zt + ridge_h
            self.quad_enu(roof_mat, wp(-hw - ov, -hd - ov, zt - 0.12), wp(hw + ov, -hd - ov, zt - 0.12), wp(hw + ov, 0, rh), wp(-hw - ov, 0, rh), roof_uv, 0.88, 1.0, double_sided=True)
            self.quad_enu(roof_mat, wp(hw + ov, hd + ov, zt - 0.12), wp(-hw - ov, hd + ov, zt - 0.12), wp(-hw - ov, 0, rh), wp(hw + ov, 0, rh), roof_uv, 0.88, 1.0, double_sided=True)
            # Gable end triangles (strictly mapped inside wall_uv!)
            self.tri_enu(wall_mat, wp(-hw, hd, zt), wp(-hw, -hd, zt), wp(-hw, 0, rh), (wu0, wv1), (wu1, wv1), (wum, wv0), 0.86, 0.86, 0.96)
            self.tri_enu(wall_mat, wp(hw, -hd, zt), wp(hw, hd, zt), wp(hw, 0, rh), (wu0, wv1), (wu1, wv1), (wum, wv0), 0.86, 0.86, 0.96)
            # Ridge cap
            self.add_box(wood_mat, cx, cy_n, ground_z + rh - 0.06, w + ov * 2, 0.28, 0.24, yaw_rad)
        else:
            rh = zt + ridge_h
            self.quad_enu(roof_mat, wp(-hw - ov, hd + ov, zt - 0.12), wp(-hw - ov, -hd - ov, zt - 0.12), wp(0, -hd - ov, rh), wp(0, hd + ov, rh), roof_uv, 0.88, 1.0, double_sided=True)
            self.quad_enu(roof_mat, wp(hw + ov, -hd - ov, zt - 0.12), wp(hw + ov, hd + ov, zt - 0.12), wp(0, hd + ov, rh), wp(0, -hd - ov, rh), roof_uv, 0.88, 1.0, double_sided=True)
            self.tri_enu(wall_mat, wp(-hw, -hd, zt), wp(hw, -hd, zt), wp(0, -hd, rh), (wu0, wv1), (wu1, wv1), (wum, wv0), 0.86, 0.86, 0.96)
            self.tri_enu(wall_mat, wp(hw, hd, zt), wp(-hw, hd, zt), wp(0, hd, rh), (wu0, wv1), (wu1, wv1), (wum, wv0), 0.86, 0.86, 0.96)
            self.add_box(wood_mat, cx, cy_n, ground_z + rh - 0.06, 0.28, d + ov * 2, 0.24, yaw_rad)

    def add_tree(self, cx: float, cy_n: float, species: str, h: float, trunk_mat: int, leaf_mat: int) -> None:
        self.add_cylinder(trunk_mat, cx, cy_n, 0.0, 0.22, 0.14, h * 0.42, 7, ao_bot=0.65, ao_top=0.88)
        if species == "cedar":
            # Layered conical cedar foliage skirts (for giant Snow Cedar beside ramp & W-L1)
            tiers = 5
            for ti in range(tiers):
                f0 = 0.25 + ti * 0.15
                f1 = f0 + 0.22
                r = (h * 0.36) * (1.0 - ti * 0.17)
                self.add_cylinder(leaf_mat, cx, cy_n, h * f0, r, r * 0.22, h * (f1 - f0), 10, UV_FOLIAGE, ao_bot=0.74, ao_top=1.0)
        else:
            # Deciduous broad dome canopy (Locust / Pine / Magnolia)
            segs = 10
            r = h * 0.34
            cz = h * 0.66
            for ring_i in range(3):
                phi0 = -0.35 + ring_i * 0.45
                phi1 = phi0 + 0.48
                r0 = r * math.cos(phi0)
                r1 = max(0.05, r * math.cos(phi1))
                z0 = cz + r * math.sin(phi0) * 0.8
                z1 = cz + r * math.sin(phi1) * 0.85
                self.add_cylinder(leaf_mat, cx, cy_n, z0, r0, r1, z1 - z0, segs, UV_FOLIAGE, ao_bot=0.76 + ring_i * 0.08, ao_top=0.92 + ring_i * 0.03)


# ---------------------------------------------------------------------------
# glTF Binary (.glb) Serializer
# ---------------------------------------------------------------------------
class GLBExporter:
    def __init__(self):
        self.textures: List[Tuple[str, bytes]] = []
        self.materials: List[dict] = []
        self.nodes: List[NodeBuilder] = []

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
        idx = len(self.materials)
        self.materials.append(m)
        return idx

    def add_node(self, name: str) -> NodeBuilder:
        nb = NodeBuilder(name)
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


def init_materials(exp: GLBExporter, tex_dir: str, include_west_details: bool = False) -> dict:
    t_gates = exp.add_png_texture("SignageGates", f"{tex_dir}/tex_signage_gates.png")
    t_stage = exp.add_png_texture("PlaquesStage", f"{tex_dir}/tex_plaques_stage.png")
    t_surf = exp.add_png_texture("Surfaces", f"{tex_dir}/tex_surfaces.png")

    mats = {
        "gates": exp.add_mat("Mat_Gates", roughness=0.55, tex_idx=t_gates),
        "led": exp.add_mat("Mat_LED", roughness=0.30, tex_idx=t_gates, emissive=(0.25, 0.10, 0.03)),
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
    return mats


def add_basketball_hoop(nb: NodeBuilder, cx: float, cy_n: float, yaw_face_rad: float, mats: dict) -> None:
    """Detailed hoop post, gooseneck overhang arm, white glass backboard & orange rim."""
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def pt(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs, lz)

    nb.add_cylinder(mats["dark_steel"], cx, cy_n, 0.0, 0.12, 0.10, 3.3, 8)
    # Overhang arm extending +ly by 1.2m toward court
    for seg_i in range(4):
        l0 = 0.0 + seg_i * 0.3
        l1 = l0 + 0.32
        p0 = pt(-0.07, l0, 3.25)
        p1 = pt(0.07, l0, 3.25)
        p2 = pt(0.07, l1, 3.25)
        p3 = pt(-0.07, l1, 3.25)
        nb.quad_enu(mats["dark_steel"], p0, p1, p2, p3, (0.1, 0.1, 0.9, 0.9), double_sided=True)
    # White rectangular backboard
    nb.add_box(mats["white_alu"], pt(0, 1.22, 0)[0], pt(0, 1.22, 0)[1], 2.90, 1.80, 0.08, 1.05, yaw_face_rad)
    # Orange basketball rim
    nb.add_cylinder(mats["orange_hoop"], pt(0, 1.48, 0)[0], pt(0, 1.48, 0)[1], 3.05, 0.24, 0.24, 0.06, 12)


def add_basketball_hoop_west(nb: NodeBuilder, cx: float, cy_n: float, yaw_face_rad: float, mats: dict) -> None:
    """West Campus photo-accurate Kelly-green box-truss hoop + tempered glass backboard & white net."""
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def pt(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs, lz)

    g_mat = mats["hoop_green"]
    # Base plate, green protective post padding & upper square steel column
    nb.add_box(mats["dark_steel"], cx, cy_n, 0.06, 0.56, 0.56, 0.05, yaw_face_rad)
    nb.add_box(mats["hoop_pad"], cx, cy_n, 0.11, 0.32, 0.32, 1.82, yaw_face_rad, ao_bot=0.78, ao_top=0.96)
    nb.add_box(g_mat, cx, cy_n, 1.93, 0.22, 0.22, 1.62, yaw_face_rad, ao_bot=0.84, ao_top=0.98)
    # Sloped main lower box arm + upper diagonal tension struts (Magnum Sports green truss)
    arm_c = pt(0.0, 0.62, 0.0)
    nb.add_box(g_mat, arm_c[0], arm_c[1], 3.16, 0.18, 1.28, 0.14, yaw_face_rad)
    for sx in (-0.16, 0.16):
        # Upper diagonal tension strut from column top (ly=0.05, z=3.52) -> backboard top (ly=1.20, z=3.82)
        nb.quad_enu(
            g_mat,
            pt(sx - 0.025, 0.04, 3.48), pt(sx + 0.025, 0.04, 3.48),
            pt(sx + 0.025, 1.20, 3.84), pt(sx - 0.025, 1.20, 3.84),
            double_sided=True,
        )
        nb.quad_enu(
            g_mat,
            pt(sx, 0.04, 3.46), pt(sx, 1.20, 3.80),
            pt(sx, 1.20, 3.86), pt(sx, 0.04, 3.52),
            double_sided=True,
        )
        # Diagonal brace from mid-column (z=2.55) to mid-arm (ly=0.72, z=3.18)
        nb.quad_enu(
            g_mat,
            pt(sx, 0.06, 2.52), pt(sx, 0.74, 3.16),
            pt(sx, 0.74, 3.23), pt(sx, 0.06, 2.60),
            double_sided=True,
        )
    # Outer green perimeter frame of 1.80m x 1.05m backboard (at ly = 1.24)
    bb_xy = pt(0.0, 1.24, 0.0)
    nb.add_box(g_mat, bb_xy[0], bb_xy[1], 2.88, 1.84, 0.05, 0.05, yaw_face_rad)
    nb.add_box(g_mat, bb_xy[0], bb_xy[1], 3.91, 1.84, 0.05, 0.05, yaw_face_rad)
    for bx_s in (-0.895, 0.895):
        post_xy = pt(bx_s, 1.24, 0.0)
        nb.add_box(g_mat, post_xy[0], post_xy[1], 2.88, 0.05, 0.05, 1.08, yaw_face_rad)
    # Semi-transparent tempered glass backboard with crisp white border & shooter's target square
    nb.quad_enu(
        mats["details_alpha"],
        pt(0.88, 1.265, 2.92), pt(-0.88, 1.265, 2.92),
        pt(-0.88, 1.265, 3.91), pt(0.88, 1.265, 3.91),
        UV_GLASS_BACKBOARD, 0.98, 1.0, double_sided=True,
    )
    # Orange rim + white tapered net skirt
    rim_xy = pt(0.0, 1.52, 0.0)
    nb.add_box(mats["orange_hoop"], pt(0.0, 1.32, 0.0)[0], pt(0.0, 1.32, 0.0)[1], 3.03, 0.14, 0.14, 0.06, yaw_face_rad)
    nb.add_cylinder(mats["orange_hoop"], rim_xy[0], rim_xy[1], 3.05, 0.24, 0.24, 0.045, 12)
    for ni in range(10):
        a0 = (2.0 * math.pi * ni) / 10
        a1 = (2.0 * math.pi * (ni + 1)) / 10
        p0t = (rim_xy[0] + 0.22 * math.cos(a0), rim_xy[1] + 0.22 * math.sin(a0), 3.04)
        p1t = (rim_xy[0] + 0.22 * math.cos(a1), rim_xy[1] + 0.22 * math.sin(a1), 3.04)
        p1b = (rim_xy[0] + 0.14 * math.cos(a1), rim_xy[1] + 0.14 * math.sin(a1), 2.66)
        p0b = (rim_xy[0] + 0.14 * math.cos(a0), rim_xy[1] + 0.14 * math.sin(a0), 2.66)
        nb.quad_enu(mats["white_alu"], p0b, p1b, p1t, p0t, (0.1, 0.1, 0.9, 0.9), 0.88, 0.98, double_sided=True)


def add_ac_unit(nb: NodeBuilder, cx: float, cy: float, z_bot: float, yaw_face_rad: float, mats: dict) -> None:
    """Split AC outdoor condenser unit on wall brackets (+ly points outward from wall)."""
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def pt(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, z_bot + lz)

    # Twin steel L-brackets
    for bx in (-0.30, 0.30):
        b_xy = pt(bx, 0.0, 0.0)
        nb.add_box(mats["dark_steel"], b_xy[0], b_xy[1], z_bot - 0.06, 0.04, 0.36, 0.04, yaw_face_rad)
    # Off-white condenser body (0.82m wide x 0.32m deep x 0.56m tall)
    nb.add_box(mats["white_alu"], cx, cy, z_bot, 0.82, 0.32, 0.56, yaw_face_rad, ao_bot=0.82, ao_top=0.98)
    # Textured front fan grille facing +ly
    nb.quad_enu(
        mats["details"],
        pt(0.40, 0.168, 0.02), pt(-0.40, 0.168, 0.02),
        pt(-0.40, 0.168, 0.54), pt(0.40, 0.168, 0.54),
        UV_AC_UNIT_FRONT, 0.90, 1.0,
    )


def add_pingpong_table(nb: NodeBuilder, cx: float, cy: float, yaw_rad: float, mats: dict) -> None:
    """Standard outdoor ping-pong table (2.74m x 1.525m x 0.76m) with royal-blue top & red steel legs."""
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

    def rot(lx: float, ly: float) -> Vec2:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs)

    # Blue table top with white markings
    nb.add_box(
        mats["blue_steel"], cx, cy, 0.72, 2.74, 1.525, 0.055, yaw_rad,
        ao_bot=0.78, ao_top=0.98, top_mat=mats["details"], top_uv=UV_PINGPONG_TOP,
    )
    # Center net assembly across width
    nb.add_box(mats["white_alu"], cx, cy, 0.775, 0.03, 1.64, 0.155, yaw_rad)
    # 4 Crimson tubular support legs + cross stretcher
    for lx in (-0.92, 0.92):
        for ly in (-0.52, 0.52):
            lp = rot(lx, ly)
            nb.add_box(mats["crimson"], lp[0], lp[1], 0.03, 0.06, 0.06, 0.69, yaw_rad)
        sp = rot(lx, 0.0)
        nb.add_box(mats["crimson"], sp[0], sp[1], 0.24, 0.05, 1.04, 0.05, yaw_rad)


def add_taihu_rockery_basin(nb: NodeBuilder, cx: float, cy: float, mats: dict) -> None:
    """Traditional multi-peak Taihu limestone rockery inside octagonal dark-slate curbed basin (Photo 5)."""
    segs = 8
    r_out, r_in = 2.45, 2.15
    z0, z1 = 0.02, 0.54
    for i in range(segs):
        a0 = (2.0 * math.pi * i) / segs + math.pi / 8
        a1 = (2.0 * math.pi * (i + 1)) / segs + math.pi / 8
        o0 = (cx + r_out * math.cos(a0), cy + r_out * math.sin(a0))
        o1 = (cx + r_out * math.cos(a1), cy + r_out * math.sin(a1))
        i0 = (cx + r_in * math.cos(a0), cy + r_in * math.sin(a0))
        i1 = (cx + r_in * math.cos(a1), cy + r_in * math.sin(a1))
        nb.quad_enu(mats["details"], (o0[0], o0[1], z0), (o1[0], o1[1], z0), (o1[0], o1[1], z1), (o0[0], o0[1], z1), UV_DARK_SLATE_PODIUM, 0.76, 0.96)
        nb.quad_enu(mats["surf"], (i0[0], i0[1], z1), (o0[0], o0[1], z1), (o1[0], o1[1], z1), (i1[0], i1[1], z1), UV_PLAZA_TILE, 0.94, 0.98)
    # Pebble/stone bed inside basin + small south-facing white inscription plaque on curb
    nb.add_cylinder(mats["details"], cx, cy, 0.03, r_in, r_in, 0.36, 8, UV_WHITE_PEBBLES, ao_bot=0.80, ao_top=0.92)
    nb.quad_enu(mats["white_alu"], (cx - 0.24, cy - r_out * 0.93, 0.22), (cx + 0.24, cy - r_out * 0.93, 0.22), (cx + 0.24, cy - r_out * 0.93, 0.38), (cx - 0.24, cy - r_out * 0.93, 0.38))
    # Layered craggy Taihu stone peaks (central tall spire + 6 flanking stone crags)
    peaks = [
        (0.0, 0.05, [(0.36, 1.55, 1.55, 1.15, 1.32, 0.98), (1.55, 2.65, 1.28, 0.95, 0.92, 0.72), (2.65, 3.48, 0.88, 0.68, 0.36, 0.30)]),
        (-0.88, -0.18, [(0.36, 1.40, 0.92, 0.80, 0.78, 0.66), (1.40, 2.42, 0.74, 0.64, 0.34, 0.30)]),
        (0.86, -0.12, [(0.36, 1.48, 0.96, 0.82, 0.80, 0.68), (1.48, 2.58, 0.76, 0.64, 0.36, 0.30)]),
        (-0.48, -0.58, [(0.36, 1.25, 0.82, 0.68, 0.62, 0.50), (1.25, 1.92, 0.58, 0.46, 0.28, 0.24)]),
        (0.52, -0.54, [(0.36, 1.30, 0.84, 0.68, 0.64, 0.52), (1.30, 2.05, 0.60, 0.48, 0.30, 0.24)]),
        (-0.56, 0.58, [(0.36, 1.35, 0.88, 0.74, 0.68, 0.56), (1.35, 2.18, 0.64, 0.52, 0.30, 0.26)]),
        (0.58, 0.56, [(0.36, 1.28, 0.86, 0.72, 0.64, 0.54), (1.28, 2.02, 0.60, 0.48, 0.28, 0.24)]),
    ]
    for dx, dy, tiers in peaks:
        add_tapered_monolith(nb, cx + dx, cy + dy, tiers, mats["gates"], UV_SHENDU_GRANITE)


def add_parked_bicycle_row(
    nb: NodeBuilder,
    x_start: float, y_start: float,
    count: int, step_x: float, step_y: float,
    yaw_rad: float, mats: dict,
) -> None:
    """Lightweight recognizable student bicycles (two wheels, frame, handlebars, saddle & front basket)."""
    frame_mats = [mats["dark_steel"], mats["blue_steel"], mats["white_alu"], mats["crimson"], mats["green_rail"]]
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

    for idx in range(count):
        bx = x_start + idx * step_x
        by = y_start + idx * step_y
        fmat = frame_mats[idx % len(frame_mats)]

        def bp(lx: float, ly: float) -> Vec2:
            return (bx + lx * cs - ly * sn, by + lx * sn + ly * cs)

        # Front (+ly = +0.52) & rear (-ly = -0.52) wheels as crisp thin dark discs/tire blocks
        for wy_off in (-0.52, 0.52):
            wc = bp(0.0, wy_off)
            nb.add_box(mats["dark_steel"], wc[0], wc[1], 0.03, 0.055, 0.62, 0.62, yaw_rad, ao_bot=0.68, ao_top=0.92)
            nb.add_box(mats["white_alu"], wc[0], wc[1], 0.13, 0.062, 0.42, 0.42, yaw_rad, ao_bot=0.78, ao_top=0.96)
        # Sloped diamond frame + seatpost + saddle + handlebar stem + front wire basket
        nb.add_box(fmat, bx, by, 0.44, 0.045, 0.92, 0.06, yaw_rad)
        seat = bp(0.0, -0.22)
        nb.add_box(mats["dark_steel"], seat[0], seat[1], 0.48, 0.04, 0.05, 0.36, yaw_rad)
        nb.add_box(mats["dark_steel"], seat[0], seat[1], 0.84, 0.16, 0.24, 0.06, yaw_rad)
        hbar = bp(0.0, 0.42)
        nb.add_box(fmat, hbar[0], hbar[1], 0.48, 0.04, 0.05, 0.48, yaw_rad)
        nb.add_box(mats["dark_steel"], hbar[0], hbar[1], 0.95, 0.52, 0.05, 0.04, yaw_rad)
        bsk = bp(0.0, 0.54)
        nb.add_box(mats["dark_steel"], bsk[0], bsk[1], 0.66, 0.30, 0.24, 0.22, yaw_rad, ao_bot=0.72, ao_top=0.90)


def add_pullup_rack_and_mats(nb: NodeBuilder, mats: dict) -> None:
    """West wall blue chin-up / fitness bar rack + crimson crash mats (Photos 3 & 7)."""
    x_bar = -93.05
    y_bays = [93.5 + i * 3.15 for i in range(8)]
    # Continuous red gymnastics protective mats along base of west wall
    nb.add_box(mats["crimson"], -92.85, 104.5, 0.025, 1.38, 22.8, 0.12, 0.0, ao_bot=0.76, ao_top=0.95)
    for idx, py in enumerate(y_bays):
        nb.add_box(mats["fitness_blue"], x_bar, py, 0.12, 0.09, 0.09, 2.34, 0.0, ao_bot=0.78, ao_top=0.98)
        if idx < len(y_bays) - 1:
            ny = y_bays[idx + 1]
            bar_z = 2.36 if idx % 2 == 0 else 2.18
            nb.add_box(mats["white_alu"], x_bar, (py + ny) * 0.5, bar_z, 0.045, (ny - py), 0.045, 0.0)
            # Hanging blue exercise straps
            for sy in (py + 0.95, ny - 0.95):
                nb.add_box(mats["fitness_blue"], x_bar, sy, bar_z - 0.52, 0.025, 0.03, 0.52, 0.0)


def add_high_ball_fence_and_floodlights(nb: NodeBuilder, mats: dict) -> None:
    """Tall sports perimeter ball-stop fence & stadium twin LED floodlights along playground boundary (Photo 7)."""
    # West wall high ball-stop fence (x = -93.92, y = 82.0..123.5, z = 2.35..5.65)
    y0, y1 = 82.0, 123.5
    n_bays = 10
    z_bot, z_top = 2.35, 5.65
    nb.add_box(mats["blue_steel"], -93.92, (y0 + y1) * 0.5, z_top - 0.05, 0.06, y1 - y0, 0.06, 0.0)
    nb.add_box(mats["blue_steel"], -93.92, (y0 + y1) * 0.5, (z_bot + z_top) * 0.5, 0.05, y1 - y0, 0.05, 0.0)
    for i in range(n_bays + 1):
        fy = y0 + (y1 - y0) * (i / n_bays)
        nb.add_box(mats["blue_steel"], -93.92, fy, z_bot, 0.08, 0.08, z_top - z_bot, 0.0)
        if i < n_bays:
            ny = y0 + (y1 - y0) * ((i + 1) / n_bays)
            # Fine diagonal chain-link tension cables
            nb.quad_enu(mats["blue_steel"], (-93.92, fy, z_bot + 0.08), (-93.92, fy + 0.06, z_bot + 0.08), (-93.92, ny, z_top - 0.08), (-93.92, ny - 0.06, z_top - 0.08), double_sided=True)
            nb.quad_enu(mats["blue_steel"], (-93.92, ny - 0.06, z_bot + 0.08), (-93.92, ny, z_bot + 0.08), (-93.92, fy + 0.06, z_top - 0.08), (-93.92, fy, z_top - 0.08), double_sided=True)

    # Stadium floodlight poles with twin angled LED fixtures (3 on west wall + 1 on east apron)
    for lx, ly, yaw_in in [(-93.65, 89.2, 0.0), (-93.65, 102.8, 0.0), (-93.65, 116.4, 0.0), (-6.15, 106.0, math.pi)]:
        nb.add_cylinder(mats["dark_steel"], lx, ly, 0.0, 0.11, 0.08, 7.25, 8)
        nb.add_box(mats["dark_steel"], lx, ly, 7.20, 0.12, 1.35, 0.08, yaw_in)
        cs, sn = math.cos(yaw_in), math.sin(yaw_in)
        for off_y in (-0.44, 0.44):
            fx = lx - off_y * sn
            fy_p = ly + off_y * cs
            nb.add_box(mats["dark_steel"], fx, fy_p, 7.28, 0.28, 0.46, 0.32, yaw_in)
            face_x = fx + 0.15 * cs
            face_y = fy_p + 0.15 * sn
            nb.add_box(mats["floodlight"], face_x, face_y, 7.31, 0.04, 0.40, 0.24, yaw_in)


def add_pa_speaker_stack(
    nb: NodeBuilder, sx: float, sy: float, yaw_rad: float, mats: dict, z_base: float = 0.0
) -> None:
    """Compact weatherproof outdoor PA speaker cabinet on dual-post steel stand."""
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

    def rot(lx: float, ly: float) -> Vec2:
        return (sx + lx * cs - ly * sn, sy + lx * sn + ly * cs)

    # Compact stone/steel pedestal & twin support stanchions
    nb.add_box(mats["surf"], sx, sy, z_base + 0.0, 0.74, 0.62, 0.22, yaw_rad, UV_QINGZHUAN, ao_bot=0.72, ao_top=0.90)
    for lx in (-0.18, 0.18):
        px, py = rot(lx, 0.0)
        nb.add_box(mats["dark_steel"], px, py, z_base + 0.22, 0.09, 0.12, 0.80, yaw_rad, ao_bot=0.76, ao_top=0.94)
    nb.add_box(mats["dark_steel"], sx, sy, z_base + 0.94, 0.50, 0.14, 0.08, yaw_rad, ao_bot=0.80, ao_top=0.96)
    # Weatherproof dark cabinet (w=0.64m, d=0.48m, h=1.30m) + rain hood
    nb.add_box(mats["dark_steel"], sx, sy, z_base + 1.02, 0.64, 0.48, 1.30, yaw_rad, ao_bot=0.80, ao_top=0.96)
    hood_xy = rot(0.0, -0.03)
    nb.add_box(mats["dark_steel"], hood_xy[0], hood_xy[1], z_base + 2.32, 0.68, 0.56, 0.05, yaw_rad, ao_bot=0.88, ao_top=1.0)
    # Front speaker grille & dual drivers facing -ly (toward playground)
    f0 = rot(-0.28, -0.255)
    f1 = rot(0.28, -0.255)
    nb.quad_enu(
        mats["stage"],
        (f0[0], f0[1], z_base + 1.07),
        (f1[0], f1[1], z_base + 1.07),
        (f1[0], f1[1], z_base + 2.27),
        (f0[0], f0[1], z_base + 2.27),
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
def build_west_campus(data_path: str, tex_dir: str, out_glb: str) -> Tuple[int, int]:
    west = json.loads(Path(data_path).read_text())
    ways = {w["id"]: w for w in west["ways"]}
    exp = GLBExporter()
    mats = init_materials(exp, tex_dir, include_west_details=True)

    # ---- Campus_Ground_West ----
    gnd = exp.add_node("Campus_Ground_West")
    gnd.add_polygon_patch(ways["352521262"]["pts"], 0.0, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    # Surrounding road base (below y=0 slightly)
    gnd.add_box(mats["surf"], -35.0, 60.0, -0.18, 290.0, 270.0, 0.16, 0.0, UV_ASPHALT, ao_bot=0.92, ao_top=0.92)
    # East entry driveway stone pavement leading to 1F bike portal (W-ST1) & Cafeteria (W-B6) + 同福夹道 alley strip
    gnd.add_polygon_patch([(-4.5, 5.2), (3.6, 5.2), (3.6, 75.2), (-5.2, 75.2)], 0.02, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    gnd.add_polygon_patch([(-5.2, 87.3), (3.6, 87.3), (3.6, 96.5), (-5.2, 96.5)], 0.02, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    gnd.add_polygon_patch([(-4.2, -55.0), (4.2, -55.0), (4.2, 5.2), (-4.2, 5.2)], -0.01, mats["surf"], UV_ASPHALT, ao=0.95)
    # Stone-paved passage east of 校史馆 (W-H1), north alley & straight W-B5 south veranda walk
    gnd.add_polygon_patch([(-70.2, 124.6), (-65.0, 124.6), (-65.0, 136.85), (-70.2, 136.85)], 0.025, mats["surf"], UV_PLAZA_TILE, ao=0.96)
    gnd.add_polygon_patch([(-93.6, 133.1), (-70.0, 133.1), (-70.0, 136.85), (-93.6, 136.85)], 0.028, mats["surf"], UV_PLAZA_TILE, ao=0.94)
    gnd.add_polygon_patch([(-70.2, 134.8), (-7.6, 134.8), (-7.6, 136.85), (-70.2, 136.85)], 0.027, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    # Decorative crazy-paving stone medallion in north alley east entry (Photo 1 foreground)
    gnd.quad_enu(
        mats["details"],
        (-72.0, 133.75, 0.036), (-70.35, 133.75, 0.036),
        (-70.35, 135.15, 0.036), (-72.0, 135.15, 0.036),
        UV_CRAZY_PAVING, 0.95, 0.98,
    )

    # Playground South Plaza Strip (matching true B/C stepped north profile)
    # West side: 石砖地 (Stone-brick open plaza including north recess x=-69.5..-55.2)
    gnd.add_polygon_patch(
        [(-89.8, 76.2), (-69.8, 77.2), (-69.5, 66.8), (-55.2, 66.8), (-55.2, 87.3), (-89.8, 87.3)],
        0.025, mats["surf"], UV_PLAZA_TILE, ao=0.96,
    )
    # East side: 自行车停放区（无车棚） + 外置楼梯东侧一层推车穿堂连接道 (Photos 4 & 7)
    gnd.add_polygon_patch(
        [(-46.8, 68.2), (-37.5, 68.4), (-11.5, 84.5), (-11.5, 87.3), (-46.8, 87.3)],
        0.032, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.92,
    )
    gnd.add_polygon_patch(
        [(-11.5, 84.5), (-9.5, 83.2), (-0.45, 83.2), (-0.45, 87.3), (-11.5, 87.3)],
        0.032, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.92,
    )
    gnd.add_polygon_patch(
        [(-0.45, 74.8), (3.35, 74.8), (3.35, 87.3), (-0.45, 87.3)],
        0.032, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.91,
    )
    # Low stone curb separating south bicycle plaza from track apron
    gnd.add_box(mats["surf"], -29.2, 87.32, 0.02, 35.4, 0.24, 0.11, 0.0, UV_PLAZA_TILE, ao_bot=0.80, ao_top=0.98)
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
    # Two rows of open steel wheel racks + realistic parked student bicycles (strictly unroofed, Photo 7)
    for rack_y in (79.8, 83.8):
        gnd.add_box(mats["dark_steel"], -29.5, rack_y, 0.035, 28.0, 0.14, 0.10, 0.0)
        for rx_i in range(18):
            rx = -42.5 + rx_i * 1.52
            gnd.add_box(mats["blue_steel"], rx, rack_y, 0.13, 0.07, 0.52, 0.36, 0.0)
    add_parked_bicycle_row(gnd, -41.8, 79.85, 16, 1.62, 0.0, 0.28, mats)
    add_parked_bicycle_row(gnd, -41.2, 83.85, 15, 1.68, 0.0, -0.24, mats)

    # North-east rockery & ping-pong plaza east of Chairman Stage (closed cleanly inside NE boundary wall)
    gnd.add_polygon_patch(
        [(-32.8, 124.6), (-6.0, 124.6), (-6.0, 127.5), (-7.6, 134.9), (-32.8, 134.9)],
        0.026, mats["surf"], UV_PLAZA_TILE, ao=0.96,
    )
    add_taihu_rockery_basin(gnd, -26.0, 129.8, mats)
    for ppx, ppy, ppyaw in [(-30.0, 128.4, 0.0), (-21.6, 128.8, 0.0), (-16.8, 129.0, 0.0), (-22.0, 131.6, 0.0)]:
        add_pingpong_table(gnd, ppx, ppy, ppyaw, mats)

    # Green lawn south of B-Wing & C-Wing junction + forecourt stone strip in front of B座 SE corner
    gnd.add_polygon_patch(
        [(-41.5, 42.5), (-5.2, 42.5), (-5.2, 68.0), (-10.2, 68.0), (-35.5, 55.6), (-41.5, 55.6)],
        0.025, mats["surf"], UV_GRASS, ao=0.94,
    )
    gnd.add_polygon_patch(
        [(-35.5, 55.6), (-10.2, 68.0), (-5.2, 68.0), (-5.2, 72.8), (-5.8, 72.8), (-35.5, 57.5)],
        0.025, mats["surf"], UV_PLAZA_TILE, ao=0.97,
    )
    # Low clipped ornamental shrubs immediately west of 慎独石 along B座 forecourt edge
    for bsx, bsy, br in ((-8.3, 69.6, 0.48), (-9.4, 69.0, 0.42)):
        gnd.add_cylinder(mats["leaf"], bsx, bsy, 0.03, br, br * 0.75, br * 1.35, 8, UV_FOLIAGE, ao_bot=0.74, ao_top=0.96)

    # Campus Perimeter Rendered Wall with Structural Pilasters & Coping (Photos 3 & 7)
    bound = ensure_ccw(ways["352521262"]["pts"])
    for i in range(len(bound)):
        a, b = bound[i], bound[(i + 1) % len(bound)]
        if a[1] < 8.0 and b[1] < 8.0 and -11.5 <= a[0] <= 5.0 and -11.5 <= b[0] <= 5.0:
            continue  # Open for West Gate & Guardhouse facade
        if min(a[1], b[1]) >= 96.4 and max(a[1], b[1]) <= 127.6 and min(a[0], b[0]) >= -5.7:
            continue  # W-B6 Cafeteria exterior walls form the campus boundary here
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 0.5:
            continue
        yaw = math.atan2(dy, dx)
        mx, my = (a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5
        gnd.add_box(mats["wall_grey_render"], mx, my, 0.0, L, 0.34, 2.30, yaw, ao_bot=0.76, ao_top=0.95)
        gnd.add_box(mats["surf"], mx, my, 2.30, L + 0.06, 0.44, 0.09, yaw, UV_QINGZHUAN, ao_bot=0.86, ao_top=0.98)
        n_pil = max(2, int(L // 4.2) + 1)
        for pi in range(n_pil):
            t_p = pi / (n_pil - 1)
            px = a[0] + dx * t_p
            py = a[1] + dy * t_p
            gnd.add_box(mats["surf"], px, py, 0.0, 0.42, 0.44, 2.38, yaw, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.96)

    # West wall fitness pull-up bars + red mats & high ball-stop fence + floodlights
    add_pullup_rack_and_mats(gnd, mats)
    add_high_ball_fence_and_floodlights(gnd, mats)

    # ---- W-G1: 同福夹道3号正门 + 左侧大理石保安厅（含转角观察窗、东侧出入门与挑檐） ----
    gate = exp.add_node("W-G1")
    # Twin marble gate piers
    gate.add_box(mats["gates"], -4.2, 5.2, 0.0, 1.2, 1.5, 4.4, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.98)
    gate.add_box(mats["gates"], 3.2, 5.2, 0.0, 1.4, 1.5, 4.4, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.98)
    # Guardhouse (left/west of gate: x -10.90..-5.65, y 4.80..10.40) with recessed doors & windows
    gate.add_box(mats["gates"], -8.275, 7.60, 0.0, 5.25, 5.60, 0.10, 0.0, UV_MARBLE, ao_bot=0.74, ao_top=0.90)
    gate.add_box(mats["gates"], -8.275, 7.60, 3.32, 5.25, 5.60, 0.28, 0.0, UV_MARBLE, ao_bot=0.86, ao_top=0.96, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    # White aluminum overhanging canopy extending east to join left gate pier
    gate.add_box(mats["white_alu"], -7.875, 7.60, 3.58, 6.35, 5.80, 0.30, 0.0, ao_bot=0.88, ao_top=1.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    # South marble wall (SW solid pier + window apron) + recessed SE corner service window
    gate.add_box(mats["gates"], -9.875, 4.98, 0.10, 2.05, 0.36, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    gate.quad_enu(mats["gates"], (-10.35, 4.78, 2.25), (-9.35, 4.78, 2.25), (-9.35, 4.78, 2.85), (-10.35, 4.78, 2.85), UV_EAST_SIGN, 0.92, 1.0)
    gate.quad_enu(mats["crimson"], (-10.08, 4.77, 1.82), (-9.62, 4.77, 1.82), (-9.62, 4.77, 2.12), (-10.08, 4.77, 2.12), (0.1, 0.1, 0.9, 0.9), 0.94, 1.0)
    gate.add_box(mats["gates"], -7.25, 4.98, 0.10, 3.20, 0.36, 0.95, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94)
    gate.add_box(mats["gates"], -7.25, 4.93, 1.01, 3.24, 0.44, 0.05, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.98)
    gate.quad_enu(mats["glass"], (-8.85, 4.94, 1.05), (-5.79, 4.94, 1.05), (-5.79, 4.94, 3.32), (-8.85, 4.94, 3.32), UV_GLASS_WINDOW)
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
    gate.quad_enu(mats["glass"], (-5.79, 4.94, 1.05), (-5.79, 7.35, 1.05), (-5.79, 7.35, 3.32), (-5.79, 4.94, 3.32), UV_GLASS_WINDOW)
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
    gate.quad_enu(mats["glass"], (-5.79, 7.72, 0.92), (-5.79, 8.78, 0.92), (-5.79, 8.78, 2.29), (-5.79, 7.72, 2.29), UV_GLASS_WINDOW)
    gate.add_box(mats["white_alu"], -5.73, 7.84, 0.96, 0.05, 0.05, 0.38, 0.0)
    # Pier & East North-bay window (y: 8.85..10.40)
    gate.add_box(mats["gates"], -5.83, 8.975, 0.10, 0.36, 0.25, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    gate.add_box(mats["gates"], -5.83, 9.625, 0.10, 0.36, 1.05, 1.05, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94)
    gate.add_box(mats["gates"], -5.83, 9.625, 2.95, 0.36, 1.05, 0.37, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.95)
    gate.add_box(mats["gates"], -5.79, 9.625, 1.11, 0.44, 1.08, 0.05, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.98)
    gate.quad_enu(mats["glass"], (-5.79, 9.10, 1.15), (-5.79, 10.15, 1.15), (-5.79, 10.15, 2.95), (-5.79, 9.10, 2.95), UV_GLASS_WINDOW)
    gate.add_box(mats["dark_steel"], -5.75, 9.625, 1.15, 0.09, 0.06, 1.80, 0.0)
    gate.add_box(mats["dark_steel"], -5.75, 9.625, 2.90, 0.09, 1.05, 0.06, 0.0)
    gate.add_box(mats["dark_steel"], -5.75, 9.625, 1.16, 0.09, 1.05, 0.05, 0.0)
    gate.add_box(mats["gates"], -5.83, 10.275, 0.10, 0.36, 0.25, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    # West wall with recessed daylight window + North solid wall
    gate.add_box(mats["gates"], -10.72, 5.68, 0.10, 0.36, 1.04, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95)
    gate.add_box(mats["gates"], -10.72, 7.60, 0.10, 0.36, 2.80, 1.05, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94)
    gate.add_box(mats["gates"], -10.72, 7.60, 2.95, 0.36, 2.80, 0.37, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.95)
    gate.quad_enu(mats["glass"], (-10.76, 9.00, 1.15), (-10.76, 6.20, 1.15), (-10.76, 6.20, 2.95), (-10.76, 9.00, 2.95), UV_GLASS_WINDOW)
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
    # Overhead fascia header (plain brown-red metal cladding + paved roof + soffit), single centered LED screen & East pier plaque
    gate.add_box(
        mats["gates"], -2.05, 5.15, 4.35, 13.0, 1.95, 1.35, 0.0,
        UV_WEST_FASCIA_PLAIN, ao_bot=0.82, ao_top=0.98,
        top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
    )
    gate.add_box(mats["white_alu"], -2.05, 5.15, 4.32, 12.92, 1.88, 0.03, 0.0, ao_bot=0.86, ao_top=0.94)
    gate.add_box(mats["dark_steel"], -0.45, 4.21, 4.52, 7.80, 0.10, 1.02, 0.0, ao_bot=0.82, ao_top=0.98)
    gate.quad_enu(
        mats["led"],
        (-4.25, 4.15, 4.58), (3.35, 4.15, 4.58),
        (3.35, 4.15, 5.48), (-4.25, 4.15, 5.48),
        UV_WEST_LED_ONLY, 1.0, 1.0,
    )
    gate.quad_enu(mats["gates"], (2.68, 4.42, 0.9), (3.72, 4.42, 0.9), (3.72, 4.42, 3.45), (2.68, 4.42, 3.45), UV_WEST_PLAQUE, 0.95, 1.0)
    for wing_x in (-3.25, 1.95):
        gate.add_box(mats["dark_steel"], wing_x, 6.8, 0.15, 0.12, 3.1, 2.2, 0.0, ao_bot=0.80, ao_top=1.0)
        for pi in range(9):
            py = 5.4 + pi * 0.34
            gate.add_box(mats["dark_steel"], wing_x, py, 0.25, 0.06, 0.06, 2.35, 0.0, ao_bot=0.85, ao_top=1.0)
    for hi in range(4):
        yoff = -1.5 + hi * 1.4
        gate.quad_enu(mats["yellow_hatch"], (-3.8, yoff, 0.015), (2.8, yoff, 0.015), (2.8, yoff + 0.14, 0.015), (-3.8, yoff + 0.14, 0.015))
        xoff = -3.4 + hi * 1.8
        gate.quad_enu(mats["yellow_hatch"], (xoff, -2.0, 0.015), (xoff + 0.14, -2.0, 0.015), (xoff + 0.14, 3.6, 0.015), (xoff, 3.6, 0.015))

    # ---- W-L1: 慎独石 (located in front of B座 SE corner, facing South driveway) ----
    shendu = exp.add_node("W-L1")
    shendu.add_box(mats["surf"], -6.6, 70.0, 0.025, 1.82, 1.06, 0.16, 0.0, UV_QINGZHUAN, ao_bot=0.72, ao_top=0.90)
    add_tapered_monolith(
        shendu,
        -6.6, 70.0,
        [
            (0.18, 1.35, 1.56, 0.86, 1.48, 0.80),
            (1.35, 2.45, 1.48, 0.80, 1.32, 0.72),
            (2.45, 3.15, 1.32, 0.72, 0.96, 0.56),
            (3.15, 3.52, 0.96, 0.56, 0.48, 0.34),
        ],
        mats["gates"], UV_SHENDU_GRANITE,
    )
    shendu.quad_enu(mats["gates"], (-7.26, 69.55, 0.32), (-5.94, 69.55, 0.32), (-6.12, 69.65, 2.85), (-7.08, 69.65, 2.85), UV_SHENDU_STONE, 0.90, 1.0)

    # ---- W-L3: 冰心像 (B座南侧绿地北部，靠近 B 座南侧人行通道与庭院) ----
    bx_node = exp.add_node("W-L3")
    bx_node.add_box(mats["surf"], -16.5, 58.8, 0.03, 3.0, 3.0, 0.18, 0.0, UV_QINGZHUAN, ao_bot=0.78, ao_top=0.92)
    bx_node.add_box(mats["white_alu"], -16.5, 58.8, 0.18, 1.5, 1.5, 0.25, 0.0)
    bx_node.add_box(mats["gates"], -16.5, 58.8, 0.43, 0.86, 0.86, 1.35, 0.0, UV_MARBLE, ao_bot=0.80, ao_top=0.98)
    bx_node.add_cylinder(mats["dark_steel"], -16.5, 58.8, 1.78, 0.36, 0.22, 0.82, 12, ao_bot=0.78, ao_top=1.0)

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
    # Ground-floor North-facing classroom/corridor double doors + parked bikes along B座 north plinth (Photo 4)
    for door_along in (10.5, 21.8):
        nd_c = (-11.5 + wb3_ntx * door_along + wb3_nnx * 0.12, 84.5 + wb3_nty * door_along + wb3_nny * 0.12)
        wb3.add_box(mats["dark_steel"], nd_c[0], nd_c[1], 0.12, 2.30, 0.22, 2.75, math.atan2(wb3_n_dy, wb3_n_dx))
        nd_l = (-11.5 + wb3_ntx * (door_along - 1.02) + wb3_nnx * 0.24, 84.5 + wb3_nty * (door_along - 1.02) + wb3_nny * 0.24)
        nd_r = (-11.5 + wb3_ntx * (door_along + 1.02) + wb3_nnx * 0.24, 84.5 + wb3_nty * (door_along + 1.02) + wb3_nny * 0.24)
        wb3.quad_enu(mats["glass"], (nd_l[0], nd_l[1], 0.20), (nd_r[0], nd_r[1], 0.20), (nd_r[0], nd_r[1], 2.65), (nd_l[0], nd_l[1], 2.65), UV_GLASS_WINDOW, 0.88, 0.98)
    add_parked_bicycle_row(
        wb3,
        -15.2 + wb3_nnx * 0.95, 82.2 + wb3_nny * 0.95,
        13, wb3_ntx * 1.55, wb3_nty * 1.55,
        wb3_n_yaw, mats,
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
    # Cantilevered entrance canopy + steel tie rods
    canc = wb3_dpt(0.0, 0.72)
    wb3.add_box(mats["white_alu"], canc[0], canc[1], 3.12, 3.90, 1.44, 0.18, wb3_yaw, ao_bot=0.86, ao_top=1.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for tie_s in (-1.65, 1.65):
        tw = wb3_dpt(tie_s, 0.20)
        tf = wb3_dpt(tie_s, 1.25)
        wb3.quad_enu(
            mats["dark_steel"],
            (tw[0], tw[1], 3.84), (tf[0], tf[1], 3.30),
            (tf[0], tf[1], 3.35), (tw[0], tw[1], 3.89),
            (0.1, 0.1, 0.9, 0.9), 0.90, 0.95, double_sided=True,
        )

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
    )
    # Split AC units along W-B2's exposed 90° East return wall (Photo 6 right side!)
    for st_ac in (1, 2, 3, 4):
        add_ac_unit(wb2, -46.62, 70.1, 0.92 + st_ac * 3.60, -math.pi * 0.5, mats)
    # Rooftop stair/elevator penthouse bulkhead
    wb2.add_box(mats["surf"], -51.0, 71.8, 22.65, 6.8, 6.4, 2.55, 0.0, UV_GREY_RIB, ao_bot=0.85, ao_top=0.98)
    wb2.add_box(mats["surf"], -51.0, 71.8, 25.20, 7.2, 6.8, 0.24, 0.0, UV_PLAZA_TILE, ao_bot=0.92, ao_top=1.0)
    # North ground-floor glazed doorway portal exiting onto south plaza
    wb2.add_box(mats["surf"], -51.0, 78.15, 0.0, 4.6, 1.9, 3.55, 0.0, UV_GREY_RIB, ao_bot=0.78, ao_top=0.96)
    wb2.add_box(mats["white_alu"], -51.0, 78.25, 3.55, 5.1, 2.2, 0.22, 0.0)
    wb2.quad_enu(mats["glass"], (-49.3, 79.14, 0.18), (-52.7, 79.14, 0.18), (-52.7, 79.14, 2.85), (-49.3, 79.14, 2.85), UV_GLASS_WINDOW)

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
    # Hero 5-Story White Classical Column & Portrait Bas-Relief Wall on C座 North Facade (Photo 2!)
    c_n_yaw = math.atan2(77.2 - 76.2, -69.8 - (-89.8))  # ~ +0.05 rad along (-89.8,76.2)->(-69.8,77.2)
    c_nnx, c_nny = -math.sin(c_n_yaw), math.cos(c_n_yaw)  # outward North normal (-0.05, +0.9988)
    rel_cx, rel_cy = -79.8 + c_nnx * 0.22, 76.7 + c_nny * 0.22
    wb1.add_box(mats["white_alu"], rel_cx, rel_cy, 1.10, 5.65, 0.42, 18.25, c_n_yaw, ao_bot=0.86, ao_top=0.99)
    # Relief textured front face (looking South from playground: Left is East +2.74, Right is West -2.74)
    cs_c, sn_c = math.cos(c_n_yaw), math.sin(c_n_yaw)
    r_p0 = (rel_cx + 2.74 * cs_c + c_nnx * 0.23, rel_cy + 2.74 * sn_c + c_nny * 0.23)
    r_p1 = (rel_cx - 2.74 * cs_c + c_nnx * 0.23, rel_cy - 2.74 * sn_c + c_nny * 0.23)
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
    # Rooftop Open Dark-Steel Pergola Frame on C座 north block (Photo 2 top!)
    wb1_roof_z = 0.85 + 6 * 3.80 + 0.25
    for px_r in (-87.8, -82.4, -77.0, -71.6):
        for py_r in (60.6, 68.0, 75.2):
            wb1.add_box(mats["dark_steel"], px_r, py_r, wb1_roof_z, 0.26, 0.26, 1.65, c_n_yaw)
    for ly in (60.6, 64.3, 68.0, 71.6, 75.2):
        wb1.add_box(mats["dark_steel"], -79.7, ly, wb1_roof_z + 1.55, 17.0, 0.22, 0.26, c_n_yaw, ao_bot=0.86, ao_top=1.0)
    for lx in (-87.8, -82.4, -77.0, -71.6):
        wb1.add_box(mats["dark_steel"], lx, 67.9, wb1_roof_z + 1.55, 0.22, 15.0, 0.26, 0.0, ao_bot=0.86, ao_top=1.0)
    # C座 South-West Exterior Return Staircase (between C座 south wing west wall and west boundary)
    wb1.add_box(mats["surf"], -82.6, 42.0, 0.0, 4.4, 9.6, 0.85, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.90)
    for lvl in range(5):
        sz = 0.85 + lvl * 3.80
        wb1.add_box(mats["white_alu"], -82.6, 42.0, sz + 1.85, 4.1, 9.2, 0.28, 0.0)
        wb1.add_box(mats["blue_steel"], -84.6, 42.0, sz + 0.2, 0.12, 9.2, 3.6, 0.0)
        wb1.add_box(mats["blue_steel"], -82.6, 37.4, sz + 0.2, 4.0, 0.12, 3.6, 0.0)
        wb1.add_box(mats["blue_steel"], -82.6, 46.6, sz + 0.2, 4.0, 0.12, 3.6, 0.0)
    # Red "C 教学楼" book plaque on C座 south wing south wall
    wb1.quad_enu(mats["stage"], (-75.8, 33.86, 17.5), (-72.5, 33.91, 17.5), (-72.5, 33.91, 21.2), (-75.8, 33.86, 21.2), UV_BOOK_C, 0.95, 1.0)

    # ---- W-R1: 室外弧形无障碍大坡道 + 大雪松 ----
    # Exits 2F of W-B2 (楼梯间) going south, then bending southeast convex SW / concave NE
    wr1 = exp.add_node("W-R1")
    ramp_pts: List[Vec3] = []
    segs_r = 28
    pA, pB, pC, pD = (-45.0, 57.5), (-43.5, 44.5), (-24.0, 41.5), (-9.5, 38.0)
    for k in range(segs_r + 1):
        t = k / segs_r
        mt = 1.0 - t
        e = mt**3 * pA[0] + 3 * mt**2 * t * pB[0] + 3 * mt * t**2 * pC[0] + t**3 * pD[0]
        n = mt**3 * pA[1] + 3 * mt**2 * t * pB[1] + 3 * mt * t**2 * pC[1] + t**3 * pD[1]
        h = 4.25 * (1.0 - t) + 0.18
        ramp_pts.append((e, n, h))

    half_w = 1.55
    for k in range(segs_r):
        a0, a1 = ramp_pts[k], ramp_pts[k + 1]
        dx, dy = a1[0] - a0[0], a1[1] - a0[1]
        ll = max(math.hypot(dx, dy), 0.01)
        nx, ny = dy / ll, -dx / ll
        l0, r0 = (a0[0] - nx * half_w, a0[1] - ny * half_w, a0[2]), (a0[0] + nx * half_w, a0[1] + ny * half_w, a0[2])
        l1, r1 = (a1[0] - nx * half_w, a1[1] - ny * half_w, a1[2]), (a1[0] + nx * half_w, a1[1] + ny * half_w, a1[2])
        wr1.quad_enu(mats["surf"], l0, r0, r1, l1, UV_ASPHALT, 0.94, 0.98)
        wr1.quad_enu(mats["white_alu"], r0, l0, l1, r1, (0.1, 0.1, 0.9, 0.9), 0.72, 0.72)
        for side_s in (-1.0, 1.0):
            s0 = (a0[0] + side_s * nx * half_w, a0[1] + side_s * ny * half_w, a0[2])
            s1 = (a1[0] + side_s * nx * half_w, a1[1] + side_s * ny * half_w, a1[2])
            wr1.quad_enu(mats["white_alu"], (s0[0], s0[1], s0[2] - 0.34), (s1[0], s1[1], s1[2] - 0.34), (s1[0], s1[1], s1[2] + 0.18), (s0[0], s0[1], s0[2] + 0.18), (0.1, 0.1, 0.9, 0.9), 0.85, 1.0, double_sided=True)
            wr1.quad_enu(mats["dark_steel"], (s0[0], s0[1], s0[2] + 1.08), (s1[0], s1[1], s1[2] + 1.08), (s1[0], s1[1], s1[2] + 1.15), (s0[0], s0[1], s0[2] + 1.15), (0.1, 0.1, 0.9, 0.9), 0.95, 1.0, double_sided=True)
            if k % 2 == 0:
                wr1.add_box(mats["crimson"], (s0[0] + s1[0]) * 0.5, (s0[1] + s1[1]) * 0.5, s0[2] + 0.20, 0.9, 0.25, 0.28, math.atan2(dy, dx))
        if k % 4 == 0:
            wr1.add_cylinder(mats["white_alu"], a0[0], a0[1], 0.0, 0.22, 0.20, a0[2] - 0.25, 8)
    # Hero Snow Cedar in NE concave pocket beside the ramp
    wr1.add_tree(-27.5, 50.5, "cedar", 14.5, mats["trunk"], mats["leaf"])

    # ---- W-B4: 南院 A 座综合楼与图书馆（way 636389217 + 北向图书馆出入口 + 1层南门接建） ----
    wb4 = exp.add_node("W-B4")
    wb4_pts = ensure_ccw(ways["636389217"]["pts"])
    wb4.add_detailed_building(
        wb4_pts, stories=3, story_h=3.6, plinth_h=0.85,
        wall_mat=mats["surf"], wall_uv=UV_GREY_RIB,
        band_mat=mats["surf"], band_uv=UV_TERRACOTTA_BRICK,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
    )
    # Smooth NE curved drum corner facing the ramp landing
    for ai in range(10):
        ang0 = -0.30 + (ai / 10.0) * 1.80
        ang1 = -0.30 + ((ai + 1) / 10.0) * 1.80
        cx_arc, cy_arc, rad = -20.8, 31.7, 6.9
        p0 = (cx_arc + rad * math.cos(ang0), cy_arc + rad * math.sin(ang0))
        p1 = (cx_arc + rad * math.cos(ang1), cy_arc + rad * math.sin(ang1))
        wb4.quad_enu(mats["surf"], (p0[0], p0[1], 0.0), (p1[0], p1[1], 0.0), (p1[0], p1[1], 4.45), (p0[0], p0[1], 4.45), UV_TERRACOTTA_BRICK, 0.78, 0.94)
        wb4.quad_enu(mats["surf"], (p0[0], p0[1], 4.45), (p1[0], p1[1], 4.45), (p1[0], p1[1], 11.65), (p0[0], p0[1], 11.65), UV_GREY_RIB, 0.88, 0.98)
    # North-facing 1F Library Entrance Portal on bay bi=3 (cx=-32.275, y=38.20, facing +Y North)
    lib_cx = -32.275
    wb4.add_box(mats["gates"], lib_cx, 38.75, 0.0, 3.90, 1.10, 0.16, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wb4.add_box(mats["gates"], lib_cx, 39.30, 0.0, 4.10, 0.50, 0.08, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for lx_off in (-1.52, 1.52):
        wb4.add_box(mats["gates"], lib_cx + lx_off, 38.36, 0.16, 0.50, 0.40, 4.02, 0.0, UV_MARBLE, ao_bot=0.78, ao_top=0.96, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wb4.add_box(mats["surf"], lib_cx, 38.36, 3.06, 3.54, 0.40, 1.12, 0.0, UV_STUCCO, ao_bot=0.84, ao_top=0.96)
    wb4.add_box(mats["dark_steel"], lib_cx, 38.28, 0.16, 2.58, 0.26, 2.92, 0.0, ao_bot=0.78, ao_top=0.94)
    wb4.quad_enu(mats["glass"], (lib_cx + 1.22, 38.43, 0.24), (lib_cx - 1.22, 38.43, 0.24), (lib_cx - 1.22, 38.43, 2.48), (lib_cx + 1.22, 38.43, 2.48), UV_GLASS_WINDOW, 0.90, 1.0)
    wb4.quad_enu(mats["glass"], (lib_cx + 1.22, 38.43, 2.56), (lib_cx - 1.22, 38.43, 2.56), (lib_cx - 1.22, 38.43, 3.00), (lib_cx + 1.22, 38.43, 3.00), UV_GLASS_WINDOW, 0.90, 1.0)
    for mx_off, mw, mz0, mz1 in [(-1.24, 0.08, 0.16, 3.06), (0.0, 0.07, 0.16, 3.06), (1.24, 0.08, 0.16, 3.06), (-0.14, 0.04, 0.94, 1.46), (0.14, 0.04, 0.94, 1.46)]:
        wb4.add_box(mats["white_alu"], lib_cx + mx_off, 38.45, mz0, mw, 0.06, mz1 - mz0, 0.0)
    wb4.add_box(mats["white_alu"], lib_cx, 38.45, 2.48, 2.56, 0.06, 0.08, 0.0)
    # Library canopy + "图书馆 / LIBRARY" signboard facing North (+Y)
    wb4.add_box(mats["white_alu"], lib_cx, 38.92, 3.12, 3.90, 1.48, 0.18, 0.0, ao_bot=0.86, ao_top=1.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for tie_x in (lib_cx - 1.65, lib_cx + 1.65):
        wb4.quad_enu(mats["dark_steel"], (tie_x, 38.42, 3.92), (tie_x, 39.48, 3.30), (tie_x, 39.48, 3.35), (tie_x, 38.42, 3.97), (0.1, 0.1, 0.9, 0.9), 0.90, 0.95, double_sided=True)
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
    # East entry doorway, granite step & small dark-steel canopy facing main driveway
    wb4.add_box(mats["surf"], -5.41, 17.25, 0.0, 0.48, 1.50, 0.10, 0.0, UV_QINGZHUAN, ao_bot=0.78, ao_top=0.94)
    wb4.add_box(mats["dark_steel"], -5.54, 17.25, 0.10, 0.12, 1.32, 2.25, 0.0, ao_bot=0.78, ao_top=0.95)
    wb4.quad_enu(mats["glass"], (-5.47, 16.65, 0.16), (-5.47, 17.85, 0.16), (-5.47, 17.85, 2.25), (-5.47, 16.65, 2.25), UV_GLASS_WINDOW)
    wb4.add_box(mats["white_alu"], -5.45, 16.76, 0.96, 0.04, 0.04, 0.34, 0.0)
    wb4.add_box(mats["dark_steel"], -5.18, 17.25, 2.45, 0.90, 1.65, 0.14, 0.0, ao_bot=0.84, ao_top=1.0)

    # ---- W-ST1: 东北外挂折返楼梯塔 & "尚美" 艺术浮雕壁 (白色Z字实心斜向护墙 + 蓝灰防坠钢网, Photo 4 & ref) ----
    wst1 = exp.add_node("W-ST1")
    wst1.add_box(mats["surf"], -6.8, 80.5, 0.0, 5.4, 5.4, 1.05, 0.0, UV_QINGZHUAN, ao_bot=0.72, ao_top=0.92)
    for pi_st in ((-9.25, 78.05), (-4.35, 78.05), (-9.25, 82.95), (-4.35, 82.95)):
        wst1.add_box(mats["white_alu"], pi_st[0], pi_st[1], 1.05, 0.34, 0.34, 18.6, 0.0)
    for lvl in range(5):
        z0 = 1.05 + lvl * 3.55
        zm = z0 + 1.77
        zt = z0 + 3.55
        # Landing slabs & solid white horizontal landing parapets
        wst1.add_box(mats["white_alu"], -6.8, 79.1, z0, 4.9, 2.0, 0.24, 0.0)
        wst1.add_box(mats["white_alu"], -6.8, 81.9, zm, 4.9, 2.0, 0.24, 0.0)
        wst1.add_box(mats["surf"], -6.8, 78.02, z0, 5.0, 0.18, 1.08, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.99)
        wst1.add_box(mats["surf"], -6.8, 82.98, zm, 5.0, 0.18, 1.08, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.99)
        # Solid white sloped Z-shaped stair stringer balustrades (visible in Photo 4!)
        # West flight rising South->North (z0 -> zm), East/North return flight rising North->South (zm -> zt)
        wst1.quad_enu(
            mats["surf"],
            (-9.32, 78.8, z0), (-9.32, 82.2, zm),
            (-9.32, 82.2, zm + 1.05), (-9.32, 78.8, z0 + 1.05),
            UV_STUCCO, 0.88, 0.99, double_sided=True,
        )
        wst1.quad_enu(
            mats["surf"],
            (-4.28, 82.2, zm), (-4.28, 78.8, zt),
            (-4.28, 78.8, zt + 1.05), (-4.28, 82.2, zm + 1.05),
            UV_STUCCO, 0.88, 0.99, double_sided=True,
        )
        wst1.quad_enu(
            mats["surf"],
            (-4.6, 83.02, zm), (-9.0, 83.02, z0 + 0.45),
            (-9.0, 83.02, z0 + 1.48), (-4.6, 83.02, zm + 1.05),
            UV_STUCCO, 0.88, 0.99, double_sided=True,
        )
        # Dense blue-grey vertical & chevron steel safety grille bars
        for bx_o in (-2.52, 2.52):
            for li in range(9):
                ly = 78.2 + li * 0.58
                wst1.add_box(mats["blue_steel"], -6.8 + bx_o, ly, z0, 0.04, 0.045, 3.55, 0.0)
        for by_o in (-2.52, 2.52):
            for li in range(9):
                lx = -9.12 + li * 0.58
                wst1.add_box(mats["blue_steel"], lx, 80.5 + by_o, z0, 0.045, 0.04, 3.55, 0.0)
    wst1.add_box(mats["white_alu"], -6.8, 80.5, 19.35, 5.3, 5.3, 0.30, 0.0)
    # Twin spotlight post in front of W-ST1 north plinth (west-stairway-2024.webp)
    wst1.add_cylinder(mats["blue_steel"], -7.8, 83.68, 0.0, 0.07, 0.06, 2.85, 8)
    wst1.add_box(mats["white_alu"], -7.8, 83.68, 2.75, 0.68, 0.16, 0.18, 0.0)

    # 1-Story Covered Bike Pass-Through Building east of W-ST1 (spanning to East Campus Wall, y=75.20..83.40)
    # West enclosed Qingzhuan bay (tying cleanly into B座 east gable & W-ST1 east plinth)
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
    # South-facing glazed duty/service window on west bay
    wst1.add_box(mats["dark_steel"], -3.70, 75.18, 1.15, 2.80, 0.10, 1.50, 0.0, ao_bot=0.78, ao_top=0.94)
    wst1.add_box(mats["surf"], -3.70, 75.14, 1.07, 2.96, 0.16, 0.08, 0.0, UV_PLAZA_TILE)
    wst1.quad_enu(
        mats["glass"],
        (-5.02, 75.12, 1.22), (-2.38, 75.12, 1.22),
        (-2.38, 75.12, 2.58), (-5.02, 75.12, 2.58),
        UV_GLASS_WINDOW, 0.88, 0.98,
    )
    wst1.add_box(mats["white_alu"], -3.70, 75.12, 1.20, 0.06, 0.05, 1.40, 0.0)
    # North-facing "尚美 · 美育浮雕" bronze relief on west bay north wall (west-stairway-2024.webp left!)
    wst1.add_box(mats["dark_steel"], -2.275, 83.42, 0.46, 3.35, 0.06, 2.58, 0.0)
    wst1.quad_enu(
        mats["stage"],
        (-0.65, 83.46, 0.52), (-3.90, 83.46, 0.52),
        (-3.90, 83.46, 2.98), (-0.65, 83.46, 2.98),
        UV_RELIEF_WALL, 0.92, 1.0,
    )
    # East Qingzhuan structural pier along East Campus Wall & hollow 1F bike tunnel (x = -0.45..+3.35, h = 3.02m)
    wst1.add_box(mats["surf"], 3.65, 79.30, 0.0, 0.60, 8.20, 3.44, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.94)
    wst1.add_box(mats["surf"], 1.45, 79.30, 3.02, 3.84, 8.20, 0.42, 0.0, UV_QINGZHUAN, ao_bot=0.84, ao_top=0.95)
    # Bright white ceiling soffit, light stucco upper tunnel walls & warm ceiling dome lights inside 1F passage
    wst1.add_box(mats["surf"], -0.43, 79.30, 1.05, 0.04, 8.08, 1.96, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.96)
    wst1.add_box(mats["surf"], 3.33, 79.30, 1.05, 0.04, 8.08, 1.96, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.96)
    wst1.add_box(mats["white_alu"], 1.45, 79.30, 2.99, 3.78, 8.12, 0.04, 0.0, ao_bot=0.92, ao_top=0.98)
    for cly in (77.3, 81.3):
        wst1.add_cylinder(mats["floodlight"], 1.45, cly, 2.94, 0.24, 0.24, 0.05, 12, ao_bot=0.98, ao_top=1.0)
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
    wst1.add_polygon_patch(pass_roof_pts, 3.664, mats["surf"], UV_PLAZA_TILE, ao=0.98)

    # ---- W-MC: 音乐长廊（始于音乐长廊牌楼 y≈81.5，沿 C 座西侧向南延伸；操场西侧不设棚廊） ----
    wmc = exp.add_node("W-MC")
    # Archway / glazed entrance portal at south edge of track southwest plaza (y=76.25..81.45)
    portal_bays = [
        (81.45, -93.50, -89.15),
        (78.85, -93.42, -89.55),
        (76.25, -93.35, -89.95),
    ]
    for py, xw, xe in portal_bays:
        wmc.add_box(mats["dark_steel"], xw, py, 0.0, 0.24, 0.24, 4.65, 0.0)
        wmc.add_box(mats["dark_steel"], xe, py, 0.0, 0.24, 0.24, 4.65, 0.0)
        wmc.add_box(mats["dark_steel"], (xw + xe) * 0.5, py, 4.55, (xe - xw) + 0.36, 0.22, 0.24, 0.0)
    # Longitudinal eave beams connecting portal bays (east beam angled cleanly along (-89.95, 76.25)->(-89.15, 81.45))
    wmc.add_box(mats["dark_steel"], -93.42, 78.85, 4.55, 0.22, 5.45, 0.22, -math.atan2(-0.15, 5.20))
    wmc.add_box(mats["dark_steel"], -89.55, 78.85, 4.55, 0.22, 5.45, 0.22, -math.atan2(0.80, 5.20))
    wmc.quad_enu(
        mats["skylight"],
        (-93.45, 76.25, 4.78),
        (-89.88, 76.25, 4.78),
        (-89.08, 81.45, 4.78),
        (-93.58, 81.45, 4.78),
        UV_SKYLIGHT, 0.96, 1.0, double_sided=True,
    )
    # North & South header boards ("音乐长廊 / MUSIC CORRIDOR") on the archway
    wmc.quad_enu(mats["stage"], (-89.15, 81.50, 3.85), (-93.50, 81.50, 3.85), (-93.50, 81.50, 4.92), (-89.15, 81.50, 4.92), UV_MUSIC_SIGN, 0.95, 1.0)
    wmc.quad_enu(mats["stage"], (-93.35, 76.20, 3.85), (-89.95, 76.20, 3.85), (-89.95, 76.20, 4.92), (-93.35, 76.20, 4.92), UV_MUSIC_SIGN, 0.95, 1.0)
    # Covered corridor extending south from archway along C-Wing west side (y=54.0..76.25)
    for pi in range(6):
        t = pi / 5.0
        py = 76.25 - t * 22.25
        xw = -93.35 + t * 1.95   # -93.35 -> -91.40 (inside campus west boundary)
        xe = -89.95 + t * 1.75   # -89.95 -> -88.20 (clear west of C-Wing west facade)
        wmc.add_box(mats["dark_steel"], xw, py, 0.0, 0.20, 0.20, 4.00, 0.0)
        wmc.add_box(mats["dark_steel"], xe, py, 0.0, 0.20, 0.20, 4.00, 0.0)
        wmc.add_box(mats["dark_steel"], (xw + xe) * 0.5, py, 3.94, (xe - xw) + 0.28, 0.18, 0.20, 0.0)
    wmc.add_box(mats["dark_steel"], -92.375, 65.125, 3.94, 0.18, 22.35, 0.18, -math.atan2(-1.95, 22.25))
    wmc.add_box(mats["dark_steel"], -89.075, 65.125, 3.94, 0.18, 22.35, 0.18, -math.atan2(-1.75, 22.25))
    wmc.quad_enu(
        mats["skylight"],
        (-91.50, 54.00, 4.14),
        (-88.12, 54.00, 4.14),
        (-89.88, 76.25, 4.14),
        (-93.45, 76.25, 4.14),
        UV_SKYLIGHT, 0.94, 1.0, double_sided=True,
    )

    # ---- W-L2: 百草园内庭绿地（无亭子，含草坪、园路、乔灌木） ----
    wl2 = exp.add_node("W-L2")
    wl2.add_polygon_patch([(-67.2, 39.0), (-45.5, 39.0), (-45.5, 57.2), (-67.2, 57.2)], 0.04, mats["surf"], UV_GRASS, ao=0.94)
    # Stone garden cross paths & central circular bed
    wl2.add_polygon_patch([(-66.5, 47.0), (-46.2, 47.0), (-46.2, 49.0), (-66.5, 49.0)], 0.06, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    wl2.add_polygon_patch([(-57.4, 39.5), (-55.4, 39.5), (-55.4, 56.8), (-57.4, 56.8)], 0.06, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    wl2.add_cylinder(mats["surf"], -56.4, 48.0, 0.05, 2.2, 2.2, 0.22, 12, UV_QINGZHUAN, ao_bot=0.80, ao_top=0.95)
    wl2.add_tree(-61.5, 44.0, "cedar", 8.5, mats["trunk"], mats["leaf"])
    wl2.add_tree(-50.0, 44.5, "broad", 8.0, mats["trunk"], mats["leaf"])
    wl2.add_tree(-62.0, 52.5, "broad", 7.8, mats["trunk"], mats["leaf"])
    wl2.add_tree(-50.5, 53.0, "broad", 7.2, mats["trunk"], mats["leaf"])

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
        return pts

    # 200m Oval EPDM track + NE 50m sprint start chute (y=120.30..124.50, x=-26.8..-6.4)
    wp1.add_polygon_patch(rounded_rect_pts(-89.5, 87.5, -8.0, 124.5, 18.5, n_arc=16), 0.05, mats["surf"], UV_TRACK_EPDM, ao=0.98)
    wp1.add_polygon_patch([(-26.8, 120.30), (-6.4, 120.30), (-6.4, 124.50), (-26.8, 124.50)], 0.055, mats["surf"], UV_TRACK_EPDM, ao=0.98)
    # Inner slotted concrete drainage curb ring around oval infield (Photo 3)
    drain_pts = rounded_rect_pts(-85.32, 91.68, -12.18, 120.32, 14.32, n_arc=16)
    for i in range(len(drain_pts)):
        a, b = drain_pts[i], drain_pts[(i + 1) % len(drain_pts)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = max(math.hypot(dx, dy), 0.01)
        nx, ny = (dy / L) * 0.11, (-dx / L) * 0.11
        wp1.quad_enu(mats["surf"], (a[0] - nx, a[1] - ny, 0.072), (b[0] - nx, b[1] - ny, 0.072), (b[0] + nx, b[1] + ny, 0.072), (a[0] + nx, a[1] + ny, 0.072), UV_PLAZA_TILE, 0.88, 0.94)
    # 5 white oval lane boundary rings (inner edge, 3 lane dividers, outer edge)
    for lane_r in (14.35, 15.35, 16.40, 17.45, 18.45):
        inset = 18.5 - lane_r
        lane_pts = rounded_rect_pts(-89.5 + inset, 87.5 + inset, -8.0 - inset, 124.5 - inset, lane_r, n_arc=16)
        for i in range(len(lane_pts)):
            a, b = lane_pts[i], lane_pts[(i + 1) % len(lane_pts)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = max(math.hypot(dx, dy), 0.01)
            nx, ny = (dy / L) * 0.045, (-dx / L) * 0.045
            wp1.quad_enu(mats["white_alu"], (a[0] - nx, a[1] - ny, 0.074), (b[0] - nx, b[1] - ny, 0.074), (b[0] + nx, b[1] + ny, 0.074), (a[0] + nx, a[1] + ny, 0.074))
    # NE 50m sprint straightaway lane stripes & Start (x=-7.0) / Finish (x=-57.0) markings
    for ly in (120.35, 121.35, 122.40, 123.45, 124.45):
        wp1.quad_enu(mats["white_alu"], (-26.6, ly - 0.045, 0.075), (-6.5, ly - 0.045, 0.075), (-6.5, ly + 0.045, 0.075), (-26.6, ly + 0.045, 0.075))
    wp1.quad_enu(mats["white_alu"], (-7.06, 120.32, 0.076), (-6.94, 120.32, 0.076), (-6.94, 124.48, 0.076), (-7.06, 124.48, 0.076))
    wp1.quad_enu(mats["white_alu"], (-57.06, 120.32, 0.076), (-56.94, 120.32, 0.076), (-56.94, 124.48, 0.076), (-57.06, 124.48, 0.076))
    # Painted white track lane numbers "1" "2" "3" "4" on North straightaway (Photo 3!) & 50m sprint start
    for idx_ln, lane_mid_y in enumerate((120.85, 121.88, 122.92, 123.95)):
        uv_ln = UV_LANE_NUMS[idx_ln]
        for nx_pos in (-69.6, -8.2):
            wp1.quad_enu(
                mats["details_alpha"],
                (nx_pos + 0.48, lane_mid_y - 0.32, 0.078),
                (nx_pos + 0.48, lane_mid_y + 0.32, 0.078),
                (nx_pos - 0.48, lane_mid_y + 0.32, 0.078),
                (nx_pos - 0.48, lane_mid_y - 0.32, 0.078),
                uv_ln, 0.98, 1.0,
            )

    # Terracotta infield apron + Green interior basketball surface + two-tone terracotta keys & circles (Photos 2, 4, 7)
    wp1.add_polygon_patch(rounded_rect_pts(-85.2, 91.8, -12.3, 120.2, 14.2, n_arc=16), 0.078, mats["surf"], UV_TRACK_EPDM, ao=0.98)
    court_xs = [(-69.5, -56.3), (-54.7, -41.5), (-39.9, -26.7)]
    for cx0, cx1 in court_xs:
        cy0, cy1 = 93.8, 118.2
        cmid_x = (cx0 + cx1) * 0.5
        cmid_y = (cy0 + cy1) * 0.5
        # Green court surface pad
        wp1.add_polygon_patch([(cx0 - 0.6, cy0 - 0.5), (cx1 + 0.6, cy0 - 0.5), (cx1 + 0.6, cy1 + 0.5), (cx0 - 0.6, cy1 + 0.5)], 0.086, mats["surf"], UV_COURT_GREEN, ao=1.0)
        # Terracotta-painted 3-second keys (w=4.8m, d=5.6m) at South & North ends + center jump circle
        kw, kd = 2.40, 5.60
        wp1.add_polygon_patch([(cmid_x - kw, cy0), (cmid_x + kw, cy0), (cmid_x + kw, cy0 + kd), (cmid_x - kw, cy0 + kd)], 0.093, mats["surf"], UV_TRACK_EPDM, ao=0.99)
        wp1.add_polygon_patch([(cmid_x - kw, cy1 - kd), (cmid_x + kw, cy1 - kd), (cmid_x + kw, cy1), (cmid_x - kw, cy1)], 0.093, mats["surf"], UV_TRACK_EPDM, ao=0.99)
        c_jump_pts = [(cmid_x + 1.8 * math.cos(2 * math.pi * k / 16), cmid_y + 1.8 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
        wp1.add_polygon_patch(c_jump_pts, 0.093, mats["surf"], UV_TRACK_EPDM, ao=0.99)
        # Crisp white boundary, center, key, free-throw & 3-point lines
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
            wp1.quad_enu(mats["white_alu"], (x0, y0, 0.102), (x1, y0, 0.102), (x1, y1, 0.102), (x0, y1, 0.102))
        # Center circle & free-throw semicircles + 3-point arcs
        for k in range(16):
            a0 = 2 * math.pi * k / 16
            a1 = 2 * math.pi * (k + 1) / 16
            p0 = (cmid_x + 1.8 * math.cos(a0), cmid_y + 1.8 * math.sin(a0))
            p1 = (cmid_x + 1.8 * math.cos(a1), cmid_y + 1.8 * math.sin(a1))
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            ll = max(math.hypot(dx, dy), 0.01)
            nx, ny = (dy / ll) * 0.045, (-dx / ll) * 0.045
            wp1.quad_enu(mats["white_alu"], (p0[0] - nx, p0[1] - ny, 0.102), (p1[0] - nx, p1[1] - ny, 0.102), (p1[0] + nx, p1[1] + ny, 0.102), (p0[0] + nx, p0[1] + ny, 0.102))
        for end_y, dir_s in ((cy0 + 1.55, 1.0), (cy1 - 1.55, -1.0)):
            for k in range(12):
                a0 = 0.18 + (math.pi - 0.36) * (k / 12)
                a1 = 0.18 + (math.pi - 0.36) * ((k + 1) / 12)
                p0 = (cmid_x + 6.15 * math.cos(a0), end_y + dir_s * 6.15 * math.sin(a0))
                p1 = (cmid_x + 6.15 * math.cos(a1), end_y + dir_s * 6.15 * math.sin(a1))
                dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                ll = max(math.hypot(dx, dy), 0.01)
                nx, ny = (dy / ll) * 0.045, (-dx / ll) * 0.045
                wp1.quad_enu(mats["white_alu"], (p0[0] - nx, p0[1] - ny, 0.102), (p1[0] - nx, p1[1] - ny, 0.102), (p1[0] + nx, p1[1] + ny, 0.102), (p0[0] + nx, p0[1] + ny, 0.102))
        add_basketball_hoop_west(wp1, cmid_x, cy0 - 0.82, 0.0, mats)
        add_basketball_hoop_west(wp1, cmid_x, cy1 + 0.82, math.pi, mats)

    # Extra side/practice green hoops visible in Photos 2, 5 & 7 (SW apron & NE apron)
    add_basketball_hoop_west(wp1, -88.4, 93.2, -math.pi * 0.5, mats)
    add_basketball_hoop_west(wp1, -9.8, 125.5, math.pi, mats)

    # Volleyball net on orange-red poles across West Court center line (Photos 2 & 7!)
    for vx in (-69.9, -55.9):
        wp1.add_cylinder(mats["orange_hoop"], vx, 106.0, 0.08, 0.055, 0.05, 2.45, 8)
    wp1.quad_enu(
        mats["details_alpha"],
        (-69.85, 106.0, 1.42), (-55.95, 106.0, 1.42),
        (-55.95, 106.0, 2.43), (-69.85, 106.0, 2.43),
        UV_VOLLEY_NET, 0.96, 1.0, double_sided=True,
    )

    # Signature leaning deciduous tree + square curb cutout + metal ladder on North track edge (Photo 5!)
    lt_x, lt_y = -19.6, 124.52
    wp1.add_box(mats["surf"], lt_x, lt_y, 0.04, 1.25, 1.15, 0.08, 0.0, UV_PLAZA_TILE, ao_bot=0.78, ao_top=0.95)
    for ti_seg in range(5):
        z_b = ti_seg * 0.92
        z_t = (ti_seg + 1) * 0.92
        r_b = 0.31 - ti_seg * 0.025
        r_t = 0.31 - (ti_seg + 1) * 0.025
        # Slight eastward lean (+0.14m per meter height) matching Photo 5!
        ox_b, ox_t = ti_seg * 0.13, (ti_seg + 1) * 0.13
        for si in range(8):
            a0 = 2 * math.pi * si / 8
            a1 = 2 * math.pi * (si + 1) / 8
            wp1.quad_enu(
                mats["trunk"],
                (lt_x + ox_b + r_b * math.cos(a0), lt_y + r_b * math.sin(a0), z_b),
                (lt_x + ox_b + r_b * math.cos(a1), lt_y + r_b * math.sin(a1), z_b),
                (lt_x + ox_t + r_t * math.cos(a1), lt_y + r_t * math.sin(a1), z_t),
                (lt_x + ox_t + r_t * math.cos(a0), lt_y + r_t * math.sin(a0), z_t),
                c_bot=0.68, c_top=0.88,
            )
    for ring_i in range(3):
        phi0 = -0.32 + ring_i * 0.45
        phi1 = phi0 + 0.48
        r0 = 3.6 * math.cos(phi0)
        r1 = max(0.08, 3.6 * math.cos(phi1))
        z0_c = 7.1 + 3.6 * math.sin(phi0) * 0.8
        z1_c = 7.1 + 3.6 * math.sin(phi1) * 0.85
        wp1.add_cylinder(mats["leaf"], lt_x + 0.65, lt_y, z0_c, r0, r1, z1_c - z0_c, 10, UV_FOLIAGE, ao_bot=0.76 + ring_i * 0.07, ao_top=0.94 + ring_i * 0.02)
    # Slender metal ladder leaning against tree fork (visible in Photo 5 & west-stage-2026.webp!)
    for lad_y in (lt_y - 0.18, lt_y + 0.18):
        wp1.quad_enu(
            mats["dark_steel"],
            (lt_x + 1.55, lad_y - 0.02, 0.08), (lt_x + 1.55, lad_y + 0.02, 0.08),
            (lt_x + 0.68, lad_y + 0.02, 4.45), (lt_x + 0.68, lad_y - 0.02, 4.45),
            double_sided=True,
        )
    for ri in range(11):
        rt = (ri + 0.5) / 11.0
        rx = (lt_x + 1.55) * (1.0 - rt) + (lt_x + 0.68) * rt
        rz = 0.08 * (1.0 - rt) + 4.45 * rt
        wp1.add_box(mats["white_alu"], rx, lt_y, rz, 0.03, 0.36, 0.03, 0.0)

    # ---- W-P2: 北侧悬挑三跨拱形张拉膜主席台与升旗台（深灰石材台基 + 左右台阶护栏, Photo 5） ----
    wp2 = exp.add_node("W-P2")
    st_cx, st_cy = -44.0, 128.5
    # Raised dark-slate stone podium deck (22.0m E-W: -55.0..-33.0 x 6.0m N-S: 125.5..131.5, Photo 5!)
    wp2.add_box(
        mats["details"], st_cx, st_cy, 0.0, 22.0, 6.0, 0.85, 0.0,
        UV_DARK_SLATE_PODIUM, ao_bot=0.74, ao_top=0.95,
        top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
    )
    # Left (West) & Right (East) side 3-step dark-slate staircases ONLY (no steps in front)
    for side_sign, x_edge in ((-1.0, -55.0), (1.0, -33.0)):
        for si, h_step in enumerate((0.64, 0.43, 0.22)):
            xc = x_edge + side_sign * (0.28 + si * 0.56)
            wp2.add_box(
                mats["details"], xc, 128.7, 0.0, 0.56, 2.80, h_step, 0.0,
                UV_DARK_SLATE_PODIUM, ao_bot=0.76, ao_top=0.95,
                top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
            )
    # Stainless steel deck guardrails & sloped stair handrails ONLY on West & East sides
    for side_sign, x_rail, x_bot in ((-1.0, -54.92, -56.60), (1.0, -33.08, -31.40)):
        for y0_r, y1_r in ((125.58, 127.30), (130.10, 131.42)):
            wp2.add_box(mats["white_alu"], x_rail, (y0_r + y1_r) * 0.5, 1.75, 0.05, y1_r - y0_r, 0.05, 0.0)
            wp2.add_box(mats["white_alu"], x_rail, (y0_r + y1_r) * 0.5, 1.32, 0.04, y1_r - y0_r, 0.04, 0.0)
            for ry_post in (y0_r, (y0_r + y1_r) * 0.5, y1_r):
                wp2.add_box(mats["white_alu"], x_rail, ry_post, 0.85, 0.05, 0.05, 0.93, 0.0)
        for hy in (127.30, 130.10):
            wp2.add_box(mats["white_alu"], x_bot, hy, 0.22, 0.05, 0.05, 0.78, 0.0)
            wp2.quad_enu(
                mats["white_alu"],
                (x_rail, hy, 1.74), (x_bot, hy, 0.96),
                (x_bot, hy, 1.01), (x_rail, hy, 1.79),
                (0.1, 0.1, 0.9, 0.9), 0.94, 1.0, double_sided=True,
            )
            wp2.quad_enu(
                mats["white_alu"],
                (x_rail, hy, 1.32), (x_bot, hy, 0.58),
                (x_bot, hy, 0.62), (x_rail, hy, 1.36),
                (0.1, 0.1, 0.9, 0.9), 0.92, 1.0, double_sided=True,
            )
    # Unified beige stone backdrop wall with cornice cap, flush motto pilasters & crimson-framed LED
    wp2.add_box(
        mats["gates"], st_cx, 130.765, 0.85, 13.6, 0.83, 4.90, 0.0,
        UV_MARBLE, ao_bot=0.78, ao_top=0.96,
        top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
    )
    wp2.add_box(
        mats["gates"], st_cx, 130.755, 5.75, 14.0, 1.02, 0.22, 0.0,
        UV_MARBLE, ao_bot=0.84, ao_top=0.98,
        top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
    )
    wp2.add_box(mats["gates"], st_cx - 5.65, 130.33, 1.15, 1.65, 0.08, 4.30, 0.0, UV_MARBLE, ao_bot=0.82, ao_top=0.96)
    wp2.quad_enu(mats["stage"], (st_cx - 6.45, 130.28, 1.15), (st_cx - 4.85, 130.28, 1.15), (st_cx - 4.85, 130.28, 5.45), (st_cx - 6.45, 130.28, 5.45), UV_PILLAR_LEFT, 0.94, 1.0)
    wp2.add_box(mats["gates"], st_cx + 5.65, 130.33, 1.15, 1.65, 0.08, 4.30, 0.0, UV_MARBLE, ao_bot=0.82, ao_top=0.96)
    wp2.quad_enu(mats["stage"], (st_cx + 4.85, 130.28, 1.15), (st_cx + 6.45, 130.28, 1.15), (st_cx + 6.45, 130.28, 5.45), (st_cx + 4.85, 130.28, 5.45), UV_PILLAR_RIGHT, 0.94, 1.0)
    wp2.add_box(mats["gates"], st_cx, 130.31, 1.38, 8.70, 0.12, 3.94, 0.0, UV_BURGUNDY, ao_bot=0.82, ao_top=0.98)
    wp2.add_box(mats["dark_steel"], st_cx, 130.27, 1.52, 8.36, 0.08, 3.66, 0.0)
    wp2.quad_enu(mats["stage_led"], (st_cx - 4.10, 130.22, 1.58), (st_cx + 4.10, 130.22, 1.58), (st_cx + 4.10, 130.22, 5.12), (st_cx - 4.10, 130.22, 5.12), UV_STAGE_LED, 1.0, 1.0)
    # Compact PA speakers mounted on outer front deck corners (clear of side stairs y=127.3..130.1)
    add_pa_speaker_stack(wp2, st_cx - 9.6, 126.40, 0.18, mats, z_base=0.85)
    add_pa_speaker_stack(wp2, st_cx + 9.6, 126.40, -0.18, mats, z_base=0.85)
    # Twin tall deciduous trees flanking East end of Chairman Stage (Photo 5 left!)
    wp2.add_tree(-30.9, 127.8, "broad", 11.8, mats["trunk"], mats["leaf"])
    wp2.add_tree(-29.5, 131.0, "broad", 10.8, mats["trunk"], mats["leaf"])
    # 4 Rear structural steel masts + cantilevered N-S valley ribs & diagonal braces (NO front ground columns)
    mast_xs = [-54.4, -47.47, -40.53, -33.6]
    for mx in mast_xs:
        wp2.add_cylinder(mats["dark_steel"], mx, 131.38, 0.0, 0.19, 0.17, 6.22, 10, ao_bot=0.74, ao_top=0.96)
        # Sloped cantilevered steel valley beam (z=5.84..6.02 rear -> z=6.10..6.28 front)
        wp2.quad_enu(mats["dark_steel"], (mx - 0.09, 131.65, 5.84), (mx + 0.09, 131.65, 5.84), (mx + 0.09, 124.75, 6.10), (mx - 0.09, 124.75, 6.10), (0.1, 0.1, 0.9, 0.9), 0.84, 0.94, double_sided=True)
        wp2.quad_enu(mats["dark_steel"], (mx - 0.09, 131.65, 6.02), (mx + 0.09, 131.65, 6.02), (mx + 0.09, 124.75, 6.28), (mx - 0.09, 124.75, 6.28), (0.1, 0.1, 0.9, 0.9), 0.90, 0.98, double_sided=True)
        wp2.quad_enu(mats["dark_steel"], (mx - 0.09, 131.65, 5.84), (mx - 0.09, 124.75, 6.10), (mx - 0.09, 124.75, 6.28), (mx - 0.09, 131.65, 6.02), (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True)
        wp2.quad_enu(mats["dark_steel"], (mx + 0.09, 124.75, 6.10), (mx + 0.09, 131.65, 5.84), (mx + 0.09, 131.65, 6.02), (mx + 0.09, 124.75, 6.28), (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True)
        wp2.quad_enu(mats["dark_steel"], (mx, 131.38, 3.85), (mx, 128.25, 6.02), (mx, 128.25, 6.15), (mx, 131.38, 3.98), (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True)
        wp2.quad_enu(mats["dark_steel"], (mx - 0.05, 131.38, 3.85), (mx + 0.05, 131.38, 3.85), (mx + 0.05, 128.25, 6.04), (mx - 0.05, 128.25, 6.04), (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True)
    # 3 Scalloped E-W barrel arches of white tensile membrane + curved black space-truss chords
    y_rear, y_front = 131.65, 124.75

    def stage_arch_z(t: float, y: float) -> float:
        z_v = 6.02 + 0.26 * ((y_rear - y) / (y_rear - y_front))
        return z_v + 1.12 * math.sin(math.pi * t)

    for span in range(3):
        xA = -54.6 + span * 7.067
        xB = xA + 7.067
        n_seg = 10
        for ai in range(n_seg):
            t0, t1 = ai / n_seg, (ai + 1) / n_seg
            x0 = xA + (xB - xA) * t0
            x1 = xA + (xB - xA) * t1
            z0r, z1r = stage_arch_z(t0, y_rear), stage_arch_z(t1, y_rear)
            z0f, z1f = stage_arch_z(t0, y_front), stage_arch_z(t1, y_front)
            wp2.quad_enu(mats["tensile"], (x0, y_front, z0f), (x1, y_front, z1f), (x1, y_rear, z1r), (x0, y_rear, z0r), (0.0, 0.0, 1.0, 1.0), 0.94, 1.0, double_sided=True)
            for y_tr in (124.82, 128.22):
                zt0 = stage_arch_z(t0, y_tr) - 0.04
                zt1 = stage_arch_z(t1, y_tr) - 0.04
                zb0 = zt0 - 0.30 * math.sin(math.pi * t0) - 0.07
                zb1 = zt1 - 0.30 * math.sin(math.pi * t1) - 0.07
                # Upper & lower curved truss chords (vertical + horizontal thickness)
                wp2.quad_enu(mats["dark_steel"], (x0, y_tr - 0.04, zt0), (x1, y_tr - 0.04, zt1), (x1, y_tr - 0.04, zt1 + 0.06), (x0, y_tr - 0.04, zt0 + 0.06), (0.1, 0.1, 0.9, 0.9), 0.88, 0.98, double_sided=True)
                wp2.quad_enu(mats["dark_steel"], (x0, y_tr - 0.04, zb0), (x1, y_tr - 0.04, zb1), (x1, y_tr - 0.04, zb1 + 0.06), (x0, y_tr - 0.04, zb0 + 0.06), (0.1, 0.1, 0.9, 0.9), 0.84, 0.95, double_sided=True)
                wp2.quad_enu(mats["dark_steel"], (x0, y_tr - 0.06, zt0), (x1, y_tr - 0.06, zt1), (x1, y_tr + 0.06, zt1), (x0, y_tr + 0.06, zt0), (0.1, 0.1, 0.9, 0.9), 0.88, 0.98, double_sided=True)
                wp2.quad_enu(mats["dark_steel"], (x0, y_tr - 0.06, zb0), (x1, y_tr - 0.06, zb1), (x1, y_tr + 0.06, zb1), (x0, y_tr + 0.06, zb0), (0.1, 0.1, 0.9, 0.9), 0.84, 0.95, double_sided=True)
                # Vertical + diagonal truss web bars
                if ai > 0:
                    wp2.quad_enu(mats["dark_steel"], (x0 - 0.03, y_tr, zb0), (x0 + 0.03, y_tr, zb0), (x0 + 0.03, y_tr, zt0), (x0 - 0.03, y_tr, zt0), (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True)
                wp2.quad_enu(mats["dark_steel"], (x0, y_tr, zb0), (x1 - 0.04, y_tr, zt1), (x1, y_tr, zt1), (x0, y_tr, zb0 + 0.04), (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True)
    # Flagpole & Red Flag on LEFT (West) side of stage when viewed from playground
    fx, fy = -58.8, 126.4
    wp2.add_box(mats["details"], fx, fy, 0.0, 2.2, 2.2, 0.48, 0.0, UV_DARK_SLATE_PODIUM, ao_bot=0.76, ao_top=0.96, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for px_off in (-1.0, 1.0):
        for py_off in (-1.0, 1.0):
            wp2.add_box(mats["white_alu"], fx + px_off, fy + py_off, 0.48, 0.05, 0.05, 0.57, 0.0)
    wp2.add_box(mats["white_alu"], fx, fy - 1.0, 1.03, 2.04, 0.04, 0.04, 0.0)
    wp2.add_box(mats["white_alu"], fx, fy + 1.0, 1.03, 2.04, 0.04, 0.04, 0.0)
    wp2.add_box(mats["white_alu"], fx - 1.0, fy, 1.03, 0.04, 2.04, 0.04, 0.0)
    wp2.add_box(mats["white_alu"], fx + 1.0, fy, 1.03, 0.04, 2.04, 0.04, 0.0)
    wp2.add_cylinder(mats["white_alu"], fx, fy, 0.48, 0.10, 0.045, 14.5, 10)
    wp2.add_cylinder(mats["gold_trim"], fx, fy, 14.98, 0.11, 0.03, 0.16, 10)
    wp2.quad_enu(mats["gates"], (fx + 0.05, fy, 13.15), (fx + 2.45, fy - 0.22, 13.15), (fx + 2.45, fy - 0.22, 14.75), (fx + 0.05, fy, 14.75), UV_FLAG, 0.96, 1.0, double_sided=True)

    # ---- W-B5: 高二平房区（北界通长直线1层教学平房 + 南向连续方柱挑檐外廊） ----
    wb5 = exp.add_node("W-B5")
    wb5_pts = [(-92.2, 136.8), (-7.8, 136.8), (-7.8, 142.1), (-92.2, 142.1)]
    wb5.add_detailed_building(
        wb5_pts, stories=1, story_h=3.15, plinth_h=0.50,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["dark_steel"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.45, add_rail=False, bay_w=3.6,
        solid_x_planes=[-7.8],
    )
    # Continuous straight south pillared veranda overhang from W-H1 north alley portal (x=-72.52) to east wall (x=-7.8)
    wb5.add_box(mats["surf"], -40.29, 135.96, 3.25, 65.08, 1.72, 0.52, 0.0, UV_STUCCO, ao_bot=0.84, ao_top=0.98, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wb5.add_box(mats["wall_grey_render"], -40.29, 135.88, 3.74, 65.20, 1.92, 0.14, 0.0, ao_bot=0.88, ao_top=1.0)
    for col_i in range(18):
        vc_x = -72.52 + col_i * 3.79
        col_h = 2.72 if col_i == 0 else 3.25
        wb5.add_box(mats["surf"], vc_x, 135.28, 0.0, 0.34, 0.34, col_h, 0.0, UV_STUCCO, ao_bot=0.76, ao_top=0.94)
    # Warm round ceiling light under west veranda bay + flush red fire extinguisher cabinet on straight south wall
    wb5.add_cylinder(mats["floodlight"], -69.8, 135.95, 3.20, 0.22, 0.22, 0.05, 12, ao_bot=0.98, ao_top=1.0)
    wb5.add_box(mats["crimson"], -71.50, 136.66, 0.03, 0.72, 0.24, 0.62, 0.0, ao_bot=0.78, ao_top=0.96)
    wb5.quad_enu(
        mats["details"],
        (-71.84, 136.53, 0.05), (-71.16, 136.53, 0.05),
        (-71.16, 136.53, 0.63), (-71.84, 136.53, 0.63),
        UV_FIRE_BOX, 0.94, 1.0,
    )

    # ---- W-H1: 校史馆（D座 · 南向双层青砖方柱绿栏杆外廊 + 北侧半露天穿树门洞与通高玻璃门厅入口, Photos 1 & 3） ----
    wh1 = exp.add_node("W-H1")
    # 1. 3-tier stepped grey stone terrace plinth along NW track edge (Photo 3!)
    for ti_p, (in_d, z_b, h_t) in enumerate([(0.0, 0.02, 0.14), (0.32, 0.16, 0.14), (0.64, 0.30, 0.14)]):
        wh1.add_box(
            mats["surf"], -81.0, 128.92 + in_d * 0.35, z_b,
            22.8 - in_d * 0.4, 8.78 - in_d * 0.7, h_t, 0.0,
            UV_PLAZA_TILE, ao_bot=0.74 + ti_p * 0.04, ao_top=0.94,
        )
    # 2. Main 2-story Qingzhuan building core (recessed south wall at y=126.38 so 1F & 2F both have open colonnade!)
    wh1_base_z = 0.44
    wh1_eave_z = 7.12
    wh1_mid_z = 3.78
    wh1.add_box(mats["surf"], -81.0, 129.79, wh1_base_z, 22.0, 6.82, wh1_eave_z - wh1_base_z, 0.0, UV_QINGZHUAN, ao_bot=0.75, ao_top=0.90)
    # Continuous white moulded inter-story cornice band wrapping N, S, E, W (clearly seen in Photos 1 & 3!)
    wh1.add_box(mats["white_alu"], -81.0, 129.15, wh1_mid_z - 0.09, 22.24, 8.26, 0.18, 0.0, ao_bot=0.88, ao_top=1.0)
    # 2F colonnade floor slab & crimson painted wooden eave lintel beam (Photo 3!)
    wh1.add_box(mats["surf"], -81.0, 125.75, wh1_mid_z - 0.12, 22.0, 1.30, 0.18, 0.0, UV_PLAZA_TILE, ao_bot=0.80, ao_top=0.94)
    wh1.add_box(mats["crimson"], -81.0, 125.22, wh1_eave_z - 0.32, 22.0, 0.32, 0.30, 0.0, ao_bot=0.82, ao_top=0.96)
    # 8 Square Qingzhuan colonnade piers (7 bays) with white stone capitals + 1F & 2F green vertical-bar railings (Photo 3!)
    n_col_bays = 7
    bay_span_h1 = 21.48 / n_col_bays
    for ci in range(n_col_bays + 1):
        px = -91.74 + ci * bay_span_h1
        wh1.add_box(mats["surf"], px, 125.24, wh1_base_z, 0.52, 0.52, wh1_eave_z - wh1_base_z, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.94)
        # White moulded column capitals at 1F & 2F tops
        wh1.add_box(mats["white_alu"], px, 125.24, wh1_mid_z - 0.24, 0.64, 0.64, 0.14, 0.0)
        wh1.add_box(mats["white_alu"], px, 125.24, wh1_eave_z - 0.44, 0.64, 0.64, 0.14, 0.0)
        if ci < n_col_bays:
            bx0 = px + 0.26
            bx1 = px + bay_span_h1 - 0.26
            b_mid = (bx0 + bx1) * 0.5
            b_w = bx1 - bx0
            # Recessed inner south wall crimson-framed multi-pane windows & doors on 1F & 2F
            for st_z0, st_z1 in ((wh1_base_z + 0.72, wh1_mid_z - 0.45), (wh1_mid_z + 0.75, wh1_eave_z - 0.55)):
                wh1.add_box(mats["crimson"], b_mid, 126.34, st_z0, b_w * 0.72, 0.10, st_z1 - st_z0, 0.0)
                wh1.quad_enu(
                    mats["glass"],
                    (b_mid - b_w * 0.33, 126.28, st_z0 + 0.08),
                    (b_mid + b_w * 0.33, 126.28, st_z0 + 0.08),
                    (b_mid + b_w * 0.33, 126.28, st_z1 - 0.08),
                    (b_mid - b_w * 0.33, 126.28, st_z1 - 0.08),
                    UV_GLASS_WINDOW, 0.88, 0.98,
                )
                for m_off in (-b_w * 0.11, b_w * 0.11):
                    wh1.add_box(mats["crimson"], b_mid + m_off, 126.26, st_z0, 0.045, 0.06, st_z1 - st_z0, 0.0)
                wh1.add_box(mats["crimson"], b_mid, 126.26, (st_z0 + st_z1) * 0.5, b_w * 0.68, 0.06, 0.045, 0.0)
            # Green vertical-picket railings on BOTH 1F (leave bay ci==2 open as stair entry) and 2F (all bays)
            for is_1f, rz_b in ((True, wh1_base_z), (False, wh1_mid_z + 0.06)):
                if is_1f and ci == 2:
                    continue
                wh1.add_box(mats["green_rail"], b_mid, 125.24, rz_b + 0.96, b_w, 0.06, 0.055, 0.0)
                wh1.add_box(mats["green_rail"], b_mid, 125.24, rz_b + 0.10, b_w, 0.05, 0.045, 0.0)
                for pk_i in range(9):
                    pk_x = bx0 + 0.12 + (b_w - 0.24) * (pk_i / 8.0)
                    wh1.add_box(mats["green_rail"], pk_x, 125.24, rz_b + 0.10, 0.032, 0.032, 0.88, 0.0)

    # 3. Overhanging traditional grey barrel-tile hard-gable roof + gable walls + East "D 校史馆" plaque
    wh1_ridge_z = 9.08
    wh1_ry_mid = 129.15
    q_u0, q_v0, q_u1, q_v1 = UV_QINGZHUAN
    q_um = (q_u0 + q_u1) * 0.5
    wh1.quad_enu(mats["surf"], (-92.55, 124.55, wh1_eave_z - 0.12), (-69.45, 124.55, wh1_eave_z - 0.12), (-69.45, wh1_ry_mid, wh1_ridge_z), (-92.55, wh1_ry_mid, wh1_ridge_z), UV_GREY_TILE, 0.88, 1.0, double_sided=True)
    wh1.quad_enu(mats["surf"], (-69.45, 133.75, wh1_eave_z - 0.12), (-92.55, 133.75, wh1_eave_z - 0.12), (-92.55, wh1_ry_mid, wh1_ridge_z), (-69.45, wh1_ry_mid, wh1_ridge_z), UV_GREY_TILE, 0.88, 1.0, double_sided=True)
    wh1.tri_enu(mats["surf"], (-92.0, 133.20, wh1_eave_z), (-92.0, 125.10, wh1_eave_z), (-92.0, wh1_ry_mid, wh1_ridge_z), (q_u0, q_v1), (q_u1, q_v1), (q_um, q_v0), 0.86, 0.86, 0.96)
    wh1.tri_enu(mats["surf"], (-70.0, 125.10, wh1_eave_z), (-70.0, 133.20, wh1_eave_z), (-70.0, wh1_ry_mid, wh1_ridge_z), (q_u0, q_v1), (q_u1, q_v1), (q_um, q_v0), 0.86, 0.86, 0.96)
    wh1.add_box(mats["dark_steel"], -81.0, wh1_ry_mid, wh1_ridge_z - 0.06, 23.2, 0.30, 0.24, 0.0)
    wh1.quad_enu(mats["stage"], (-69.88, 127.6, 3.9), (-69.88, 130.4, 3.9), (-69.88, 130.4, 6.5), (-69.88, 127.6, 6.5), UV_BOOK_D, 0.95, 1.0)
    # West end raised stone planter & twin tall deciduous trees (Photo 3 center!)
    wh1.add_box(mats["surf"], -92.3, 124.8, 0.02, 2.9, 5.2, 0.46, 0.0, UV_PLAZA_TILE, ao_bot=0.74, ao_top=0.94)
    wh1.add_tree(-91.8, 123.6, "broad", 11.4, mats["trunk"], mats["leaf"])
    wh1.add_tree(-92.4, 126.2, "broad", 9.6, mats["trunk"], mats["leaf"])

    # 4. North Facade Details & Semi-Open Skywell Courtyard Entrance (Photo 1 1:1 Reconstruction!)
    # North wall crimson arched-top windows (1F & 2F) + 4 white split AC units on 2F brackets
    for nwx in (-71.05, -74.55, -79.2, -83.8, -88.4):
        for nwz0, nwz1 in ((1.38, 2.68), (4.62, 5.92)):
            if nwx == -79.2 and nwz0 < 3.0:
                continue  # Inside enclosed glass entrance lobby
            wh1.add_box(mats["crimson"], nwx, 133.22, nwz0, 1.08, 0.12, nwz1 - nwz0, 0.0)
            wh1.quad_enu(mats["glass"], (nwx + 0.46, 133.29, nwz0 + 0.08), (nwx - 0.46, 133.29, nwz0 + 0.08), (nwx - 0.46, 133.29, nwz1 - 0.08), (nwx + 0.46, 133.29, nwz1 - 0.08), UV_GLASS_WINDOW, 0.86, 0.98)
            wh1.add_box(mats["surf"], nwx, 133.26, nwz0 - 0.09, 1.20, 0.16, 0.09, 0.0, UV_QINGZHUAN)
    for ac_hx, ac_hz in ((-70.65, 4.95), (-71.75, 4.78), (-73.45, 4.62), (-74.55, 4.48)):
        add_ac_unit(wh1, ac_hx, 133.38, ac_hz, 0.0, mats)
    # Cluster of upright yellow training/hurdle poles along 1F north wall east of portal (Photo 1 bottom-left!)
    for py_i in range(20):
        px_pole = -72.18 + (py_i % 10) * 0.21 + (0.07 if py_i >= 10 else 0.0)
        py_pole = 133.36 + (0.14 if py_i >= 10 else 0.0)
        tilt_x = ((py_i * 7) % 5 - 2) * 0.03
        wh1.add_cylinder(mats["yellow_pole"], px_pole, py_pole, 0.03, 0.07, 0.07, 0.03, 6)
        wh1.quad_enu(
            mats["yellow_pole"],
            (px_pole - 0.016, py_pole, 0.05), (px_pole + 0.016, py_pole, 0.05),
            (px_pole + tilt_x + 0.016, py_pole + 0.02, 1.36), (px_pole + tilt_x - 0.016, py_pole + 0.02, 1.36),
            double_sided=True,
        )
    # Grey-brick flat-lintel portal frame spanning alley from W-H1 pilaster (y=133.2) to W-B5 pier (y=135.25)
    wh1.add_box(mats["surf"], -72.52, 133.48, 0.03, 0.62, 0.56, 3.16, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.95)
    wh1.add_box(mats["surf"], -72.52, 134.35, 2.72, 0.62, 2.35, 0.46, 0.0, UV_QINGZHUAN, ao_bot=0.84, ao_top=0.98, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wh1.add_box(mats["white_alu"], -72.52, 134.35, 2.68, 0.58, 1.72, 0.04, 0.0)
    # Semi-open skywell courtyard (x = -77.35..-72.52, y = 133.2..136.8): perimeter roof collar + open skywell for mature tree!
    wh1.add_box(mats["white_alu"], -74.95, 136.32, 2.92, 4.86, 0.96, 0.24, 0.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wh1.add_box(mats["white_alu"], -76.85, 134.55, 2.92, 1.00, 2.70, 0.24, 0.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    # Stone-curbed white-pebble tree pit (cx=-75.05, cy=134.55) + tall skywell tree rising through open roof!
    pit_x, pit_y = -75.05, 134.55
    wh1.add_box(mats["surf"], pit_x, pit_y, 0.03, 2.25, 1.48, 0.14, 0.0, UV_PLAZA_TILE, ao_bot=0.78, ao_top=0.95, top_mat=mats["details"], top_uv=UV_WHITE_PEBBLES)
    wh1.add_cylinder(mats["trunk"], pit_x, pit_y, 0.12, 0.34, 0.24, 5.45, 9, ao_bot=0.64, ao_top=0.88)
    for ring_i in range(3):
        phi0 = -0.30 + ring_i * 0.45
        phi1 = phi0 + 0.48
        r0 = 3.2 * math.cos(phi0)
        r1 = max(0.08, 3.2 * math.cos(phi1))
        z0_t = 7.4 + 3.2 * math.sin(phi0) * 0.8
        z1_t = 7.4 + 3.2 * math.sin(phi1) * 0.85
        wh1.add_cylinder(mats["leaf"], pit_x, pit_y, z0_t, r0, r1, z1_t - z0_t, 10, UV_FOLIAGE, ao_bot=0.78 + ring_i * 0.06, ao_top=0.95)
    # Second red fire cabinet + row of 6 grey stone pole-bases inside skywell left wall (Photo 1 center-left!)
    wh1.add_box(mats["crimson"], -73.08, 133.42, 0.03, 0.56, 0.22, 0.58, 0.0)
    wh1.quad_enu(mats["details"], (-72.80, 133.54, 0.05), (-73.36, 133.54, 0.05), (-73.36, 133.54, 0.59), (-72.80, 133.54, 0.59), UV_FIRE_BOX, 0.90, 0.98)
    for sb_i in range(6):
        sb_x = -73.68 - sb_i * 0.46
        wh1.add_box(mats["surf"], sb_x, 133.56, 0.03, 0.40, 0.42, 0.11, 0.0, UV_PLAZA_TILE)
        wh1.add_cylinder(mats["dark_steel"], sb_x, 133.56, 0.14, 0.03, 0.03, 0.36, 6)
    # Full-height dark-framed glass entrance partition & double glass doors into 校史馆 behind tree (x = -77.35, Photo 1!)
    gx_ent = -77.35
    wh1.add_box(mats["surf"], -79.45, 135.0, 3.04, 4.25, 3.62, 0.24, 0.0, UV_PLAZA_TILE, ao_bot=0.84, ao_top=0.98)
    wh1.add_box(mats["surf"], -81.52, 135.0, 0.03, 0.30, 3.62, 3.05, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.94)
    for gy_m in (133.26, 134.35, 135.65, 136.74):
        wh1.add_box(mats["dark_steel"], gx_ent, gy_m, 0.03, 0.08, 0.08, 3.02, 0.0)
    for gz_m in (0.06, 2.28, 3.00):
        wh1.add_box(mats["dark_steel"], gx_ent, 135.0, gz_m, 0.08, 3.56, 0.07, 0.0)
    wh1.quad_enu(
        mats["details_alpha"],
        (gx_ent + 0.02, 133.30, 0.08), (gx_ent + 0.02, 136.70, 0.08),
        (gx_ent + 0.02, 136.70, 2.98), (gx_ent + 0.02, 133.30, 2.98),
        UV_HISTORY_GLASS_DOOR, 0.94, 1.0, double_sided=True,
    )
    # "校史馆" plaque beside the glass entrance lobby
    wh1.quad_enu(mats["stage"], (gx_ent + 0.06, 135.72, 1.95), (gx_ent + 0.06, 136.66, 1.95), (gx_ent + 0.06, 136.66, 2.34), (gx_ent + 0.06, 135.72, 2.34), UV_HISTORY_SIGN, 0.95, 1.0)

    # ---- W-B6: 学生食堂（操场东侧 1层圆拱顶建筑，南端拱窗面对东侧通道） ----
    wb6 = exp.add_node("W-B6")
    caf_cx, caf_cy, caf_w, caf_d = 0.2, 112.0, 11.6, 31.0
    caf_eave, caf_crown = 4.55, 6.35
    caf_hw, caf_hd = caf_w * 0.5, caf_d * 0.5
    # Lower 1-story main wall volume
    wb6.add_box(mats["surf"], caf_cx, caf_cy, 0.0, caf_w, caf_d, 1.0, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.90)
    wb6.add_box(mats["surf"], caf_cx, caf_cy, 1.0, caf_w, caf_d, caf_eave - 1.0, 0.0, UV_STUCCO, ao_bot=0.82, ao_top=0.96)
    # West & East high-bay dining hall windows
    for side in (-1.0, 1.0):
        x_w = caf_cx + side * (caf_hw + 0.04)
        for wi in range(7):
            wy0 = (caf_cy - caf_hd + 2.5) + wi * 3.8
            wy1 = wy0 + 2.6
            if side < 0:
                wb6.quad_enu(mats["glass"], (x_w, wy1, 1.25), (x_w, wy0, 1.25), (x_w, wy0, 3.85), (x_w, wy1, 3.85), UV_GLASS_WINDOW)
            else:
                wb6.quad_enu(mats["glass"], (x_w, wy0, 1.25), (x_w, wy1, 1.25), (x_w, wy1, 3.85), (x_w, wy0, 3.85), UV_GLASS_WINDOW)
    # Barrel-vaulted arched roof along Y (y: caf_cy - caf_hd - 0.3 .. caf_cy + caf_hd + 0.3)
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
        # Roof shell
        wb6.quad_enu(mats["surf"], (x0, y_s, z0), (x1, y_s, z1), (x1, y_n, z1), (x0, y_n, z0), UV_GREY_TILE, 0.88, 1.0, double_sided=True)
        # South & North semi-circular glazed fanlight / spandrel gables
        wb6.tri_enu(mats["glass"], (caf_cx, y_s + 0.25, caf_eave), (x1 * 0.94 + caf_cx * 0.06, y_s + 0.25, z1 - 0.05), (x0 * 0.94 + caf_cx * 0.06, y_s + 0.25, z0 - 0.05), (0.5, 0.9), (0.8, 0.2), (0.2, 0.2), double_sided=True)
        wb6.tri_enu(mats["surf"], (caf_cx, y_n - 0.25, caf_eave), (x0 * 0.96 + caf_cx * 0.04, y_n - 0.25, z0), (x1 * 0.96 + caf_cx * 0.04, y_n - 0.25, z1), (0.5, 0.8), (0.2, 0.2), (0.8, 0.2), double_sided=True)
    # South main entrance canopy, glass doors & "学生食堂" sign facing down east passage
    wb6.add_box(mats["dark_steel"], caf_cx, y_s - 0.5, 2.95, 5.8, 1.4, 0.22, 0.0)
    wb6.quad_enu(mats["glass"], (caf_cx - 2.3, y_s + 0.22, 0.1), (caf_cx + 2.3, y_s + 0.22, 0.1), (caf_cx + 2.3, y_s + 0.22, 2.9), (caf_cx - 2.3, y_s + 0.22, 2.9), UV_GLASS_WINDOW)
    wb6.quad_enu(mats["stage"], (caf_cx - 2.6, y_s + 0.14, 3.25), (caf_cx + 2.2, y_s + 0.14, 3.25), (caf_cx + 2.2, y_s + 0.14, 4.50), (caf_cx - 2.6, y_s + 0.14, 4.50), UV_CAFETERIA_SIGN, 0.95, 1.0)

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
        # East & West glazed semicircular end gables + white radial mullion ribs
        ctx_w.tri_enu(mats["warm_glass"], (sun_x1, sun_cy, sun_z0), (sun_x1, y0_s, z0_s), (sun_x1, y1_s, z1_s), (0.5, 0.9), (0.2, 0.2), (0.8, 0.2), 0.96, 1.0, 1.0, double_sided=True)
        ctx_w.add_box(mats["white_alu"], sun_x1 + 0.03, (y0_s + y1_s) * 0.5, (z0_s + z1_s) * 0.5 - 0.04, 0.08, math.hypot(y1_s - y0_s, z1_s - z0_s), 0.08, 0.0)
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
    )
    # Overhanging bright cobalt-blue pitched hipped/gable tile roof over eastern main block (-167..-92, 30.2..63.4)
    br_x0, br_x1, br_y0, br_y1 = -167.4, -91.6, 29.8, 63.8
    br_ymid, br_z0, br_z1 = (br_y0 + br_y1) * 0.5, 8.75, 11.35
    ctx_w.quad_enu(mats["details"], (br_x0, br_y0, br_z0), (br_x1, br_y0, br_z0), (br_x1 - 5.0, br_ymid, br_z1), (br_x0 + 5.0, br_ymid, br_z1), UV_BLUE_TILE_ROOF, 0.90, 1.0, double_sided=True)
    ctx_w.quad_enu(mats["details"], (br_x1, br_y1, br_z0), (br_x0, br_y1, br_z0), (br_x0 + 5.0, br_ymid, br_z1), (br_x1 - 5.0, br_ymid, br_z1), UV_BLUE_TILE_ROOF, 0.90, 1.0, double_sided=True)
    ctx_w.tri_enu(mats["details"], (br_x1, br_y0, br_z0), (br_x1, br_y1, br_z0), (br_x1 - 5.0, br_ymid, br_z1), (0.53, 0.98), (0.74, 0.98), (0.63, 0.78), 0.90, 0.90, 1.0, double_sided=True)
    ctx_w.tri_enu(mats["details"], (br_x0, br_y1, br_z0), (br_x0, br_y0, br_z0), (br_x0 + 5.0, br_ymid, br_z1), (0.53, 0.98), (0.74, 0.98), (0.63, 0.78), 0.90, 0.90, 1.0, double_sided=True)

    # 3. NE External Hutong Courtyard Cluster (way 636389213 + front 1F grey-brick gable + east red-tile roofs, Photos 4 & 5!)
    # Front 1-story Qingzhuan pitched-gable courtyard house immediately outside NE boundary (Photo 5 right foreground!)
    ctx_w.add_pitched_gable_building(
        cx=-0.2, cy_n=135.4, w=13.2, d=5.6, eave_h=3.45, ridge_h=1.55, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["warm_glass"], win_uv=(0.0, 0.0, 1.0, 1.0),
        wood_mat=mats["white_alu"], stories=1, ridge_along_x=True,
    )
    ctx_w.add_box(mats["surf"], 7.2, 133.2, 0.0, 6.2, 4.4, 3.35, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.94, top_mat=mats["surf"], top_uv=UV_GREY_TILE)
    ctx_w.quad_enu(mats["warm_glass"], (4.08, 134.8, 0.9), (4.08, 131.6, 0.9), (4.08, 131.6, 2.7), (4.08, 134.8, 2.7), (0.0, 0.0, 1.0, 1.0))
    # Rear 2-story Qingzhuan pitched-gable building (way 636389213, Photo 5 right background!)
    ctx_w.add_pitched_gable_building(
        cx=2.1, cy_n=142.4, w=18.6, d=6.8, eave_h=6.85, ridge_h=1.85, yaw_rad=0.03,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=2, ridge_along_x=True,
    )
    # East-boundary purple-red corrugated tile pitched-roof annexes (visible behind W-ST1 in Photo 4, stairway ref & Photo 5 far right!)
    ctx_w.add_pitched_gable_building(
        cx=10.2, cy_n=86.5, w=8.2, d=14.5, eave_h=3.6, ridge_h=1.45, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        roof_mat=mats["surf"], roof_uv=UV_RED_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=1, ridge_along_x=False,
    )
    ctx_w.add_pitched_gable_building(
        cx=12.8, cy_n=133.5, w=9.2, d=7.6, eave_h=3.8, ridge_h=1.55, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_RED_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=1, ridge_along_x=True,
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
    )
    # Salmon-pink corner bay & AC units right beside East Gate Pier (west-gate-2024.webp & west-gate-2020.webp!)
    ctx_w.add_box(mats["details"], 7.45, 5.65, 3.6, 2.5, 3.2, 11.8, 0.0, UV_SALMON_WALL, ao_bot=0.84, ao_top=0.98)
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
            ctx_w.add_polygon_slab(pts, 0.0, 3.65, mats["surf"], mats["surf"], UV_QINGZHUAN, UV_GREY_TILE, ao_bot=0.74, ao_top=0.94)
        else:
            h = 11.5 if w["tags"].get("building") == "school" else 9.5
            ctx_w.add_polygon_slab(pts, 0.0, h, mats["surf"], mats["surf"], UV_STUCCO, UV_PLAZA_TILE, ao_bot=0.74, ao_top=0.95)
    # Campus, east passage & surrounding hutong trees
    for tx, ty, sp, th in [
        (-22, 52, "broad", 8.5), (-35, 51, "broad", 8.0), (-9.2, 25.6, "broad", 7.2),
        (1.0, 26, "broad", 7.8), (1.0, 44, "broad", 7.8), (-89.5, 134.8, "broad", 7.8),
        (-102.0, 92.0, "broad", 9.5), (-118.0, 90.0, "broad", 10.2), (-2.5, 130.4, "broad", 9.6),
    ]:
        ctx_w.add_tree(tx, ty, sp, th, mats["trunk"], mats["leaf"])

    return exp.write_glb(out_glb)


# ---------------------------------------------------------------------------
# EAST CAMPUS (东四六条甲44号 毕业年级校区)
# ---------------------------------------------------------------------------
def build_east_campus(data_path: str, tex_dir: str, out_glb: str) -> Tuple[int, int]:
    east = json.loads(Path(data_path).read_text())
    ways = {w["id"]: w for w in east["ways"]}
    exp = GLBExporter()
    mats = init_materials(exp, tex_dir)

    # ---- Campus_Ground_East ----
    gnd = exp.add_node("Campus_Ground_East")
    gnd.add_polygon_patch(ways["398694728"]["pts"], 0.0, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    gnd.add_polygon_patch([(-34.0, 23.0), (54.0, 24.0), (54.0, 79.5), (-34.0, 79.5)], 0.0, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    gnd.add_box(mats["surf"], 10.0, 15.0, -0.18, 220.0, 220.0, 0.16, 0.0, UV_ASPHALT, ao_bot=0.92, ao_top=0.92)
    # Perimeter Qingzhuan Campus Walls
    walls = [
        ((-35.5, -40.6), (55.3, -39.3)),
        ((55.3, -39.3), (54.3, 79.5)),
        ((-35.5, -40.6), (-35.5, 79.5)),
        ((-35.5, 79.5), (-8.5, 79.5)),
        ((2.0, 79.5), (54.3, 79.5)),
    ]
    for a, b in walls:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        yaw = math.atan2(b[1] - a[1], b[0] - a[0])
        gnd.add_box(mats["surf"], (a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, 0.0, L, 0.35, 2.5, yaw, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.96)

    # ---- E-G1: 东四六条甲44号北大门 + 左青砖门房 + 限速5标志 ----
    eg1 = exp.add_node("E-G1")
    # Deep burgundy twin square portal piers
    eg1.add_box(mats["gates"], -7.2, 80.5, 0.0, 1.0, 1.0, 4.7, 0.0, UV_BURGUNDY, ao_bot=0.76, ao_top=0.98)
    eg1.add_box(mats["gates"], 1.2, 80.5, 0.0, 1.0, 1.0, 4.7, 0.0, UV_BURGUNDY, ao_bot=0.76, ao_top=0.98)
    # Crossbeam header + traditional overhanging grey barrel-tile roof eave
    eg1.add_box(mats["gates"], -3.0, 80.5, 3.6, 9.6, 1.25, 1.25, 0.0, UV_BURGUNDY)
    eg1.add_box(mats["surf"], -3.0, 80.5, 4.85, 10.6, 2.2, 0.55, 0.0, UV_GREY_TILE)
    # Finial end posts & top beam crest
    eg1.add_box(mats["surf"], -7.4, 80.5, 5.4, 0.55, 0.65, 0.72, 0.0, UV_QINGZHUAN)
    eg1.add_box(mats["surf"], 1.4, 80.5, 5.4, 0.55, 0.65, 0.72, 0.0, UV_QINGZHUAN)
    # School Name Plaque facing North onto 东四六条 (viewer at North looking South: East=left, West=right)
    eg1.quad_enu(mats["gates"], (1.65, 81.03, 1.2), (0.75, 81.03, 1.2), (0.75, 81.03, 3.2), (1.65, 81.03, 3.2), UV_EAST_SIGN)
    eg1.quad_enu(mats["gates"], (0.8, 81.03, 3.85), (-6.8, 81.03, 3.85), (-6.8, 81.03, 4.75), (0.8, 81.03, 4.75), UV_EAST_SIGN)
    # Silver accordion gate slats across doorway
    for si in range(11):
        sx = -6.2 + si * 0.64
        eg1.add_box(mats["white_alu"], sx, 80.3, 0.05, 0.10, 0.32, 1.65, 0.45)
    # Left (East when facing from North!) Qingzhuan pitched-roof guardhouse
    eg1.add_pitched_gable_building(
        cx=5.4, cy_n=78.5, w=6.8, d=4.8, eave_h=3.2, ridge_h=1.2, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=1, ridge_along_x=True,
    )
    # Ground "5" speed limit roundel in front of gate
    eg1.quad_enu(mats["gates"], (-4.2, 82.5, 0.02), (-1.8, 82.5, 0.02), (-1.8, 84.9, 0.02), (-4.2, 84.9, 0.02), UV_SPEED_5)

    # ---- E-N1: 55m中轴红砖林荫甬道 + 双排行道大树 ----
    en1 = exp.add_node("E-N1")
    en1.add_polygon_patch([(-7.2, 22.0), (1.2, 22.0), (1.2, 79.0), (-7.2, 79.0)], 0.04, mats["surf"], UV_RED_BRICK_WALK, ao=0.98)
    for row_x in (-11.0, 5.2):
        for ty in (29.0, 41.0, 53.0, 65.0, 75.0):
            en1.add_tree(row_x, ty, "broad", 10.5, mats["trunk"], mats["leaf"])

    # ---- E-N2 & E-N3: 北院东西两侧传统四合院平房肌理（原徐世昌弢园）----
    en2 = exp.add_node("E-N2")
    en2.add_pitched_gable_building(
        cx=24.0, cy_n=48.0, w=28.0, d=10.5, eave_h=3.6, ridge_h=1.7, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN, roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW, wood_mat=mats["crimson"], stories=1, ridge_along_x=True,
    )
    en2.add_pitched_gable_building(
        cx=24.0, cy_n=66.0, w=28.0, d=9.5, eave_h=3.6, ridge_h=1.6, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN, roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW, wood_mat=mats["crimson"], stories=1, ridge_along_x=True,
    )

    en3 = exp.add_node("E-N3")
    en3.add_pitched_gable_building(
        cx=-22.5, cy_n=52.0, w=14.0, d=24.0, eave_h=3.6, ridge_h=1.6, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN, roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW, wood_mat=mats["crimson"], stories=1, ridge_along_x=False,
    )

    # ---- E-P1: 南院双联标准篮球场 + 红色塑胶边 + 4套篮球架 ----
    ep1 = exp.add_node("E-P1")
    ep1.add_polygon_patch([(-6.0, -16.0), (31.0, -15.5), (30.5, 19.0), (-6.0, 18.5)], 0.04, mats["surf"], UV_TRACK_EPDM, ao=0.98)
    for wid in ("838569683", "838569684"):
        pts = ways[wid]["pts"]
        ep1.add_polygon_patch(pts, 0.07, mats["surf"], UV_COURT_GREEN, ao=1.0)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        mx = (min(xs) + max(xs)) * 0.5
        # White court border markings
        c_pts = ensure_ccw(pts)
        for i in range(len(c_pts)):
            a, b = c_pts[i], c_pts[(i + 1) % len(c_pts)]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            ep1.add_box(mats["white_alu"], (a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, 0.08, L, 0.14, 0.02, math.atan2(b[1] - a[1], b[0] - a[0]))
        add_basketball_hoop(ep1, mx, min(ys) - 0.6, 0.0, mats)
        add_basketball_hoop(ep1, mx, max(ys) + 0.6, math.pi, mats)
    # West teal mini-activity plaza (satellite visible north of E-B4)
    ep1.add_polygon_patch([(-32.0, 4.5), (-11.0, 4.8), (-11.0, 18.5), (-32.0, 18.0)], 0.05, mats["surf"], UV_COURT_GREEN, ao=0.98)

    # ---- E-B1: 南主教学楼 (way 477977123, Green Roof!) ----
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

    # ---- E-B2: 西南 L 形教学楼 (way 477977122, Green Roof!) ----
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

    # ---- E-B3: 东南教学配楼 (way 477977121) ----
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

    # ---- E-B4: 西中教学配楼 (way 477977120) ----
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

    # ---- E-B5: 操场东缘灰瓦平房 ----
    eb5 = exp.add_node("E-B5")
    eb5.add_pitched_gable_building(
        cx=43.0, cy_n=1.0, w=12.0, d=30.0, eave_h=3.5, ridge_h=1.5, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN, roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW, wood_mat=mats["dark_steel"], stories=1, ridge_along_x=False,
    )

    # ---- Context_East: 60m Beijing Siheyuan Hutong Context ----
    ctx_e = exp.add_node("Context_East")
    hutong_blocks = [
        (-52, 102, 34, 14), (2, 102, 38, 16), (48, 102, 36, 14),
        (-52, 48, 22, 38), (68, 46, 22, 36),
        (-52, -16, 20, 48), (68, -14, 22, 46),
        (-10, -56, 48, 14), (42, -56, 36, 14),
    ]
    for bx, by, bw, bd in hutong_blocks:
        ctx_e.add_box(mats["context"], bx, by, 0.0, bw, bd, 3.6, 0.0, ao_bot=0.72, ao_top=0.92)
    ctx_e.add_tree(-30, 26, "broad", 9.0, mats["trunk"], mats["leaf"])
    ctx_e.add_tree(36, 22, "broad", 8.5, mats["trunk"], mats["leaf"])

    return exp.write_glb(out_glb)


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


def sync_campuses_model_version(repo: Path, filename: str) -> str:
    """Update `?v=<sha8>` query param on modelUrl in src/data/campuses.ts after rebuilding a GLB."""
    sha8 = hashlib.sha256((repo / "public" / "models" / filename).read_bytes()).hexdigest()[:8]
    campuses_ts = repo / "src" / "data" / "campuses.ts"
    if campuses_ts.exists():
        text = campuses_ts.read_text()
        updated = re.sub(
            rf"/models/{re.escape(filename)}(?:\?v=[0-9a-f]+)?",
            f"/models/{filename}?v={sha8}",
            text,
        )
        if updated != text:
            campuses_ts.write_text(updated)
    return sha8


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate procedural campus GLB models")
    parser.add_argument(
        "--campus",
        choices=("west", "east", "all"),
        default="all",
        help="Which campus GLB to rebuild (default: all)",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    data_dir = repo / "blender" / "data"
    out_dir = repo / "public" / "models"
    tex_dir = resolve_tex_dir(repo)

    if args.campus in ("west", "all"):
        wv, wt = build_west_campus(str(data_dir / "west_metric.json"), tex_dir, str(out_dir / "west-campus.glb"))
        ws = (out_dir / "west-campus.glb").stat().st_size
        w_ver = sync_campuses_model_version(repo, "west-campus.glb")
        print(f"west-campus.glb (v={w_ver}): {wv} verts, {wt} tris, {ws:,} bytes")

    if args.campus in ("east", "all"):
        ev, et = build_east_campus(str(data_dir / "east_metric.json"), tex_dir, str(out_dir / "east-campus.glb"))
        es = (out_dir / "east-campus.glb").stat().st_size
        e_ver = sync_campuses_model_version(repo, "east-campus.glb")
        print(f"east-campus.glb (v={e_ver}): {ev} verts, {et} tris, {es:,} bytes")


if __name__ == "__main__":
    main()

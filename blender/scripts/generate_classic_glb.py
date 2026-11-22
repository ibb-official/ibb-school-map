#!/usr/bin/env python3
"""
Procedural Classic-Mode glTF 2.0 (.glb) Generator for Beijing No. 166 Middle School
Generates Z-fighting-free, precision-preserved classic models:
  - public/models/west-campus-classic.glb
  - public/models/east-campus-classic.glb

Coordinate system:
  - Input metric data: ENU relative meters (e = +X East, n = +Y North, h = Up)
  - Export glTF 2.0 (right-handed Y-up): (x = e, y = h, z = -n)
  - Preserves exact FLOAT32 vertex positions (no destructive 14-bit position quantization),
    eliminates coplanar overlaps, double-sided duplicate faces, and tight Z-fighting offsets.
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


class NodeBuilder:
    def __init__(self, name: str, double_sided_mats: Optional[Set[int]] = None):
        self.name = name
        self.buckets: Dict[int, PrimitiveBucket] = {}
        self.double_sided_mats: Set[int] = double_sided_mats if double_sided_mats is not None else set()

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
        # Never emit duplicate back-to-back faces when the glTF material itself is doubleSided
        if mat in self.double_sided_mats:
            double_sided = False
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
        if mat in self.double_sided_mats:
            double_sided = False
        self.bucket(mat).add_tri(
            enu_to_gltf(*e0), enu_to_gltf(*e1), enu_to_gltf(*e2),
            uv0, uv1, uv2, (c0, c0, c0), (c1, c1, c1), (c2, c2, c2), double_sided=double_sided
        )

    def add_mitered_ring(
        self,
        pts_ccw: List[Vec2],
        half_w: float,
        z: float,
        mat: int,
        uv_box: UVBox = (0.0, 0.0, 1.0, 1.0),
        ao_in: float = 1.0,
        ao_out: float = 1.0,
        closed: bool = True,
    ) -> None:
        """Continuous mitered ribbon strip along a 2D polyline/ring with zero vertex overlap."""
        n = len(pts_ccw)
        if n < 2:
            return
        seg_normals: List[Vec2] = []
        n_segs = n if closed else n - 1
        for i in range(n_segs):
            a = pts_ccw[i]
            b = pts_ccw[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = max(math.hypot(dx, dy), 1e-6)
            seg_normals.append((dy / L, -dx / L))
        outer_pts: List[Vec2] = []
        inner_pts: List[Vec2] = []
        for i in range(n):
            if closed:
                n0 = seg_normals[(i - 1) % n]
                n1 = seg_normals[i]
            elif i == 0:
                n0 = n1 = seg_normals[0]
            elif i == n - 1:
                n0 = n1 = seg_normals[-1]
            else:
                n0 = seg_normals[i - 1]
                n1 = seg_normals[i]
            mx, my = n0[0] + n1[0], n0[1] + n1[1]
            ml = math.hypot(mx, my)
            if ml < 1e-6:
                ux, uy, scale = n1[0], n1[1], 1.0
            else:
                ux, uy = mx / ml, my / ml
                dot = max(ux * n1[0] + uy * n1[1], 0.35)
                scale = min(1.0 / dot, 2.2)
            ox, oy = ux * half_w * scale, uy * half_w * scale
            outer_pts.append((pts_ccw[i][0] + ox, pts_ccw[i][1] + oy))
            inner_pts.append((pts_ccw[i][0] - ox, pts_ccw[i][1] - oy))
        for i in range(n_segs):
            j = (i + 1) % n
            self.quad_enu(
                mat,
                (outer_pts[i][0], outer_pts[i][1], z),
                (outer_pts[j][0], outer_pts[j][1], z),
                (inner_pts[j][0], inner_pts[j][1], z),
                (inner_pts[i][0], inner_pts[i][1], z),
                uv_box, ao_out, ao_in,
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
        add_bottom: Optional[bool] = None,
        add_top: bool = True,
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
        if add_top:
            tm = top_mat if top_mat is not None else mat
            tuv = top_uv if top_uv is not None else uv_box
            self.quad_enu(
                tm,
                (c0[0], c0[1], zt), (c1[0], c1[1], zt),
                (c2[0], c2[1], zt), (c3[0], c3[1], zt),
                tuv, ao_top, ao_top,
            )
        # Skip hidden bottom caps on ground-resting boxes (z_bot <= 0.05m) to prevent underground coplanar faces
        emit_bottom = (z_bot > 0.05) if add_bottom is None else add_bottom
        if emit_bottom:
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

                for bi in range(n_bays):
                    b0 = bi * actual_bay
                    b1 = (bi + 1) * actual_bay
                    pw = pilaster_w * 0.5
                    w0 = b0 + pw
                    w1 = b1 - pw
                    # Spandrel band & top lintel strictly within bay [w0..w1] (never behind pilasters!)
                    self.quad_enu(
                        band_mat,
                        wpt(w0, 0.03, sz0), wpt(w1, 0.03, sz0),
                        wpt(w1, 0.03, win_z0), wpt(w0, 0.03, win_z0),
                        band_uv, 0.88, 0.96,
                    )
                    self.quad_enu(
                        wall_mat,
                        wpt(w0, 0.04, win_z1), wpt(w1, 0.04, win_z1),
                        wpt(w1, 0.04, sz1), wpt(w0, 0.04, sz1),
                        wall_uv, 0.86, 0.98,
                    )
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
                    # Vertical aluminum mullions (outer frame + center 2 splits, 35mm proud of recessed glass)
                    if not simple_recess:
                        for mx in [w0 + 0.05, w0 + (w1 - w0) * 0.34, w0 + (w1 - w0) * 0.66, w1 - 0.05]:
                            self.quad_enu(
                                mullion_mat,
                                wpt(mx - 0.03, -recess + 0.035, win_z0 + 0.01),
                                wpt(mx + 0.03, -recess + 0.035, win_z0 + 0.01),
                                wpt(mx + 0.03, -recess + 0.035, win_z1 - 0.01),
                                wpt(mx - 0.03, -recess + 0.035, win_z1 - 0.01),
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
                                wpt(w0 + 0.04, 0.095, gz_b - 0.035),
                                wpt(w1 - 0.04, 0.095, gz_b - 0.035),
                                wpt(w1 - 0.04, 0.095, gz_b),
                                wpt(w0 + 0.04, 0.095, gz_b),
                                (0.1, 0.1, 0.9, 0.9), 0.88, 0.98, double_sided=True,
                            )

            # 3. Cornice + Parapet Wall + Rooftop Safety Railing (non-overlapping corners & posts/bars)
            self.quad_enu(
                wall_mat,
                wpt(0, 0.10, top_z), wpt(seg_len, 0.10, top_z),
                wpt(seg_len, 0.10, top_z + parapet_h), wpt(0, 0.10, top_z + parapet_h),
                wall_uv, 0.90, 1.0,
            )
            if add_rail:
                rm = rail_mat if rail_mat is not None else mullion_mat
                rz0 = top_z + parapet_h
                rz1 = rz0 + 0.95
                # Horizontal rails at out_d=0.070, vertical posts at out_d=0.040 (30mm clean separation)
                for bar_z, bar_h in ((rz1 - 0.05, 0.05), (rz0 + 0.46, 0.035)):
                    self.quad_enu(
                        rm,
                        wpt(0.08, 0.070, bar_z), wpt(max(0.08, seg_len - 0.08), 0.070, bar_z),
                        wpt(max(0.08, seg_len - 0.08), 0.070, bar_z + bar_h), wpt(0.08, 0.070, bar_z + bar_h),
                        (0.1, 0.1, 0.9, 0.9), 0.94, 1.0, double_sided=True,
                    )
                n_posts = max(2, int(seg_len // 2.4) + 1)
                for pi in range(n_posts):
                    pa = 0.12 + (max(0.24, seg_len - 0.24)) * pi / (n_posts - 1)
                    self.quad_enu(
                        rm,
                        wpt(pa - 0.03, 0.040, rz0),
                        wpt(pa + 0.03, 0.040, rz0),
                        wpt(pa + 0.03, 0.040, rz1),
                        wpt(pa - 0.03, 0.040, rz1),
                        (0.1, 0.1, 0.9, 0.9), 0.90, 1.0, double_sided=True,
                    )

        # Mitered Parapet Coping Cap (single seamless non-overlapping ring at top_z + parapet_h)
        outer_cope: List[Vec2] = []
        inner_cope: List[Vec2] = []
        edge_norms: List[Vec2] = []
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            el = max(math.hypot(dx, dy), 1e-6)
            edge_norms.append((dy / el, -dx / el))
        for i in range(n):
            n0, n1 = edge_norms[(i - 1) % n], edge_norms[i]
            mx, my = n0[0] + n1[0], n0[1] + n1[1]
            ml = math.hypot(mx, my)
            if ml < 1e-6:
                ux, uy, sc = n1[0], n1[1], 1.0
            else:
                ux, uy = mx / ml, my / ml
                sc = min(1.0 / max(ux * n1[0] + uy * n1[1], 0.35), 2.0)
            outer_cope.append((pts[i][0] + ux * 0.12 * sc, pts[i][1] + uy * 0.12 * sc))
            inner_cope.append((pts[i][0] - ux * 0.25 * sc, pts[i][1] - uy * 0.25 * sc))
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            is_pw = False
            if solid_x_planes:
                for px in solid_x_planes:
                    if abs(a[0] - px) < 0.25 and abs(b[0] - px) < 0.25:
                        max_y_lim = party_max_y_on_x.get(px) if party_max_y_on_x else None
                        if max_y_lim is None or max(a[1], b[1]) <= max_y_lim:
                            is_pw = True
                            break
            if is_pw or math.hypot(b[0] - a[0], b[1] - a[1]) < 2.8:
                continue
            j = (i + 1) % n
            cz = top_z + parapet_h
            self.quad_enu(
                mullion_mat,
                (inner_cope[i][0], inner_cope[i][1], cz),
                (inner_cope[j][0], inner_cope[j][1], cz),
                (outer_cope[j][0], outer_cope[j][1], cz),
                (outer_cope[i][0], outer_cope[i][1], cz),
                (0.1, 0.1, 0.9, 0.9), 0.95, 1.0,
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

    def add_tree(
        self,
        cx: float, cy_n: float, species: str, h: float,
        trunk_mat: int, leaf_mat: int,
        accent_mat: Optional[int] = None,
    ) -> None:
        """Species-aware campus tree.

        cedar 雪松 / pine 青松 / ginkgo 银杏 / magnolia 玉兰 /
        persimmon 柿树 / rose 月季（花灌木）/ broad 落叶乔木。
        """
        if species == "rose":
            # Low flowering shrub mass, no tall trunk
            for k in range(5):
                a = 2.0 * math.pi * k / 5.0
                px = cx + 0.42 * math.cos(a)
                py = cy_n + 0.42 * math.sin(a)
                self.add_sphere(leaf_mat, px, py, h * 0.34, h * 0.30, h * 0.24, h * 0.30, 8, 4, UV_FOLIAGE, 0.94)
            if accent_mat is not None:
                for k in range(7):
                    a = 2.0 * math.pi * k / 7.0
                    px = cx + 0.38 * math.cos(a)
                    py = cy_n + 0.38 * math.sin(a)
                    self.add_sphere(accent_mat, px, py, h * 0.56, 0.10, 0.08, 0.10, 6, 3, (0.0, 0.0, 1.0, 1.0), 1.0)
            return

        trunk_h = h * (0.30 if species in ("pine", "cedar") else 0.40)
        self.add_cylinder(trunk_mat, cx, cy_n, 0.0, 0.22, 0.14, trunk_h, 7, ao_bot=0.65, ao_top=0.88)

        if species == "cedar":
            # Narrow, layered Himalayan cedar: 6 skirts + a top spike
            tiers = 7
            for ti in range(tiers):
                f0 = 0.26 + ti * 0.098
                f1 = f0 + 0.155
                r = (h * 0.18) * (1.0 - ti * 0.115)
                self.add_cylinder(leaf_mat, cx, cy_n, h * f0, r, r * 0.22, h * (f1 - f0), 10, UV_FOLIAGE, ao_bot=0.74, ao_top=1.0)
            self.add_cylinder(leaf_mat, cx, cy_n, h * 0.95, h * 0.045, 0.0, h * 0.05, 8, UV_FOLIAGE, 0.9, 1.0)
        elif species == "pine":
            # Chinese pine: irregular dark tiers, slightly leaning crown
            for ti in range(4):
                f0 = 0.34 + ti * 0.15
                f1 = f0 + 0.20
                r = (h * 0.26) * (1.0 - ti * 0.18)
                ox = 0.10 * ti
                self.add_cylinder(leaf_mat, cx + ox, cy_n, h * f0, r, r * 0.20, h * (f1 - f0), 9, UV_FOLIAGE, ao_bot=0.72, ao_top=0.98)
            self.add_cylinder(leaf_mat, cx + 0.30, cy_n, h * 0.90, h * 0.05, 0.0, h * 0.06, 8, UV_FOLIAGE, 0.9, 1.0)
        else:
            # Broad deciduous crown built from overlapping spheres
            crowns = [
                (0.00, 0.00, 0.68, 0.34),
                (-0.22, 0.06, 0.78, 0.26),
                (0.20, -0.05, 0.80, 0.24),
                (0.02, 0.16, 0.60, 0.24),
            ]
            for ox, oy, fz, fr in crowns:
                self.add_sphere(
                    leaf_mat, cx + ox * h, cy_n + oy * h, h * fz,
                    h * fr, h * fr * 0.82, h * fr,
                    9, 5, UV_FOLIAGE, 0.96,
                )
            if species == "magnolia" and accent_mat is not None:
                for k in range(6):
                    a = 2.0 * math.pi * k / 6.0
                    px = cx + h * 0.26 * math.cos(a)
                    py = cy_n + h * 0.26 * math.sin(a)
                    self.add_sphere(accent_mat, px, py, h * (0.72 + 0.05 * (k % 2)), 0.11, 0.09, 0.11, 6, 3, (0.0, 0.0, 1.0, 1.0), 1.0)
            elif species == "persimmon" and accent_mat is not None:
                for k in range(8):
                    a = 2.0 * math.pi * k / 8.0
                    px = cx + h * 0.30 * math.cos(a)
                    py = cy_n + h * 0.30 * math.sin(a)
                    self.add_sphere(accent_mat, px, py, h * (0.58 + 0.12 * (k % 3)), 0.085, 0.085, 0.085, 6, 3, (0.0, 0.0, 1.0, 1.0), 1.0)
            elif species == "ginkgo" and accent_mat is not None:
                # Golden fan-shaped clumps at the crown edge
                for k in range(5):
                    a = 2.0 * math.pi * k / 5.0
                    px = cx + h * 0.24 * math.cos(a)
                    py = cy_n + h * 0.24 * math.sin(a)
                    self.add_sphere(accent_mat, px, py, h * (0.62 + 0.06 * (k % 2)), 0.16, 0.12, 0.16, 6, 3, (0.0, 0.0, 1.0, 1.0), 1.0)


# ---------------------------------------------------------------------------
# glTF Binary (.glb) Serializer
# ---------------------------------------------------------------------------
class GLBExporter:
    def __init__(self):
        self.textures: List[Tuple[str, bytes]] = []
        self.materials: List[dict] = []
        self.double_sided_mats: Set[int] = set()
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
        if double_sided:
            self.double_sided_mats.add(idx)
        return idx

    def add_node(self, name: str) -> NodeBuilder:
        nb = NodeBuilder(name, self.double_sided_mats)
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
                # Pack UV as normalized UINT16 (core glTF 2.0) when all coords in [0, 1] -> saves 50% UV bytes
                uv_in_unit = all(0.0 <= u[0] <= 1.0 and 0.0 <= u[1] <= 1.0 for u in b.uv)
                if uv_in_unit:
                    uv_bytes = b"".join(
                        struct.pack("<HH", max(0, min(65535, round(u[0] * 65535))), max(0, min(65535, round(u[1] * 65535))))
                        for u in b.uv
                    )
                else:
                    uv_bytes = b"".join(struct.pack("<ff", *u) for u in b.uv)
                # Pack vertex AO COLOR_0 as normalized UINT8 VEC3 padded to 4-byte stride (core glTF 2.0) -> saves 67% color bytes
                col_bytes = b"".join(
                    struct.pack("<BBBB", max(0, min(255, round(c[0] * 255))), max(0, min(255, round(c[1] * 255))), max(0, min(255, round(c[2] * 255))), 0)
                    for c in b.col
                )
                use_u16_idx = nv <= 65535
                idx_bytes = b"".join(struct.pack("<H" if use_u16_idx else "<I", i) for i in b.idx)

                bv_pos = append_bytes(pos_bytes, 34962)
                bv_norm = append_bytes(norm_bytes, 34962)
                bv_uv = append_bytes(uv_bytes, 34962)
                bv_col = append_bytes(col_bytes, 34962)
                buffer_views[bv_col]["byteStride"] = 4
                bv_idx = append_bytes(idx_bytes, 34963)

                acc_pos = len(accessors)
                accessors.append({"bufferView": bv_pos, "componentType": 5126, "count": nv, "type": "VEC3", "min": min_p, "max": max_p})
                acc_norm = len(accessors)
                accessors.append({"bufferView": bv_norm, "componentType": 5126, "count": nv, "type": "VEC3"})
                acc_uv = len(accessors)
                if uv_in_unit:
                    accessors.append({"bufferView": bv_uv, "componentType": 5123, "normalized": True, "count": nv, "type": "VEC2"})
                else:
                    accessors.append({"bufferView": bv_uv, "componentType": 5126, "count": nv, "type": "VEC2"})
                acc_col = len(accessors)
                accessors.append({"bufferView": bv_col, "componentType": 5121, "normalized": True, "count": nv, "type": "VEC3"})
                acc_idx = len(accessors)
                accessors.append({"bufferView": bv_idx, "componentType": 5123 if use_u16_idx else 5125, "count": len(b.idx), "type": "SCALAR"})

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
    mats["bare_soil"] = exp.add_mat("Mat_BareSoil", base_color=(0.46, 0.40, 0.32, 1.0), roughness=1.0)
    mats["fence_mesh"] = exp.add_mat("Mat_FenceMesh", base_color=(0.55, 0.58, 0.60, 0.30), roughness=0.55, double_sided=True, alpha_mode="BLEND")
    mats["sign_red"] = exp.add_mat("Mat_SignRed", base_color=(0.62, 0.12, 0.12, 1.0), roughness=0.60)
    mats["sign_blue"] = exp.add_mat("Mat_SignBlue", base_color=(0.10, 0.30, 0.55, 1.0), roughness=0.55)
    mats["plaque_white"] = exp.add_mat("Mat_PlaqueWhite", base_color=(0.92, 0.92, 0.89, 1.0), roughness=0.45)
    return mats


def add_basketball_hoop(nb: NodeBuilder, cx: float, cy_n: float, yaw_face_rad: float, mats: dict) -> None:
    """Detailed hoop post, gooseneck overhang arm, white glass backboard & orange rim."""
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def pt(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs, lz)

    nb.add_cylinder(mats["dark_steel"], cx, cy_n, 0.0, 0.12, 0.10, 3.24, 8)
    # Overhang arm extending +ly by 1.18m toward court (single clean box, zero segment overlap)
    arm_c = pt(0.0, 0.59, 0.0)
    nb.add_box(mats["dark_steel"], arm_c[0], arm_c[1], 3.24, 0.14, 1.18, 0.08, yaw_face_rad)
    # White rectangular backboard
    nb.add_box(mats["white_alu"], pt(0, 1.22, 0)[0], pt(0, 1.22, 0)[1], 2.90, 1.80, 0.08, 1.05, yaw_face_rad)
    # Orange basketball rim
    nb.add_cylinder(mats["orange_hoop"], pt(0, 1.50, 0)[0], pt(0, 1.50, 0)[1], 3.05, 0.24, 0.24, 0.06, 12)


def add_basketball_hoop_west(nb: NodeBuilder, cx: float, cy_n: float, yaw_face_rad: float, mats: dict) -> None:
    """West Campus photo-accurate Kelly-green box-truss hoop + tempered glass backboard & white net."""
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def pt(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs, lz)

    g_mat = mats["hoop_green"]
    # Base plate, green protective post padding & upper square steel column
    nb.add_box(mats["dark_steel"], cx, cy_n, 0.06, 0.56, 0.56, 0.05, yaw_face_rad, add_bottom=False)
    nb.add_box(mats["hoop_pad"], cx, cy_n, 0.11, 0.32, 0.32, 1.82, yaw_face_rad, ao_bot=0.78, ao_top=0.96, add_bottom=False)
    nb.add_box(g_mat, cx, cy_n, 1.93, 0.22, 0.22, 1.62, yaw_face_rad, ao_bot=0.84, ao_top=0.98, add_bottom=False)
    # Sloped main lower box arm + upper diagonal tension struts (clear of backboard frame & column)
    arm_c = pt(0.0, 0.65, 0.0)
    nb.add_box(g_mat, arm_c[0], arm_c[1], 3.16, 0.18, 1.08, 0.14, yaw_face_rad)
    for sx in (-0.16, 0.16):
        # Upper diagonal tension strut from column top -> backboard top
        nb.quad_enu(
            g_mat,
            pt(sx - 0.025, 0.12, 3.48), pt(sx + 0.025, 0.12, 3.48),
            pt(sx + 0.025, 1.20, 3.84), pt(sx - 0.025, 1.20, 3.84),
            double_sided=True,
        )
        # Diagonal brace from mid-column to mid-arm
        nb.quad_enu(
            g_mat,
            pt(sx, 0.12, 2.52), pt(sx, 0.74, 3.15),
            pt(sx, 0.74, 3.22), pt(sx, 0.12, 2.60),
            double_sided=True,
        )
    # Outer green perimeter frame of 1.80m x 1.05m backboard (at ly = 1.24; clean butt joints, zero overlap)
    bb_xy = pt(0.0, 1.24, 0.0)
    nb.add_box(g_mat, bb_xy[0], bb_xy[1], 2.88, 1.84, 0.05, 0.05, yaw_face_rad)
    nb.add_box(g_mat, bb_xy[0], bb_xy[1], 3.91, 1.84, 0.05, 0.05, yaw_face_rad)
    for bx_s in (-0.895, 0.895):
        post_xy = pt(bx_s, 1.24, 0.0)
        nb.add_box(g_mat, post_xy[0], post_xy[1], 2.93, 0.05, 0.05, 0.98, yaw_face_rad, add_bottom=False, add_top=False)
    # Semi-transparent tempered glass backboard cleanly inset inside green frame (ly = 1.24, single-sided via doubleSided mat)
    nb.quad_enu(
        mats["details_alpha"],
        pt(0.87, 1.24, 2.93), pt(-0.87, 1.24, 2.93),
        pt(-0.87, 1.24, 3.91), pt(0.87, 1.24, 3.91),
        UV_GLASS_BACKBOARD, 0.98, 1.0,
    )
    # Orange rim mounting plate (clear 20mm ahead of glass & 20mm below rim top) + rim + white tapered net skirt
    rim_xy = pt(0.0, 1.55, 0.0)
    nb.add_box(mats["orange_hoop"], pt(0.0, 1.31, 0.0)[0], pt(0.0, 1.31, 0.0)[1], 3.02, 0.14, 0.10, 0.05, yaw_face_rad)
    nb.add_cylinder(mats["orange_hoop"], rim_xy[0], rim_xy[1], 3.04, 0.22, 0.22, 0.05, 12)
    for ni in range(10):
        a0 = (2.0 * math.pi * ni) / 10
        a1 = (2.0 * math.pi * (ni + 1)) / 10
        p0t = (rim_xy[0] + 0.22 * math.cos(a0), rim_xy[1] + 0.22 * math.sin(a0), 3.03)
        p1t = (rim_xy[0] + 0.22 * math.cos(a1), rim_xy[1] + 0.22 * math.sin(a1), 3.03)
        p1b = (rim_xy[0] + 0.14 * math.cos(a1), rim_xy[1] + 0.14 * math.sin(a1), 2.66)
        p0b = (rim_xy[0] + 0.14 * math.cos(a0), rim_xy[1] + 0.14 * math.sin(a0), 2.66)
        nb.quad_enu(mats["white_alu"], p0b, p1b, p1t, p0t, (0.1, 0.1, 0.9, 0.9), 0.88, 0.98, double_sided=True)


def add_double_basketball_hoop_west(
    nb: NodeBuilder, cx: float, cy_n: float, yaw_axis_rad: float, mats: dict
) -> None:
    """West Campus back-to-back connected twin Kelly-green box-truss basketball hoops (zero coplanar overlaps)."""
    g_mat = mats["hoop_green"]
    # Shared reinforced steel base plate, twin-post green protective padding & central box column (clean butt joints!)
    nb.add_box(mats["dark_steel"], cx, cy_n, 0.06, 0.62, 0.92, 0.05, yaw_axis_rad, add_bottom=False)
    nb.add_box(mats["hoop_pad"], cx, cy_n, 0.11, 0.34, 0.54, 1.82, yaw_axis_rad, ao_bot=0.78, ao_top=0.96, add_bottom=False, add_top=False)
    nb.add_box(g_mat, cx, cy_n, 1.93, 0.24, 0.42, 1.62, yaw_axis_rad, ao_bot=0.84, ao_top=0.98, add_bottom=False, add_top=False)
    nb.add_box(g_mat, cx, cy_n, 3.55, 0.28, 0.48, 0.08, yaw_axis_rad, ao_bot=0.88, ao_top=0.98, add_bottom=False)

    for yaw_face in (yaw_axis_rad, yaw_axis_rad + math.pi):
        cs, sn = math.cos(yaw_face), math.sin(yaw_face)

        def pt(lx: float, ly: float, lz: float) -> Vec3:
            return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs, lz)

        # Overhang arm extending cleanly outside shared column (ly = 0.21..1.295)
        arm_c = pt(0.0, 0.7525, 0.0)
        nb.add_box(g_mat, arm_c[0], arm_c[1], 3.16, 0.18, 1.085, 0.14, yaw_face)
        for sx in (-0.16, 0.16):
            # Upper diagonal tension strut & lower brace (cleanly separated, no crossed coplanar planes)
            nb.quad_enu(
                g_mat,
                pt(sx - 0.025, 0.22, 3.48), pt(sx + 0.025, 0.22, 3.48),
                pt(sx + 0.025, 1.29, 3.84), pt(sx - 0.025, 1.29, 3.84),
                double_sided=True,
            )
            nb.quad_enu(
                g_mat,
                pt(sx, 0.22, 2.52), pt(sx, 0.82, 3.10),
                pt(sx, 0.82, 3.16), pt(sx, 0.22, 2.60),
                double_sided=True,
            )
        # Green perimeter frame of 1.80m x 1.05m backboard (at ly = 1.32; clean butt joints!)
        bb_xy = pt(0.0, 1.32, 0.0)
        nb.add_box(g_mat, bb_xy[0], bb_xy[1], 2.88, 1.84, 0.05, 0.05, yaw_face)
        nb.add_box(g_mat, bb_xy[0], bb_xy[1], 3.91, 1.84, 0.05, 0.05, yaw_face)
        for bx_s in (-0.895, 0.895):
            post_xy = pt(bx_s, 1.32, 0.0)
            nb.add_box(g_mat, post_xy[0], post_xy[1], 2.93, 0.05, 0.05, 0.98, yaw_face, add_bottom=False, add_top=False)
        # Semi-transparent tempered glass backboard cleanly inset inside frame (single-sided via doubleSided mat)
        nb.quad_enu(
            mats["details_alpha"],
            pt(0.87, 1.32, 2.93), pt(-0.87, 1.32, 2.93),
            pt(-0.87, 1.32, 3.91), pt(0.87, 1.32, 3.91),
            UV_GLASS_BACKBOARD, 0.98, 1.0,
        )
        # Orange rim mounting plate (20mm clear of glass & 20mm clear of rim top) + rim + net
        rim_xy = pt(0.0, 1.63, 0.0)
        nb.add_box(mats["orange_hoop"], pt(0.0, 1.39, 0.0)[0], pt(0.0, 1.39, 0.0)[1], 3.02, 0.14, 0.10, 0.05, yaw_face)
        nb.add_cylinder(mats["orange_hoop"], rim_xy[0], rim_xy[1], 3.04, 0.22, 0.22, 0.05, 12)
        for ni in range(10):
            a0 = (2.0 * math.pi * ni) / 10
            a1 = (2.0 * math.pi * (ni + 1)) / 10
            p0t = (rim_xy[0] + 0.22 * math.cos(a0), rim_xy[1] + 0.22 * math.sin(a0), 3.03)
            p1t = (rim_xy[0] + 0.22 * math.cos(a1), rim_xy[1] + 0.22 * math.sin(a1), 3.03)
            p1b = (rim_xy[0] + 0.14 * math.cos(a1), rim_xy[1] + 0.14 * math.sin(a1), 2.66)
            p0b = (rim_xy[0] + 0.14 * math.cos(a0), rim_xy[1] + 0.14 * math.sin(a0), 2.66)
            nb.quad_enu(mats["white_alu"], p0b, p1b, p1t, p0t, (0.1, 0.1, 0.9, 0.9), 0.88, 0.98, double_sided=True)


def add_ac_unit(nb: NodeBuilder, cx: float, cy: float, z_bot: float, yaw_face_rad: float, mats: dict) -> None:
    """Split AC outdoor condenser unit on wall brackets (+ly points outward from wall)."""
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def pt(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, z_bot + lz)

    # Twin steel L-brackets (stop cleanly below condenser base)
    for bx in (-0.30, 0.30):
        b_xy = pt(bx, 0.0, 0.0)
        nb.add_box(mats["dark_steel"], b_xy[0], b_xy[1], z_bot - 0.06, 0.04, 0.36, 0.04, yaw_face_rad)
    # Off-white condenser body (0.82m wide x 0.32m deep x 0.56m tall; front face at ly = +0.160)
    nb.add_box(mats["white_alu"], cx, cy, z_bot, 0.82, 0.32, 0.56, yaw_face_rad, ao_bot=0.82, ao_top=0.98)
    # Textured front fan grille facing +ly (25mm proud of condenser front to prevent distant Z-fighting)
    nb.quad_enu(
        mats["details"],
        pt(0.40, 0.185, 0.02), pt(-0.40, 0.185, 0.02),
        pt(-0.40, 0.185, 0.54), pt(0.40, 0.185, 0.54),
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
    nb.add_box(mats["white_alu"], cx, cy, 0.775, 0.03, 1.64, 0.155, yaw_rad, add_bottom=False)
    # 4 Crimson tubular support legs + cleanly inset cross stretcher (no leg overlap)
    for lx in (-0.92, 0.92):
        for ly in (-0.52, 0.52):
            lp = rot(lx, ly)
            nb.add_box(mats["crimson"], lp[0], lp[1], 0.03, 0.06, 0.06, 0.69, yaw_rad, add_top=False)
        sp = rot(lx, 0.0)
        nb.add_box(mats["crimson"], sp[0], sp[1], 0.24, 0.05, 0.98, 0.05, yaw_rad)


def add_taihu_rockery_basin(nb: NodeBuilder, cx: float, cy: float, mats: dict) -> None:
    """Water-filled dark-slate octagonal basin with vertical-fluted rockery & cascading waterfall (Photo 2)."""
    segs = 8
    r_out, r_in = 2.28, 1.98
    z0, z1 = 0.03, 0.54
    inner_ring: List[Vec2] = []
    for i in range(segs):
        a0 = (2.0 * math.pi * i) / segs + math.pi / 8
        a1 = (2.0 * math.pi * (i + 1)) / segs + math.pi / 8
        o0 = (cx + r_out * math.cos(a0), cy + r_out * math.sin(a0))
        o1 = (cx + r_out * math.cos(a1), cy + r_out * math.sin(a1))
        i0 = (cx + r_in * math.cos(a0), cy + r_in * math.sin(a0))
        i1 = (cx + r_in * math.cos(a1), cy + r_in * math.sin(a1))
        inner_ring.append(i0)
        # Outer & inner dark-slate pool curb walls + top stone coping
        nb.quad_enu(mats["details"], (o0[0], o0[1], z0), (o1[0], o1[1], z0), (o1[0], o1[1], z1), (o0[0], o0[1], z1), UV_DARK_SLATE_PODIUM, 0.76, 0.96)
        nb.quad_enu(mats["details"], (i1[0], i1[1], 0.12), (i0[0], i0[1], 0.12), (i0[0], i0[1], z1), (i1[0], i1[1], z1), UV_DARK_SLATE_PODIUM, 0.68, 0.88)
        nb.quad_enu(mats["surf"], (i0[0], i0[1], z1), (o0[0], o0[1], z1), (o1[0], o1[1], z1), (i1[0], i1[1], z1), UV_PLAZA_TILE, 0.94, 0.98)
    # Submerged dark-slate pool floor + south-right silver inscription plaque (35mm proud of south curb face)
    nb.add_polygon_patch(inner_ring, 0.12, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.72)
    nb.quad_enu(
        mats["white_alu"],
        (cx + 0.10, cy - r_out * 0.942, 0.22), (cx + 0.56, cy - r_out * 0.942, 0.22),
        (cx + 0.56, cy - r_out * 0.942, 0.37), (cx + 0.10, cy - r_out * 0.942, 0.37),
    )
    # Reflective translucent emerald-blue pool water surface (z = 0.44m)
    nb.add_polygon_patch(inner_ring, 0.44, mats["pool_water"], UV_ROCKERY_WATER, ao=0.98)
    # Asymmetric vertical-striated craggy mountain rockery (left main spire ~3.45m, right secondary crags ~2.86m)
    peaks = [
        (-0.46, 0.10, [(0.12, 1.50, 1.38, 1.12, 1.18, 0.94), (1.50, 2.68, 1.06, 0.86, 0.80, 0.64), (2.68, 3.46, 0.72, 0.56, 0.32, 0.26)]),
        (-1.02, -0.14, [(0.12, 1.36, 0.82, 0.76, 0.68, 0.62), (1.36, 2.45, 0.62, 0.56, 0.28, 0.26)]),
        (0.56, 0.08, [(0.12, 1.44, 1.14, 0.94, 0.96, 0.78), (1.44, 2.38, 0.84, 0.68, 0.58, 0.48), (2.38, 2.88, 0.52, 0.42, 0.26, 0.22)]),
        (0.06, -0.22, [(0.12, 1.15, 1.04, 0.88, 0.92, 0.76), (1.15, 1.72, 0.86, 0.68, 0.74, 0.54)]),
        (-0.56, -0.58, [(0.12, 1.22, 0.76, 0.64, 0.58, 0.48), (1.22, 1.94, 0.52, 0.42, 0.26, 0.22)]),
        (0.68, -0.48, [(0.12, 1.28, 0.80, 0.66, 0.62, 0.50), (1.28, 2.08, 0.56, 0.46, 0.28, 0.22)]),
        (-0.48, 0.62, [(0.12, 1.34, 0.86, 0.72, 0.66, 0.54), (1.34, 2.16, 0.60, 0.48, 0.28, 0.24)]),
        (0.54, 0.60, [(0.12, 1.26, 0.84, 0.70, 0.62, 0.52), (1.26, 1.98, 0.56, 0.46, 0.26, 0.22)]),
    ]
    for dx, dy, tiers in peaks:
        add_tapered_monolith(nb, cx + dx, cy + dy, tiers, mats["rockery_stone"], UV_SHENDU_GRANITE)
    # Cascading waterfall stream sheets (single-sided geometry via doubleSided mat) + white splash foam collar (28mm above pool)
    nb.quad_enu(
        mats["waterfall"],
        (cx - 0.14, cy - 0.10, 1.70), (cx + 0.22, cy - 0.10, 1.70),
        (cx + 0.16, cy + 0.02, 2.28), (cx - 0.10, cy + 0.02, 2.28),
        (0.1, 0.1, 0.9, 0.9), 0.95, 1.0,
    )
    nb.quad_enu(
        mats["waterfall"],
        (cx - 0.24, cy - 0.82, 0.470), (cx + 0.32, cy - 0.82, 0.470),
        (cx + 0.24, cy - 0.48, 1.70), (cx - 0.18, cy - 0.48, 1.70),
        (0.1, 0.1, 0.9, 0.9), 0.96, 1.0,
    )
    splash_pts = [
        (cx + 0.04 + 0.52 * math.cos(2 * math.pi * k / 12), cy - 0.86 + 0.34 * math.sin(2 * math.pi * k / 12))
        for k in range(12)
    ]
    nb.add_polygon_patch(splash_pts, 0.468, mats["waterfall"], (0.1, 0.1, 0.9, 0.9), ao=1.0)
    # Small rock-crevice shrub sprig on upper-right crag (visible in Photo 2!)
    nb.add_cylinder(mats["trunk"], cx + 0.88, cy + 0.04, 1.95, 0.035, 0.02, 0.55, 5)
    nb.add_cylinder(mats["leaf"], cx + 0.96, cy + 0.04, 2.38, 0.32, 0.12, 0.36, 7, UV_FOLIAGE, ao_bot=0.82, ao_top=0.98)


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

        # Front (+ly = +0.54) & rear (-ly = -0.54) wheels with crisp 25mm proud hub rims (zero overlap with frame/posts!)
        for wy_off in (-0.54, 0.54):
            wc = bp(0.0, wy_off)
            nb.add_box(mats["dark_steel"], wc[0], wc[1], 0.05, 0.040, 0.56, 0.56, yaw_rad, ao_bot=0.68, ao_top=0.92, add_bottom=False)
            nb.add_box(mats["white_alu"], wc[0], wc[1], 0.16, 0.090, 0.34, 0.34, yaw_rad, ao_bot=0.78, ao_top=0.96)
        # Main frame tube cleanly between tires (ly=-0.24..+0.24) + seatpost + saddle + stem + handlebar + raised front basket
        nb.add_box(fmat, bx, by, 0.44, 0.045, 0.48, 0.06, yaw_rad)
        seat = bp(0.0, -0.18)
        nb.add_box(mats["dark_steel"], seat[0], seat[1], 0.50, 0.045, 0.05, 0.34, yaw_rad, add_bottom=False, add_top=False)
        nb.add_box(mats["dark_steel"], seat[0], seat[1], 0.84, 0.16, 0.24, 0.06, yaw_rad)
        hbar = bp(0.0, 0.20)
        nb.add_box(fmat, hbar[0], hbar[1], 0.50, 0.045, 0.05, 0.45, yaw_rad, add_bottom=False, add_top=False)
        nb.add_box(mats["dark_steel"], hbar[0], hbar[1], 0.95, 0.52, 0.05, 0.04, yaw_rad)
        bsk = bp(0.0, 0.48)
        nb.add_box(mats["dark_steel"], bsk[0], bsk[1], 0.66, 0.30, 0.22, 0.22, yaw_rad, ao_bot=0.72, ao_top=0.90)


def add_pullup_rack_and_mats(nb: NodeBuilder, mats: dict) -> None:
    """West wall blue chin-up / fitness bar rack (5 bars) + crimson crash mats flush against NW trees to midline."""
    x_bar = -93.25
    # 5 horizontal bars (6 vertical posts) from playground N-S midline (y=107.60) up to NW tree planter (y=122.20)
    y_bays = [108.10 + i * 2.70 for i in range(6)]
    # Compact red gymnastics protective mats hugging west wall (y=107.60..122.15, zero gap to NW tree planter)
    nb.add_box(mats["crimson"], -93.12, 114.875, 0.065, 1.08, 14.55, 0.11, 0.0, ao_bot=0.76, ao_top=0.95, add_bottom=False)
    for idx, py in enumerate(y_bays):
        nb.add_box(mats["fitness_blue"], x_bar, py, 0.175, 0.09, 0.09, 2.30, 0.0, ao_bot=0.78, ao_top=0.98, add_bottom=False)
        if idx < len(y_bays) - 1:
            ny = y_bays[idx + 1]
            bar_z = 2.36 if idx % 2 == 0 else 2.18
            nb.add_box(mats["white_alu"], x_bar, (py + ny) * 0.5, bar_z, 0.045, (ny - py) - 0.09, 0.045, 0.0)
            # Hanging blue exercise straps (stop cleanly below bar)
            for sy in (py + 0.85, ny - 0.85):
                nb.add_box(mats["fitness_blue"], x_bar, sy, bar_z - 0.52, 0.025, 0.03, 0.52, 0.0, add_top=False)


def add_high_ball_fence_and_floodlights(nb: NodeBuilder, mats: dict) -> None:
    """Tall sports perimeter ball-stop fence & stadium twin LED floodlights along playground boundary (Photo 7)."""
    # West wall high ball-stop fence (x = -93.92, y = 89.5..124.5, z = 2.40..5.65; clean butt joints, zero overlap)
    y0, y1 = 89.5, 124.5
    n_bays = 10
    z_bot, z_top = 2.40, 5.65
    bay_len = (y1 - y0) / n_bays
    for i in range(n_bays + 1):
        fy = y0 + bay_len * i
        nb.add_box(mats["blue_steel"], -93.92, fy, z_bot, 0.08, 0.08, z_top - z_bot, 0.0, add_bottom=False)
        if i < n_bays:
            ny = y0 + bay_len * (i + 1)
            mid_y = (fy + ny) * 0.5
            seg_d = bay_len - 0.08
            nb.add_box(mats["blue_steel"], -93.92, mid_y, z_top - 0.06, 0.05, seg_d, 0.06, 0.0)
            nb.add_box(mats["blue_steel"], -93.92, mid_y, (z_bot + z_top) * 0.5, 0.05, seg_d, 0.05, 0.0)
            # Fine diagonal chain-link tension cables offset cleanly at x=-93.87 and x=-93.97 (no self-crossing!)
            nb.quad_enu(mats["blue_steel"], (-93.87, fy + 0.05, z_bot + 0.08), (-93.87, fy + 0.11, z_bot + 0.08), (-93.87, ny - 0.05, z_top - 0.08), (-93.87, ny - 0.11, z_top - 0.08), double_sided=True)
            nb.quad_enu(mats["blue_steel"], (-93.97, ny - 0.11, z_bot + 0.08), (-93.97, ny - 0.05, z_bot + 0.08), (-93.97, fy + 0.11, z_top - 0.08), (-93.97, fy + 0.05, z_top - 0.08), double_sided=True)

    # Stadium floodlight poles with twin angled LED fixtures (3 on west wall + 1 on east playground edge)
    for lx, ly, yaw_in in [(-93.65, 92.2, 0.0), (-93.65, 107.6, 0.0), (-93.65, 121.8, 0.0), (-13.20, 107.6, math.pi)]:
        nb.add_cylinder(mats["dark_steel"], lx, ly, 0.0, 0.11, 0.08, 7.20, 8)
        nb.add_box(mats["dark_steel"], lx, ly, 7.20, 0.12, 1.35, 0.08, yaw_in)
        cs, sn = math.cos(yaw_in), math.sin(yaw_in)
        for off_y in (-0.44, 0.44):
            fx = lx - off_y * sn
            fy_p = ly + off_y * cs
            nb.add_box(mats["dark_steel"], fx, fy_p, 7.28, 0.28, 0.46, 0.32, yaw_in, add_bottom=False)
            face_x = fx + 0.175 * cs
            face_y = fy_p + 0.175 * sn
            nb.add_box(mats["floodlight"], face_x, face_y, 7.31, 0.05, 0.40, 0.24, yaw_in)


def add_pa_speaker_stack(
    nb: NodeBuilder, sx: float, sy: float, yaw_rad: float, mats: dict, z_base: float = 0.0
) -> None:
    """Ground-stacked 2-tier outdoor PA speaker system (bottom horizontal subwoofer + top vertical main cabinet, >=25mm grille clearance)."""
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

    def rot(lx: float, ly: float) -> Vec2:
        return (sx + lx * cs - ly * sn, sy + lx * sn + ly * cs)

    # 4 low rubber feet directly on ground (clean butt joints)
    for fx in (-0.44, 0.44):
        for fy in (-0.28, 0.28):
            rx, ry = rot(fx, fy)
            nb.add_box(mats["dark_steel"], rx, ry, z_base + 0.0, 0.08, 0.08, 0.04, yaw_rad, ao_bot=0.68, ao_top=0.82, add_bottom=False, add_top=False)

    # Tier 1: Bottom HORIZONTAL subwoofer cabinet (w=1.06m E-W, d=0.72m N-S, h=0.62m; front face at ly=-0.36)
    nb.add_box(mats["dark_steel"], sx, sy, z_base + 0.04, 1.06, 0.72, 0.62, yaw_rad, ao_bot=0.72, ao_top=0.92)
    # Recessed horizontal dual-woofer grille facing -ly (25mm proud of subwoofer front -0.36 -> -0.385!)
    sub_f0 = rot(-0.48, -0.385)
    sub_f1 = rot(0.48, -0.385)
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
    nb.add_box(mats["dark_steel"], sx, sy, z_base + 0.66, 0.62, 0.54, 0.03, yaw_rad, ao_bot=0.76, ao_top=0.88, add_bottom=False, add_top=False)

    # Tier 2: Top VERTICAL full-range main speaker cabinet (w=0.58m, d=0.52m, h=1.02m; front face at ly=-0.26) + slim weather cap
    nb.add_box(mats["dark_steel"], sx, sy, z_base + 0.69, 0.58, 0.52, 1.02, yaw_rad, ao_bot=0.82, ao_top=0.96, add_bottom=False, add_top=False)
    hood_xy = rot(0.0, -0.02)
    nb.add_box(mats["dark_steel"], hood_xy[0], hood_xy[1], z_base + 1.71, 0.62, 0.58, 0.04, yaw_rad, ao_bot=0.88, ao_top=1.0, add_bottom=False)
    # Front vertical speaker grille & horn/drivers facing -ly (25mm proud of cabinet front -0.26 -> -0.285!)
    top_f0 = rot(-0.25, -0.285)
    top_f1 = rot(0.25, -0.285)
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
def build_west_campus(data_path: str, tex_dir: str, out_glb: str) -> Tuple[int, int]:
    west = json.loads(Path(data_path).read_text())
    ways = {w["id"]: w for w in west["ways"]}
    exp = GLBExporter()
    mats = init_materials(exp, tex_dir, include_west_details=True)

    # ---- Campus_Ground_West (strictly stratified Z-layers, zero coplanar overlaps) ----
    gnd = exp.add_node("Campus_Ground_West")
    # Layer -0.06m: Surrounding road base
    gnd.add_box(mats["surf"], -35.0, 60.0, -0.24, 290.0, 270.0, 0.18, 0.0, UV_ASPHALT, ao_bot=0.92, ao_top=0.92, add_bottom=False)
    # Layer -0.03m: 同福夹道 alley strip south of gate (stops cleanly at y=5.10 outside campus boundary)
    gnd.add_polygon_patch([(-4.2, -55.0), (4.2, -55.0), (4.2, 5.10), (-4.2, 5.10)], -0.03, mats["surf"], UV_ASPHALT, ao=0.95)
    # Layer 0.00m: Campus base plaza
    gnd.add_polygon_patch(ways["352521262"]["pts"], 0.0, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    # Layer +0.025m: Non-overlapping stone walkways, south lawn & plazas
    # East entry driveway south segment (stops cleanly at y=74.80 before dark-slate push-bike lane)
    gnd.add_polygon_patch([(-4.5, 5.2), (3.6, 5.2), (3.6, 74.8), (-5.2, 74.8)], 0.025, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    # East entry driveway north segment (starts cleanly at y=90.40 after dark-slate push-bike lane)
    gnd.add_polygon_patch([(-5.2, 90.4), (3.6, 90.4), (3.6, 96.5), (-5.2, 96.5)], 0.025, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    # Stone-paved passage east of 校史馆 (trimmed strictly between track y=124.8 & veranda walk y=134.35)
    gnd.add_polygon_patch([(-70.2, 124.8), (-65.0, 124.8), (-65.0, 134.35), (-70.2, 134.35)], 0.025, mats["surf"], UV_PLAZA_TILE, ao=0.96)
    # North alley west of W-H1 portal (stops cleanly at x=-70.2 before veranda walk)
    gnd.add_polygon_patch([(-93.6, 133.1), (-70.2, 133.1), (-70.2, 136.85), (-93.6, 136.85)], 0.025, mats["surf"], UV_PLAZA_TILE, ao=0.94)
    # Straight W-B5 south veranda walk (y=134.35..136.85, meets ping-pong apron at y=134.35 without overlap)
    gnd.add_polygon_patch([(-70.2, 134.35), (-6.8, 134.35), (-6.8, 136.85), (-70.2, 136.85)], 0.025, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    # Decorative crazy-paving stone medallion in north alley east entry (30mm proud of 0.025m alley)
    gnd.quad_enu(
        mats["details"],
        (-72.0, 133.75, 0.055), (-70.35, 133.75, 0.055),
        (-70.35, 135.15, 0.055), (-72.0, 135.15, 0.055),
        UV_CRAZY_PAVING, 0.95, 0.98,
    )

    # Playground South Plaza Strip (west stone-brick plaza)
    gnd.add_polygon_patch(
        [
            (-93.75, 81.5), (-89.15, 81.5), (-89.8, 76.2), (-69.8, 77.2),
            (-69.5, 66.8), (-55.2, 66.8), (-55.2, 77.2), (-46.8, 77.4),
            (-46.8, 90.4), (-93.75, 90.4),
        ],
        0.025, mats["surf"], UV_PLAZA_TILE, ao=0.96,
    )
    # East forecourt stone-brick walkway in front of Student Cafeteria (trimmed at x=-7.0 north of y=124.8 so zero overlap with ping-pong apron!)
    gnd.add_polygon_patch(
        [(-13.50, 90.4), (-5.60, 90.4), (-5.60, 127.5), (-5.80, 132.5), (-7.00, 132.5), (-7.00, 124.8), (-9.20, 124.8), (-9.20, 120.3), (-13.50, 120.3)],
        0.025, mats["surf"], UV_PLAZA_TILE, ao=0.97,
    )
    # Layer +0.050m: Dark-slate 自行车停放区 & 外置楼梯东侧一层推车穿堂连接道 (25mm clear above 0.025m stone plazas)
    gnd.add_polygon_patch(
        [(-46.8, 68.2), (-37.5, 68.4), (-11.5, 84.5), (-11.5, 90.4), (-46.8, 90.4)],
        0.050, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.92,
    )
    gnd.add_polygon_patch(
        [(-11.5, 84.5), (-9.5, 83.2), (-0.45, 83.2), (-0.45, 90.4), (-11.5, 90.4)],
        0.050, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.92,
    )
    gnd.add_polygon_patch(
        [(-0.45, 74.8), (3.35, 74.8), (3.35, 90.4), (-0.45, 90.4)],
        0.050, mats["details"], UV_DARK_SLATE_PODIUM, ao=0.91,
    )
    # Straight low stone curb separating south plaza / bicycle zone from EPDM playground edge (y = 90.36)
    gnd.add_box(mats["surf"], -53.6, 90.36, 0.02, 80.2, 0.24, 0.10, 0.0, UV_PLAZA_TILE, ao_bot=0.80, ao_top=0.98, add_bottom=False)
    # Layer +0.075m: Bike parking & push-bike lane white markings (strictly non-overlapping segments, 25mm above dark slate!)
    for lx0, ly0, lx1, ly1 in [
        # Main horizontal bay lines
        (-44.6, 78.2, -14.5, 78.34),
        (-44.6, 81.6, -14.5, 81.74),
        (-44.6, 85.4, 1.51, 85.54),
        # Vertical dividers trimmed strictly between horizontal lines
        (-44.6, 78.34, -44.45, 81.6),
        (-44.6, 81.74, -44.45, 85.4),
        (-29.5, 78.34, -29.35, 81.6),
        (-29.5, 81.74, -29.35, 85.4),
        (-14.65, 78.34, -14.5, 81.6),
        (-14.65, 81.74, -14.5, 85.4),
        # Parking bay stripes north of W-ST1 (vertical ticks start cleanly above horizontal bar at y=83.67)
        (-9.2, 83.55, -2.0, 83.67),
        (-9.2, 83.67, -9.08, 85.15),
        (-6.8, 83.67, -6.68, 85.15),
        (-4.4, 83.67, -4.28, 85.15),
        (-2.12, 83.67, -2.0, 85.15),
        # 1F push-bike lane guide lines through east portal (stop cleanly below y=85.40)
        (-0.22, 74.9, -0.10, 85.40),
        (3.00, 74.9, 3.12, 85.40),
        (1.39, 75.7, 1.51, 77.3),
        (1.39, 78.5, 1.51, 80.1),
        (1.39, 81.3, 1.51, 82.9),
    ]:
        gnd.quad_enu(mats["white_alu"], (lx0, ly0, 0.075), (lx1, ly0, 0.075), (lx1, ly1, 0.075), (lx0, ly1, 0.075))
    # Two rows of open steel wheel racks + realistic parked student bicycles (trimmed clear of W-B3 north-wall bikes!)
    for rack_y, rack_cx, rack_w, n_loops in ((79.8, -33.5, 20.0, 13), (83.8, -30.5, 26.0, 17)):
        gnd.add_box(mats["dark_steel"], rack_cx, rack_y, 0.05, rack_w, 0.14, 0.10, 0.0, add_bottom=False)
        for rx_i in range(n_loops):
            rx = -42.5 + rx_i * 1.52
            gnd.add_box(mats["blue_steel"], rx, rack_y, 0.15, 0.07, 0.52, 0.25, 0.0, add_bottom=False)
    add_parked_bicycle_row(gnd, -41.8, 79.85, 12, 1.62, 0.0, 0.28, mats)
    add_parked_bicycle_row(gnd, -41.2, 83.85, 15, 1.68, 0.0, -0.24, mats)

    # North-east water-rockery & 5 ping-pong tables apron in front of W-B5 east section (Photo 2: left 2, right 3!)
    gnd.add_polygon_patch(
        [(-31.4, 124.8), (-7.0, 124.8), (-7.0, 134.35), (-31.4, 134.35)],
        0.030, mats["surf"], UV_TRACK_EPDM, ao=0.96,
    )
    add_taihu_rockery_basin(gnd, -20.6, 131.5, mats)
    # 5 outdoor ping-pong tables oriented North-South (yaw=pi/2) & aligned parallel to rockery center (y=131.5)
    for ppx, ppy, ppyaw in [
        (-28.6, 131.5, math.pi * 0.5),  # Left 1
        (-25.2, 131.5, math.pi * 0.5),  # Left 2
        (-16.2, 131.5, math.pi * 0.5),  # Right 1
        (-13.2, 131.5, math.pi * 0.5),  # Right 2
        (-10.2, 131.5, math.pi * 0.5),  # Right 3
    ]:
        add_pingpong_table(gnd, ppx, ppy, ppyaw, mats)

    # Green lawn south of B-Wing & C-Wing junction + forecourt stone strip in front of B座 SE corner
    # (east edge stops at x=-5.2 to meet east entry driveway cleanly without overlapping!)
    gnd.add_polygon_patch(
        [(-41.5, 42.5), (-5.2, 42.5), (-5.2, 68.0), (-10.2, 68.0), (-35.5, 55.6), (-41.5, 55.6)],
        0.025, mats["surf"], UV_GRASS, ao=0.94,
    )
    gnd.add_polygon_patch(
        [(-35.5, 55.6), (-10.2, 68.0), (-5.2, 68.0), (-5.2, 72.8), (-5.8, 72.8), (-35.5, 57.5)],
        0.025, mats["surf"], UV_PLAZA_TILE, ao=0.97,
    )
    # Low clipped ornamental shrubs flanking 慎独石 on the entry axis (N≈30)
    for bsx, bsy, br in ((-4.25, 29.25, 0.42), (-1.05, 29.25, 0.38)):
        gnd.add_cylinder(mats["leaf"], bsx, bsy, 0.03, br, br * 0.75, br * 1.30, 8, UV_FOLIAGE, ao_bot=0.74, ao_top=0.96)

    # Campus Perimeter Rendered Wall with Structural Pilasters & Coping (non-overlapping segments & pilasters!)
    bound = ensure_ccw(ways["352521262"]["pts"])
    placed_pilasters: List[Vec2] = []

    def add_wall_segment(p_a: Vec2, p_b: Vec2) -> None:
        dx, dy = p_b[0] - p_a[0], p_b[1] - p_a[1]
        L = math.hypot(dx, dy)
        if L < 0.8:
            return
        yaw = math.atan2(dy, dx)
        tx, ty = dx / L, dy / L
        # Trim wall/coping ends by 0.26m so they butt cleanly into 0.52x0.52 corner pilasters (zero overlap!)
        trim = min(0.26, L * 0.22)
        eff_L = L - 2.0 * trim
        mx, my = (p_a[0] + p_b[0]) * 0.5, (p_a[1] + p_b[1]) * 0.5
        gnd.add_box(mats["wall_grey_render"], mx, my, 0.0, eff_L, 0.34, 2.30, yaw, ao_bot=0.76, ao_top=0.95, add_top=False)
        gnd.add_box(mats["surf"], mx, my, 2.30, eff_L, 0.44, 0.10, yaw, UV_QINGZHUAN, ao_bot=0.86, ao_top=0.98)
        n_pil = max(2, int(L // 4.2) + 1)
        for pi in range(n_pil):
            t_p = pi / (n_pil - 1)
            px = p_a[0] + dx * t_p
            py = p_a[1] + dy * t_p
            if any(math.hypot(px - ox, py - oy) < 0.55 for ox, oy in placed_pilasters):
                continue
            placed_pilasters.append((px, py))
            # Square 0.52x0.52 pilaster (40mm proud of 0.44m coping on all 4 sides, capped at z=2.44m cleanly above coping!)
            gnd.add_box(mats["surf"], px, py, 0.0, 0.52, 0.52, 2.44, yaw, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.96)

    for i in range(len(bound)):
        a, b = bound[i], bound[(i + 1) % len(bound)]
        if a[1] < 8.0 and b[1] < 8.0 and -11.5 <= a[0] <= 5.0 and -11.5 <= b[0] <= 5.0:
            continue  # Open for West Gate & Guardhouse facade
        if min(a[1], b[1]) >= 96.4 and max(a[1], b[1]) <= 138.3 and min(a[0], b[0]) >= -6.9:
            continue  # W-B6 Cafeteria & its northern school annex exterior walls form the campus boundary here
        # Split east boundary around W-ST1 1F bike pass-through east pier (y=75.0..83.6) so wall doesn't intersect W-ST1!
        if abs(a[0] - 3.9) < 0.5 and abs(b[0] - 3.9) < 0.5 and min(a[1], b[1]) < 75.0 and max(a[1], b[1]) > 83.6:
            y_lo, y_hi = (a, b) if a[1] < b[1] else (b, a)
            t1 = (75.0 - y_lo[1]) / (y_hi[1] - y_lo[1])
            t2 = (83.6 - y_lo[1]) / (y_hi[1] - y_lo[1])
            p1 = (y_lo[0] + (y_hi[0] - y_lo[0]) * t1, 75.0)
            p2 = (y_lo[0] + (y_hi[0] - y_lo[0]) * t2, 83.6)
            add_wall_segment(y_lo, p1)
            add_wall_segment(p2, y_hi)
            continue
        add_wall_segment(a, b)

    # West wall fitness pull-up bars + red mats & high ball-stop fence + floodlights
    add_pullup_rack_and_mats(gnd, mats)
    add_high_ball_fence_and_floodlights(gnd, mats)

    # ---- W-G1: 同福夹道3号正门 + 左侧大理石保安厅（含转角观察窗、东侧出入门与挑檐） ----
    gate = exp.add_node("W-G1")
    # Twin marble gate piers (stop cleanly at z=4.32 under white fascia soffit)
    gate.add_box(mats["gates"], -4.2, 5.2, 0.0, 1.2, 1.5, 4.32, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.98, add_top=False)
    gate.add_box(mats["gates"], 3.2, 5.2, 0.0, 1.4, 1.5, 4.32, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.98, add_top=False)
    # Guardhouse (left/west of gate: x -10.90..-5.65, y 4.80..10.40) with recessed doors & windows
    gate.add_box(mats["gates"], -8.275, 7.60, 0.0, 5.25, 5.60, 0.10, 0.0, UV_MARBLE, ao_bot=0.74, ao_top=0.90)
    gate.add_box(mats["gates"], -8.275, 7.60, 3.32, 5.25, 5.60, 0.28, 0.0, UV_MARBLE, ao_bot=0.86, ao_top=0.96, add_top=False)
    # White aluminum overhanging canopy extending east to join left gate pier (sits cleanly ON TOP at z=3.60)
    gate.add_box(mats["white_alu"], -7.875, 7.60, 3.60, 6.35, 5.80, 0.28, 0.0, ao_bot=0.88, ao_top=1.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    # South marble wall (SW solid pier + window apron) + recessed SE corner service window (zero frame overlaps!)
    gate.add_box(mats["gates"], -9.875, 4.98, 0.10, 2.05, 0.36, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95, add_bottom=False, add_top=False)
    gate.quad_enu(mats["gates"], (-10.35, 4.775, 2.25), (-9.35, 4.775, 2.25), (-9.35, 4.775, 2.85), (-10.35, 4.775, 2.85), UV_EAST_SIGN, 0.92, 1.0)
    gate.quad_enu(mats["crimson"], (-10.08, 4.775, 1.82), (-9.62, 4.775, 1.82), (-9.62, 4.775, 2.12), (-10.08, 4.775, 2.12), (0.1, 0.1, 0.9, 0.9), 0.94, 1.0)
    gate.add_box(mats["gates"], -7.25, 4.98, 0.10, 3.20, 0.36, 0.91, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94, add_bottom=False, add_top=False)
    gate.add_box(mats["gates"], -7.25, 4.93, 1.01, 3.20, 0.46, 0.05, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.98)
    gate.quad_enu(mats["glass"], (-8.80, 4.96, 1.12), (-5.81, 4.96, 1.12), (-5.81, 4.96, 3.27), (-8.80, 4.96, 3.27), UV_GLASS_WINDOW)
    gate.add_box(mats["dark_steel"], -7.31, 4.89, 1.06, 2.98, 0.08, 0.06, 0.0, add_bottom=False)
    gate.add_box(mats["dark_steel"], -7.31, 4.89, 2.18, 2.98, 0.08, 0.08, 0.0)
    gate.add_box(mats["dark_steel"], -7.31, 4.89, 3.26, 2.98, 0.08, 0.06, 0.0, add_top=False)
    for vx_s in (-8.81, -7.25):
        gate.add_box(mats["dark_steel"], vx_s, 4.89, 1.12, 0.07, 0.08, 1.06, 0.0, add_bottom=False, add_top=False)
        gate.add_box(mats["dark_steel"], vx_s, 4.89, 2.26, 0.07, 0.08, 1.00, 0.0, add_bottom=False, add_top=False)
    gate.add_box(mats["dark_steel"], -6.52, 4.89, 1.12, 0.05, 0.08, 1.06, 0.0, add_bottom=False, add_top=False)
    # Corner steel post joining South & East glass corner window
    gate.add_box(mats["dark_steel"], -5.72, 4.88, 1.06, 0.18, 0.18, 2.26, 0.0, add_bottom=False, add_top=False)
    # East wall (facing main entry driveway: SE corner window trimmed cleanly north of y=5.16 + entrance glass door + north window)
    gate.add_box(mats["gates"], -5.83, 6.255, 0.10, 0.36, 2.19, 0.91, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94, add_bottom=False, add_top=False)
    gate.add_box(mats["gates"], -5.81, 6.255, 1.01, 0.40, 2.19, 0.05, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.98)
    gate.quad_enu(mats["glass"], (-5.81, 4.98, 1.12), (-5.81, 7.35, 1.12), (-5.81, 7.35, 3.26), (-5.81, 4.98, 3.26), UV_GLASS_WINDOW)
    gate.add_box(mats["dark_steel"], -5.74, 6.165, 1.06, 0.08, 2.37, 0.06, 0.0, add_bottom=False)
    gate.add_box(mats["dark_steel"], -5.74, 6.165, 2.18, 0.08, 2.37, 0.08, 0.0)
    gate.add_box(mats["dark_steel"], -5.74, 6.165, 3.26, 0.08, 2.37, 0.06, 0.0, add_top=False)
    for vy_e in (6.15, 7.31):
        gate.add_box(mats["dark_steel"], -5.74, vy_e, 1.12, 0.08, 0.07, 1.06, 0.0, add_bottom=False, add_top=False)
        gate.add_box(mats["dark_steel"], -5.74, vy_e, 2.26, 0.08, 0.07, 1.00, 0.0, add_bottom=False, add_top=False)
    # Pier between corner window & guardhouse door
    gate.add_box(mats["gates"], -5.83, 7.50, 0.10, 0.36, 0.30, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95, add_bottom=False, add_top=False)
    # Guardhouse East Entrance Doorway (y: 7.65..8.85) with granite step, door frame, transom & handle
    gate.add_box(mats["surf"], -5.465, 8.25, 0.0, 0.37, 1.40, 0.10, 0.0, UV_QINGZHUAN, ao_bot=0.78, ao_top=0.94)
    gate.add_box(mats["gates"], -5.83, 8.25, 2.35, 0.36, 1.20, 0.97, 0.0, UV_MARBLE, ao_bot=0.82, ao_top=0.95, add_top=False)
    gate.add_box(mats["dark_steel"], -5.77, 7.69, 0.10, 0.12, 0.08, 2.19, 0.0, add_bottom=False, add_top=False)
    gate.add_box(mats["dark_steel"], -5.77, 8.81, 0.10, 0.12, 0.08, 2.19, 0.0, add_bottom=False, add_top=False)
    gate.add_box(mats["dark_steel"], -5.77, 8.25, 2.29, 0.12, 1.20, 0.06, 0.0, add_top=False)
    gate.add_box(mats["dark_steel"], -5.77, 8.25, 2.02, 0.12, 1.04, 0.06, 0.0)
    gate.add_box(mats["dark_steel"], -5.80, 8.25, 0.10, 0.06, 1.04, 0.82, 0.0, add_bottom=False)
    gate.quad_enu(mats["glass"], (-5.79, 7.73, 0.92), (-5.79, 8.77, 0.92), (-5.79, 8.77, 2.29), (-5.79, 7.73, 2.29), UV_GLASS_WINDOW)
    gate.add_box(mats["white_alu"], -5.72, 7.84, 0.96, 0.05, 0.05, 0.38, 0.0)
    # Pier & East North-bay window (y: 8.85..10.40)
    gate.add_box(mats["gates"], -5.83, 8.975, 0.10, 0.36, 0.25, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95, add_bottom=False, add_top=False)
    gate.add_box(mats["gates"], -5.83, 9.625, 0.10, 0.36, 1.05, 1.01, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94, add_bottom=False, add_top=False)
    gate.add_box(mats["gates"], -5.83, 9.625, 2.95, 0.36, 1.05, 0.37, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.95, add_top=False)
    gate.add_box(mats["gates"], -5.79, 9.625, 1.11, 0.44, 1.05, 0.05, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.98)
    gate.quad_enu(mats["glass"], (-5.81, 9.10, 1.21), (-5.81, 10.15, 1.21), (-5.81, 10.15, 2.90), (-5.81, 9.10, 2.90), UV_GLASS_WINDOW)
    gate.add_box(mats["dark_steel"], -5.74, 9.625, 1.21, 0.08, 0.06, 1.69, 0.0, add_bottom=False, add_top=False)
    gate.add_box(mats["dark_steel"], -5.74, 9.625, 2.90, 0.08, 1.05, 0.05, 0.0, add_top=False)
    gate.add_box(mats["dark_steel"], -5.74, 9.625, 1.16, 0.08, 1.05, 0.05, 0.0, add_bottom=False)
    gate.add_box(mats["gates"], -5.83, 10.275, 0.10, 0.36, 0.25, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95, add_bottom=False, add_top=False)
    # West wall with recessed daylight window + North solid wall
    gate.add_box(mats["gates"], -10.72, 5.68, 0.10, 0.36, 1.04, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95, add_bottom=False, add_top=False)
    gate.add_box(mats["gates"], -10.72, 7.60, 0.10, 0.36, 2.80, 1.05, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94, add_bottom=False)
    gate.add_box(mats["gates"], -10.72, 7.60, 2.95, 0.36, 2.80, 0.37, 0.0, UV_MARBLE, ao_bot=0.84, ao_top=0.95, add_top=False)
    gate.quad_enu(mats["glass"], (-10.74, 9.00, 1.21), (-10.74, 6.20, 1.21), (-10.74, 6.20, 2.90), (-10.74, 9.00, 2.90), UV_GLASS_WINDOW)
    gate.add_box(mats["dark_steel"], -10.81, 7.60, 1.21, 0.08, 0.06, 1.69, 0.0, add_bottom=False, add_top=False)
    gate.add_box(mats["dark_steel"], -10.81, 7.60, 2.90, 0.08, 2.80, 0.05, 0.0, add_top=False)
    gate.add_box(mats["dark_steel"], -10.81, 7.60, 1.15, 0.08, 2.80, 0.06, 0.0, add_bottom=False)
    gate.add_box(mats["gates"], -10.72, 9.70, 0.10, 0.36, 1.40, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95, add_bottom=False, add_top=False)
    gate.add_box(mats["gates"], -8.275, 10.22, 0.10, 4.53, 0.36, 3.22, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.95, add_bottom=False, add_top=False)
    # Pedestrian passage lintel & glazed doorway frame between guardhouse and left gate pier (20mm clear of guardhouse sill!)
    gate.add_box(mats["gates"], -5.225, 5.375, 3.35, 0.85, 1.15, 0.97, 0.0, UV_MARBLE, ao_bot=0.80, ao_top=0.96, add_top=False)
    gate.add_box(mats["dark_steel"], -5.56, 5.05, 0.0, 0.06, 0.09, 2.20, 0.0, add_top=False)
    gate.add_box(mats["dark_steel"], -4.85, 5.05, 0.0, 0.07, 0.09, 2.20, 0.0, add_top=False)
    gate.add_box(mats["dark_steel"], -5.205, 5.05, 2.20, 0.80, 0.09, 0.08, 0.0)
    gate.add_box(mats["dark_steel"], -5.56, 5.38, 0.05, 0.05, 0.56, 2.12, 0.0, add_bottom=False)
    # Overhead fascia header (plain brown-red metal cladding + paved roof + soffit), single centered LED screen & East pier plaque
    gate.add_box(
        mats["gates"], -2.05, 5.15, 4.35, 13.0, 1.95, 1.35, 0.0,
        UV_WEST_FASCIA_PLAIN, ao_bot=0.82, ao_top=0.98,
        top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
    )
    gate.add_box(mats["white_alu"], -2.05, 5.15, 4.32, 12.92, 1.88, 0.03, 0.0, ao_bot=0.86, ao_top=0.94, add_top=False)
    gate.add_box(mats["dark_steel"], -0.45, 4.13, 4.52, 7.80, 0.09, 1.02, 0.0, ao_bot=0.82, ao_top=0.98)
    gate.quad_enu(
        mats["led"],
        (-4.25, 4.055, 4.58), (3.35, 4.055, 4.58),
        (3.35, 4.055, 5.48), (-4.25, 4.055, 5.48),
        UV_WEST_LED_ONLY, 1.0, 1.0,
    )
    gate.quad_enu(mats["gates"], (2.68, 4.415, 0.9), (3.72, 4.415, 0.9), (3.72, 4.415, 3.45), (2.68, 4.415, 3.45), UV_WEST_PLAQUE, 0.95, 1.0)
    for wing_x in (-3.25, 1.95):
        gate.add_box(mats["dark_steel"], wing_x, 6.8, 0.15, 0.12, 3.1, 2.2, 0.0, ao_bot=0.80, ao_top=1.0)
        for pi in range(9):
            py = 5.4 + pi * 0.34
            gate.add_box(mats["dark_steel"], wing_x, py, 2.35, 0.06, 0.06, 0.25, 0.0, ao_bot=0.85, ao_top=1.0, add_bottom=False)
    # Yellow hatch grid lines outside gate (non-overlapping E-W at +0.025m, N-S segments trimmed between E-W bands!)
    hy_bands = [-1.5 + hi * 1.4 for hi in range(4)]
    for yoff in hy_bands:
        gate.quad_enu(mats["yellow_hatch"], (-3.8, yoff, 0.025), (2.8, yoff, 0.025), (2.8, yoff + 0.14, 0.025), (-3.8, yoff + 0.14, 0.025))
    vy_spans = [(-2.0, hy_bands[0]), (hy_bands[0] + 0.14, hy_bands[1]), (hy_bands[1] + 0.14, hy_bands[2]), (hy_bands[2] + 0.14, hy_bands[3]), (hy_bands[3] + 0.14, 3.6)]
    for hi in range(4):
        xoff = -3.4 + hi * 1.8
        for ys0, ys1 in vy_spans:
            gate.quad_enu(mats["yellow_hatch"], (xoff, ys0, 0.025), (xoff + 0.14, ys0, 0.025), (xoff + 0.14, ys1, 0.025), (xoff, ys1, 0.025))

    # Stainless-steel retractable gate (half-open X-lattice; offset diagonal bars ±0.03m from vertical pickets!)
    gate.add_box(mats["stainless"], -0.45, 5.12, 1.62, 6.60, 0.06, 0.06, 0.0)
    gate.add_box(mats["stainless"], -0.45, 5.12, 0.12, 6.60, 0.06, 0.06, 0.0)
    for gi in range(9):
        gx = -3.75 + gi * 0.735
        z0, z1 = (0.18, 1.58) if gi % 2 == 0 else (1.58, 0.18)
        y_diag = 5.165 if gi % 2 == 0 else 5.075
        gate.quad_enu(
            mats["stainless"],
            (gx, y_diag, z0), (gx + 0.66, y_diag, z1),
            (gx + 0.66, y_diag, z1 + 0.035), (gx, y_diag, z0 + 0.035),
            (0.1, 0.1, 0.9, 0.9), 0.92, 1.0, double_sided=True,
        )
    for gx in (-3.75 + 0.735 * k for k in range(10)):
        gate.add_box(mats["stainless"], gx, 5.12, 0.18, 0.035, 0.035, 1.44, 0.0, add_bottom=False, add_top=False)

    # Five yellow/black bollards in front of the gate (3 non-overlapping stacked bands!)
    for bi in range(5):
        bxp = -3.55 + bi * 1.50
        gate.add_cylinder(mats["yellow_hatch"], bxp, 2.45, 0.0, 0.092, 0.088, 0.42, 10, ao_bot=0.78, ao_top=0.92)
        gate.add_cylinder(mats["dark_steel"], bxp, 2.45, 0.42, 0.094, 0.092, 0.12, 10, ao_bot=0.86, ao_top=0.96)
        gate.add_cylinder(mats["yellow_hatch"], bxp, 2.45, 0.54, 0.087, 0.084, 0.32, 10, ao_bot=0.92, ao_top=1.0)

    # Gold-framed glass honours/notice case on the low wall just east of the gate (west face; 25mm stepped!)
    dcx, dcy = 5.54, 2.20
    gate.add_box(mats["gold_trim"], dcx, dcy, 0.98, 0.10, 1.85, 1.45, 0.0, ao_bot=0.86, ao_top=1.0)
    gate.add_box(mats["white_alu"], dcx - 0.07, dcy, 1.08, 0.04, 1.65, 1.25, 0.0, ao_bot=0.88, ao_top=1.0)
    gate.quad_enu(
        mats["glass"],
        (dcx - 0.115, dcy + 0.80, 1.10), (dcx - 0.115, dcy - 0.80, 1.10),
        (dcx - 0.115, dcy - 0.80, 2.28), (dcx - 0.115, dcy + 0.80, 2.28),
        (0.1, 0.1, 0.9, 0.9), 0.94, 1.0,
    )

    # ---- W-L1: 慎独石 (entry axis, ~N30, facing south; natural boulder + red vertical inscription) ----
    shendu = exp.add_node("W-L1")
    shendu.add_box(mats["surf"], -2.6, 30.0, 0.025, 2.20, 1.50, 0.14, 0.0, UV_QINGZHUAN, ao_bot=0.72, ao_top=0.90)
    add_tapered_monolith(
        shendu,
        -2.6, 30.0,
        [
            (0.14, 0.98, 1.12, 0.84, 1.08, 0.78),
            (0.98, 1.78, 1.08, 0.78, 0.98, 0.70),
            (1.78, 2.30, 0.98, 0.70, 0.74, 0.54),
            (2.30, 2.58, 0.74, 0.54, 0.38, 0.28),
        ],
        mats["gates"], UV_SHENDU_GRANITE,
    )
    shendu.quad_enu(mats["gates"], (-3.08, 29.53, 0.30), (-2.12, 29.53, 0.30), (-2.24, 29.63, 2.10), (-2.96, 29.63, 2.10), UV_SHENDU_STONE, 0.90, 1.0)
    # Low granite kerb + clipped hedge strips framing the stone on the axis
    shendu.add_box(mats["surf"], -3.85, 29.15, 0.03, 1.25, 0.55, 0.36, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.94)
    shendu.add_box(mats["surf"], -1.35, 29.15, 0.03, 1.25, 0.55, 0.36, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.94)
    # Teaching-building front pines (校方供稿：教学楼前青松)
    gnd.add_tree(-4.55, 33.6, "pine", 7.6, mats["trunk"], mats["leaf_pine"])
    gnd.add_tree(-4.30, 41.0, "pine", 6.8, mats["trunk"], mats["leaf_pine"])

    # ---- W-L3: 冰心像 (bronze portrait bust on stone pedestal, magnolia beside it) ----
    bx_node = exp.add_node("W-L3")
    bx_node.add_box(mats["surf"], -16.5, 58.8, 0.03, 3.0, 3.0, 0.18, 0.0, UV_QINGZHUAN, ao_bot=0.78, ao_top=0.92)
    bx_node.add_box(mats["white_alu"], -16.5, 58.8, 0.18, 1.50, 1.50, 0.25, 0.0)
    bx_node.add_box(mats["gates"], -16.5, 58.8, 0.43, 0.86, 0.86, 1.35, 0.0, UV_MARBLE, ao_bot=0.80, ao_top=0.98)
    # Bronze plaque on the south face of the pedestal
    bx_node.quad_enu(mats["gold_trim"], (-17.02, 58.28, 0.72), (-15.98, 58.28, 0.72), (-15.98, 58.28, 1.12), (-17.02, 58.28, 1.12), (0.1, 0.1, 0.9, 0.9), 0.92, 1.0)
    # Bust: chest, shoulders, neck, head, hair cap; total height ~2.65 m
    bx_node.add_cylinder(mats["bronze"], -16.5, 58.8, 1.78, 0.34, 0.26, 0.46, 12, ao_bot=0.80, ao_top=1.0)
    bx_node.add_box(mats["bronze"], -16.5, 58.8, 1.92, 0.62, 0.34, 0.34, 0.0, ao_bot=0.82, ao_top=1.0)
    bx_node.add_cylinder(mats["bronze"], -16.5, 58.8, 2.24, 0.095, 0.085, 0.14, 10, ao_bot=0.86, ao_top=1.0)
    bx_node.add_sphere(mats["bronze"], -16.5, 58.8, 2.44, 0.155, 0.195, 0.145, 12, 8, (0.0, 0.0, 1.0, 1.0), 1.0)
    bx_node.add_sphere(mats["bronze"], -16.5, 58.86, 2.53, 0.165, 0.135, 0.150, 12, 6, (0.0, 0.0, 1.0, 1.0), 0.94)
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
    # Projecting balconies on the south facade (cleanly separated white rails, terracotta side panels & exterior hanging flower boxes!)
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
            # Balcony floor slab starts cleanly at out_d=0.08m (20mm proud of pilasters at 0.06m) -> center 0.62, d=1.08 (0.08..1.16)
            px = ba[0] + btx * along + bnx * 0.62
            py = ba[1] + bty * along + bny * 0.62
            wb3.add_box(mats["white_alu"], px, py, bz, 3.70, 1.08, 0.14, byaw, ao_bot=0.84, ao_top=0.98)
            for s in (-1, 1):
                sx = px + btx * s * 1.78
                sy = py + bty * s * 1.78
                wb3.add_box(mats["surf"], sx, sy, bz + 0.14, 0.14, 1.02, 0.55, byaw, UV_TERRACOTTA_BRICK, 0.84, 0.98, add_bottom=False)
            for rz, rw in ((0.48, 3.42), (0.78, 3.66), (1.08, 3.66)):
                rx = ba[0] + btx * along + bnx * 1.11
                ry = ba[1] + bty * along + bny * 1.11
                wb3.add_box(mats["white_alu"], rx, ry, bz + rz, rw, 0.05, 0.05, byaw, ao_bot=0.90, ao_top=1.0)
            # Crimson hanging flower box mounted cleanly OUTSIDE the white railing (out_d=1.18..1.38, z=bz+0.80..1.02)
            # Zero intersection with white top handrail (out_d=1.085..1.135, z=bz+1.08..1.13)!
            fx = ba[0] + btx * along + bnx * 1.28
            fy = ba[1] + bty * along + bny * 1.28
            wb3.add_box(mats["crimson"], fx, fy, bz + 0.80, 2.60, 0.20, 0.22, byaw, ao_bot=0.86, ao_top=1.0)
            for fi in range(4):
                wb3.add_sphere(
                    mats["flower_rose"],
                    fx + btx * (-0.90 + fi * 0.60), fy + bty * (-0.90 + fi * 0.60),
                    bz + 1.09, 0.095, 0.075, 0.095, 6, 3, (0.0, 0.0, 1.0, 1.0), 1.0,
                )
    for aac, zac in ((6.0, 11.5), (18.5, 14.9), (28.0, 18.3)):
        acx = ba[0] + btx * aac + bnx * 0.26
        acy = ba[1] + bty * aac + bny * 0.26
        add_ac_unit(wb3, acx, acy, zac, byaw, mats)

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
    # Ground-floor North-facing classroom/corridor double doors (cleanly proud of plinth & clear of pilasters) + parked bikes
    for door_along in (10.5, 21.5):
        nd_c = (-11.5 + wb3_ntx * door_along + wb3_nnx * 0.14, 84.5 + wb3_nty * door_along + wb3_nny * 0.14)
        wb3.add_box(mats["dark_steel"], nd_c[0], nd_c[1], 0.12, 2.20, 0.18, 2.75, math.atan2(wb3_n_dy, wb3_n_dx), add_bottom=False)
        nd_l = (-11.5 + wb3_ntx * (door_along - 0.98) + wb3_nnx * 0.255, 84.5 + wb3_nty * (door_along - 0.98) + wb3_nny * 0.255)
        nd_r = (-11.5 + wb3_ntx * (door_along + 0.98) + wb3_nnx * 0.255, 84.5 + wb3_nty * (door_along + 0.98) + wb3_nny * 0.255)
        wb3.quad_enu(mats["glass"], (nd_l[0], nd_l[1], 0.20), (nd_r[0], nd_r[1], 0.20), (nd_r[0], nd_r[1], 2.65), (nd_l[0], nd_l[1], 2.65), UV_GLASS_WINDOW, 0.88, 0.98)
    add_parked_bicycle_row(
        wb3,
        -15.2 + wb3_nnx * 0.95, 82.2 + wb3_nny * 0.95,
        11, wb3_ntx * 1.55, wb3_nty * 1.55,
        wb3_n_yaw, mats,
    )
    # Split AC outdoor units on B座 south & north walls
    for ac_along, ac_st in [(6.2, 1), (6.2, 2), (15.0, 2), (15.0, 3), (24.2, 1), (24.2, 4)]:
        ac_p = (-11.5 + wb3_ntx * ac_along + wb3_nnx * 0.24, 84.5 + wb3_nty * ac_along + wb3_nny * 0.24)
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
        sap = (wb3_ax + wb3_tx * s_along + wb3_nx * 0.24, wb3_ay + wb3_ty * s_along + wb3_ny * 0.24)
        add_ac_unit(wb3, sap[0], sap[1], 1.12 + s_st * 3.45, wb3_yaw - math.pi * 0.5, mats)

    # Granite entry step + protruding marble portal frame (jambs stop cleanly at z=3.05 under stucco header!)
    st_c = wb3_dpt(0.0, 0.52)
    wb3.add_box(mats["gates"], st_c[0], st_c[1], 0.0, 3.70, 1.04, 0.14, wb3_yaw, UV_MARBLE, ao_bot=0.76, ao_top=0.95, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for jamb_s in (-1.48, 1.48):
        jc = wb3_dpt(jamb_s, 0.16)
        wb3.add_box(mats["gates"], jc[0], jc[1], 0.14, 0.48, 0.36, 2.91, wb3_yaw, UV_MARBLE, ao_bot=0.78, ao_top=0.96, add_bottom=False, add_top=False)
    hc = wb3_dpt(0.0, 0.16)
    wb3.add_box(mats["surf"], hc[0], hc[1], 3.05, 3.44, 0.36, 0.90, wb3_yaw, UV_STUCCO, ao_bot=0.84, ao_top=0.96)
    # Recessed double aluminum-framed glass entrance doors + glazed transom (30mm clear of backing)
    dc_back = wb3_dpt(0.0, 0.08)
    wb3.add_box(mats["dark_steel"], dc_back[0], dc_back[1], 0.14, 2.48, 0.24, 2.91, wb3_yaw, ao_bot=0.78, ao_top=0.94, add_bottom=False, add_top=False)
    p_dl0, p_dl1 = wb3_dpt(-1.18, 0.23), wb3_dpt(1.18, 0.23)
    wb3.quad_enu(mats["glass"], (p_dl0[0], p_dl0[1], 0.22), (p_dl1[0], p_dl1[1], 0.22), (p_dl1[0], p_dl1[1], 2.42), (p_dl0[0], p_dl0[1], 2.42), UV_GLASS_WINDOW, 0.90, 1.0)
    wb3.quad_enu(mats["glass"], (p_dl0[0], p_dl0[1], 2.52), (p_dl1[0], p_dl1[1], 2.52), (p_dl1[0], p_dl1[1], 2.98), (p_dl0[0], p_dl0[1], 2.98), UV_GLASS_WINDOW, 0.90, 1.0)
    for mul_s, w_m, z0_m, z1_m in [(-1.20, 0.08, 0.14, 2.43), (-1.20, 0.08, 2.51, 3.05), (0.0, 0.07, 0.14, 2.43), (0.0, 0.07, 2.51, 3.05), (1.20, 0.08, 0.14, 2.43), (1.20, 0.08, 2.51, 3.05), (-0.14, 0.04, 0.92, 1.42), (0.14, 0.04, 0.92, 1.42)]:
        mc = wb3_dpt(mul_s, 0.28)
        wb3.add_box(mats["white_alu"], mc[0], mc[1], z0_m, w_m, 0.06, z1_m - z0_m, wb3_yaw, add_bottom=False, add_top=False)
    mc_bar = wb3_dpt(0.0, 0.28)
    wb3.add_box(mats["white_alu"], mc_bar[0], mc_bar[1], 2.43, 2.48, 0.06, 0.08, wb3_yaw)
    # Cantilevered entrance canopy + steel tie rods (cleanly proud of pilasters at 0.06m!)
    canc = wb3_dpt(0.0, 0.80)
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
    # Relief textured front face (30mm proud of white backing box at +0.21)
    cs_c, sn_c = math.cos(c_n_yaw), math.sin(c_n_yaw)
    r_p0 = (rel_cx + 2.74 * cs_c + c_nnx * 0.24, rel_cy + 2.74 * sn_c + c_nny * 0.24)
    r_p1 = (rel_cx - 2.74 * cs_c + c_nnx * 0.24, rel_cy - 2.74 * sn_c + c_nny * 0.24)
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
    # Rooftop Open Dark-Steel Pergola Frame on C座 north block (posts stop under beams; transverse/longitudinal beams stacked cleanly!)
    wb1_roof_z = 0.85 + 6 * 3.80 + 0.25
    for px_r in (-87.8, -82.4, -77.0, -71.6):
        for py_r in (60.6, 68.0, 75.2):
            wb1.add_box(mats["dark_steel"], px_r, py_r, wb1_roof_z, 0.26, 0.26, 1.35, c_n_yaw, add_bottom=False, add_top=False)
    for lx in (-87.8, -82.4, -77.0, -71.6):
        wb1.add_box(mats["dark_steel"], lx, 67.9, wb1_roof_z + 1.35, 0.22, 15.0, 0.24, 0.0, ao_bot=0.86, ao_top=1.0)
    for ly in (60.6, 64.3, 68.0, 71.6, 75.2):
        wb1.add_box(mats["dark_steel"], -79.7, ly, wb1_roof_z + 1.59, 17.0, 0.22, 0.24, c_n_yaw, ao_bot=0.86, ao_top=1.0)
    # C座 South-West Exterior Return Staircase (cleanly separated landing slabs & corner-trimmed blue_steel screens!)
    wb1.add_box(mats["surf"], -82.6, 42.0, 0.0, 4.4, 9.6, 0.85, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.90)
    for lvl in range(5):
        sz = 0.85 + lvl * 3.80
        wb1.add_box(mats["white_alu"], -82.6, 42.0, sz + 1.85, 3.85, 8.95, 0.28, 0.0)
        wb1.add_box(mats["blue_steel"], -84.62, 42.0, sz + 0.2, 0.12, 9.32, 3.55, 0.0)
        wb1.add_box(mats["blue_steel"], -82.54, 37.38, sz + 0.2, 4.04, 0.12, 3.55, 0.0)
        wb1.add_box(mats["blue_steel"], -82.54, 46.62, sz + 0.2, 4.04, 0.12, 3.55, 0.0)
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

    # Precompute continuous vertex normals along Bézier ramp so adjacent deck/underside/curb segments join seamlessly with zero overlap!
    half_w = 1.55
    ramp_l: List[Vec3] = []
    ramp_r: List[Vec3] = []
    for k in range(segs_r + 1):
        p_prev = ramp_pts[max(0, k - 1)]
        p_next = ramp_pts[min(segs_r, k + 1)]
        dx, dy = p_next[0] - p_prev[0], p_next[1] - p_prev[1]
        ll = max(math.hypot(dx, dy), 0.01)
        nx, ny = dy / ll, -dx / ll
        a0 = ramp_pts[k]
        ramp_l.append((a0[0] - nx * half_w, a0[1] - ny * half_w, a0[2]))
        ramp_r.append((a0[0] + nx * half_w, a0[1] + ny * half_w, a0[2]))

    for k in range(segs_r):
        a0, a1 = ramp_pts[k], ramp_pts[k + 1]
        dx, dy = a1[0] - a0[0], a1[1] - a0[1]
        l0, r0 = ramp_l[k], ramp_r[k]
        l1, r1 = ramp_l[k + 1], ramp_r[k + 1]
        wr1.quad_enu(mats["surf"], l0, r0, r1, l1, UV_ASPHALT, 0.94, 0.98)
        # Solid box-girder soffit 0.34m below deck (never coplanar with asphalt deck!)
        wr1.quad_enu(
            mats["white_alu"],
            (r0[0], r0[1], r0[2] - 0.34), (l0[0], l0[1], l0[2] - 0.34),
            (l1[0], l1[1], l1[2] - 0.34), (r1[0], r1[1], r1[2] - 0.34),
            (0.1, 0.1, 0.9, 0.9), 0.72, 0.72,
        )
        for s0, s1 in ((l0, l1), (r0, r1)):
            wr1.quad_enu(mats["white_alu"], (s0[0], s0[1], s0[2] - 0.34), (s1[0], s1[1], s1[2] - 0.34), (s1[0], s1[1], s1[2] + 0.18), (s0[0], s0[1], s0[2] + 0.18), (0.1, 0.1, 0.9, 0.9), 0.85, 1.0, double_sided=True)
            wr1.quad_enu(mats["dark_steel"], (s0[0], s0[1], s0[2] + 1.08), (s1[0], s1[1], s1[2] + 1.08), (s1[0], s1[1], s1[2] + 1.15), (s0[0], s0[1], s0[2] + 1.15), (0.1, 0.1, 0.9, 0.9), 0.95, 1.0, double_sided=True)
            if k % 2 == 0:
                wr1.add_box(mats["crimson"], (s0[0] + s1[0]) * 0.5, (s0[1] + s1[1]) * 0.5, s0[2] + 0.22, 0.9, 0.25, 0.28, math.atan2(dy, dx))
        if k % 4 == 0:
            wr1.add_cylinder(mats["white_alu"], a0[0], a0[1], 0.0, 0.22, 0.20, max(0.1, a0[2] - 0.34), 8)
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
    # North-facing 1F Library Entrance Portal on bay bi=3 (clean non-overlapping steps, jambs, header & glass!)
    lib_cx = -32.275
    wb4.add_box(mats["gates"], lib_cx, 38.75, 0.0, 3.90, 1.10, 0.16, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wb4.add_box(mats["gates"], lib_cx, 39.55, 0.0, 4.10, 0.50, 0.08, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.94, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for lx_off in (-1.52, 1.52):
        wb4.add_box(mats["gates"], lib_cx + lx_off, 38.36, 0.16, 0.50, 0.40, 2.90, 0.0, UV_MARBLE, ao_bot=0.78, ao_top=0.96, add_bottom=False, add_top=False)
    wb4.add_box(mats["surf"], lib_cx, 38.36, 3.06, 3.54, 0.40, 1.12, 0.0, UV_STUCCO, ao_bot=0.84, ao_top=0.96)
    wb4.add_box(mats["dark_steel"], lib_cx, 38.28, 0.16, 2.54, 0.26, 2.90, 0.0, ao_bot=0.78, ao_top=0.94, add_bottom=False, add_top=False)
    wb4.quad_enu(mats["glass"], (lib_cx + 1.22, 38.44, 0.24), (lib_cx - 1.22, 38.44, 0.24), (lib_cx - 1.22, 38.44, 2.48), (lib_cx + 1.22, 38.44, 2.48), UV_GLASS_WINDOW, 0.90, 1.0)
    wb4.quad_enu(mats["glass"], (lib_cx + 1.22, 38.44, 2.56), (lib_cx - 1.22, 38.44, 2.56), (lib_cx - 1.22, 38.44, 3.00), (lib_cx + 1.22, 38.44, 3.00), UV_GLASS_WINDOW, 0.90, 1.0)
    for mx_off, mw, mz0, mz1 in [(-1.24, 0.08, 0.16, 2.48), (-1.24, 0.08, 2.56, 3.06), (0.0, 0.07, 0.16, 2.48), (0.0, 0.07, 2.56, 3.06), (1.24, 0.08, 0.16, 2.48), (1.24, 0.08, 2.56, 3.06), (-0.14, 0.04, 0.94, 1.46), (0.14, 0.04, 0.94, 1.46)]:
        wb4.add_box(mats["white_alu"], lib_cx + mx_off, 38.49, mz0, mw, 0.06, mz1 - mz0, 0.0, add_bottom=False, add_top=False)
    wb4.add_box(mats["white_alu"], lib_cx, 38.49, 2.48, 2.56, 0.06, 0.08, 0.0)
    # Library canopy + "图书馆 / LIBRARY" signboard facing North (+Y, 25mm proud of backing!)
    wb4.add_box(mats["white_alu"], lib_cx, 38.92, 3.12, 3.90, 1.48, 0.18, 0.0, ao_bot=0.86, ao_top=1.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for tie_x in (lib_cx - 1.65, lib_cx + 1.65):
        wb4.quad_enu(mats["dark_steel"], (tie_x, 38.42, 3.92), (tie_x, 39.48, 3.30), (tie_x, 39.48, 3.35), (tie_x, 38.42, 3.97), (0.1, 0.1, 0.9, 0.9), 0.90, 0.95, double_sided=True)
    wb4.add_box(mats["dark_steel"], lib_cx, 38.58, 3.36, 2.75, 0.08, 0.86, 0.0, ao_bot=0.84, ao_top=0.98)
    wb4.quad_enu(mats["stage"], (lib_cx + 1.33, 38.645, 3.40), (lib_cx - 1.33, 38.645, 3.40), (lib_cx - 1.33, 38.645, 4.18), (lib_cx + 1.33, 38.645, 4.18), UV_LIBRARY_SIGN, 0.96, 1.0)
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
    # East entry doorway, granite step & small dark-steel canopy facing main driveway (glass 25mm proud of frame!)
    wb4.add_box(mats["surf"], -5.41, 17.25, 0.0, 0.48, 1.50, 0.10, 0.0, UV_QINGZHUAN, ao_bot=0.78, ao_top=0.94)
    wb4.add_box(mats["dark_steel"], -5.54, 17.25, 0.10, 0.12, 1.32, 2.25, 0.0, ao_bot=0.78, ao_top=0.95, add_bottom=False)
    wb4.quad_enu(mats["glass"], (-5.455, 16.65, 0.16), (-5.455, 17.85, 0.16), (-5.455, 17.85, 2.25), (-5.455, 16.65, 2.25), UV_GLASS_WINDOW)
    wb4.add_box(mats["white_alu"], -5.42, 16.76, 0.96, 0.04, 0.04, 0.34, 0.0)
    wb4.add_box(mats["dark_steel"], -5.18, 17.25, 2.45, 0.90, 1.65, 0.14, 0.0, ao_bot=0.84, ao_top=1.0)

    # ---- W-ST1: 东北外挂折返楼梯塔 & "尚美" 艺术浮雕壁 (白色Z字实心斜向护墙 + 蓝灰防坠钢网, zero coplanar overlaps!) ----
    wst1 = exp.add_node("W-ST1")
    wst1.add_box(mats["surf"], -6.8, 80.5, 0.0, 5.4, 5.4, 1.05, 0.0, UV_QINGZHUAN, ao_bot=0.72, ao_top=0.92)
    for pi_st in ((-9.25, 78.05), (-4.35, 78.05), (-9.25, 82.95), (-4.35, 82.95)):
        wst1.add_box(mats["white_alu"], pi_st[0], pi_st[1], 1.05, 0.34, 0.34, 18.30, 0.0, add_bottom=False, add_top=False)
    for lvl in range(5):
        z0 = 1.05 + lvl * 3.55
        zm = z0 + 1.77
        zt = z0 + 3.55
        # Landing slabs cleanly inset between corner columns & horizontal parapets (zero column/parapet overlap)
        wst1.add_box(mats["white_alu"], -6.8, 79.1, z0 + 0.02, 4.54, 1.92, 0.24, 0.0)
        wst1.add_box(mats["white_alu"], -6.8, 81.9, zm, 4.54, 1.92, 0.24, 0.0)
        wst1.add_box(mats["surf"], -6.8, 77.96, z0 + 0.02, 4.54, 0.16, 1.06, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.99)
        wst1.add_box(mats["surf"], -6.8, 83.04, zm, 4.54, 0.16, 1.06, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.99)
        # Solid white sloped Z-shaped stair stringer balustrades (offset cleanly from columns & grille cage, capped <=19.35!)
        wst1.quad_enu(
            mats["surf"],
            (-9.46, 78.8, z0), (-9.46, 82.2, zm),
            (-9.46, 82.2, min(zm + 1.05, 19.35)), (-9.46, 78.8, min(z0 + 1.05, 19.35)),
            UV_STUCCO, 0.88, 0.99, double_sided=True,
        )
        wst1.quad_enu(
            mats["surf"],
            (-4.14, 82.2, zm), (-4.14, 78.8, zt),
            (-4.14, 78.8, min(zt + 1.05, 19.35)), (-4.14, 82.2, min(zm + 1.05, 19.35)),
            UV_STUCCO, 0.88, 0.99, double_sided=True,
        )
        wst1.quad_enu(
            mats["surf"],
            (-4.6, 83.16, zm), (-9.0, 83.16, z0 + 0.45),
            (-9.0, 83.16, min(z0 + 1.48, 19.35)), (-4.6, 83.16, min(zm + 1.05, 19.35)),
            UV_STUCCO, 0.88, 0.99, double_sided=True,
        )
        # Dense blue-grey vertical steel safety grille bars (outer cage at ±2.72m, 40mm clear of stringers & columns!)
        for bx_o in (-2.72, 2.72):
            for li in range(9):
                ly = 78.2 + li * 0.58
                wst1.add_box(mats["blue_steel"], -6.8 + bx_o, ly, z0 + 0.04, 0.04, 0.045, 3.48, 0.0)
        for by_o in (-2.72, 2.72):
            for li in range(9):
                lx = -9.12 + li * 0.58
                wst1.add_box(mats["blue_steel"], lx, 80.5 + by_o, z0 + 0.04, 0.045, 0.04, 3.48, 0.0)
    wst1.add_box(mats["white_alu"], -6.8, 80.5, 19.35, 5.60, 5.60, 0.30, 0.0)
    # Twin spotlight post in front of W-ST1 north plinth (west-stairway-2024.webp)
    wst1.add_cylinder(mats["blue_steel"], -7.8, 83.68, 0.0, 0.07, 0.06, 2.75, 8)
    wst1.add_box(mats["white_alu"], -7.8, 83.68, 2.75, 0.68, 0.16, 0.18, 0.0)

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
    # South-facing glazed duty/service window on west bay (25mm stepped separation)
    wst1.add_box(mats["dark_steel"], -3.70, 75.15, 1.15, 2.80, 0.10, 1.50, 0.0, ao_bot=0.78, ao_top=0.94)
    wst1.add_box(mats["surf"], -3.70, 75.12, 1.07, 2.96, 0.16, 0.08, 0.0, UV_PLAZA_TILE)
    wst1.quad_enu(
        mats["glass"],
        (-5.02, 75.075, 1.22), (-2.38, 75.075, 1.22),
        (-2.38, 75.075, 2.58), (-5.02, 75.075, 2.58),
        UV_GLASS_WINDOW, 0.88, 0.98,
    )
    wst1.add_box(mats["white_alu"], -3.70, 75.04, 1.20, 0.06, 0.04, 1.40, 0.0)
    # North-facing "尚美 · 美育浮雕" bronze relief on west bay north wall (30mm proud of steel backing!)
    wst1.add_box(mats["dark_steel"], -2.275, 83.44, 0.46, 3.35, 0.08, 2.58, 0.0)
    wst1.quad_enu(
        mats["stage"],
        (-0.65, 83.51, 0.52), (-3.90, 83.51, 0.52),
        (-3.90, 83.51, 2.98), (-0.65, 83.51, 2.98),
        UV_RELIEF_WALL, 0.92, 1.0,
    )
    # East Qingzhuan structural pier & hollow 1F bike tunnel (clean butt joints, zero overlap!)
    wst1.add_box(mats["surf"], 3.65, 79.30, 0.0, 0.60, 8.20, 3.44, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.94, add_top=False)
    wst1.add_box(mats["surf"], 1.45, 79.30, 3.02, 3.80, 8.20, 0.42, 0.0, UV_QINGZHUAN, ao_bot=0.84, ao_top=0.95, add_top=False, add_bottom=False)
    # Bright white ceiling soffit, light stucco upper tunnel walls & warm ceiling dome lights inside 1F passage
    wst1.add_box(mats["surf"], -0.415, 79.30, 1.05, 0.06, 8.04, 1.92, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.96, add_top=False)
    wst1.add_box(mats["surf"], 3.315, 79.30, 1.05, 0.06, 8.04, 1.92, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=0.96, add_top=False)
    wst1.add_box(mats["white_alu"], 1.45, 79.30, 2.97, 3.66, 8.04, 0.05, 0.0, ao_bot=0.92, ao_top=0.98, add_top=False)
    for cly in (77.3, 81.3):
        wst1.add_cylinder(mats["floodlight"], 1.45, cly, 2.92, 0.24, 0.24, 0.05, 12, ao_bot=0.98, ao_top=1.0)
    # Crisp white portal jambs & lintel frames on South (y=75.12) & North (y=83.48) exits (jambs stop at z=2.97 under lintel!)
    for py_port in (75.12, 83.48):
        wst1.add_box(mats["white_alu"], -0.52, py_port, 0.05, 0.16, 0.14, 2.92, 0.0, ao_bot=0.82, ao_top=0.98, add_bottom=False, add_top=False)
        wst1.add_box(mats["white_alu"], 3.42, py_port, 0.05, 0.16, 0.14, 2.92, 0.0, ao_bot=0.82, ao_top=0.98, add_bottom=False, add_top=False)
        wst1.add_box(mats["white_alu"], 1.45, py_port, 2.97, 4.10, 0.16, 0.16, 0.0, ao_bot=0.88, ao_top=1.0)
    # Continuous 1-story flat roof & overhanging white moulded cornice (z = 3.44..3.66m; NO duplicate 3.664m patch!)
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

    # ---- W-MC: 音乐长廊（始于音乐长廊牌楼 y≈81.5，沿 C 座西侧向南延伸；操场西侧不设棚廊） ----
    wmc = exp.add_node("W-MC")
    # Archway / glazed entrance portal at south edge of track southwest plaza (y=76.25..81.45)
    portal_bays = [
        (81.45, -93.50, -89.15),
        (78.85, -93.42, -89.55),
        (76.25, -93.35, -89.95),
    ]
    for py, xw, xe in portal_bays:
        wmc.add_box(mats["dark_steel"], xw, py, 0.0, 0.24, 0.24, 4.55, 0.0, add_top=False)
        wmc.add_box(mats["dark_steel"], xe, py, 0.0, 0.24, 0.24, 4.55, 0.0, add_top=False)
        wmc.add_box(mats["dark_steel"], (xw + xe) * 0.5, py, 4.55, (xe - xw) + 0.36, 0.22, 0.22, 0.0)
    # Longitudinal eave beams connecting portal bays (cleanly beneath crossbeams at z=4.33..4.55)
    wmc.add_box(mats["dark_steel"], -93.42, 78.85, 4.33, 0.20, 5.20, 0.22, -math.atan2(-0.15, 5.20), add_top=False)
    wmc.add_box(mats["dark_steel"], -89.55, 78.85, 4.33, 0.20, 5.20, 0.22, -math.atan2(0.80, 5.20), add_top=False)
    # Skylight glazing 30mm proud of steel crossbeams (top=4.77 -> glass=4.80; single-sided via doubleSided mat)
    wmc.quad_enu(
        mats["skylight"],
        (-93.45, 76.25, 4.80),
        (-89.88, 76.25, 4.80),
        (-89.08, 81.45, 4.80),
        (-93.58, 81.45, 4.80),
        UV_SKYLIGHT, 0.96, 1.0,
    )
    # North & South header boards ("音乐长廊 / MUSIC CORRIDOR") on the archway
    wmc.quad_enu(mats["stage"], (-89.15, 81.60, 3.85), (-93.50, 81.60, 3.85), (-93.50, 81.60, 4.92), (-89.15, 81.60, 4.92), UV_MUSIC_SIGN, 0.95, 1.0)
    wmc.quad_enu(mats["stage"], (-93.35, 76.10, 3.85), (-89.95, 76.10, 3.85), (-89.95, 76.10, 4.92), (-93.35, 76.10, 4.92), UV_MUSIC_SIGN, 0.95, 1.0)
    # Covered corridor extending south from archway along C-Wing west side (y=54.0..76.25)
    for pi in range(6):
        t = pi / 5.0
        py = 76.25 - t * 22.25
        xw = -93.35 + t * 1.95   # -93.35 -> -91.40 (inside campus west boundary)
        xe = -89.95 + t * 1.75   # -89.95 -> -88.20 (clear west of C-Wing west facade)
        if pi > 0:
            wmc.add_box(mats["dark_steel"], xw, py, 0.0, 0.20, 0.20, 3.94, 0.0, add_top=False)
            wmc.add_box(mats["dark_steel"], xe, py, 0.0, 0.20, 0.20, 3.94, 0.0, add_top=False)
        wmc.add_box(mats["dark_steel"], (xw + xe) * 0.5, py, 3.94, (xe - xw) + 0.28, 0.18, 0.20, 0.0)
    wmc.add_box(mats["dark_steel"], -92.375, 65.125, 3.76, 0.16, 22.10, 0.18, -math.atan2(-1.95, 22.25), add_top=False)
    wmc.add_box(mats["dark_steel"], -89.075, 65.125, 3.76, 0.16, 22.10, 0.18, -math.atan2(-1.75, 22.25), add_top=False)
    wmc.quad_enu(
        mats["skylight"],
        (-91.50, 54.00, 4.17),
        (-88.12, 54.00, 4.17),
        (-89.88, 76.25, 4.17),
        (-93.45, 76.25, 4.17),
        UV_SKYLIGHT, 0.94, 1.0,
    )

    # ---- W-L2: 百草园内庭绿地（含中式方亭、月季花境与青松/银杏/柿树/玉兰） ----
    wl2 = exp.add_node("W-L2")
    wl2.add_polygon_patch([(-67.2, 39.0), (-45.5, 39.0), (-45.5, 57.2), (-67.2, 57.2)], 0.04, mats["surf"], UV_GRASS, ao=0.94)
    # Stone garden cross paths (strictly non-overlapping: E-W full + N-S split south & north of E-W path, 25mm above grass!)
    wl2.add_polygon_patch([(-66.5, 47.0), (-46.2, 47.0), (-46.2, 49.0), (-66.5, 49.0)], 0.065, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    wl2.add_polygon_patch([(-57.4, 39.5), (-55.4, 39.5), (-55.4, 47.0), (-57.4, 47.0)], 0.065, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    wl2.add_polygon_patch([(-57.4, 49.0), (-55.4, 49.0), (-55.4, 56.8), (-57.4, 56.8)], 0.065, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    wl2.add_cylinder(mats["surf"], -56.4, 48.0, 0.065, 2.2, 2.2, 0.22, 12, UV_QINGZHUAN, ao_bot=0.80, ao_top=0.95)
    # Small Chinese pavilion (亭子) in the south-east quadrant of the garden (clean non-overlapping beams!)
    pv_x, pv_y = -52.4, 43.2
    wl2.add_box(mats["surf"], pv_x, pv_y, 0.12, 4.60, 4.60, 0.18, 0.0, UV_QINGZHUAN, ao_bot=0.78, ao_top=0.96, add_bottom=False)
    for px, py in ((pv_x - 1.50, pv_y - 1.50), (pv_x + 1.50, pv_y - 1.50),
                   (pv_x - 1.50, pv_y + 1.50), (pv_x + 1.50, pv_y + 1.50)):
        wl2.add_cylinder(mats["pavilion_wood"], px, py, 0.30, 0.135, 0.120, 2.75, 8, ao_bot=0.78, ao_top=0.98)
    for bx, by, bw, bd in ((pv_x, pv_y - 1.50, 3.30, 0.18), (pv_x, pv_y + 1.50, 3.30, 0.18),
                           (pv_x - 1.50, pv_y, 0.18, 2.82), (pv_x + 1.50, pv_y, 0.18, 2.82)):
        wl2.add_box(mats["pavilion_wood"], bx, by, 3.05, bw, bd, 0.20, 0.0, ao_bot=0.84, ao_top=1.0)
    # Hipped roof: four triangular slopes + ridge cap + finial
    eave_z, apex_z = 3.25, 4.55
    e = 2.35
    corners = [(pv_x - e, pv_y - e), (pv_x + e, pv_y - e), (pv_x + e, pv_y + e), (pv_x - e, pv_y + e)]
    for k in range(4):
        a = corners[k]
        b = corners[(k + 1) % 4]
        tu0, tv0, tu1, tv1 = UV_GREY_TILE
        wl2.tri_enu(
            mats["surf"],
            (a[0], a[1], eave_z), (b[0], b[1], eave_z), (pv_x, pv_y, apex_z),
            (tu0, tv0), (tu1, tv0), ((tu0 + tu1) * 0.5, tv1),
            0.92, 0.92, 1.0, double_sided=True,
        )
    wl2.add_box(mats["surf"], pv_x, pv_y, apex_z - 0.06, 0.55, 0.55, 0.16, 0.0, UV_GREY_TILE, ao_bot=0.92, ao_top=1.0)
    wl2.add_cylinder(mats["gold_trim"], pv_x, pv_y, apex_z + 0.10, 0.07, 0.02, 0.55, 8, ao_bot=0.95, ao_top=1.0)
    # Rose beds flanking the east-west garden path (月季)
    for rx, ry, rw, rd in ((-63.6, 47.7, 3.6, 0.75), (-49.2, 47.7, 3.6, 0.75)):
        wl2.add_box(mats["surf"], rx, ry, 0.06, rw, rd, 0.34, 0.0, UV_QINGZHUAN, ao_bot=0.80, ao_top=0.96)
        for ri in range(6):
            wl2.add_tree(rx - rw * 0.38 + ri * rw * 0.152, ry, "rose", 0.95, mats["trunk"], mats["leaf"], mats["flower_rose"])
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

    # Full rectangular EPDM playground base (Layer 0.055m — 30mm above adjacent stone plazas!)
    wp1.add_polygon_patch(
        [
            (-93.75, 90.40),
            (-13.50, 90.40),
            (-13.50, 120.30),
            (-9.20, 120.30),
            (-9.20, 124.80),
            (-93.75, 124.80),
        ],
        0.055, mats["surf"], UV_TRACK_EPDM, ao=0.98,
    )
    # Smooth harder acrylic/silicon-PU oval infield apron (Layer 0.075m — 20mm above EPDM base)
    wp1.add_polygon_patch(rounded_rect_pts(-88.08, 94.82, -18.52, 120.38, 12.78, n_arc=16), 0.075, mats["hard_court"], UV_HARD_COURT_APRON, ao=0.99)
    # Inner slotted concrete drainage curb ring (Layer 0.095m — 20mm above infield, continuous mitered strip!)
    drain_pts = rounded_rect_pts(-88.20, 94.70, -18.40, 120.50, 12.90, n_arc=16)
    wp1.add_mitered_ring(drain_pts, 0.12, 0.095, mats["surf"], UV_PLAZA_TILE, ao_in=0.94, ao_out=0.88, closed=True)
    # 5 white oval lane boundary rings (Layer 0.115m — 20mm above drainage ring, continuous mitered strips!)
    for lane_r in (12.90, 13.925, 14.95, 15.975, 17.00):
        inset = 17.00 - lane_r
        lane_pts = rounded_rect_pts(-92.30 + inset, 90.60 + inset, -14.30 - inset, 124.60 - inset, lane_r, n_arc=16)
        wp1.add_mitered_ring(lane_pts, 0.05, 0.115, mats["white_alu"], (0.0, 0.0, 1.0, 1.0), ao_in=1.0, ao_out=1.0, closed=True)
    # NE 50m sprint straightaway lane stripes (Layer 0.135m — 20mm clear where sprint lanes cross outer oval curves!)
    for ly in (120.50, 121.525, 122.55, 123.575, 124.60):
        wp1.quad_enu(mats["white_alu"], (-31.28, ly - 0.05, 0.135), (-9.50, ly - 0.05, 0.135), (-9.50, ly + 0.05, 0.135), (-31.28, ly + 0.05, 0.135))
    # Start & Finish cross lines (Layer 0.155m — 20mm above sprint & oval lane lines so crossings never coplanar!)
    wp1.quad_enu(mats["white_alu"], (-9.86, 120.48, 0.155), (-9.74, 120.48, 0.155), (-9.74, 124.62, 0.155), (-9.86, 124.62, 0.155))
    wp1.quad_enu(mats["white_alu"], (-59.86, 120.48, 0.155), (-59.74, 120.48, 0.155), (-59.74, 124.62, 0.155), (-59.86, 124.62, 0.155))
    # Painted white track lane numbers "1" "2" "3" "4" (Layer 0.115m, cleanly centered inside lanes!)
    for idx_ln, lane_mid_y in enumerate((121.01, 122.04, 123.06, 124.09)):
        uv_ln = UV_LANE_NUMS[idx_ln]
        for nx_pos in (-72.0, -10.8):
            wp1.quad_enu(
                mats["details_alpha"],
                (nx_pos + 0.48, lane_mid_y - 0.32, 0.115),
                (nx_pos + 0.48, lane_mid_y + 0.32, 0.115),
                (nx_pos - 0.48, lane_mid_y + 0.32, 0.115),
                (nx_pos - 0.48, lane_mid_y - 0.32, 0.115),
                uv_ln, 0.98, 1.0,
            )

    # 3 green/red basketball courts & 6 hoops (cleanly stratified: Green 0.095m -> Red keys 0.115m -> White lines 0.135m!)
    court_xs = [(-74.8, -61.8), (-59.8, -46.8), (-44.8, -31.8)]
    for cx0, cx1 in court_xs:
        cy0, cy1 = 96.1, 119.1
        cmid_x = (cx0 + cx1) * 0.5
        cmid_y = (cy0 + cy1) * 0.5
        # Green court surface pad (Layer 0.095m — 20mm above 0.075m infield!)
        wp1.add_polygon_patch([(cx0 - 0.5, cy0 - 0.45), (cx1 + 0.5, cy0 - 0.45), (cx1 + 0.5, cy1 + 0.45), (cx0 - 0.5, cy1 + 0.45)], 0.095, mats["surf"], UV_COURT_GREEN, ao=1.0)
        # Hard-court terracotta-painted 3-second keys & center jump circle (Layer 0.115m — 20mm above green court!)
        kw, kd = 2.40, 5.50
        wp1.add_polygon_patch([(cmid_x - kw, cy0), (cmid_x + kw, cy0), (cmid_x + kw, cy0 + kd), (cmid_x - kw, cy0 + kd)], 0.115, mats["hard_court"], UV_HARD_COURT_APRON, ao=0.99)
        wp1.add_polygon_patch([(cmid_x - kw, cy1 - kd), (cmid_x + kw, cy1 - kd), (cmid_x + kw, cy1), (cmid_x - kw, cy1)], 0.115, mats["hard_court"], UV_HARD_COURT_APRON, ao=0.99)
        c_jump_pts = [(cmid_x + 1.8 * math.cos(2 * math.pi * k / 16), cmid_y + 1.8 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
        wp1.add_polygon_patch(c_jump_pts, 0.115, mats["hard_court"], UV_HARD_COURT_APRON, ao=0.99)
        # Crisp white boundary, center, key lines (Layer 0.135m — 20mm above keys, strictly trimmed at all corners/T-junctions!)
        for x0, y0, x1, y1 in [
            (cx0, cy0, cx1, cy0 + 0.11),
            (cx0, cy1 - 0.11, cx1, cy1),
            (cx0, cy0 + 0.11, cx0 + 0.11, cy1 - 0.11),
            (cx1 - 0.11, cy0 + 0.11, cx1, cy1 - 0.11),
            # Center line split around center jump circle (r=1.80) so zero overlap with circle ring!
            (cx0 + 0.11, cmid_y - 0.055, cmid_x - 1.85, cmid_y + 0.055),
            (cmid_x + 1.85, cmid_y - 0.055, cx1 - 0.11, cmid_y + 0.055),
            (cmid_x - 1.75, cmid_y - 0.055, cmid_x + 1.75, cmid_y + 0.055),
            # South & North key boxes (side legs trimmed cleanly between baseline & free-throw line)
            (cmid_x - kw, cy0 + 0.11, cmid_x - kw + 0.10, cy0 + kd - 0.10),
            (cmid_x + kw - 0.10, cy0 + 0.11, cmid_x + kw, cy0 + kd - 0.10),
            (cmid_x - kw, cy0 + kd - 0.10, cmid_x + kw, cy0 + kd),
            (cmid_x - kw, cy1 - kd + 0.10, cmid_x - kw + 0.10, cy1 - 0.11),
            (cmid_x + kw - 0.10, cy1 - kd + 0.10, cmid_x + kw, cy1 - 0.11),
            (cmid_x - kw, cy1 - kd, cmid_x + kw, cy1 - kd + 0.10),
        ]:
            wp1.quad_enu(mats["white_alu"], (x0, y0, 0.135), (x1, y0, 0.135), (x1, y1, 0.135), (x0, y1, 0.135))
        # Center circle & 3-point arcs as seamless mitered strips (zero vertex overlap!)
        c_ring_pts = [(cmid_x + 1.8 * math.cos(2 * math.pi * k / 16), cmid_y + 1.8 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
        wp1.add_mitered_ring(c_ring_pts, 0.045, 0.135, mats["white_alu"], closed=True)
        for end_y, dir_s in ((cy0 + 1.50, 1.0), (cy1 - 1.50, -1.0)):
            arc_pts = [
                (cmid_x + 6.00 * math.cos(0.20 + (math.pi - 0.40) * (k / 12)),
                 end_y + dir_s * 6.00 * math.sin(0.20 + (math.pi - 0.40) * (k / 12)))
                for k in range(13)
            ]
            if dir_s < 0:
                arc_pts.reverse()
            wp1.add_mitered_ring(arc_pts, 0.045, 0.135, mats["white_alu"], closed=False)
        add_basketball_hoop_west(wp1, cmid_x, cy0 - 0.72, 0.0, mats)
        add_basketball_hoop_west(wp1, cmid_x, cy1 + 0.72, math.pi, mats)

    # Two North-South green volleyball courts tucked inside West & East semicircular infield arcs (zero overlapping lines!)
    for vx0, vx1 in ((-83.55, -76.15), (-30.45, -23.05)):
        vy0, vy1 = 100.20, 115.00
        vy_mid = (vy0 + vy1) * 0.5  # 107.60 (playground N-S midline)
        atk_off = 2.47  # proportional 3m attack line offset (7.4m x 14.8m court)
        # Green court surface pad (Layer 0.095m — 20mm above 0.075m infield, matching basketball courts!)
        wp1.add_polygon_patch(
            [(vx0 - 0.35, vy0 - 0.35), (vx1 + 0.35, vy0 - 0.35), (vx1 + 0.35, vy1 + 0.35), (vx0 - 0.35, vy1 + 0.35)],
            0.095, mats["surf"], UV_COURT_GREEN, ao=1.0,
        )
        # Crisp white volleyball outer boundary, center line & attack lines (Layer 0.135m — strictly trimmed at corners/T-junctions!)
        for x0, y0, x1, y1 in [
            (vx0, vy0, vx1, vy0 + 0.09),
            (vx0, vy1 - 0.09, vx1, vy1),
            (vx0, vy0 + 0.09, vx0 + 0.09, vy1 - 0.09),
            (vx1 - 0.09, vy0 + 0.09, vx1, vy1 - 0.09),
            (vx0 + 0.09, vy_mid - 0.045, vx1 - 0.09, vy_mid + 0.045),
            (vx0 + 0.09, vy_mid - atk_off - 0.04, vx1 - 0.09, vy_mid - atk_off + 0.04),
            (vx0 + 0.09, vy_mid + atk_off - 0.04, vx1 - 0.09, vy_mid + atk_off + 0.04),
        ]:
            wp1.quad_enu(mats["white_alu"], (x0, y0, 0.135), (x1, y0, 0.135), (x1, y1, 0.135), (x0, y1, 0.135))
        # Volleyball net on orange-red poles across each volleyball court's N-S midline (single-sided via doubleSided mat)
        px_w, px_e = vx0 - 0.35, vx1 + 0.35
        for px_v in (px_w, px_e):
            wp1.add_cylinder(mats["orange_hoop"], px_v, vy_mid, 0.095, 0.055, 0.05, 2.435, 8)
        wp1.quad_enu(
            mats["details_alpha"],
            (px_w + 0.05, vy_mid, 1.42), (px_e - 0.05, vy_mid, 1.42),
            (px_e - 0.05, vy_mid, 2.43), (px_w + 0.05, vy_mid, 2.43),
            UV_VOLLEY_NET, 0.96, 1.0,
        )

    # Back-to-back connected twin hoops on N-S midline (y=107.60), facing North & South on BOTH West & East sides
    add_double_basketball_hoop_west(wp1, -86.05, 107.60, 0.0, mats)
    add_double_basketball_hoop_west(wp1, -20.55, 107.60, 0.0, mats)

    # Two diagonal practice hoops on West side INSIDE the running track (NW facing SE, SW facing NE; East side has none)
    add_basketball_hoop_west(wp1, -82.27, 117.55, -3.0 * math.pi / 4.0, mats)
    add_basketball_hoop_west(wp1, -82.27, 97.65, -math.pi / 4.0, mats)

    # Signature leaning deciduous tree + square curb cutout + metal ladder along inner edge of North track (Photo 1!)
    lt_x, lt_y = -22.0, 120.25
    wp1.add_box(mats["surf"], lt_x, lt_y, 0.06, 1.25, 1.15, 0.12, 0.0, UV_PLAZA_TILE, ao_bot=0.78, ao_top=0.95, add_bottom=False)
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
    # Stainless steel deck guardrails & sloped stair handrails ONLY on West & East sides (clean non-overlapping butt joints!)
    for side_sign, x_rail, x_bot in ((-1.0, -54.92, -56.60), (1.0, -33.08, -31.40)):
        for y0_r, y1_r in ((125.58, 127.30), (130.10, 131.42)):
            wp2.add_box(mats["white_alu"], x_rail, (y0_r + y1_r) * 0.5, 1.75, 0.05, y1_r - y0_r, 0.05, 0.0)
            for ry_post in (y0_r + 0.025, (y0_r + y1_r) * 0.5, y1_r - 0.025):
                wp2.add_box(mats["white_alu"], x_rail, ry_post, 0.85, 0.05, 0.05, 0.90, 0.0, add_bottom=False, add_top=False)
            half_seg = (y1_r - y0_r - 0.15) * 0.5
            wp2.add_box(mats["white_alu"], x_rail, y0_r + 0.05 + half_seg * 0.5, 1.32, 0.04, half_seg, 0.04, 0.0)
            wp2.add_box(mats["white_alu"], x_rail, y1_r - 0.05 - half_seg * 0.5, 1.32, 0.04, half_seg, 0.04, 0.0)
        for hy in (127.30, 130.10):
            wp2.add_box(mats["white_alu"], x_bot, hy, 0.22, 0.05, 0.05, 0.74, 0.0, add_bottom=False)
            xr_in = x_rail + side_sign * 0.03
            xb_in = x_bot - side_sign * 0.03
            wp2.quad_enu(
                mats["white_alu"],
                (xr_in, hy, 1.74), (xb_in, hy, 0.96),
                (xb_in, hy, 1.01), (xr_in, hy, 1.79),
                (0.1, 0.1, 0.9, 0.9), 0.94, 1.0, double_sided=True,
            )
            wp2.quad_enu(
                mats["white_alu"],
                (xr_in, hy, 1.32), (xb_in, hy, 0.58),
                (xb_in, hy, 0.62), (xr_in, hy, 1.36),
                (0.1, 0.1, 0.9, 0.9), 0.92, 1.0, double_sided=True,
            )
    # Unified beige stone backdrop wall with cornice cap, flush motto pilasters & crimson-framed LED (30mm stepped clearance!)
    wp2.add_box(
        mats["gates"], st_cx, 130.765, 0.85, 13.6, 0.83, 4.90, 0.0,
        UV_MARBLE, ao_bot=0.78, ao_top=0.96, add_bottom=False, add_top=False,
    )
    wp2.add_box(
        mats["gates"], st_cx, 130.755, 5.75, 14.0, 1.02, 0.22, 0.0,
        UV_MARBLE, ao_bot=0.84, ao_top=0.98,
        top_mat=mats["surf"], top_uv=UV_PLAZA_TILE,
    )
    wp2.add_box(mats["gates"], st_cx - 5.65, 130.31, 1.15, 1.65, 0.08, 4.30, 0.0, UV_MARBLE, ao_bot=0.82, ao_top=0.96)
    wp2.quad_enu(mats["stage"], (st_cx - 6.45, 130.24, 1.15), (st_cx - 4.85, 130.24, 1.15), (st_cx - 4.85, 130.24, 5.45), (st_cx - 6.45, 130.24, 5.45), UV_PILLAR_LEFT, 0.94, 1.0)
    wp2.add_box(mats["gates"], st_cx + 5.65, 130.31, 1.15, 1.65, 0.08, 4.30, 0.0, UV_MARBLE, ao_bot=0.82, ao_top=0.96)
    wp2.quad_enu(mats["stage"], (st_cx + 4.85, 130.24, 1.15), (st_cx + 6.45, 130.24, 1.15), (st_cx + 6.45, 130.24, 5.45), (st_cx + 4.85, 130.24, 5.45), UV_PILLAR_RIGHT, 0.94, 1.0)
    wp2.add_box(mats["gates"], st_cx, 130.29, 1.38, 8.70, 0.12, 3.94, 0.0, UV_BURGUNDY, ao_bot=0.82, ao_top=0.98)
    wp2.add_box(mats["dark_steel"], st_cx, 130.21, 1.52, 8.36, 0.08, 3.66, 0.0)
    wp2.quad_enu(mats["stage_led"], (st_cx - 4.10, 130.14, 1.58), (st_cx + 4.10, 130.14, 1.58), (st_cx + 4.10, 130.14, 5.12), (st_cx - 4.10, 130.14, 5.12), UV_STAGE_LED, 1.0, 1.0)
    # Ground-stacked 2-tier PA speakers below stage on West & East sides (south of side stairs y=127.3..130.1, north of track y=124.8)
    add_pa_speaker_stack(wp2, -55.90, 126.05, 0.08, mats, z_base=0.025)
    add_pa_speaker_stack(wp2, -32.10, 126.05, -0.08, mats, z_base=0.025)
    # Twin tall deciduous trees flanking East end of Chairman Stage (clear of East stairs & ground PA speaker)
    wp2.add_tree(-30.5, 127.8, "broad", 11.2, mats["trunk"], mats["leaf"])
    wp2.add_tree(-26.9, 126.8, "broad", 9.6, mats["trunk"], mats["leaf"])
    # 4 Rear structural steel masts + cantilevered N-S valley ribs & diagonal braces (NO front ground columns)
    mast_xs = [-54.4, -47.47, -40.53, -33.6]
    for mx in mast_xs:
        wp2.add_cylinder(mats["dark_steel"], mx, 131.38, 0.0, 0.19, 0.17, 5.84, 10, ao_bot=0.74, ao_top=0.96)
        # Sloped cantilevered steel valley beam (z=5.82..5.98 rear -> z=6.08..6.24 front, cleanly below membrane!)
        wp2.quad_enu(mats["dark_steel"], (mx - 0.09, 131.65, 5.82), (mx + 0.09, 131.65, 5.82), (mx + 0.09, 124.75, 6.08), (mx - 0.09, 124.75, 6.08), (0.1, 0.1, 0.9, 0.9), 0.84, 0.94, double_sided=True)
        wp2.quad_enu(mats["dark_steel"], (mx - 0.09, 131.65, 5.98), (mx + 0.09, 131.65, 5.98), (mx + 0.09, 124.75, 6.24), (mx - 0.09, 124.75, 6.24), (0.1, 0.1, 0.9, 0.9), 0.90, 0.98, double_sided=True)
        wp2.quad_enu(mats["dark_steel"], (mx - 0.09, 131.65, 5.82), (mx - 0.09, 124.75, 6.08), (mx - 0.09, 124.75, 6.24), (mx - 0.09, 131.65, 5.98), (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True)
        wp2.quad_enu(mats["dark_steel"], (mx + 0.09, 124.75, 6.08), (mx + 0.09, 131.65, 5.82), (mx + 0.09, 131.65, 5.98), (mx + 0.09, 124.75, 6.24), (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True)
        wp2.quad_enu(mats["dark_steel"], (mx, 131.38, 3.85), (mx, 128.25, 5.94), (mx, 128.25, 6.06), (mx, 131.38, 3.98), (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True)
    # 3 Scalloped E-W barrel arches of white tensile membrane (single-sided via doubleSided mat!) + curved black space-truss chords
    y_rear, y_front = 131.65, 124.75

    def stage_arch_z(t: float, y: float) -> float:
        z_v = 6.04 + 0.26 * ((y_rear - y) / (y_rear - y_front))
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
            wp2.quad_enu(mats["tensile"], (x0, y_front, z0f), (x1, y_front, z1f), (x1, y_rear, z1r), (x0, y_rear, z0r), (0.0, 0.0, 1.0, 1.0), 0.94, 1.0)
            for y_tr in (124.82, 128.22):
                zt0 = stage_arch_z(t0, y_tr) - 0.10
                zt1 = stage_arch_z(t1, y_tr) - 0.10
                zb0 = zt0 - 0.30 * math.sin(math.pi * t0) - 0.08
                zb1 = zt1 - 0.30 * math.sin(math.pi * t1) - 0.08
                # Upper & lower curved truss chords (cleanly separated from web planes!)
                wp2.quad_enu(mats["dark_steel"], (x0, y_tr - 0.05, zt0), (x1, y_tr - 0.05, zt1), (x1, y_tr - 0.05, zt1 + 0.05), (x0, y_tr - 0.05, zt0 + 0.05), (0.1, 0.1, 0.9, 0.9), 0.88, 0.98, double_sided=True)
                wp2.quad_enu(mats["dark_steel"], (x0, y_tr - 0.05, zb0), (x1, y_tr - 0.05, zb1), (x1, y_tr - 0.05, zb1 + 0.05), (x0, y_tr - 0.05, zb0 + 0.05), (0.1, 0.1, 0.9, 0.9), 0.84, 0.95, double_sided=True)
                wp2.quad_enu(mats["dark_steel"], (x0, y_tr - 0.05, zt0), (x1, y_tr - 0.05, zt1), (x1, y_tr + 0.05, zt1), (x0, y_tr + 0.05, zt0), (0.1, 0.1, 0.9, 0.9), 0.88, 0.98, double_sided=True)
                wp2.quad_enu(mats["dark_steel"], (x0, y_tr - 0.05, zb0), (x1, y_tr - 0.05, zb1), (x1, y_tr + 0.05, zb1), (x0, y_tr + 0.05, zb0), (0.1, 0.1, 0.9, 0.9), 0.84, 0.95, double_sided=True)
                # Vertical + diagonal truss web bars offset to y_tr (50mm clear of front chord face) & y_tr + 0.03 (30mm clear of verticals)
                if ai > 0:
                    wp2.quad_enu(mats["dark_steel"], (x0 - 0.025, y_tr, zb0 + 0.05), (x0 + 0.025, y_tr, zb0 + 0.05), (x0 + 0.025, y_tr, zt0), (x0 - 0.025, y_tr, zt0), (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True)
                dx_d, dz_d = (x1 - 0.02) - (x0 + 0.03), zt1 - (zb0 + 0.05)
                ld_d = max(math.hypot(dx_d, dz_d), 1e-4)
                px_d, pz_d = (-dz_d / ld_d) * 0.018, (dx_d / ld_d) * 0.018
                wp2.quad_enu(
                    mats["dark_steel"],
                    (x0 + 0.03 - px_d, y_tr + 0.03, zb0 + 0.05 - pz_d),
                    (x1 - 0.02 - px_d, y_tr + 0.03, zt1 - pz_d),
                    (x1 - 0.02 + px_d, y_tr + 0.03, zt1 + pz_d),
                    (x0 + 0.03 + px_d, y_tr + 0.03, zb0 + 0.05 + pz_d),
                    (0.1, 0.1, 0.9, 0.9), 0.86, 0.96, double_sided=True,
                )
    # Flagpole & Red Flag on LEFT (West) side of stage when viewed from playground (clean butt-joint railings!)
    fx, fy = -58.8, 126.4
    wp2.add_box(mats["details"], fx, fy, 0.0, 2.2, 2.2, 0.48, 0.0, UV_DARK_SLATE_PODIUM, ao_bot=0.76, ao_top=0.96, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    for px_off in (-1.0, 1.0):
        for py_off in (-1.0, 1.0):
            wp2.add_box(mats["white_alu"], fx + px_off, fy + py_off, 0.48, 0.05, 0.05, 0.55, 0.0, add_bottom=False, add_top=False)
    wp2.add_box(mats["white_alu"], fx, fy - 1.0, 1.03, 2.05, 0.05, 0.04, 0.0)
    wp2.add_box(mats["white_alu"], fx, fy + 1.0, 1.03, 2.05, 0.05, 0.04, 0.0)
    wp2.add_box(mats["white_alu"], fx - 1.0, fy, 1.03, 0.05, 1.95, 0.04, 0.0)
    wp2.add_box(mats["white_alu"], fx + 1.0, fy, 1.03, 0.05, 1.95, 0.04, 0.0)
    wp2.add_cylinder(mats["white_alu"], fx, fy, 0.48, 0.10, 0.045, 14.5, 10)
    wp2.add_cylinder(mats["gold_trim"], fx, fy, 14.98, 0.11, 0.03, 0.16, 10)
    wp2.quad_enu(mats["gates"], (fx + 0.05, fy, 13.15), (fx + 2.45, fy - 0.22, 13.15), (fx + 2.45, fy - 0.22, 14.75), (fx + 0.05, fy, 14.75), UV_FLAG, 0.96, 1.0, double_sided=True)

    # ---- W-B5: 高二平房区（北界通长直线1层教学平房 + 南向连续悬挑檐廊） ----
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
        solid_x_planes=[-6.8],
    )
    # Continuous straight south cantilevered eave (cleanly clear of y=136.8 south wall & stacked cleanly beneath fascia!)
    wb5.add_box(mats["surf"], -39.66, 135.91, 3.25, 65.72, 1.62, 0.49, 0.0, UV_STUCCO, ao_bot=0.84, ao_top=0.98, add_top=False)
    wb5.add_box(mats["wall_grey_render"], -39.66, 135.81, 3.74, 65.84, 1.82, 0.16, 0.0, ao_bot=0.88, ao_top=1.0)
    # West veranda columns between W-H1 north portal & Chairman Stage (east ping-pong apron has cantilevered eave without columns per Photo 2)
    for col_i in range(5):
        vc_x = -72.52 + col_i * 3.85
        col_h = 2.68 if col_i == 0 else 3.25
        wb5.add_box(mats["surf"], vc_x, 135.28, 0.0, 0.34, 0.34, col_h, 0.0, UV_STUCCO, ao_bot=0.76, ao_top=0.94, add_top=False)
    # Warm round ceiling light under west veranda bay + flush red fire extinguisher cabinet (25mm proud front face!)
    wb5.add_cylinder(mats["floodlight"], -69.8, 135.95, 3.20, 0.22, 0.22, 0.05, 12, ao_bot=0.98, ao_top=1.0)
    wb5.add_box(mats["crimson"], -71.50, 136.60, 0.03, 0.72, 0.24, 0.62, 0.0, ao_bot=0.78, ao_top=0.96)
    wb5.quad_enu(
        mats["details"],
        (-71.84, 136.455, 0.05), (-71.16, 136.455, 0.05),
        (-71.16, 136.455, 0.63), (-71.84, 136.455, 0.63),
        UV_FIRE_BOX, 0.94, 1.0,
    )

    # ---- W-H1: 校史馆（D座 · 南向双层青砖方柱绿栏杆外廊 + 北侧半露天穿树门洞与通高玻璃门厅入口, zero coplanar overlaps!） ----
    wh1 = exp.add_node("W-H1")
    # 1. 3-tier stepped grey stone terrace plinth along NW track edge (no bottom caps on stacked tiers)
    for ti_p, (in_d, z_b, h_t) in enumerate([(0.0, 0.02, 0.14), (0.32, 0.16, 0.14), (0.64, 0.30, 0.14)]):
        wh1.add_box(
            mats["surf"], -81.0, 128.92 + in_d * 0.35, z_b,
            22.8 - in_d * 0.4, 8.78 - in_d * 0.7, h_t, 0.0,
            UV_PLAZA_TILE, ao_bot=0.74 + ti_p * 0.04, ao_top=0.94, add_bottom=False,
        )
    # 2. Main 2-story Qingzhuan building core (recessed south wall at y=126.38 so 1F & 2F both have open colonnade!)
    wh1_base_z = 0.44
    wh1_eave_z = 7.12
    wh1_mid_z = 3.78
    wh1.add_box(mats["surf"], -81.0, 129.79, wh1_base_z, 22.0, 6.82, wh1_eave_z - wh1_base_z, 0.0, UV_QINGZHUAN, ao_bot=0.75, ao_top=0.90, add_bottom=False)
    # Continuous white moulded inter-story cornice band wrapping N, S, E, W (clearly proud of core & slab!)
    wh1.add_box(mats["white_alu"], -81.0, 129.15, wh1_mid_z - 0.09, 22.24, 8.26, 0.18, 0.0, ao_bot=0.88, ao_top=1.0)
    # 2F colonnade floor slab (sits cleanly below cornice at z=3.54..3.69, inset from east/west ends!)
    wh1.add_box(mats["surf"], -81.0, 125.75, wh1_mid_z - 0.24, 21.84, 1.24, 0.15, 0.0, UV_PLAZA_TILE, ao_bot=0.80, ao_top=0.94, add_top=False)
    # Crimson painted wooden eave lintel beam (inset cleanly below eave roof & clear of end piers)
    wh1.add_box(mats["crimson"], -81.0, 125.24, wh1_eave_z - 0.32, 21.40, 0.32, 0.28, 0.0, ao_bot=0.82, ao_top=0.96)
    # 8 Square Qingzhuan colonnade piers (7 bays) with white stone capitals + 1F & 2F green vertical-bar railings
    n_col_bays = 7
    bay_span_h1 = 21.48 / n_col_bays
    for ci in range(n_col_bays + 1):
        px = -91.74 + ci * bay_span_h1
        wh1.add_box(mats["surf"], px, 125.24, wh1_base_z, 0.52, 0.52, wh1_eave_z - wh1_base_z - 0.02, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.94, add_bottom=False)
        # White moulded column capitals at 1F & 2F tops
        wh1.add_box(mats["white_alu"], px, 125.24, wh1_mid_z - 0.26, 0.64, 0.64, 0.14, 0.0)
        wh1.add_box(mats["white_alu"], px, 125.24, wh1_eave_z - 0.46, 0.64, 0.64, 0.14, 0.0)
        if ci < n_col_bays:
            bx0 = px + 0.26
            bx1 = px + bay_span_h1 - 0.26
            b_mid = (bx0 + bx1) * 0.5
            b_w = bx1 - bx0
            # Recessed inner south wall crimson-framed multi-pane windows & doors (25mm stepped clearance!)
            for st_z0, st_z1 in ((wh1_base_z + 0.72, wh1_mid_z - 0.45), (wh1_mid_z + 0.75, wh1_eave_z - 0.55)):
                wh1.add_box(mats["crimson"], b_mid, 126.33, st_z0, b_w * 0.72, 0.10, st_z1 - st_z0, 0.0)
                wh1.quad_enu(
                    mats["glass"],
                    (b_mid - b_w * 0.33, 126.255, st_z0 + 0.08),
                    (b_mid + b_w * 0.33, 126.255, st_z0 + 0.08),
                    (b_mid + b_w * 0.33, 126.255, st_z1 - 0.08),
                    (b_mid - b_w * 0.33, 126.255, st_z1 - 0.08),
                    UV_GLASS_WINDOW, 0.88, 0.98,
                )
                mid_z_w = (st_z0 + st_z1) * 0.5
                wh1.add_box(mats["crimson"], b_mid, 126.22, mid_z_w - 0.022, b_w * 0.68, 0.05, 0.044, 0.0)
                for m_off in (-b_w * 0.11, b_w * 0.11):
                    wh1.add_box(mats["crimson"], b_mid + m_off, 126.22, st_z0, 0.044, 0.05, (mid_z_w - 0.022) - st_z0, 0.0, add_top=False)
                    wh1.add_box(mats["crimson"], b_mid + m_off, 126.22, mid_z_w + 0.022, 0.044, 0.05, st_z1 - (mid_z_w + 0.022), 0.0, add_bottom=False)
            # Green vertical-picket railings (pickets stop cleanly BETWEEN bottom rail top & top rail bottom!)
            for is_1f, rz_b in ((True, wh1_base_z), (False, wh1_mid_z + 0.09)):
                if is_1f and ci == 2:
                    continue
                wh1.add_box(mats["green_rail"], b_mid, 125.24, rz_b + 0.96, b_w, 0.06, 0.055, 0.0)
                wh1.add_box(mats["green_rail"], b_mid, 125.24, rz_b + 0.10, b_w, 0.05, 0.045, 0.0)
                for pk_i in range(9):
                    pk_x = bx0 + 0.12 + (b_w - 0.24) * (pk_i / 8.0)
                    wh1.add_box(mats["green_rail"], pk_x, 125.24, rz_b + 0.145, 0.032, 0.032, 0.815, 0.0, add_bottom=False, add_top=False)

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
    # West end raised stone planter & twin tall deciduous trees (cleanly clear of terrace south edge)
    wh1.add_box(mats["surf"], -92.3, 124.8, 0.02, 2.9, 5.2, 0.46, 0.0, UV_PLAZA_TILE, ao_bot=0.74, ao_top=0.94, add_bottom=False)
    wh1.add_tree(-91.8, 123.6, "broad", 11.4, mats["trunk"], mats["leaf"])
    wh1.add_tree(-92.4, 126.2, "broad", 9.6, mats["trunk"], mats["leaf"])

    # 4. North Facade Details & Semi-Open Skywell Courtyard Entrance (Photo 1 1:1 Reconstruction!)
    for nwx in (-71.05, -74.55, -79.2, -83.8, -88.4):
        for nwz0, nwz1 in ((1.38, 2.68), (4.62, 5.92)):
            if nwx == -79.2 and nwz0 < 3.0:
                continue  # Inside enclosed glass entrance lobby
            wh1.add_box(mats["crimson"], nwx, 133.24, nwz0, 1.08, 0.12, nwz1 - nwz0, 0.0)
            wh1.quad_enu(mats["glass"], (nwx + 0.46, 133.325, nwz0 + 0.08), (nwx - 0.46, 133.325, nwz0 + 0.08), (nwx - 0.46, 133.325, nwz1 - 0.08), (nwx + 0.46, 133.325, nwz1 - 0.08), UV_GLASS_WINDOW, 0.86, 0.98)
            wh1.add_box(mats["surf"], nwx, 133.26, nwz0 - 0.09, 1.20, 0.16, 0.09, 0.0, UV_QINGZHUAN, add_top=False)
    for ac_hx, ac_hz in ((-70.65, 4.95), (-71.75, 4.78), (-73.45, 4.62), (-74.55, 4.48)):
        add_ac_unit(wh1, ac_hx, 133.42, ac_hz, 0.0, mats)
    # Cluster of upright yellow training/hurdle poles along 1F north wall east of portal
    for py_i in range(20):
        px_pole = -72.18 + (py_i % 10) * 0.21 + (0.07 if py_i >= 10 else 0.0)
        py_pole = 133.36 + (0.14 if py_i >= 10 else 0.0)
        tilt_x = ((py_i * 7) % 5 - 2) * 0.03
        wh1.add_cylinder(mats["yellow_pole"], px_pole, py_pole, 0.03, 0.07, 0.07, 0.03, 6)
        wh1.quad_enu(
            mats["yellow_pole"],
            (px_pole - 0.016, py_pole, 0.06), (px_pole + 0.016, py_pole, 0.06),
            (px_pole + tilt_x + 0.016, py_pole + 0.02, 1.36), (px_pole + tilt_x - 0.016, py_pole + 0.02, 1.36),
            double_sided=True,
        )
    # Grey-brick flat-lintel portal frame spanning alley (clean butt joints: pier stops at z=2.72 under lintel!)
    wh1.add_box(mats["surf"], -72.52, 133.48, 0.03, 0.62, 0.56, 2.69, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.95, add_bottom=False, add_top=False)
    wh1.add_box(mats["surf"], -72.52, 134.35, 2.72, 0.62, 2.35, 0.46, 0.0, UV_QINGZHUAN, ao_bot=0.84, ao_top=0.98, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wh1.add_box(mats["white_alu"], -72.52, 134.35, 2.68, 0.58, 1.48, 0.04, 0.0, add_top=False)
    # Semi-open skywell courtyard (non-overlapping L-shaped perimeter roof collar!)
    wh1.add_box(mats["white_alu"], -75.09, 136.32, 2.92, 4.52, 0.96, 0.24, 0.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    wh1.add_box(mats["white_alu"], -76.85, 134.52, 2.92, 1.00, 2.64, 0.24, 0.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    # Stone-curbed white-pebble tree pit (cx=-75.05, cy=134.55) + tall skywell tree rising through open roof!
    pit_x, pit_y = -75.05, 134.55
    wh1.add_box(mats["surf"], pit_x, pit_y, 0.03, 2.25, 1.48, 0.14, 0.0, UV_PLAZA_TILE, ao_bot=0.78, ao_top=0.95, top_mat=mats["details"], top_uv=UV_WHITE_PEBBLES, add_bottom=False)
    wh1.add_cylinder(mats["trunk"], pit_x, pit_y, 0.17, 0.34, 0.24, 5.40, 9, ao_bot=0.64, ao_top=0.88)
    for ring_i in range(3):
        phi0 = -0.30 + ring_i * 0.45
        phi1 = phi0 + 0.48
        r0 = 3.2 * math.cos(phi0)
        r1 = max(0.08, 3.2 * math.cos(phi1))
        z0_t = 7.4 + 3.2 * math.sin(phi0) * 0.8
        z1_t = 7.4 + 3.2 * math.sin(phi1) * 0.85
        wh1.add_cylinder(mats["leaf"], pit_x, pit_y, z0_t, r0, r1, z1_t - z0_t, 10, UV_FOLIAGE, ao_bot=0.78 + ring_i * 0.06, ao_top=0.95)
    # Second red fire cabinet (25mm proud front face) + row of 6 grey stone pole-bases inside skywell left wall
    wh1.add_box(mats["crimson"], -73.08, 133.42, 0.03, 0.56, 0.22, 0.58, 0.0, add_bottom=False)
    wh1.quad_enu(mats["details"], (-72.80, 133.555, 0.05), (-73.36, 133.555, 0.05), (-73.36, 133.555, 0.59), (-72.80, 133.555, 0.59), UV_FIRE_BOX, 0.90, 0.98)
    for sb_i in range(6):
        sb_x = -73.68 - sb_i * 0.46
        wh1.add_box(mats["surf"], sb_x, 133.56, 0.03, 0.40, 0.42, 0.11, 0.0, UV_PLAZA_TILE, add_bottom=False)
        wh1.add_cylinder(mats["dark_steel"], sb_x, 133.56, 0.14, 0.03, 0.03, 0.36, 6)
    # Full-height dark-framed glass entrance partition & double glass doors (clean butt-joint frame, single-sided glass!)
    gx_ent = -77.35
    wh1.add_box(mats["surf"], -79.45, 135.0, 3.04, 4.20, 3.52, 0.22, 0.0, UV_PLAZA_TILE, ao_bot=0.84, ao_top=0.98)
    wh1.add_box(mats["surf"], -81.52, 135.0, 0.03, 0.30, 3.52, 3.01, 0.0, UV_QINGZHUAN, ao_bot=0.76, ao_top=0.94, add_bottom=False, add_top=False)
    for gz_m in (0.03, 2.28, 2.97):
        wh1.add_box(mats["dark_steel"], gx_ent, 135.04, gz_m, 0.08, 3.44, 0.07, 0.0, add_bottom=(gz_m > 0.05))
    for gy_m in (133.36, 134.35, 135.65, 136.72):
        wh1.add_box(mats["dark_steel"], gx_ent, gy_m, 0.10, 0.08, 0.08, 2.18, 0.0, add_bottom=False, add_top=False)
        wh1.add_box(mats["dark_steel"], gx_ent, gy_m, 2.35, 0.08, 0.08, 0.62, 0.0, add_bottom=False, add_top=False)
    wh1.quad_enu(
        mats["details_alpha"],
        (gx_ent + 0.065, 133.40, 0.10), (gx_ent + 0.065, 136.68, 0.10),
        (gx_ent + 0.065, 136.68, 2.97), (gx_ent + 0.065, 133.40, 2.97),
        UV_HISTORY_GLASS_DOOR, 0.94, 1.0,
    )
    # "校史馆" plaque beside the glass entrance lobby (30mm proud of glass!)
    wh1.quad_enu(mats["stage"], (gx_ent + 0.095, 135.72, 1.95), (gx_ent + 0.095, 136.66, 1.95), (gx_ent + 0.095, 136.66, 2.34), (gx_ent + 0.095, 135.72, 2.34), UV_HISTORY_SIGN, 0.95, 1.0)

    # Persimmon outside the history museum (校方供稿：校史馆外柿树)
    wh1.add_tree(-68.6, 137.4, "persimmon", 7.6, mats["trunk"], mats["leaf_persimmon"], mats["fruit_orange"])

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
    # West playground-facing glazed entrance vestibule + flat light-grey canopy & AC units (25mm stepped separation!)
    wb6.add_box(mats["white_alu"], -6.12, 121.8, 3.05, 1.08, 4.40, 0.28, 0.0, ao_bot=0.86, ao_top=1.0)
    wb6.add_box(mats["surf"], -5.82, 121.8, 0.04, 0.48, 3.90, 3.01, 0.0, UV_STUCCO, ao_bot=0.80, ao_top=0.96, add_bottom=False, add_top=False)
    wb6.quad_enu(
        mats["warm_glass"],
        (-6.09, 123.55, 0.12), (-6.09, 120.05, 0.12),
        (-6.09, 120.05, 2.92), (-6.09, 123.55, 2.92),
        (0.0, 0.0, 1.0, 1.0), 0.94, 1.0,
    )
    for wmy in (120.05, 121.15, 121.80, 122.45, 123.55):
        wb6.add_box(mats["white_alu"], -6.14, wmy, 0.08, 0.05, 0.07, 2.24, 0.0, add_bottom=False, add_top=False)
        wb6.add_box(mats["white_alu"], -6.14, wmy, 2.39, 0.05, 0.07, 0.59, 0.0, add_bottom=False, add_top=False)
    wb6.add_box(mats["white_alu"], -6.14, 121.8, 2.32, 0.05, 3.57, 0.07, 0.0)
    # Warm-lit north dining window & outdoor AC units along west wall (Photo 1!)
    wb6.quad_enu(mats["warm_glass"], (-5.66, 126.9, 1.05), (-5.66, 124.5, 1.05), (-5.66, 124.5, 2.75), (-5.66, 126.9, 2.75), (0.0, 0.0, 1.0, 1.0), 0.94, 1.0)
    add_ac_unit(wb6, -5.80, 119.1, 0.45, math.pi * 0.5, mats)
    add_ac_unit(wb6, -5.80, 115.6, 0.45, math.pi * 0.5, mats)
    add_ac_unit(wb6, -5.80, 115.6, 1.25, math.pi * 0.5, mats)

    # 1F Flat-Eaved Connecting Bay north of Cafeteria + West-Facing White Double-Leaf Small Door opening to Campus (Photo 1!)
    wb6.add_box(mats["surf"], 0.10, 129.95, 0.0, 11.80, 4.90, 0.85, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.90, add_top=False)
    wb6.add_box(mats["wall_grey_render"], 0.10, 129.95, 0.85, 11.80, 4.90, 2.60, 0.0, ao_bot=0.80, ao_top=0.95, add_bottom=False, add_top=False)
    wb6.add_box(mats["surf"], -0.02, 129.95, 3.45, 12.15, 5.05, 0.22, 0.0, UV_STUCCO, ao_bot=0.88, ao_top=1.0, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)
    # White double-leaf small door (y=130.65..132.05, z=0.08..2.22m) facing West (-X) onto the campus (25mm clear glass!)
    wb6.add_box(mats["surf"], -5.97, 131.35, 0.02, 0.34, 1.56, 0.08, 0.0, UV_PLAZA_TILE, ao_bot=0.78, ao_top=0.95, add_bottom=False)
    wb6.add_box(mats["white_alu"], -5.85, 131.35, 0.10, 0.10, 1.44, 2.14, 0.0, ao_bot=0.84, ao_top=0.99, add_bottom=False)
    for dy_pane in (130.98, 131.72):
        wb6.quad_enu(
            mats["warm_glass"],
            (-5.925, dy_pane + 0.24, 1.18), (-5.925, dy_pane - 0.24, 1.18),
            (-5.925, dy_pane - 0.24, 2.06), (-5.925, dy_pane + 0.24, 2.06),
            (0.0, 0.0, 1.0, 1.0), 0.94, 1.0,
        )
    wb6.add_box(mats["dark_steel"], -5.94, 131.35, 0.12, 0.04, 0.04, 2.10, 0.0)
    wb6.add_box(mats["dark_steel"], -5.95, 131.26, 0.98, 0.04, 0.03, 0.18, 0.0)
    wb6.add_box(mats["dark_steel"], -5.95, 131.44, 0.98, 0.04, 0.03, 0.18, 0.0)
    # Outdoor AC unit on low stand & small white electrical box immediately south of the small white door (Photo 1!)
    add_ac_unit(wb6, -6.00, 129.05, 0.32, math.pi * 0.5, mats)
    wb6.add_box(mats["white_alu"], -5.84, 129.15, 1.92, 0.10, 0.38, 0.48, 0.0)

    # 1F Qingzhuan Pitched-Gable School Building immediately north of Cafeteria (Photo 1 left & Photo 2 right!)
    wb6.add_pitched_gable_building(
        cx=-0.4, cy_n=135.3, w=12.8, d=5.8, eave_h=3.45, ridge_h=1.65, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["warm_glass"], win_uv=(0.0, 0.0, 1.0, 1.0),
        wood_mat=mats["dark_steel"], stories=1, ridge_along_x=True,
    )
    # Recessed dark side doorway on the west Qingzhuan gable wall (visible just left of the white small door in Photo 1!)
    wb6.add_box(mats["surf"], -6.96, 133.55, 0.02, 0.32, 1.05, 0.08, 0.0, UV_PLAZA_TILE)
    wb6.add_box(mats["dark_steel"], -6.82, 133.55, 0.08, 0.08, 0.92, 2.10, 0.0, ao_bot=0.68, ao_top=0.86)
    # Tall deciduous tree standing in front of north cafeteria window (Photo 1 center & Photo 2 right!)
    wb6.add_tree(-8.2, 128.2, "broad", 10.6, mats["trunk"], mats["leaf"])

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
        ctx_w.add_box(mats["white_alu"], sun_x1 + 0.065, (y0_s + y1_s) * 0.5, (z0_s + z1_s) * 0.5 - 0.04, 0.08, math.hypot(y1_s - y0_s, z1_s - z0_s), 0.08, 0.0)
    # White rooftop balustrade along East gable below glass arch (posts stop cleanly under top rail!)
    ctx_w.add_box(mats["white_alu"], -94.70, sun_cy, sun_z0 + 0.72, 0.08, sun_hw * 1.96, 0.07, 0.0)
    for bal_i in range(15):
        by_b = (sun_cy - sun_hw * 0.95) + bal_i * (sun_hw * 1.90 / 14.0)
        ctx_w.add_box(mats["white_alu"], -94.70, by_b, sun_z0, 0.07, 0.07, 0.72, 0.0, add_bottom=False, add_top=False)
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
    )
    # Salmon-pink corner bay & AC units right beside East Gate Pier (25mm proud windows!)
    ctx_w.add_box(mats["details"], 7.45, 5.65, 3.6, 2.5, 3.2, 11.8, 0.0, UV_SALMON_WALL, ao_bot=0.84, ao_top=0.98)
    for wy in (4.75, 6.55):
        for wz in (4.55, 7.10, 9.65, 12.20):
            ctx_w.quad_enu(
                mats["glass"],
                (6.175, wy + 0.52, wz), (6.175, wy - 0.52, wz),
                (6.175, wy - 0.52, wz + 1.55), (6.175, wy + 0.52, wz + 1.55),
                UV_GLASS_WINDOW, 0.92, 1.0,
            )
            ctx_w.add_box(mats["white_alu"], 6.15, wy, wz - 0.08, 0.06, 1.18, 0.08, 0.0, ao_bot=0.90, ao_top=1.0)
    for wx in (6.95, 8.05):
        for wz in (4.55, 7.10, 9.65, 12.20):
            ctx_w.quad_enu(
                mats["glass"],
                (wx - 0.40, 4.025, wz), (wx + 0.40, 4.025, wz),
                (wx + 0.40, 4.025, wz + 1.55), (wx - 0.40, 4.025, wz + 1.55),
                UV_GLASS_WINDOW, 0.92, 1.0,
            )
            ctx_w.add_box(mats["white_alu"], wx, 4.00, wz - 0.08, 0.96, 0.06, 0.08, 0.0, ao_bot=0.90, ao_top=1.0)
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
        (-22, 52, "broad", 8.5), (-35, 51, "broad", 8.0),
        (5.0, 34, "broad", 7.5), (5.2, 48, "broad", 8.0),
        (5.0, 62, "broad", 7.6), (5.2, 76, "broad", 8.2),
        (-89.5, 134.8, "broad", 7.8),
        (-102.0, 92.0, "broad", 9.5), (-118.0, 90.0, "broad", 10.2),
    ]:
        ctx_w.add_tree(tx, ty, sp, th, mats["trunk"], mats["leaf"])

    return exp.write_glb(out_glb)


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
                 mat: int, uv: UVBox, cap_mat: Optional[int] = None, cap_uv: Optional[UVBox] = None,
                 trim_start: float = 0.0, trim_end: float = 0.0) -> None:
    """Wall segment with an optional tiled coping cap (trimmed ends prevent corner Z-fighting)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    if L < 0.05 + trim_start + trim_end:
        return
    ux, uy = dx / L, dy / L
    p0 = (a[0] + ux * trim_start, a[1] + uy * trim_start)
    p1 = (b[0] - ux * trim_end, b[1] - uy * trim_end)
    eff_L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    yaw = math.atan2(dy, dx)
    cx = (p0[0] + p1[0]) * 0.5
    cy = (p0[1] + p1[1]) * 0.5
    nb.add_box(mat, cx, cy, 0.0, eff_L, thick, h, yaw, uv, ao_bot=0.78, ao_top=0.97, add_top=(cap_mat is None))
    if cap_mat is not None:
        nb.add_box(cap_mat, cx, cy, h, eff_L, thick + 0.16, 0.10, yaw, cap_uv or uv)


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
    """Flat upward-facing ground stripe quad at exact elevation z (zero overlapping box caps)."""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 0.02:
        return
    nx, ny = (dy / L) * (width * 0.5), (-dx / L) * (width * 0.5)
    nb.quad_enu(
        mat,
        (x0 + nx, y0 + ny, z), (x1 + nx, y1 + ny, z),
        (x1 - nx, y1 - ny, z), (x0 - nx, y0 - ny, z),
    )


def add_ground_circle(nb: NodeBuilder, mat: int, cx: float, cy: float, r: float,
                      width: float, z: float, segs: int = 16,
                      a0: float = 0.0, a1: float = math.pi * 2.0) -> None:
    is_full = abs((a1 - a0) - math.pi * 2.0) < 1e-4
    pts = [
        (cx + r * math.cos(a0 + (a1 - a0) * i / segs), cy + r * math.sin(a0 + (a1 - a0) * i / segs))
        for i in range(segs if is_full else segs + 1)
    ]
    nb.add_mitered_ring(pts, width * 0.5, z, mat, closed=is_full)


def add_hutong_house(nb: NodeBuilder, cx: float, cy: float, w: float, d: float, h: float,
                     yaw: float, wall_mat: int, wall_uv: UVBox, roof_mat: int, roof_uv: UVBox,
                     ridge: float = 1.3, ridge_along_x: bool = True) -> None:
    """Cheap gable hutong house (walls + two roof slopes + gable ends)."""
    cs, sn = math.cos(yaw), math.sin(yaw)

    def wp(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, lz)

    nb.add_box(wall_mat, cx, cy, 0.0, w, d, h, yaw, wall_uv, ao_bot=0.76, ao_top=0.95, add_top=False)
    ov = 0.45
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
    else:
        nb.quad_enu(roof_mat, wp(-w / 2 - ov, d / 2 + ov, h - 0.08), wp(-w / 2 - ov, -d / 2 - ov, h - 0.08),
                    wp(0, -d / 2 - ov, rh), wp(0, d / 2 + ov, rh), roof_uv, 0.88, 1.0, double_sided=True)
        nb.quad_enu(roof_mat, wp(w / 2 + ov, -d / 2 - ov, h - 0.08), wp(w / 2 + ov, d / 2 + ov, h - 0.08),
                    wp(0, d / 2 + ov, rh), wp(0, -d / 2 - ov, rh), roof_uv, 0.88, 1.0, double_sided=True)
        nb.tri_enu(wall_mat, wp(-w / 2, -d / 2, h), wp(w / 2, -d / 2, h), wp(0, -d / 2, rh),
                   (0.05, 0.95), (0.95, 0.95), (0.5, 0.05), 0.85, 0.85, 0.95)
        nb.tri_enu(wall_mat, wp(w / 2, d / 2, h), wp(-w / 2, d / 2, h), wp(0, d / 2, rh),
                   (0.05, 0.95), (0.95, 0.95), (0.5, 0.05), 0.85, 0.85, 0.95)


def add_court_markings(nb: NodeBuilder, cx: float, cy: float, w: float, l: float,
                       mat: int, z: float = 0.105) -> None:
    """White FIBA-style markings scaled to the measured court (strictly trimmed at all corners & circle crossings)."""
    t = 0.06
    ht = t * 0.5
    hw, hl = w * 0.5 - 0.18, l * 0.5 - 0.18
    # Perimeter lines (sidelines trimmed cleanly between baselines)
    add_ground_line(nb, mat, cx - hw - ht, cy - hl, cx + hw + ht, cy - hl, t, z)
    add_ground_line(nb, mat, cx - hw - ht, cy + hl, cx + hw + ht, cy + hl, t, z)
    add_ground_line(nb, mat, cx + hw, cy - hl + ht, cx + hw, cy + hl - ht, t, z)
    add_ground_line(nb, mat, cx - hw, cy - hl + ht, cx - hw, cy + hl - ht, t, z)
    # Center line split cleanly around center circle (r=1.75)
    add_ground_line(nb, mat, cx - hw + ht, cy, cx - 1.75 - ht, cy, t, z)
    add_ground_line(nb, mat, cx + 1.75 + ht, cy, cx + hw - ht, cy, t, z)
    add_ground_line(nb, mat, cx - 1.75 + ht, cy, cx + 1.75 - ht, cy, t, z)
    add_ground_circle(nb, mat, cx, cy, 1.75, t, z, 16)
    for sgn in (-1.0, 1.0):
        base = cy + sgn * hl
        lane_end = base - sgn * 5.8
        y_a = base - sgn * ht
        y_b = lane_end + sgn * ht
        add_ground_line(nb, mat, cx - 2.45, y_a, cx - 2.45, y_b, t, z)
        add_ground_line(nb, mat, cx + 2.45, y_a, cx + 2.45, y_b, t, z)
        # Free-throw line split around free-throw circle (r=1.75)
        add_ground_line(nb, mat, cx - 2.45 - ht, lane_end, cx - 1.75 - ht, lane_end, t, z)
        add_ground_line(nb, mat, cx + 1.75 + ht, lane_end, cx + 2.45 + ht, lane_end, t, z)
        add_ground_line(nb, mat, cx - 1.75 + ht, lane_end, cx + 1.75 - ht, lane_end, t, z)
        add_ground_circle(nb, mat, cx, lane_end, 1.75, t, z, 14)
        hoop = base - sgn * 1.35
        add_ground_circle(nb, mat, cx, hoop, 6.55, t, z, 18,
                          a0=(math.pi * 0.5 - 1.12) if sgn > 0 else (-math.pi * 0.5 - 1.12),
                          a1=(math.pi * 0.5 + 1.12) if sgn > 0 else (-math.pi * 0.5 + 1.12))


def build_east_campus(data_path: str, tex_dir: str, out_glb: str) -> Tuple[int, int]:
    east = json.loads(Path(data_path).read_text())
    ways = {w["id"]: w for w in east["ways"]}
    exp = GLBExporter()
    mats = init_materials(exp, tex_dir, include_west_details=True)

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

    # ---- Campus_Ground_East : strictly stratified & non-overlapping ground layers ----
    gnd = exp.add_node("Campus_Ground_East")
    # Layer -0.055m: Neutral ground under surrounding hutong blocks (trimmed outside road y=81..89!)
    add_grid_patch(gnd, -36.0, 24.95, 56.0, 81.0, -0.055, mats["surf"], UV_ASPHALT, cell=6.0, ao=0.92)
    add_grid_patch(gnd, -36.0, 89.0, 56.0, 95.5, -0.055, mats["surf"], UV_ASPHALT, cell=6.0, ao=0.92)
    add_grid_patch(gnd, -36.0, -64.0, 56.0, -40.8, -0.055, mats["surf"], UV_ASPHALT, cell=6.0, ao=0.92)
    # Layer -0.030m: East Si Liu Tiao roadway (non-overlapping with hutong base!)
    add_grid_patch(gnd, -62.0, 81.0, 66.0, 89.0, -0.030, mats["surf"], UV_ASPHALT, cell=4.0)
    # Layer 0.000m: Campus south yard base & street south sidewalk (split around gate apron x=-11.2..-1.6!)
    gnd.add_polygon_patch(ways["398694728"]["pts"], 0.0, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    add_grid_patch(gnd, -62.0, 80.1, -11.2, 81.0, 0.0, mats["surf"], UV_PLAZA_TILE, cell=1.5)
    add_grid_patch(gnd, -1.6, 80.1, 66.0, 81.0, 0.0, mats["surf"], UV_PLAZA_TILE, cell=1.5)
    # Layer +0.025m: Gate apron + Bare/gravel yard north of courts (trimmed south at y=19.05 clear of E-P1!)
    add_grid_patch(gnd, -11.2, 80.1, -1.6, 82.6, 0.025, mats["surf"], UV_PLAZA_TILE, cell=1.2)
    add_grid_patch(gnd, -12.0, 19.05, 32.0, 24.0, 0.025, mats["bare_soil"], (0.0, 0.0, 1.0, 1.0), cell=4.0)
    # Layer +0.050m: 6 m red-brick entrance lane + north gate bay + west veranda apron (25mm above bare soil!)
    add_grid_patch(gnd, LANE_W, 23.9, LANE_E, 76.4, 0.050, mats["surf"], UV_RED_BRICK_WALK, cell=1.6)
    add_grid_patch(gnd, LANE_W, 76.4, LANE_E, 80.1, 0.050, mats["surf"], UV_PLAZA_TILE, cell=1.6)
    add_grid_patch(gnd, -10.2, 54.0, LANE_W, 68.0, 0.050, mats["surf"], UV_PLAZA_TILE, cell=1.6)

    # ---- Walls: south yard perimeter + lane flanks (trimmed >=0.26m clear of 0.51m coping caps, zero overlap!) ----
    add_wall_run(gnd, (-35.5, -40.6), (55.3, -39.3), WALL_H, 0.35, mats["surf"], UV_QINGZHUAN, mats["surf"], UV_GREY_TILE)
    add_wall_run(gnd, (55.3, -39.3), (54.3, 24.1), WALL_H, 0.35, mats["surf"], UV_QINGZHUAN, mats["surf"], UV_GREY_TILE, trim_start=0.26, trim_end=0.26)
    add_wall_run(gnd, (-35.5, -40.6), (-35.5, 24.0), WALL_H, 0.35, mats["surf"], UV_QINGZHUAN, mats["surf"], UV_GREY_TILE, trim_start=0.26, trim_end=0.26)
    add_wall_run(gnd, (-35.5, 24.0), (LANE_W, 24.0), WALL_H, 0.35, mats["surf"], UV_QINGZHUAN, mats["surf"], UV_GREY_TILE)
    add_wall_run(gnd, (LANE_E, 24.0), (54.3, 24.1), WALL_H, 0.35, mats["surf"], UV_QINGZHUAN, mats["surf"], UV_GREY_TILE)
    add_wall_run(gnd, (LANE_W, 24.0), (LANE_W, 54.0), WALL_H, 0.30, mats["surf"], UV_QINGZHUAN, mats["surf"], UV_GREY_TILE, trim_start=0.26)
    add_wall_run(gnd, (LANE_W, 68.0), (LANE_W, 76.2), WALL_H, 0.30, mats["surf"], UV_QINGZHUAN, mats["surf"], UV_GREY_TILE)
    add_wall_run(gnd, (LANE_E, 24.0), (LANE_E, 76.2), WALL_H, 0.30, mats["surf"], UV_QINGZHUAN, mats["surf"], UV_GREY_TILE, trim_start=0.26)

    # ---- E-G1 : north gate, guardhouse, plaques, barriers (all clearances >= 25mm, zero crossing overlaps!) ----
    eg1 = exp.add_node("E-G1")
    for px in (WEST_PIER, EAST_PIER):
        eg1.add_box(mats["surf"], px, GATE_Y, 0.0, PIER + 0.08, PIER + 0.08, 0.20, 0.0, UV_QINGZHUAN)
        eg1.add_box(mats["gates"], px, GATE_Y, 0.20, PIER, PIER, 4.35, 0.0, UV_BURGUNDY, ao_bot=0.74, ao_top=0.98, add_bottom=False, add_top=False)
    # beam + deep maroon fascia + tiled coping + upright tile row + corner finials (finials sit ON TOP at z=5.95!)
    eg1.add_box(mats["gates"], GX, GATE_Y, 4.55, OPEN + 2 * PIER + 0.10, PIER + 0.06, 0.45, 0.0, UV_BURGUNDY, add_top=False)
    eg1.add_box(mats["gates"], GX, GATE_Y, 5.00, OPEN + 2 * PIER + 0.35, PIER + 0.20, 0.85, 0.0, UV_BURGUNDY, ao_bot=0.86, ao_top=1.0, add_top=False)
    eg1.add_box(mats["surf"], GX, GATE_Y, 5.85, OPEN + 2 * PIER + 0.55, PIER + 0.36, 0.10, 0.0, UV_GREY_TILE)
    for i in range(15):
        tx = GX - 2.80 + i * (5.60 / 14.0)
        eg1.add_box(mats["surf"], tx, GATE_Y, 5.95, 0.20, 0.18, 0.22, 0.0, UV_GREY_TILE, add_bottom=False)
    for px in (GX - 3.45, GX + 3.45):
        eg1.add_box(mats["surf"], px, GATE_Y, 5.95, 0.36, 0.36, 0.50, 0.0, UV_QINGZHUAN, add_bottom=False)
    # LED screen (off, dark) on the beam's north face (25mm proud of dark steel frame, single-sided!)
    eg1.add_box(mats["dark_steel"], GX, GATE_Y + 0.46, 3.83, 4.72, 0.06, 0.70, 0.0, (0.1, 0.1, 0.9, 0.9))
    eg1.quad_enu(mats["led_off"], (GX + 2.30, GATE_Y + 0.515, 3.88), (GX - 2.30, GATE_Y + 0.515, 3.88),
                 (GX - 2.30, GATE_Y + 0.515, 4.50), (GX + 2.30, GATE_Y + 0.515, 4.50),
                 (0.0, 0.0, 1.0, 1.0), 1.0, 1.0)
    # vertical white plaque on the WEST pier (north face, 25mm proud of backing!)
    eg1.add_box(mats["dark_steel"], WEST_PIER, GATE_Y + 0.455, 1.10, 0.34, 0.04, 2.10, 0.0, (0.1, 0.1, 0.9, 0.9))
    eg1.quad_enu(mats["gates"], (WEST_PIER + 0.15, GATE_Y + 0.50, 1.20), (WEST_PIER - 0.15, GATE_Y + 0.50, 1.20),
                 (WEST_PIER - 0.15, GATE_Y + 0.50, 3.10), (WEST_PIER + 0.15, GATE_Y + 0.50, 3.10),
                 UV_WEST_PLAQUE, 1.0, 1.0)
    # stainless steel school plaque + address plate + security sign on guardhouse north wall (clean 25mm steps, clear of window!)
    eg1.add_box(mats["stainless"], -2.05, GATE_Y + 0.455, 1.93, 1.42, 0.03, 0.56, 0.0, (0.05, 0.05, 0.95, 0.95))
    eg1.quad_enu(mats["gates"], (-1.38, GATE_Y + 0.495, 1.97), (-2.72, GATE_Y + 0.495, 1.97),
                 (-2.72, GATE_Y + 0.495, 2.49), (-1.38, GATE_Y + 0.495, 2.49),
                 UV_EAST_SIGN, 1.0, 1.0)
    eg1.add_box(mats["sign_red"], -3.02, GATE_Y + 0.43, 1.44, 0.52, 0.025, 0.34, 0.0, (0.0, 0.0, 1.0, 1.0))
    eg1.add_box(mats["plaque_white"], -3.02, GATE_Y + 0.468, 1.47, 0.44, 0.02, 0.28, 0.0, (0.0, 0.0, 1.0, 1.0))
    eg1.add_box(mats["sign_blue"], -1.95, GATE_Y + 0.43, 2.78, 0.56, 0.025, 0.38, 0.0, (0.0, 0.0, 1.0, 1.0))
    # folding gate: vertical pickets + cleanly offset X braces (±0.03m from pickets so zero crossing overlaps!) + tracks + wheels
    bays = 12
    bw = OPEN / bays
    for i in range(bays + 1):
        bx = GX - OPEN * 0.5 + i * bw
        eg1.add_box(mats["white_alu"], bx, GATE_Y - 0.30, 0.05, 0.045, 0.045, 1.68, 0.0, (0.1, 0.1, 0.9, 0.9), add_bottom=False)
    for i in range(bays):
        x0 = GX - OPEN * 0.5 + i * bw
        x1 = x0 + bw
        yb = GATE_Y - 0.30
        add_ribbon(eg1, mats["white_alu"], (x0 + 0.02, yb - 0.048, 0.18), (x1 - 0.02, yb - 0.048, 1.52), 0.032)
        add_ribbon(eg1, mats["white_alu"], (x0 + 0.02, yb + 0.048, 1.52), (x1 - 0.02, yb + 0.048, 0.18), 0.032)
        if i % 2 == 0:
            eg1.add_cylinder(mats["orange_hoop"], x0, yb, 0.03, 0.07, 0.07, 0.10, 8, (0.1, 0.1, 0.9, 0.9))
    for ty in (GATE_Y - 0.36, GATE_Y - 0.24):
        eg1.add_box(mats["stainless"], GX, ty, 0.025, OPEN + 0.3, 0.05, 0.025, 0.0, (0.1, 0.1, 0.9, 0.9), add_bottom=False)
    # card reader pillar (west side of the opening; LED 25mm proud!)
    eg1.add_box(mats["stainless"], GX - OPEN * 0.5 - 0.28, GATE_Y - 0.75, 0.0, 0.26, 0.26, 1.18, 0.0, (0.1, 0.1, 0.9, 0.9))
    eg1.add_box(mats["led"], GX - OPEN * 0.5 - 0.28, GATE_Y - 0.905, 0.80, 0.16, 0.025, 0.12, 0.0, (0.05, 0.05, 0.95, 0.95))
    # guardhouse (east of gate), grey brick with shallow tiled roof
    eg1.add_pitched_gable_building(
        cx=0.20, cy_n=78.55, w=7.0, d=4.7, eave_h=3.05, ridge_h=0.75, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=1, ridge_along_x=True,
    )
    # two white A-frame barriers (cleanly offset legs & top red sign sitting ON TOP of white bar!)
    for bx in (-11.4, 1.9):
        add_ribbon(eg1, mats["white_alu"], (bx - 0.19, 82.97, 0.0), (bx, 82.97, 1.02), 0.07)
        add_ribbon(eg1, mats["white_alu"], (bx + 0.19, 83.03, 0.0), (bx, 83.03, 1.02), 0.07)
        eg1.add_box(mats["white_alu"], bx, 83.0, 1.02, 1.0, 0.07, 0.07, 0.0, (0.1, 0.1, 0.9, 0.9))
        eg1.add_box(mats["sign_red"], bx, 83.0, 1.09, 0.55, 0.08, 0.08, 0.0, (0.1, 0.1, 0.9, 0.9), add_bottom=False)
    # white/red "5" roundel (30mm proud of -0.030m road, single-sided!) + two manhole covers
    eg1.quad_enu(mats["gates"], (GX - 1.15, 83.55, 0.00), (GX + 1.15, 83.55, 0.00),
                 (GX + 1.15, 85.85, 0.00), (GX - 1.15, 85.85, 0.00), UV_SPEED_5, 1.0, 1.0)
    for hx, hy in ((GX - 1.9, 82.9), (GX + 1.7, 83.2)):
        eg1.add_cylinder(mats["dark_steel"], hx, hy, -0.02, 0.34, 0.34, 0.025, 12, (0.1, 0.1, 0.9, 0.9))

    # ---- E-N1 : 56 m brick lane + west veranda annex + east tree court -----
    en1 = exp.add_node("E-N1")
    # single-storey veranda building on the west side (facade opens onto the lane)
    en1.add_pitched_gable_building(
        cx=-13.50, cy_n=61.0, w=7.0, d=14.0, eave_h=3.30, ridge_h=1.05, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=1, ridge_along_x=False,
    )
    # lean-to veranda canopy + posts facing the lane
    en1.add_box(mats["surf"], -9.45, 61.0, 2.95, 1.20, 13.6, 0.10, 0.0, UV_GREY_TILE)
    for py in (54.9, 58.9, 62.9, 66.9):
        en1.add_cylinder(mats["crimson"], -9.15, py, 0.0, 0.09, 0.09, 2.95, 8)
    # east side: walled tree courtyard (no buildings within 8 m of the lane)
    for tx, ty, sp, th in ((0.6, 74.0, "cedar", 9.0), (3.6, 68.0, "broad", 11.0),
                           (1.4, 62.0, "cedar", 8.2), (4.6, 56.0, "broad", 10.0),
                           (2.2, 50.5, "broad", 9.0)):
        en1.add_tree(tx, ty, sp, th, mats["trunk"], mats["leaf"])
    # two trees behind the west annex (positioned cleanly in courtyard gaps outside neighboring hutong roofs)
    en1.add_tree(-14.2, 72.0, "broad", 10.0, mats["trunk"], mats["leaf"])
    en1.add_tree(-14.2, 53.3, "broad", 9.0, mats["trunk"], mats["leaf"])

    # ---- E-P1 : two measured courts + buffer + fence + floodlights (25mm clean vertical steps!) ----
    ep1 = exp.add_node("E-P1")
    add_grid_patch(ep1, -6.0, -16.0, 31.0, 19.0, 0.055, mats["surf"], UV_TRACK_EPDM, cell=2.2, ao=0.98)
    for wid in ("838569683", "838569684"):
        pts = ways[wid]["pts"]
        ep1.add_polygon_patch(pts, 0.080, mats["surf"], UV_COURT_GREEN, ao=1.0)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        cx = (min(xs) + max(xs)) * 0.5
        cy = (min(ys) + max(ys)) * 0.5
        add_court_markings(ep1, cx, cy, max(xs) - min(xs), max(ys) - min(ys), mats["white_alu"], 0.105)
        add_basketball_hoop(ep1, cx, min(ys) - 0.6, 0.0, mats)
        add_basketball_hoop(ep1, cx, max(ys) + 0.6, math.pi, mats)
    # chain-link fence around the sports pad (deduplicated corner posts, top rail sits ON TOP of posts, single-sided mesh!)
    fx0, fy0, fx1, fy1 = -6.0, -16.0, 31.0, 19.0
    fence_runs = [((fx0, fy0), (fx1, fy0)), ((fx1, fy0), (fx1, fy1)),
                  ((fx1, fy1), (fx0, fy1)), ((fx0, 2.0), (fx0, fy0)),
                  ((fx0, fy1), (fx0, 4.6))]
    post_mat = mats["dark_steel"]
    placed_fposts: List[Vec2] = []
    for run_idx, (a, b) in enumerate(fence_runs):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        yaw = math.atan2(dy, dx)
        n = max(2, int(L / 3.0) + 1)
        for i in range(n):
            t = i / (n - 1)
            px = a[0] + dx * t
            py = a[1] + dy * t
            if any(math.hypot(px - ox, py - oy) < 0.15 for ox, oy in placed_fposts):
                continue
            placed_fposts.append((px, py))
            ep1.add_cylinder(post_mat, px, py, 0.0, 0.06, 0.06, 3.16, 6, (0.1, 0.1, 0.9, 0.9))
        # Trim rail ends slightly on N-S runs so corner joints don't overlap E-W rails
        rail_trim = 0.06 if abs(dx) < abs(dy) else 0.0
        ep1.add_box(post_mat, (a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, 3.16, max(0.1, L - 2.0 * rail_trim), 0.05, 0.05, yaw, (0.1, 0.1, 0.9, 0.9))
        ep1.quad_enu(mats["fence_mesh"],
                     (a[0], a[1], 0.10), (b[0], b[1], 0.10), (b[0], b[1], 3.15), (a[0], a[1], 3.15),
                     (0.0, 0.0, 1.0, 1.0), 1.0, 1.0)
    # four floodlight masts
    for lx, ly in ((fx0 + 0.6, fy0 + 0.6), (fx1 - 0.6, fy0 + 0.6), (fx0 + 0.6, fy1 - 0.6), (fx1 - 0.6, fy1 - 0.6)):
        ep1.add_cylinder(mats["dark_steel"], lx, ly, 0.0, 0.14, 0.09, 7.55, 8)
        ep1.add_box(mats["floodlight"], lx, ly, 7.55, 0.9, 0.22, 0.34, 0.0, (0.05, 0.05, 0.95, 0.95))
        ep1.add_box(mats["dark_steel"], lx, ly, 7.89, 0.95, 0.30, 0.06, 0.0, (0.1, 0.1, 0.9, 0.9), add_bottom=False)

    # ---- E-B1 : south main teaching building (green roof) ------------------
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

    # ---- E-B2 : south-west L building --------------------------------------
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

    # ---- E-B3 : south-east annex block -------------------------------------
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

    # ---- E-B4 : west mid building + blue-tile two-storey annex -------------
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
    # north annex with blue tile roof + red diamond plaster (seen from the courts)
    eb4.add_pitched_gable_building(
        cx=-22.0, cy_n=8.0, w=16.0, d=12.0, eave_h=6.60, ridge_h=2.10, yaw_rad=0.0,
        wall_mat=mats["details"], wall_uv=UV_NEIGHBOR_DIAMOND,
        roof_mat=mats["details"], roof_uv=UV_BLUE_TILE_ROOF,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"], stories=2, ridge_along_x=True,
    )

    # ---- E-B5 : east edge green-roof building (was a 1-storey grey shed) ---
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

    # ---- Context_East : hutong neighbours around the lane ------------------
    ctx_e = exp.add_node("Context_East")
    # lane-side houses (strictly non-overlapping footprints & >= 1m clear of north perimeter wall y=24.0!)
    houses = [
        (-14.5, 73.0, 8.6, 8.8, 3.4), (-14.5, 47.0, 8.6, 11.4, 3.6),
        (-14.8, 33.5, 8.8, 10.6, 3.4),
        (-26.5, 70.0, 11.6, 11.4, 3.8), (-27.0, 55.0, 11.6, 11.4, 3.6),
        (-27.0, 41.5, 11.6, 10.6, 3.6), (-27.0, 29.5, 11.6, 7.6, 3.4),
        (14.0, 72.0, 9.6, 9.6, 3.6), (14.0, 58.0, 9.6, 9.6, 3.4),
        (16.0, 44.5, 11.6, 11.2, 3.8), (17.5, 31.5, 11.6, 9.4, 3.4),
        (30.0, 66.0, 13.4, 11.6, 3.8), (32.0, 48.0, 13.4, 13.4, 4.0),
        (33.0, 32.0, 13.4, 10.8, 3.6),
        (46.0, 72.0, 11.6, 11.6, 3.6), (47.0, 54.0, 11.6, 13.4, 3.8),
        (47.0, 36.0, 11.6, 13.4, 3.6),
    ]
    for hx, hy, hw, hd, hh in houses:
        add_hutong_house(ctx_e, hx, hy, hw, hd, hh, 0.0, mats["surf"], UV_QINGZHUAN,
                         mats["surf"], UV_GREY_TILE, ridge=1.25, ridge_along_x=True)
    # the light two-storey volume at the south end of the lane (ownership unconfirmed)
    ctx_e.add_box(mats["surf"], 4.5, 41.0, 0.0, 9.0, 14.0, 6.9, 0.0, UV_STUCCO, ao_bot=0.8, ao_top=0.98, add_top=False)
    ctx_e.add_box(mats["surf"], 4.5, 41.0, 6.9, 9.4, 14.4, 0.4, 0.0, UV_PLAZA_TILE)
    # remaining distant hutong blocks (kept from the original context massing)
    for bx, by, bw, bd in [(-52, 102, 34, 14), (2, 102, 38, 16), (48, 102, 36, 14),
                           (-52, 48, 22, 38), (68, 46, 22, 36),
                           (-52, -16, 20, 48), (68, -14, 22, 46),
                           (-10, -56, 48, 14), (42, -56, 36, 14)]:
        ctx_e.add_box(mats["context"], bx, by, 0.0, bw, bd, 3.6, 0.0, (0.0, 0.0, 1.0, 1.0), ao_bot=0.72, ao_top=0.92)
    ctx_e.add_tree(-30, 26, "broad", 9.0, mats["trunk"], mats["leaf"])
    ctx_e.add_tree(36, 22, "broad", 8.5, mats["trunk"], mats["leaf"])
    # south yard trees (west wall, north edge, east corner)
    for tx, ty, th in ((-33.0, -33.0, 10.0), (-33.0, -24.0, 9.0), (-22.0, 22.0, 11.0),
                       (12.0, 22.0, 10.0), (52.0, 10.0, 9.0)):
        ctx_e.add_tree(tx, ty, "broad", th, mats["trunk"], mats["leaf"])

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


def sync_campuses_model_version(repo: Path, filename: str, campus_key: str) -> str:
    """Update `?v=<sha8>` query param and classicModelMB in src/data/campuses.ts after rebuilding a classic GLB."""
    glb_path = repo / "public" / "models" / filename
    raw = glb_path.read_bytes()
    sha8 = hashlib.sha256(raw).hexdigest()[:8]
    size_mb = round(len(raw) / (1024 * 1024), 1)
    campuses_ts = repo / "src" / "data" / "campuses.ts"
    if campuses_ts.exists():
        text = campuses_ts.read_text()
        updated = re.sub(
            rf"/models/{re.escape(filename)}(?:\?v=[0-9a-f]+)?",
            f"/models/{filename}?v={sha8}",
            text,
        )
        updated = re.sub(
            rf'(classicModelUrl:\s*"/models/{re.escape(filename)}\?v=[0-9a-f]+",\s*\n\s*classicModelMB:\s*)[0-9.]+',
            rf"\g<1>{size_mb}",
            updated,
        )
        if updated != text:
            campuses_ts.write_text(updated)
    return sha8


def optimize_classic_glb(repo: Path, glb_path: Path) -> None:
    """Run dedup + weld + prune while preserving lossless FLOAT32 vertex positions."""
    node_bin = shutil.which("node")
    opt_script = repo / "blender" / "scripts" / "optimize_glb.mjs"
    if node_bin and opt_script.exists():
        subprocess.run([node_bin, str(opt_script), "--preserve-positions", str(glb_path)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Z-fighting-free classic campus GLB models")
    parser.add_argument(
        "--campus",
        choices=("west", "east", "all"),
        default="all",
        help="Which classic campus GLB to rebuild (default: all)",
    )
    parser.add_argument(
        "--skip-optimize",
        action="store_true",
        help="Skip @gltf-transform dedup/weld/prune pass",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    data_dir = repo / "blender" / "data"
    out_dir = repo / "public" / "models"
    tex_dir = resolve_tex_dir(repo)

    if args.campus in ("west", "all"):
        w_out = out_dir / "west-campus-classic.glb"
        wv, wt = build_west_campus(str(data_dir / "west_metric.json"), tex_dir, str(w_out))
        if not args.skip_optimize:
            optimize_classic_glb(repo, w_out)
        ws = w_out.stat().st_size
        w_ver = sync_campuses_model_version(repo, "west-campus-classic.glb", "west")
        print(f"west-campus-classic.glb (v={w_ver}): {wv} verts, {wt} tris, {ws:,} bytes ({ws / (1024*1024):.2f} MB)")

    if args.campus in ("east", "all"):
        e_out = out_dir / "east-campus-classic.glb"
        ev, et = build_east_campus(str(data_dir / "east_metric.json"), tex_dir, str(e_out))
        if not args.skip_optimize:
            optimize_classic_glb(repo, e_out)
        es = e_out.stat().st_size
        e_ver = sync_campuses_model_version(repo, "east-campus-classic.glb", "east")
        print(f"east-campus-classic.glb (v={e_ver}): {ev} verts, {et} tris, {es:,} bytes ({es / (1024*1024):.2f} MB)")


if __name__ == "__main__":
    main()

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
import json
import math
import os
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
UV_WEST_PLAQUE: UVBox = (0.015, 0.245, 0.268, 0.755)
UV_SHENDU_STONE: UVBox = (0.305, 0.245, 0.615, 0.755)
UV_MARBLE: UVBox = (0.645, 0.245, 0.995, 0.515)
UV_BURGUNDY: UVBox = (0.645, 0.545, 0.995, 0.755)
UV_EAST_SIGN: UVBox = (0.015, 0.785, 0.49, 0.992)
UV_SPEED_5: UVBox = (0.525, 0.785, 0.755, 0.992)
UV_FLAG: UVBox = (0.785, 0.785, 0.995, 0.995)

UV_STAGE_LED: UVBox = (0.005, 0.005, 0.715, 0.315)
UV_PILLAR_LEFT: UVBox = (0.742, 0.005, 0.858, 0.515)
UV_PILLAR_RIGHT: UVBox = (0.882, 0.005, 0.995, 0.515)
UV_B_WALL_SIGN: UVBox = (0.005, 0.345, 0.335, 0.995)
UV_BOOK_B: UVBox = (0.365, 0.345, 0.505, 0.655)
UV_BOOK_D: UVBox = (0.525, 0.345, 0.665, 0.655)
UV_BOOK_C: UVBox = (0.688, 0.530, 0.808, 0.668)
UV_CAFETERIA_SIGN: UVBox = (0.822, 0.543, 0.992, 0.654)
UV_MUSIC_SIGN: UVBox = (0.365, 0.682, 0.995, 0.836)
UV_RELIEF_WALL: UVBox = (0.365, 0.862, 0.995, 0.995)


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
        self.add_tri(p0, p1, p2, uv0, uv1, uv2, cb, cb, ct, double_sided=double_sided)
        self.add_tri(p0, p2, p3, uv0, uv2, uv3, cb, ct, ct, double_sided=double_sided)


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

            is_party_wall = bool(
                solid_x_planes
                and any(abs(a[0] - px) < 0.25 and abs(b[0] - px) < 0.25 for px in solid_x_planes)
            )
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
                    self.quad_enu(
                        win_mat,
                        wpt(w0, -recess, win_z0), wpt(w1, -recess, win_z0),
                        wpt(w1, -recess, win_z1), wpt(w0, -recess, win_z1),
                        win_uv, 0.85, 1.0,
                    )
                    # Vertical aluminum mullions (outer frame + center 2 splits)
                    for mx in [w0 + 0.05, w0 + (w1 - w0) * 0.34, w0 + (w1 - w0) * 0.66, w1 - 0.05]:
                        self.quad_enu(
                            mullion_mat,
                            wpt(mx - 0.03, -recess + 0.03, win_z0),
                            wpt(mx + 0.03, -recess + 0.03, win_z0),
                            wpt(mx + 0.03, -recess + 0.03, win_z1),
                            wpt(mx - 0.03, -recess + 0.03, win_z1),
                            (0.1, 0.1, 0.9, 0.9), 0.95, 1.0,
                        )

            # 3. Cornice + Parapet Wall + Rooftop Blue-Grey Metal Safety Railing
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
                rz0 = top_z + parapet_h
                rz1 = rz0 + 0.95
                # Top handrail bar + intermediate bar + posts every 2.5m
                self.quad_enu(
                    mullion_mat,
                    wpt(0, 0.05, rz1 - 0.06), wpt(seg_len, 0.05, rz1 - 0.06),
                    wpt(seg_len, 0.05, rz1), wpt(0, 0.05, rz1),
                    (0.1, 0.1, 0.9, 0.9), 0.95, 1.0, double_sided=True,
                )
                n_posts = max(2, int(seg_len // 2.8) + 1)
                for pi in range(n_posts):
                    pa = seg_len * pi / (n_posts - 1)
                    self.quad_enu(
                        mullion_mat,
                        wpt(max(0, pa - 0.03), 0.05, rz0),
                        wpt(min(seg_len, pa + 0.03), 0.05, rz0),
                        wpt(min(seg_len, pa + 0.03), 0.05, rz1),
                        wpt(max(0, pa - 0.03), 0.05, rz1),
                        (0.1, 0.1, 0.9, 0.9), 0.92, 1.0, double_sided=True,
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
        if ridge_along_x:
            rh = zt + ridge_h
            self.quad_enu(roof_mat, wp(-hw - ov, -hd - ov, zt - 0.12), wp(hw + ov, -hd - ov, zt - 0.12), wp(hw + ov, 0, rh), wp(-hw - ov, 0, rh), roof_uv, 0.88, 1.0, double_sided=True)
            self.quad_enu(roof_mat, wp(hw + ov, hd + ov, zt - 0.12), wp(-hw - ov, hd + ov, zt - 0.12), wp(-hw - ov, 0, rh), wp(hw + ov, 0, rh), roof_uv, 0.88, 1.0, double_sided=True)
            # Gable end triangles
            self.tri_enu(wall_mat, wp(-hw, hd, zt), wp(-hw, -hd, zt), wp(-hw, 0, rh), (0.1, 0.9), (0.9, 0.9), (0.5, 0.1), 0.86, 0.86, 0.96)
            self.tri_enu(wall_mat, wp(hw, -hd, zt), wp(hw, hd, zt), wp(hw, 0, rh), (0.1, 0.9), (0.9, 0.9), (0.5, 0.1), 0.86, 0.86, 0.96)
            # Ridge cap
            self.add_box(wood_mat, cx, cy_n, ground_z + rh - 0.06, w + ov * 2, 0.28, 0.24, yaw_rad)
        else:
            rh = zt + ridge_h
            self.quad_enu(roof_mat, wp(-hw - ov, hd + ov, zt - 0.12), wp(-hw - ov, -hd - ov, zt - 0.12), wp(0, -hd - ov, rh), wp(0, hd + ov, rh), roof_uv, 0.88, 1.0, double_sided=True)
            self.quad_enu(roof_mat, wp(hw + ov, -hd - ov, zt - 0.12), wp(hw + ov, hd + ov, zt - 0.12), wp(0, hd + ov, rh), wp(0, -hd - ov, rh), roof_uv, 0.88, 1.0, double_sided=True)
            self.tri_enu(wall_mat, wp(-hw, -hd, zt), wp(hw, -hd, zt), wp(0, -hd, rh), (0.1, 0.9), (0.9, 0.9), (0.5, 0.1), 0.86, 0.86, 0.96)
            self.tri_enu(wall_mat, wp(hw, hd, zt), wp(-hw, hd, zt), wp(0, hd, rh), (0.1, 0.9), (0.9, 0.9), (0.5, 0.1), 0.86, 0.86, 0.96)
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


def init_materials(exp: GLBExporter, tex_dir: str) -> dict:
    t_gates = exp.add_png_texture("SignageGates", f"{tex_dir}/tex_signage_gates.png")
    t_stage = exp.add_png_texture("PlaquesStage", f"{tex_dir}/tex_plaques_stage.png")
    t_surf = exp.add_png_texture("Surfaces", f"{tex_dir}/tex_surfaces.png")

    return {
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


# ---------------------------------------------------------------------------
# WEST CAMPUS (同福夹道3号 校本部)
# ---------------------------------------------------------------------------
def build_west_campus(data_path: str, tex_dir: str, out_glb: str) -> Tuple[int, int]:
    west = json.loads(Path(data_path).read_text())
    ways = {w["id"]: w for w in west["ways"]}
    exp = GLBExporter()
    mats = init_materials(exp, tex_dir)

    # ---- Campus_Ground_West ----
    gnd = exp.add_node("Campus_Ground_West")
    gnd.add_polygon_patch(ways["352521262"]["pts"], 0.0, mats["surf"], UV_PLAZA_TILE, ao=0.95)
    # Surrounding road base (below y=0 slightly)
    gnd.add_box(mats["surf"], -35.0, 60.0, -0.18, 290.0, 270.0, 0.16, 0.0, UV_ASPHALT, ao_bot=0.92, ao_top=0.92)
    # East entry driveway stone pavement leading north to Cafeteria (W-B6) + 同福夹道 alley strip
    gnd.add_polygon_patch([(-4.5, 5.2), (3.6, 5.2), (3.6, 96.5), (-5.2, 96.5)], 0.02, mats["surf"], UV_PLAZA_TILE, ao=0.98)
    gnd.add_polygon_patch([(-4.2, -55.0), (4.2, -55.0), (4.2, 5.2), (-4.2, 5.2)], -0.01, mats["surf"], UV_ASPHALT, ao=0.95)

    # Playground South Plaza Strip (between track south edge y=87.5 and B/C wing north wall y=76.8)
    # West side: 石砖地 (Stone-brick open plaza)
    gnd.add_polygon_patch([(-89.5, 76.8), (-51.8, 76.8), (-51.8, 87.3), (-89.5, 87.3)], 0.025, mats["surf"], UV_PLAZA_TILE, ao=0.96)
    # East side: 自行车停放区（无车棚） — painted ground parking bays + open unroofed wheel racks
    gnd.add_polygon_patch([(-44.8, 76.8), (-11.5, 76.8), (-11.5, 87.3), (-44.8, 87.3)], 0.025, mats["surf"], UV_PLAZA_TILE, ao=0.96)
    for lx0, ly0, lx1, ly1 in [
        (-43.8, 78.2, -13.5, 78.38),
        (-43.8, 85.4, -13.5, 85.58),
        (-43.8, 78.2, -43.62, 85.58),
        (-28.7, 78.2, -28.52, 85.58),
        (-13.68, 78.2, -13.5, 85.58),
    ]:
        gnd.quad_enu(mats["white_alu"], (lx0, ly0, 0.035), (lx1, ly0, 0.035), (lx1, ly1, 0.035), (lx0, ly1, 0.035))
    # Two rows of open steel wheel racks (strictly unroofed)
    for rack_y in (79.8, 83.8):
        gnd.add_box(mats["dark_steel"], -28.6, rack_y, 0.03, 27.0, 0.14, 0.12, 0.0)
        for rx_i in range(18):
            rx = -41.5 + rx_i * 1.5
            gnd.add_box(mats["blue_steel"], rx, rack_y, 0.14, 0.08, 0.55, 0.42, 0.0)

    # Green lawn south of B-Wing & C-Wing junction (home to W-L3 冰心像 & W-L1 慎独石)
    gnd.add_polygon_patch([(-41.5, 42.5), (-4.6, 42.5), (-4.6, 57.5), (-41.5, 57.5)], 0.025, mats["surf"], UV_GRASS, ao=0.94)

    # Campus Perimeter Brick Wall (avoiding front gate opening x: -4.5..+3.5 at south gate)
    bound = ensure_ccw(ways["352521262"]["pts"])
    for i in range(len(bound)):
        a, b = bound[i], bound[(i + 1) % len(bound)]
        if a[1] < 8.0 and b[1] < 8.0 and -5.5 <= a[0] <= 5.0 and -5.5 <= b[0] <= 5.0:
            continue  # Open for West Gate
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 0.5:
            continue
        yaw = math.atan2(dy, dx)
        gnd.add_box(mats["surf"], (a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5, 0.0, L, 0.35, 2.35, yaw, UV_QINGZHUAN, ao_bot=0.78, ao_top=0.96)

    # ---- W-G1: 同福夹道3号正门 ----
    gate = exp.add_node("W-G1")
    gate.add_box(mats["gates"], -4.5, 5.2, 0.0, 1.5, 1.5, 4.4, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.98)
    gate.add_box(mats["gates"], 3.2, 5.2, 0.0, 1.5, 1.5, 4.4, 0.0, UV_MARBLE, ao_bot=0.76, ao_top=0.98)
    gate.add_box(mats["gates"], -8.0, 7.2, 0.0, 6.2, 4.6, 3.6, 0.0, UV_MARBLE, ao_bot=0.74, ao_top=0.95)
    gate.quad_enu(mats["glass"], (-6.0, 4.86, 1.0), (-4.95, 4.86, 1.0), (-4.95, 4.86, 2.9), (-6.0, 4.86, 2.9), UV_GLASS_WINDOW)
    gate.add_box(mats["gates"], -0.65, 5.1, 4.35, 12.8, 1.9, 1.35, 0.0, UV_WEST_FASCIA, ao_bot=0.82, ao_top=1.0)
    gate.quad_enu(mats["led"], (-5.5, 4.12, 4.42), (3.8, 4.12, 4.42), (3.8, 4.12, 5.62), (-5.5, 4.12, 5.62), UV_WEST_FASCIA, 1.0, 1.0)
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

    # ---- W-L1: 慎独石 (located at SE lawn south of B座, facing South driveway) ----
    shendu = exp.add_node("W-L1")
    shendu.add_polygon_patch([(-9.0, 52.8), (-4.8, 52.8), (-4.8, 57.6), (-9.0, 57.6)], 0.04, mats["surf"], UV_GRASS, ao=0.92)
    shendu.add_box(mats["gates"], -6.8, 55.2, 0.04, 2.6, 1.8, 0.38, 0.0, UV_BURGUNDY, ao_bot=0.72, ao_top=0.90)
    shendu.add_box(mats["gates"], -6.8, 55.2, 0.42, 1.45, 0.85, 2.55, 0.0, UV_SHENDU_STONE, ao_bot=0.78, ao_top=0.98)
    shendu.add_box(mats["gates"], -6.8, 55.2, 2.95, 1.05, 0.60, 0.72, 0.0, UV_MARBLE, ao_bot=0.88, ao_top=1.0)
    shendu.quad_enu(mats["gates"], (-7.52, 54.73, 0.50), (-6.08, 54.73, 0.50), (-6.08, 54.73, 3.05), (-7.52, 54.73, 3.05), UV_SHENDU_STONE, 0.90, 1.0)

    # ---- W-L3: 冰心像 (B座南侧绿地，慎独石以西、坡道下端东北侧) ----
    bx_node = exp.add_node("W-L3")
    bx_node.add_box(mats["surf"], -16.5, 52.0, 0.03, 3.0, 3.0, 0.18, 0.0, UV_QINGZHUAN, ao_bot=0.78, ao_top=0.92)
    bx_node.add_box(mats["white_alu"], -16.5, 52.0, 0.18, 1.5, 1.5, 0.25, 0.0)
    bx_node.add_box(mats["gates"], -16.5, 52.0, 0.43, 0.86, 0.86, 1.35, 0.0, UV_MARBLE, ao_bot=0.80, ao_top=0.98)
    bx_node.add_cylinder(mats["dark_steel"], -16.5, 52.0, 1.78, 0.36, 0.22, 0.82, 12, ao_bot=0.78, ao_top=1.0)

    # ---- Connected 6-Story Complex: W-B1 (C座) + W-B2 (中部楼梯间) + W-B3 (B座 ~26° NE angle) ----
    # Shared junction planes: x = -55.2 (W-B1 | W-B2) and x = -41.5 (W-B2 | W-B3).
    # C座 (west) is 6 stories taller (~23.65m slab + 0.85m open concrete pergola = 24.5m).
    # 中部楼梯间 + B座 (east) are 6 stories (~21.5m slab, ~22.35m parapet).

    # ---- W-B3: B座教学主楼 (6层 · 保留东北折角) ----
    wb3 = exp.add_node("W-B3")
    wb3_pts = [(-41.5, 70.0), (-11.5, 84.5), (-5.8, 72.8), (-35.5, 57.5), (-41.5, 57.5)]
    wb3.add_detailed_building(
        wb3_pts, stories=6, story_h=3.45, plinth_h=0.80,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_TERRACOTTA_BRICK,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        solid_x_planes=[-41.5],
    )
    # East gable vertical calligraphy ("北京市第一六六中学（原贝满女中、女十二中）") south of W-ST1
    wb3.quad_enu(mats["stage"], (-6.02, 74.15, 6.2), (-7.52, 77.25, 6.2), (-7.52, 77.25, 19.8), (-6.02, 74.15, 19.8), UV_B_WALL_SIGN, 0.92, 1.0)
    # South-east facing red "B 教学楼" open-book plaque
    wb3.quad_enu(mats["stage"], (-30.68, 59.82, 16.5), (-27.71, 61.35, 16.5), (-27.71, 61.35, 20.4), (-30.68, 59.82, 20.4), UV_BOOK_B, 0.95, 1.0)

    # ---- W-B2: 中部楼梯间枢纽 (6层 + 屋顶机房 + 北侧门斗) ----
    wb2 = exp.add_node("W-B2")
    wb2_pts = [(-55.2, 76.8), (-41.5, 76.8), (-41.5, 57.5), (-55.2, 58.0)]
    wb2.add_detailed_building(
        wb2_pts, stories=6, story_h=3.45, plinth_h=0.80,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_TERRACOTTA_BRICK,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        solid_x_planes=[-55.2, -41.5],
    )
    # Rooftop stair/elevator penthouse bulkhead
    wb2.add_box(mats["surf"], -48.35, 67.2, 21.75, 8.4, 7.2, 2.65, 0.0, UV_STUCCO, ao_bot=0.85, ao_top=0.98)
    wb2.add_box(mats["surf"], -48.35, 67.2, 24.40, 8.8, 7.6, 0.25, 0.0, UV_PLAZA_TILE, ao_bot=0.92, ao_top=1.0)
    # North 1-story entrance vestibule leading out to north stone-brick plaza
    wb2.add_box(mats["surf"], -48.35, 78.6, 0.0, 6.8, 3.6, 3.8, 0.0, UV_STUCCO, ao_bot=0.78, ao_top=0.96)
    wb2.add_box(mats["white_alu"], -48.35, 78.7, 3.8, 7.4, 4.0, 0.28, 0.0)
    wb2.quad_enu(mats["glass"], (-46.5, 80.44, 0.2), (-50.2, 80.44, 0.2), (-50.2, 80.44, 2.9), (-46.5, 80.44, 2.9), UV_GLASS_WINDOW)

    # ---- W-B1: C座教学实验楼 (6层 · 最高体量 + 屋顶白色混凝土开敞梁格构架 + 西南室外楼梯) ----
    wb1 = exp.add_node("W-B1")
    wb1_pts = [(-89.8, 76.2), (-55.2, 76.8), (-55.2, 58.0), (-68.2, 58.0), (-68.2, 34.2), (-79.9, 34.0), (-81.0, 49.8), (-87.8, 53.5)]
    wb1.add_detailed_building(
        wb1_pts, stories=6, story_h=3.80, plinth_h=0.85,
        wall_mat=mats["surf"], wall_uv=UV_GREY_RIB,
        band_mat=mats["surf"], band_uv=UV_STUCCO,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["white_alu"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        solid_x_planes=[-55.2],
    )
    # Rooftop Open White Concrete Rectangular Pergola Grid (5x8 cells, no glass pyramids)
    wb1_roof_z = 0.85 + 6 * 3.80 + 0.25
    for ly in [60.2 + i * 2.8 for i in range(6)]:
        wb1.add_box(mats["white_alu"], -72.5, ly, wb1_roof_z, 30.0, 0.42, 0.72, 0.0, ao_bot=0.88, ao_top=1.0)
    for lx in [-87.0 + j * 3.625 for j in range(9)]:
        wb1.add_box(mats["white_alu"], lx, 67.2, wb1_roof_z, 0.42, 14.4, 0.72, 0.0, ao_bot=0.88, ao_top=1.0)
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

    # ---- W-B4: 南院 A 座行政办公楼 (way 636389217 + 1层门房接建) ----
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
    # 1-story south entrance service annex behind West Gate guardhouse
    wb4.add_box(mats["surf"], -8.2, 17.5, 0.0, 5.4, 14.0, 3.6, 0.0, UV_QINGZHUAN, ao_bot=0.74, ao_top=0.94, top_mat=mats["surf"], top_uv=UV_PLAZA_TILE)

    # ---- W-ST1: 东北外挂折返楼梯塔 & "尚美" 艺术浮雕壁 ----
    wst1 = exp.add_node("W-ST1")
    wst1.add_box(mats["surf"], -6.8, 80.5, 0.0, 5.2, 5.2, 1.2, 0.0, UV_QINGZHUAN, ao_bot=0.72, ao_top=0.92)
    for lvl in range(5):
        z0 = 1.2 + lvl * 3.55
        wst1.add_box(mats["white_alu"], -6.8, 80.5, z0 + 1.55, 4.9, 4.9, 0.32, 0.0)
        for bx_o in (-2.5, 2.5):
            wst1.quad_enu(mats["blue_steel"], (-6.8 + bx_o, 78.0, z0), (-6.8 + bx_o, 83.0, z0), (-6.8 + bx_o, 83.0, z0 + 0.14), (-6.8 + bx_o, 78.0, z0 + 0.14), double_sided=True)
            for li in range(5):
                ly = 78.2 + li * 0.95
                wst1.quad_enu(mats["blue_steel"], (-6.8 + bx_o, ly, z0), (-6.8 + bx_o, ly + 0.08, z0), (-6.8 + bx_o, ly + 0.78, z0 + 3.45), (-6.8 + bx_o, ly + 0.70, z0 + 3.45), double_sided=True)
                wst1.quad_enu(mats["blue_steel"], (-6.8 + bx_o, ly + 0.70, z0), (-6.8 + bx_o, ly + 0.78, z0), (-6.8 + bx_o, ly + 0.08, z0 + 3.45), (-6.8 + bx_o, ly, z0 + 3.45), double_sided=True)
        for by_o in (-2.5, 2.5):
            for li in range(5):
                lx = -9.1 + li * 0.95
                wst1.quad_enu(mats["blue_steel"], (lx, 80.5 + by_o, z0), (lx + 0.08, 80.5 + by_o, z0), (lx + 0.78, 80.5 + by_o, z0 + 3.45), (lx + 0.70, 80.5 + by_o, z0 + 3.45), double_sided=True)
    # North-facing "尚美 · 美育浮雕" wall toward playground/plaza
    wst1.quad_enu(mats["stage"], (-3.8, 83.6, 0.35), (-9.5, 83.6, 0.35), (-9.5, 83.6, 3.1), (-3.8, 83.6, 3.1), UV_RELIEF_WALL, 0.90, 1.0)

    # ---- W-MC: 西侧文化走廊 & 音乐长廊 ----
    wmc = exp.add_node("W-MC")
    # North section of west gallery along track west boundary (y=81.5..123.5)
    for pi in range(9):
        py = 82.5 + pi * 5.0
        wmc.add_box(mats["dark_steel"], -93.4, py, 0.0, 0.22, 0.22, 4.2, 0.0)
        wmc.add_box(mats["dark_steel"], -90.0, py, 0.0, 0.22, 0.22, 4.2, 0.0)
        wmc.add_box(mats["dark_steel"], -91.7, py, 4.15, 3.8, 0.20, 0.24, 0.0)
    wmc.quad_enu(mats["skylight"], (-93.5, 81.5, 4.38), (-89.9, 81.5, 4.38), (-89.9, 123.5, 4.38), (-93.5, 123.5, 4.38), UV_SKYLIGHT, 0.95, 1.0, double_sided=True)
    # Main Music Corridor glazed entrance portal beside C座 NW corner (y=74.0..81.5)
    for pi in range(3):
        py = 74.5 + pi * 3.2
        wmc.add_box(mats["dark_steel"], -93.5, py, 0.0, 0.26, 0.26, 4.7, 0.0)
        wmc.add_box(mats["dark_steel"], -88.8, py, 0.0, 0.26, 0.26, 4.7, 0.0)
        wmc.add_box(mats["dark_steel"], -91.15, py, 4.65, 5.2, 0.24, 0.28, 0.0)
    wmc.quad_enu(mats["skylight"], (-93.6, 74.0, 4.88), (-88.6, 74.0, 4.88), (-88.6, 81.5, 4.88), (-93.6, 81.5, 4.88), UV_SKYLIGHT, 0.96, 1.0, double_sided=True)
    # North & South header boards ("音乐长廊 / MUSIC CORRIDOR")
    wmc.quad_enu(mats["stage"], (-88.7, 81.55, 3.95), (-93.5, 81.55, 3.95), (-93.5, 81.55, 5.05), (-88.7, 81.55, 5.05), UV_MUSIC_SIGN, 0.95, 1.0)
    wmc.quad_enu(mats["stage"], (-93.5, 73.95, 3.95), (-88.7, 73.95, 3.95), (-88.7, 73.95, 5.05), (-93.5, 73.95, 5.05), UV_MUSIC_SIGN, 0.95, 1.0)
    # South continuation along west edge beside C座
    for pi in range(5):
        py = 56.0 + pi * 4.2
        wmc.add_box(mats["dark_steel"], -91.2, py, 0.0, 0.20, 0.20, 3.8, 0.0)
        wmc.add_box(mats["dark_steel"], -89.6, py + 0.5, 3.75, 3.2, 0.18, 0.22, 0.0)
    wmc.quad_enu(mats["skylight"], (-91.4, 55.0, 3.95), (-88.4, 55.0, 3.95), (-89.8, 74.0, 3.95), (-93.4, 74.0, 3.95), UV_SKYLIGHT, 0.94, 1.0, double_sided=True)

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

    # ---- W-P1: 北区 200m 环形塑胶操场 + 3片标准篮球场 + 6个篮球架 ----
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

    # 200m Oval EPDM track + western sprint chute extension
    wp1.add_polygon_patch(rounded_rect_pts(-89.5, 87.5, -8.0, 124.5, 18.5, n_arc=16), 0.05, mats["surf"], UV_TRACK_EPDM, ao=0.98)
    wp1.add_polygon_patch([(-91.5, 87.5), (-70.0, 87.5), (-70.0, 91.7), (-91.5, 91.7)], 0.055, mats["surf"], UV_TRACK_EPDM, ao=0.98)
    # 4 white lane stripe rings
    for lane_r in (15.35, 16.40, 17.45):
        inset = 18.5 - lane_r
        lane_pts = rounded_rect_pts(-89.5 + inset, 87.5 + inset, -8.0 - inset, 124.5 - inset, lane_r, n_arc=16)
        for i in range(len(lane_pts)):
            a, b = lane_pts[i], lane_pts[(i + 1) % len(lane_pts)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = max(math.hypot(dx, dy), 0.01)
            nx, ny = (dy / L) * 0.05, (-dx / L) * 0.05
            wp1.quad_enu(mats["white_alu"], (a[0] - nx, a[1] - ny, 0.07), (b[0] - nx, b[1] - ny, 0.07), (b[0] + nx, b[1] + ny, 0.07), (a[0] + nx, a[1] + ny, 0.07))
    # Green interior athletic surface
    wp1.add_polygon_patch(rounded_rect_pts(-85.3, 91.7, -12.2, 120.3, 14.3, n_arc=16), 0.08, mats["surf"], UV_COURT_GREEN, ao=1.0)
    # 3 N-S full basketball courts inside the oval straightaway + 6 hoops
    court_xs = [(-69.5, -56.3), (-54.7, -41.5), (-39.9, -26.7)]
    for cx0, cx1 in court_xs:
        cy0, cy1 = 93.8, 118.2
        for x0, y0, x1, y1 in [
            (cx0, cy0, cx1, cy0 + 0.16),
            (cx0, cy1 - 0.16, cx1, cy1),
            (cx0, cy0, cx0 + 0.16, cy1),
            (cx1 - 0.16, cy0, cx1, cy1),
            (cx0, (cy0 + cy1) * 0.5 - 0.08, cx1, (cy0 + cy1) * 0.5 + 0.08),
        ]:
            wp1.quad_enu(mats["white_alu"], (x0, y0, 0.10), (x1, y0, 0.10), (x1, y1, 0.10), (x0, y1, 0.10))
        add_basketball_hoop(wp1, (cx0 + cx1) * 0.5, cy0 - 0.75, 0.0, mats)
        add_basketball_hoop(wp1, (cx0 + cx1) * 0.5, cy1 + 0.75, math.pi, mats)

    # ---- W-P2: 北侧弧顶张拉膜主席台与升旗台（坐北朝南，紧靠高二平房前） ----
    wp2 = exp.add_node("W-P2")
    st_cx, st_cy = -44.0, 129.0
    # Raised marble podium deck (22.0m E-W x 6.0m N-S)
    wp2.add_box(mats["gates"], st_cx, st_cy, 0.0, 22.0, 6.0, 0.85, 0.0, UV_MARBLE, ao_bot=0.74, ao_top=0.95)
    # 3 front podium steps on SOUTH side facing playground
    for si in range(3):
        wp2.add_box(mats["gates"], st_cx, st_cy - 3.25 - si * 0.45, 0.0, 16.0, 0.5, 0.85 - si * 0.25, 0.0, UV_MARBLE)
    # Central wide LED screen facing SOUTH (-Y / +Z)
    wp2.add_box(mats["dark_steel"], st_cx, st_cy + 0.8, 1.35, 9.4, 0.7, 4.4, 0.0)
    wp2.quad_enu(mats["stage_led"], (st_cx - 4.5, st_cy + 0.42, 1.50), (st_cx + 4.5, st_cy + 0.42, 1.50), (st_cx + 4.5, st_cy + 0.42, 5.55), (st_cx - 4.5, st_cy + 0.42, 5.55), UV_STAGE_LED, 1.0, 1.0)
    # Left (West: 求實進取) & Right (East: 敬業樂羣) motto pillars facing SOUTH
    wp2.add_box(mats["stage"], st_cx - 5.8, st_cy + 0.8, 0.85, 1.9, 0.9, 5.0, 0.0, UV_PILLAR_LEFT)
    wp2.quad_enu(mats["stage"], (st_cx - 6.7, st_cy + 0.32, 0.95), (st_cx - 4.9, st_cy + 0.32, 0.95), (st_cx - 4.9, st_cy + 0.32, 5.75), (st_cx - 6.7, st_cy + 0.32, 5.75), UV_PILLAR_LEFT)
    wp2.add_box(mats["stage"], st_cx + 5.8, st_cy + 0.8, 0.85, 1.9, 0.9, 5.0, 0.0, UV_PILLAR_RIGHT)
    wp2.quad_enu(mats["stage"], (st_cx + 4.9, st_cy + 0.32, 0.95), (st_cx + 6.7, st_cy + 0.32, 0.95), (st_cx + 6.7, st_cy + 0.32, 5.75), (st_cx + 4.9, st_cy + 0.32, 5.75), UV_PILLAR_RIGHT)
    # Flanking 1-story side wings behind stage
    wp2.add_box(mats["surf"], st_cx - 14.0, st_cy + 1.0, 0.0, 5.2, 4.2, 3.8, 0.0, UV_QINGZHUAN)
    wp2.add_box(mats["surf"], st_cx + 14.0, st_cy + 1.0, 0.0, 5.2, 4.2, 3.8, 0.0, UV_QINGZHUAN)
    # 3-Span Doubly-Curved Tensile Membrane Roof spanning East-West (-54.5..-33.5) & arching South-North
    for cx_col in (st_cx - 10.5, st_cx - 3.5, st_cx + 3.5, st_cx + 10.5):
        wp2.add_cylinder(mats["dark_steel"], cx_col, st_cy + 2.6, 0.85, 0.16, 0.16, 5.8, 8)
        wp2.add_cylinder(mats["dark_steel"], cx_col, st_cy - 2.8, 0.85, 0.14, 0.14, 6.8, 8)
    for span in range(3):
        xA = (st_cx - 10.5) + span * 7.0
        xB = xA + 7.0
        for sy_i in range(6):
            t0, t1 = sy_i / 6.0, (sy_i + 1) / 6.0
            y0, y1 = (st_cy - 3.5) + t0 * 7.2, (st_cy - 3.5) + t1 * 7.2
            z0 = 6.2 + 2.4 * math.sin(t0 * math.pi)
            z1 = 6.2 + 2.4 * math.sin(t1 * math.pi)
            wp2.quad_enu(mats["tensile"], (xA, y0, z0), (xB, y0, z0), (xB, y1, z1), (xA, y1, z1), (0.0, 0.0, 1.0, 1.0), 0.92, 1.0, double_sided=True)
    # Flagpole & Red Flag on East front side of stage facing Playground
    fx, fy = -29.8, 126.2
    wp2.add_box(mats["gates"], fx, fy, 0.0, 2.4, 2.4, 0.55, 0.0, UV_MARBLE)
    wp2.add_cylinder(mats["white_alu"], fx, fy, 0.55, 0.10, 0.05, 14.5, 8)
    wp2.quad_enu(mats["gates"], (fx, fy, 13.0), (fx + 2.4, fy - 0.3, 13.0), (fx + 2.4, fy - 0.3, 14.7), (fx, fy, 14.7), UV_FLAG, 0.95, 1.0, double_sided=True)

    # ---- W-B5: 高二平房区（操场北侧 · 1层平顶教学平房） ----
    wb5 = exp.add_node("W-B5")
    wb5_pts = [(-65.0, 133.8), (-13.0, 133.8), (-13.0, 141.8), (-65.0, 141.8)]
    wb5.add_detailed_building(
        wb5_pts, stories=1, story_h=3.15, plinth_h=0.55,
        wall_mat=mats["surf"], wall_uv=UV_STUCCO,
        band_mat=mats["surf"], band_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_PLAZA_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        mullion_mat=mats["dark_steel"],
        plaster_plinth_mat=mats["surf"], plaster_plinth_uv=UV_QINGZHUAN,
        parapet_h=0.45, add_rail=False, bay_w=3.2,
    )

    # ---- W-H1: 校史馆（部分办公室 / D座 · 西北角 2层青砖灰瓦挑廊楼） ----
    wh1 = exp.add_node("W-H1")
    wh1.add_pitched_gable_building(
        cx=-81.0, cy_n=129.0, w=22.0, d=8.4, eave_h=6.8, ridge_h=2.0, yaw_rad=0.0,
        wall_mat=mats["surf"], wall_uv=UV_QINGZHUAN,
        roof_mat=mats["surf"], roof_uv=UV_GREY_TILE,
        win_mat=mats["glass"], win_uv=UV_GLASS_WINDOW,
        wood_mat=mats["dark_steel"],
        stories=2, ridge_along_x=True, balcony_south=True, balcony_mat=mats["green_rail"],
    )
    # Red Book Plaque "D 校史馆" on East Gable (+X) & South Wall (-Y) facing playground
    wh1.quad_enu(mats["stage"], (-69.88, 127.6, 3.8), (-69.88, 130.4, 3.8), (-69.88, 130.4, 6.4), (-69.88, 127.6, 6.4), UV_BOOK_D, 0.95, 1.0)
    wh1.quad_enu(mats["stage"], (-75.2, 124.66, 3.8), (-72.6, 124.66, 3.8), (-72.6, 124.66, 6.4), (-75.2, 124.66, 6.4), UV_BOOK_D, 0.95, 1.0)

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

    # ---- Context_West: Desaturated Hutong & Neighbor Context (including 灯市口小学) ----
    ctx_w = exp.add_node("Context_West")
    skip_w = {"352521262", "398697589", "636389217", "636389213"}
    for w in west["ways"]:
        if w["id"] in skip_w or "building" not in w.get("tags", {}):
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
        h = 3.8 if lv_str == "1" else (11.5 if w["tags"].get("building") == "school" else 9.0)
        is_blue_ref = w["id"] in {"398697588", "479455921"}
        m_side = mats["context_blue"] if is_blue_ref else mats["context"]
        ctx_w.add_polygon_slab(pts, 0.0, h, mats["context"], m_side, (0.0, 0.0, 1.0, 1.0), (0.0, 0.0, 1.0, 1.0), ao_bot=0.72, ao_top=0.95)
    # Campus & east passage trees
    for tx, ty, sp, th in [(-22, 52, "broad", 8.5), (-35, 51, "broad", 8.0), (-8, 12, "broad", 7.2), (1.0, 26, "broad", 7.8), (1.0, 44, "broad", 7.8)]:
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

    required = ("tex_signage_gates.png", "tex_plaques_stage.png", "tex_surfaces.png")
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
        print(f"west-campus.glb: {wv} verts, {wt} tris, {ws:,} bytes")

    if args.campus in ("east", "all"):
        ev, et = build_east_campus(str(data_dir / "east_metric.json"), tex_dir, str(out_dir / "east-campus.glb"))
        es = (out_dir / "east-campus.glb").stat().st_size
        print(f"east-campus.glb: {ev} verts, {et} tris, {es:,} bytes")


if __name__ == "__main__":
    main()

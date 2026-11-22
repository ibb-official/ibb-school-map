"""
High-Precision Architectural & Campus Prop Geometry Library for ibb-school-map.

Provides photo-faithful 3D procedural builders (zero paper-thin planes, zero crude red blocks,
zero square-wheel bicycles) shared across both Enhanced (ArchViz PBR) and Classic GLB exports:
  - 3D rectangular structural beams & hollow torus rings
  - Realistic circular-wheel tubular-frame bicycles & inverted-U parking racks
  - Hollow molded stone/terracotta/brick planter boxes with soil & foliage tufts
  - Continuous brick/granite stone curbs, 40cm retaining walls & granite staircases
  - Full-stone curved ramp railings (Scheme A: carved newel posts, stone balusters & curved coping)
  - Upturned flying-eave Chinese garden pavilion with Meirenkao seating & finial
  - Tempered-glass basketball hoops with hollow orange rims & openwork braided nets
  - Realistic outdoor ping-pong tables with tubular legs & fine mesh nets
  - East Gate photo-faithful 3D wheeled A-frame barricades & diamond pier lattices
  - Multi-head angled stadium floodlights, Beijing hutong two-slope tile walls,
    detailed building entrance portals, rooftop penthouses & braced AC outdoor units.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

Vec2 = Tuple[float, float]
Vec3 = Tuple[float, float, float]
UVBox = Tuple[float, float, float, float]


def _vsub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vcross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vnorm(a: Vec3) -> Vec3:
    l = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    return (a[0] / l, a[1] / l, a[2] / l) if l > 1e-8 else (0.0, 0.0, 1.0)


def _enu_to_gltf(e: float, n: float, h: float) -> Vec3:
    return (e, h, -n)


# ---------------------------------------------------------------------------
# 1. Core 3D Primitives: Oriented 3D Rectangular Beam & Hollow Torus Ring
# ---------------------------------------------------------------------------
def add_rect_beam(
    nb,
    mat: int,
    p0: Vec3,
    p1: Vec3,
    width: float,
    height: float,
    uv_box: UVBox = (0.0, 0.0, 1.0, 1.0),
    ao_bot: float = 0.80,
    ao_top: float = 0.98,
    caps: bool = True,
) -> None:
    """Solid 3D rectangular bar between arbitrary ENU endpoints p0 -> p1 (outward CCW normals)."""
    d = _vsub(p1, p0)
    length = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
    if length < 1e-4:
        return
    t = (d[0] / length, d[1] / length, d[2] / length)
    up_ref = (0.0, 0.0, 1.0) if abs(t[2]) < 0.92 else (1.0, 0.0, 0.0)
    s = _vnorm(_vcross(t, up_ref))  # right axis; (s, t, u) right-handed
    u = _vnorm(_vcross(s, t))       # local up axis
    hw, hh = width * 0.5, height * 0.5

    def ring(p: Vec3) -> Tuple[Vec3, Vec3, Vec3, Vec3]:
        c0 = (p[0] - hw * s[0] - hh * u[0], p[1] - hw * s[1] - hh * u[1], p[2] - hw * s[2] - hh * u[2])
        c1 = (p[0] + hw * s[0] - hh * u[0], p[1] + hw * s[1] - hh * u[1], p[2] + hw * s[2] - hh * u[2])
        c2 = (p[0] + hw * s[0] + hh * u[0], p[1] + hw * s[1] + hh * u[1], p[2] + hw * s[2] + hh * u[2])
        c3 = (p[0] - hw * s[0] + hh * u[0], p[1] - hw * s[1] + hh * u[1], p[2] - hw * s[2] + hh * u[2])
        return c0, c1, c2, c3

    a0, a1, a2, a3 = ring(p0)
    b0, b1, b2, b3 = ring(p1)
    # 4 side faces (strictly outward normals verified by (-S)xT=-U, (-U)xT=+S, (+S)xT=+U, (+U)xT=-S)
    nb.quad_enu(mat, a1, a0, b0, b1, uv_box, ao_bot, ao_bot)  # bottom (-U)
    nb.quad_enu(mat, a2, a1, b1, b2, uv_box, ao_bot, ao_top)  # right (+S)
    nb.quad_enu(mat, a3, a2, b2, b3, uv_box, ao_top, ao_top)  # top (+U)
    nb.quad_enu(mat, a0, a3, b3, b0, uv_box, ao_bot, ao_top)  # left (-S)
    if caps:
        nb.quad_enu(mat, a0, a1, a2, a3, uv_box, ao_bot, ao_top)  # start cap (-T)
        nb.quad_enu(mat, b0, b3, b2, b1, uv_box, ao_bot, ao_top)  # end cap (+T)


def add_torus_ring(
    nb,
    mat: int,
    center: Vec3,
    axis_u: Vec3,
    axis_v: Vec3,
    major_r: float,
    minor_r: float,
    major_segs: int = 12,
    minor_segs: int = 6,
    ao_bot: float = 0.74,
    ao_top: float = 0.98,
) -> None:
    """Smooth-shaded hollow 3D torus ring lying in the (axis_u, axis_v) ENU plane."""
    u_ax = _vnorm(axis_u)
    w_ax = _vnorm(_vcross(u_ax, axis_v))
    v_ax = _vnorm(_vcross(w_ax, u_ax))

    resolved_mat, _ = nb._resolve_mat_tile(mat, None)
    bucket = nb.bucket(resolved_mat)

    grid_p: List[List[Vec3]] = []
    grid_n: List[List[Vec3]] = []
    for i in range(major_segs):
        ang_u = (2.0 * math.pi * i) / major_segs
        cu, su = math.cos(ang_u), math.sin(ang_u)
        r_dir = (cu * u_ax[0] + su * v_ax[0], cu * u_ax[1] + su * v_ax[1], cu * u_ax[2] + su * v_ax[2])
        row_p: List[Vec3] = []
        row_n: List[Vec3] = []
        for j in range(minor_segs):
            ang_v = (2.0 * math.pi * j) / minor_segs
            cv, sv = math.cos(ang_v), math.sin(ang_v)
            rad = major_r + minor_r * cv
            px = center[0] + rad * r_dir[0] + minor_r * sv * w_ax[0]
            py = center[1] + rad * r_dir[1] + minor_r * sv * w_ax[1]
            pz = center[2] + rad * r_dir[2] + minor_r * sv * w_ax[2]
            nx = cv * r_dir[0] + sv * w_ax[0]
            ny = cv * r_dir[1] + sv * w_ax[1]
            nz = cv * r_dir[2] + sv * w_ax[2]
            row_p.append(_enu_to_gltf(px, py, pz))
            row_n.append(_enu_to_gltf(nx, ny, nz))
        grid_p.append(row_p)
        grid_n.append(row_n)

    for i in range(major_segs):
        inext = (i + 1) % major_segs
        for j in range(minor_segs):
            jnext = (j + 1) % minor_segs
            p00, p10 = grid_p[i][j], grid_p[inext][j]
            p11, p01 = grid_p[inext][jnext], grid_p[i][jnext]
            n00, n10 = grid_n[i][j], grid_n[inext][j]
            n11, n01 = grid_n[inext][jnext], grid_n[i][jnext]
            ao0 = ao_bot + (ao_top - ao_bot) * max(0.0, min(1.0, 0.5 + 0.5 * n00[1]))
            ao1 = ao_bot + (ao_top - ao_bot) * max(0.0, min(1.0, 0.5 + 0.5 * n11[1]))
            bucket.add_smooth_quad(
                p00, p10, p11, p01,
                n00, n10, n11, n01,
                [(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)],
                [(ao0, ao0, ao0), (ao0, ao0, ao0), (ao1, ao1, ao1), (ao1, ao1, ao1)],
            )


# ---------------------------------------------------------------------------
# 2. Realistic Bicycles (Circular Wheels, Spokes, Tubular Frames, Hollow Baskets)
# ---------------------------------------------------------------------------
def add_detailed_bicycle_rack(
    nb,
    cx: float,
    cy: float,
    z_base: float,
    length: float,
    n_slots: int,
    yaw_rad: float,
    mats: dict,
) -> None:
    """Galvanized steel twin-rail ground base + hollow inverted-U tubular wheel hoops."""
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

    def wp(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, z_base + lz)

    # Twin longitudinal base steel rails
    for rail_y in (-0.22, 0.22):
        add_rect_beam(nb, mats["dark_steel"], wp(-length * 0.5, rail_y, 0.025), wp(length * 0.5, rail_y, 0.025), 0.055, 0.045)
    # Periodic cross tie bars + hollow inverted-U wheel hoops
    if n_slots < 2:
        return
    step = (length - 0.8) / (n_slots - 1)
    for i in range(n_slots):
        lx = -(length - 0.8) * 0.5 + i * step
        # Cross tie bar on ground
        add_rect_beam(nb, mats["dark_steel"], wp(lx, -0.24, 0.02), wp(lx, 0.24, 0.02), 0.04, 0.035)
        # Inverted-U tubular hoop (front leg -> angled top arch -> rear leg)
        p_f0 = wp(lx, 0.22, 0.03)
        p_f1 = wp(lx, 0.20, 0.36)
        p_t0 = wp(lx, 0.11, 0.43)
        p_t1 = wp(lx, -0.11, 0.43)
        p_r1 = wp(lx, -0.20, 0.36)
        p_r0 = wp(lx, -0.22, 0.03)
        r_tube = 0.017
        nb.add_limb(mats["blue_steel"], p_f0, p_f1, r_tube, r_tube, segs=4)
        nb.add_limb(mats["blue_steel"], p_f1, p_t0, r_tube, r_tube, segs=4)
        nb.add_limb(mats["blue_steel"], p_t0, p_t1, r_tube, r_tube, segs=4)
        nb.add_limb(mats["blue_steel"], p_t1, p_r1, r_tube, r_tube, segs=4)
        nb.add_limb(mats["blue_steel"], p_r1, p_r0, r_tube, r_tube, segs=4)


def add_realistic_bicycle_row(
    nb,
    x_start: float,
    y_start: float,
    count: int,
    step_x: float,
    step_y: float,
    yaw_rad: float,
    mats: dict,
    z_base: float = 0.03,
) -> None:
    """
    Photo-faithful parked student bicycles with:
      - Circular hollow rubber tires + inner alloy rims + axle hubs + radial spokes
      - Tubular diamond / step-through frames (front fork, head/top/down/seat tubes, rear stays)
      - Crankset, kickstand, mudguards, contoured saddle, swept tubular handlebars with grips
      - Hollow open-top front wire basket & occasional rear luggage rack
    """
    frame_palette = [
        mats["blue_steel"],
        mats["white_alu"],
        mats["crimson"],
        mats["dark_steel"],
        mats["green_rail"],
        mats["yellow_pole"],
    ]
    tire_mat = mats["dark_steel"]
    rim_mat = mats["stainless"] if "stainless" in mats else mats["white_alu"]

    for idx in range(count):
        bx = x_start + idx * step_x
        by = y_start + idx * step_y
        # Natural organic parking variation (subtle yaw & slight kickstand lean)
        yaw_var = yaw_rad + (((idx * 13) % 7) - 3) * 0.045
        lean = (((idx * 5) % 3) - 1) * 0.045
        steer = (((idx * 11) % 7) - 3) * 0.085
        fmat = frame_palette[idx % len(frame_palette)]
        is_commuter = (idx % 3 != 0)  # 2/3 commuter w/ basket, 1/3 mountain bike

        cs, sn = math.cos(yaw_var), math.sin(yaw_var)
        cl, sl = math.cos(lean), math.sin(lean)

        def bp(lx: float, ly: float, lz: float) -> Vec3:
            # Apply slight kickstand lean around ground contact line (lx rotates with lz)
            rx = lx * cl - lz * sl
            rz = lx * sl + lz * cl
            return (bx + rx * cs - ly * sn, by + rx * sn + ly * cs, z_base + rz)

        # Front steering sub-transform around head axis at (0, +0.40)
        cst, sst = math.cos(steer), math.sin(steer)

        def fp(lx: float, ly_rel: float, lz: float) -> Vec3:
            sx = lx * cst - ly_rel * sst
            sy = 0.40 + lx * sst + ly_rel * cst
            return bp(sx, sy, lz)

        wheel_r = 0.305
        # 1. Rear wheel (ly = -0.52) & Front wheel (steered around ly = +0.40 -> hub at ly_rel = +0.12)
        rear_c = bp(0.0, -0.52, wheel_r)
        rear_u = _vsub(bp(0.0, -0.52 + 1.0, wheel_r), rear_c)
        rear_v = _vsub(bp(0.0, -0.52, wheel_r + 1.0), rear_c)
        add_torus_ring(nb, tire_mat, rear_c, rear_u, rear_v, wheel_r - 0.022, 0.024, major_segs=10, minor_segs=4)
        add_torus_ring(nb, rim_mat, rear_c, rear_u, rear_v, wheel_r - 0.044, 0.011, major_segs=10, minor_segs=3)
        nb.add_limb(rim_mat, bp(-0.048, -0.52, wheel_r), bp(0.048, -0.52, wheel_r), 0.018, 0.018, segs=4)

        front_c = fp(0.0, 0.12, wheel_r)
        front_u = _vsub(fp(0.0, 1.12, wheel_r), front_c)
        front_v = _vsub(fp(0.0, 0.12, wheel_r + 1.0), front_c)
        add_torus_ring(nb, tire_mat, front_c, front_u, front_v, wheel_r - 0.022, 0.024, major_segs=10, minor_segs=4)
        add_torus_ring(nb, rim_mat, front_c, front_u, front_v, wheel_r - 0.044, 0.011, major_segs=10, minor_segs=3)
        nb.add_limb(rim_mat, fp(-0.044, 0.12, wheel_r), fp(0.044, 0.12, wheel_r), 0.016, 0.016, segs=4)

        # Crisp radial spokes (4 per wheel -> 2 full diameters)
        for sp_i in range(2):
            sa = (math.pi * sp_i) / 2.0 + 0.35
            csa, ssa = math.cos(sa), math.sin(sa)
            sr = wheel_r - 0.045
            nb.add_limb(
                rim_mat,
                bp(0.0, -0.52 - sr * csa, wheel_r - sr * ssa),
                bp(0.0, -0.52 + sr * csa, wheel_r + sr * ssa),
                0.005, 0.005, segs=3,
            )
            nb.add_limb(
                rim_mat,
                fp(0.0, 0.12 - sr * csa, wheel_r - sr * ssa),
                fp(0.0, 0.12 + sr * csa, wheel_r + sr * ssa),
                0.005, 0.005, segs=3,
            )

        # 2. Tubular Frame Key Nodes
        bb = bp(0.0, -0.06, 0.28)       # bottom bracket
        seat_cl = bp(0.0, -0.22, 0.72)  # seat cluster
        head_top = bp(0.0, 0.34, 0.77)  # head tube top
        head_bot = bp(0.0, 0.39, 0.62)  # head tube bottom
        r_frame = 0.016

        nb.add_limb(fmat, bb, seat_cl, r_frame, r_frame, segs=4)       # seat tube
        nb.add_limb(fmat, bb, head_bot, r_frame * 1.1, r_frame, segs=4)  # down tube
        nb.add_limb(fmat, head_bot, head_top, r_frame * 1.15, r_frame * 1.15, segs=4)  # head tube
        if is_commuter:
            # Low step-through commuter frame bar
            mid_low = bp(0.0, 0.06, 0.50)
            nb.add_limb(fmat, bp(0.0, -0.15, 0.52), mid_low, r_frame * 0.9, r_frame * 0.9, segs=4)
            nb.add_limb(fmat, mid_low, head_top, r_frame * 0.9, r_frame * 0.9, segs=4)
        else:
            # Classic mountain bike top tube
            nb.add_limb(fmat, seat_cl, head_top, r_frame * 0.95, r_frame * 0.95, segs=4)

        # Twin rear chainstays & seatstays
        for side_x in (-0.048, 0.048):
            r_drop = bp(side_x, -0.52, wheel_r)
            nb.add_limb(fmat, bb, r_drop, 0.011, 0.009, segs=4)
            nb.add_limb(fmat, seat_cl, r_drop, 0.010, 0.009, segs=4)

        # Twin front fork blades (steered)
        fork_crown = fp(0.0, 0.0, 0.61)
        for side_x in (-0.044, 0.044):
            nb.add_limb(fmat, fork_crown, fp(side_x, 0.12, wheel_r), 0.013, 0.010, segs=4)

        # 3. Crank chainring, pedals & kickstand
        nb.add_limb(tire_mat, bp(-0.07, -0.06, 0.28), bp(0.07, -0.06, 0.28), 0.014, 0.014, segs=4)
        nb.add_limb(rim_mat, bp(0.05, -0.06, 0.28), bp(0.06, 0.04, 0.17), 0.009, 0.008, segs=3)
        add_rect_beam(nb, tire_mat, bp(0.05, 0.04, 0.17), bp(0.14, 0.04, 0.17), 0.06, 0.022)
        nb.add_limb(tire_mat, bp(-0.04, -0.14, 0.27), bp(-0.18, -0.22, 0.01), 0.009, 0.007, segs=3)  # kickstand

        # 4. Seatpost & Tapered Saddle
        seat_top = bp(0.0, -0.25, 0.87)
        nb.add_limb(rim_mat, seat_cl, seat_top, 0.012, 0.012, segs=4)
        add_rect_beam(nb, tire_mat, bp(0.0, -0.35, 0.88), bp(0.0, -0.22, 0.89), 0.15, 0.045)
        add_rect_beam(nb, tire_mat, bp(0.0, -0.22, 0.89), bp(0.0, -0.11, 0.895), 0.075, 0.038)

        # 5. Steered Stem, Swept Handlebar & Rubber Grips
        stem_top = fp(0.0, -0.04, 0.94)
        nb.add_limb(rim_mat, head_top, stem_top, 0.013, 0.012, segs=4)
        for side_x in (-1.0, 1.0):
            hb_mid = fp(side_x * 0.14, -0.05, 0.96)
            hb_end = fp(side_x * 0.27, -0.11, 0.95)
            nb.add_limb(rim_mat, stem_top, hb_mid, 0.011, 0.011, segs=4)
            nb.add_limb(tire_mat, hb_mid, hb_end, 0.015, 0.015, segs=4)  # rubber grip

        # 6. Rear Fender & Optional Hollow Front Wire Basket + Rear Rack
        if is_commuter:
            # Curved rear fender (2 segments)
            for fa0, fa1 in ((0.45, 1.32), (1.32, 2.20)):
                r_f = wheel_r + 0.025
                add_rect_beam(
                    nb, fmat,
                    bp(0.0, -0.52 + r_f * math.cos(fa0), wheel_r + r_f * math.sin(fa0)),
                    bp(0.0, -0.52 + r_f * math.cos(fa1), wheel_r + r_f * math.sin(fa1)),
                    0.055, 0.012, caps=False,
                )
            # Hollow open-top front wire basket mounted in front of head tube (NO solid black cube!)
            b_z0, b_z1 = 0.65, 0.87
            b_y0, b_y1 = 0.04, 0.28
            bw_b, bw_t = 0.135, 0.165
            # Bottom tray plate
            nb.quad_enu(
                tire_mat,
                fp(-bw_b, b_y0, b_z0), fp(bw_b, b_y0, b_z0),
                fp(bw_b, b_y1, b_z0), fp(-bw_b, b_y1, b_z0),
                double_sided=True,
            )
            # 4 sloped corner wire posts + top wire rim loop
            corners_b = [fp(-bw_b, b_y0, b_z0), fp(bw_b, b_y0, b_z0), fp(bw_b, b_y1, b_z0), fp(-bw_b, b_y1, b_z0)]
            corners_t = [fp(-bw_t, b_y0 - 0.01, b_z1), fp(bw_t, b_y0 - 0.01, b_z1), fp(bw_t, b_y1 + 0.02, b_z1), fp(-bw_t, b_y1 + 0.02, b_z1)]
            for k in range(4):
                kn = (k + 1) % 4
                nb.add_limb(tire_mat, corners_b[k], corners_t[k], 0.007, 0.007, segs=3)
                nb.add_limb(tire_mat, corners_t[k], corners_t[kn], 0.008, 0.008, segs=3)
            # Support stay from fork crown to basket bottom
            nb.add_limb(tire_mat, fork_crown, fp(0.0, 0.16, b_z0), 0.008, 0.008, segs=3)
            # Rear luggage rack on every second commuter bike
            if idx % 2 == 0:
                for sx in (-0.075, 0.075):
                    nb.add_limb(tire_mat, bp(sx, -0.34, 0.67), bp(sx, -0.74, 0.67), 0.008, 0.008, segs=3)
                    nb.add_limb(tire_mat, bp(sx, -0.52, wheel_r), bp(sx, -0.70, 0.67), 0.007, 0.007, segs=3)
                nb.add_limb(tire_mat, bp(-0.075, -0.74, 0.67), bp(0.075, -0.74, 0.67), 0.008, 0.008, segs=3)


# ---------------------------------------------------------------------------
# 3. Hollow Molded Planter Boxes & Foliage Tufts (Eliminating All Red Boxes)
# ---------------------------------------------------------------------------
def add_planter_foliage(
    nb,
    cx: float,
    cy: float,
    z_soil: float,
    span_x: float,
    span_y: float,
    yaw_rad: float,
    mats: dict,
    plant_kind: str = "rose",
    height: float = 0.42,
    seed: int = 0,
) -> None:
    """
    Populates a planter or hedge bed with lush organic foliage & blossoms:
      - Enhanced mode: crossed alpha-cutout botanical foliage cards (spherical normals)
      - Classic mode: sculpted multi-lobe organic leaf clusters + delicate blossom specks
    """
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)
    n_tufts = max(2, min(8, int(round(max(span_x, 0.45) / 0.42))))

    def pt(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, z_soil + lz)

    if not getattr(nb, "classic_mode", False) and "foliage_rose" in mats and "foliage_broad" in mats:
        fmat = mats["foliage_rose"] if plant_kind == "rose" else mats["foliage_broad"]
        b = nb.bucket(fmat)
        for ti in range(n_tufts):
            u_t = (ti + 0.5) / n_tufts - 0.5
            jx = (((seed + ti * 17) % 11) - 5) * 0.012
            jy = (((seed + ti * 29) % 11) - 5) * 0.010
            kc = pt(u_t * (span_x * 0.82) + jx, jy, height * 0.52)
            rad_xy = min(0.32, max(0.18, span_y * 0.72))
            rad_z = height * 0.56
            cc_gltf = _enu_to_gltf(kc[0], kc[1], kc[2] - height * 0.08)
            for ci in range(3):
                ang = yaw_rad + (math.pi * ci) / 3.0 + ((seed + ti * 7 + ci * 13) % 9) * 0.11
                tilt = (((seed + ci * 19 + ti * 5) % 7) - 3) * 0.08
                ca, sa = math.cos(ang), math.sin(ang)
                ct, st = math.cos(tilt), math.sin(tilt)
                rx_e, rx_n, rx_z = ca * rad_xy, sa * rad_xy, 0.0
                ry_e, ry_n, ry_z = -sa * st * rad_z, ca * st * rad_z, ct * rad_z
                e0 = (kc[0] - rx_e - ry_e, kc[1] - rx_n - ry_n, kc[2] - rx_z - ry_z)
                e1 = (kc[0] + rx_e - ry_e, kc[1] + rx_n - ry_n, kc[2] + rx_z - ry_z)
                e2 = (kc[0] + rx_e + ry_e, kc[1] + rx_n + ry_n, kc[2] + rx_z + ry_z)
                e3 = (kc[0] - rx_e + ry_e, kc[1] - rx_n + ry_n, kc[2] - rx_z + ry_z)
                pts = [_enu_to_gltf(*e0), _enu_to_gltf(*e1), _enu_to_gltf(*e2), _enu_to_gltf(*e3)]
                norms, cols = [], []
                for p in pts:
                    dx, dy, dz = p[0] - cc_gltf[0], (p[1] - cc_gltf[1]) * 1.2 + 0.35, p[2] - cc_gltf[2]
                    l = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
                    norms.append((dx / l, dy / l, dz / l))
                    ao_v = max(0.72, min(1.0, 0.86 + 0.14 * (dy / l)))
                    cols.append((ao_v, ao_v, ao_v))
                b.add_smooth_quad(
                    pts[0], pts[1], pts[2], pts[3],
                    norms[0], norms[1], norms[2], norms[3],
                    [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)],
                    cols,
                )
        return

    # Classic mode: lush multi-cluster organic green leaf tufts + soft blossom accents
    leaf_m = mats["leaf_magnolia"] if plant_kind == "hedge" else mats["leaf"]
    n_cls = max(2, min(4, n_tufts))
    for ti in range(n_cls):
        u_t = (ti + 0.5) / n_cls - 0.5
        jx = (((seed + ti * 13) % 9) - 4) * 0.014
        jy = (((seed + ti * 23) % 9) - 4) * 0.012
        r_base = min(0.24, max(0.13, span_y * 0.55))
        p_c = pt(u_t * (span_x * 0.80) + jx, jy, height * 0.42)
        nb.add_sphere(leaf_m, p_c[0], p_c[1], p_c[2], r_base * 1.18, height * 0.46, r_base, segs=6, rings=3, ao=0.92)
        if plant_kind == "rose":
            bf_mat = mats["flower_rose"] if (ti + seed) % 3 != 0 else mats["flower_white"]
            p_fl = pt(u_t * (span_x * 0.80) + jx * 1.4, jy + 0.04, height * 0.78)
            nb.add_sphere(bf_mat, p_fl[0], p_fl[1], p_fl[2], 0.065, 0.055, 0.065, segs=5, rings=2, ao=1.0)


def add_planter_box(
    nb,
    cx: float,
    cy: float,
    z_bot: float,
    length: float,
    width: float,
    height: float,
    yaw_rad: float,
    mats: dict,
    uv_consts: dict,
    style: str = "stone",
    plant_kind: str = "rose",
    plant_h: float = 0.40,
    seed: int = 0,
) -> None:
    """
    Hollow architectural planter trough with recessed base kick, 4 thick walls,
    overhanging beveled coping rim, dark soil bed, and realistic plant foliage.
    """
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

    def rot(lx: float, ly: float) -> Vec2:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs)

    if style == "terracotta":
        body_mat, body_uv = mats["surf"], uv_consts["UV_TERRACOTTA_BRICK"]
        rim_mat, rim_uv = mats["surf"], uv_consts["UV_PLAZA_TILE"]
    elif style == "qingzhuan":
        body_mat, body_uv = mats["surf"], uv_consts["UV_QINGZHUAN"]
        rim_mat, rim_uv = mats["surf"], uv_consts["UV_PLAZA_TILE"]
    else:  # "stone" (light granite / carved pale stone)
        body_mat, body_uv = mats["surf"], uv_consts["UV_PLAZA_TILE"]
        rim_mat, rim_uv = mats["gates"], uv_consts["UV_MARBLE"]

    wall_t = min(0.055, width * 0.18)
    rim_h = min(0.055, height * 0.22)
    base_h = min(0.045, height * 0.16)
    body_h = max(0.08, height - rim_h - base_h)

    # 1. Slightly inset shadow base plinth
    nb.add_box(body_mat, cx, cy, z_bot, max(0.12, length - 0.05), max(0.10, width - 0.04), base_h, yaw_rad, body_uv, ao_bot=0.72, ao_top=0.86)

    # 2. Hollow 4-wall planter trough body
    z_body = z_bot + base_h
    hl, hw = length * 0.5, width * 0.5
    # Front & Back long walls
    for sy in (-hw + wall_t * 0.5, hw - wall_t * 0.5):
        p = rot(0.0, sy)
        nb.add_box(body_mat, p[0], p[1], z_body, length, wall_t, body_h, yaw_rad, body_uv, ao_bot=0.78, ao_top=0.94)
    # Left & Right end walls
    inner_w = max(0.04, width - 2.0 * wall_t)
    for sx in (-hl + wall_t * 0.5, hl - wall_t * 0.5):
        p = rot(sx, 0.0)
        nb.add_box(body_mat, p[0], p[1], z_body, wall_t, inner_w, body_h, yaw_rad, body_uv, ao_bot=0.78, ao_top=0.94)

    # 3. Projecting molded coping rim (4 hollow rim bars)
    z_rim = z_body + body_h
    ov = 0.025
    rim_t = wall_t + ov
    rl, rw = length + ov * 2.0, width + ov * 2.0
    for sy in (-(rw * 0.5 - rim_t * 0.5), rw * 0.5 - rim_t * 0.5):
        p = rot(0.0, sy)
        nb.add_box(rim_mat, p[0], p[1], z_rim, rl, rim_t, rim_h, yaw_rad, rim_uv, ao_bot=0.88, ao_top=1.0)
    for sx in (-(rl * 0.5 - rim_t * 0.5), rl * 0.5 - rim_t * 0.5):
        p = rot(sx, 0.0)
        nb.add_box(rim_mat, p[0], p[1], z_rim, rim_t, max(0.04, rw - 2.0 * rim_t), rim_h, yaw_rad, rim_uv, ao_bot=0.88, ao_top=1.0)

    # 4. Recessed dark soil bed inside the hollow trough
    z_soil = z_bot + height - 0.05
    il, iw = max(0.06, length - 2.0 * wall_t), max(0.05, width - 2.0 * wall_t)
    s0, s1 = rot(-il * 0.5, -iw * 0.5), rot(il * 0.5, -iw * 0.5)
    s2, s3 = rot(il * 0.5, iw * 0.5), rot(-il * 0.5, iw * 0.5)
    nb.quad_enu(
        mats["bare_soil"],
        (s0[0], s0[1], z_soil), (s1[0], s1[1], z_soil),
        (s2[0], s2[1], z_soil), (s3[0], s3[1], z_soil),
        (0.0, 0.0, 1.0, 1.0), 0.72, 0.78,
    )

    # 5. Organic plant foliage rising from soil
    if plant_h > 0.02:
        add_planter_foliage(nb, cx, cy, z_soil, il, iw, yaw_rad, mats, plant_kind=plant_kind, height=plant_h, seed=seed)


def add_hollow_round_planter(
    nb,
    cx: float,
    cy: float,
    z_bot: float,
    r_out: float,
    height: float,
    mats: dict,
    uv_consts: dict,
    segs: int = 16,
    plant_kind: str = "rose",
    plant_h: float = 0.55,
) -> None:
    """Hollow circular masonry flower bed with granite coping ring, soil bed, and layered flowers."""
    wall_t = min(0.24, r_out * 0.18)
    r_in = max(0.15, r_out - wall_t)
    cap_h = 0.065
    z_wall_top = z_bot + height - cap_h
    z_top = z_bot + height
    z_soil = z_top - 0.07

    inner_ring: List[Vec2] = []
    for i in range(segs):
        a0 = (2.0 * math.pi * i) / segs
        a1 = (2.0 * math.pi * (i + 1)) / segs
        ca0, sa0, ca1, sa1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        o0 = (cx + r_out * ca0, cy + r_out * sa0)
        o1 = (cx + r_out * ca1, cy + r_out * sa1)
        i0 = (cx + r_in * ca0, cy + r_in * sa0)
        i1 = (cx + r_in * ca1, cy + r_in * sa1)
        co0 = (cx + (r_out + 0.03) * ca0, cy + (r_out + 0.03) * sa0)
        co1 = (cx + (r_out + 0.03) * ca1, cy + (r_out + 0.03) * sa1)
        ci0 = (cx + (r_in - 0.02) * ca0, cy + (r_in - 0.02) * sa0)
        ci1 = (cx + (r_in - 0.02) * ca1, cy + (r_in - 0.02) * sa1)
        inner_ring.append(i0)

        # Brick outer & inner walls
        nb.quad_enu(mats["surf"], (o0[0], o0[1], z_bot), (o1[0], o1[1], z_bot), (o1[0], o1[1], z_wall_top), (o0[0], o0[1], z_wall_top), uv_consts["UV_QINGZHUAN"], 0.74, 0.92)
        nb.quad_enu(mats["surf"], (i1[0], i1[1], z_soil - 0.04), (i0[0], i0[1], z_soil - 0.04), (i0[0], i0[1], z_wall_top), (i1[0], i1[1], z_wall_top), uv_consts["UV_QINGZHUAN"], 0.68, 0.86)
        # Overhanging stone coping rim
        nb.quad_enu(mats["surf"], (co0[0], co0[1], z_wall_top), (co1[0], co1[1], z_wall_top), (co1[0], co1[1], z_top), (co0[0], co0[1], z_top), uv_consts["UV_PLAZA_TILE"], 0.86, 0.98)
        nb.quad_enu(mats["surf"], (ci1[0], ci1[1], z_wall_top), (ci0[0], ci0[1], z_wall_top), (ci0[0], ci0[1], z_top), (ci1[0], ci1[1], z_top), uv_consts["UV_PLAZA_TILE"], 0.84, 0.96)
        nb.quad_enu(mats["surf"], (ci0[0], ci0[1], z_top), (co0[0], co0[1], z_top), (co1[0], co1[1], z_top), (ci1[0], ci1[1], z_top), uv_consts["UV_PLAZA_TILE"], 0.94, 1.0)

    nb.add_polygon_patch(inner_ring, z_soil, mats["bare_soil"], (0.0, 0.0, 1.0, 1.0), ao=0.78)
    if plant_h > 0.02:
        # Center bush + ring of flowers inside the circular bed
        add_planter_foliage(nb, cx, cy, z_soil, r_in * 0.9, r_in * 0.9, 0.0, mats, plant_kind=plant_kind, height=plant_h * 1.15, seed=7)
        for k in range(6):
            ang = (2.0 * math.pi * k) / 6.0
            rx = cx + r_in * 0.56 * math.cos(ang)
            ry = cy + r_in * 0.56 * math.sin(ang)
            add_planter_foliage(nb, rx, ry, z_soil, 0.55, 0.45, ang, mats, plant_kind=plant_kind, height=plant_h * 0.82, seed=20 + k)


# ---------------------------------------------------------------------------
# 4. Stone Curbs, Brick Retaining Walls & Granite Staircases
# ---------------------------------------------------------------------------
def add_stone_curb_polyline(
    nb,
    pts: Sequence[Vec2],
    z_bot: float,
    height: float,
    width: float,
    mats: dict,
    uv_consts: dict,
    wall_uv_key: str = "UV_QINGZHUAN",
    cap_uv_key: str = "UV_PLAZA_TILE",
    closed: bool = False,
) -> None:
    """Continuous masonry curb / low retaining wall with overhanging granite coping & clean vertex caps."""
    n = len(pts)
    if n < 2:
        return
    cap_h = min(0.065, height * 0.34)
    wall_h = max(0.03, height - cap_h)
    w_uv = uv_consts[wall_uv_key]
    c_uv = uv_consts[cap_uv_key]
    cap_ov = 0.03

    seg_count = n if closed else (n - 1)
    for i in range(seg_count):
        a = pts[i]
        b = pts[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 0.05:
            continue
        yaw = math.atan2(dy, dx)
        mx, my = (a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5
        nb.add_box(mats["surf"], mx, my, z_bot, L + width * 0.25, width, wall_h, yaw, w_uv, ao_bot=0.72, ao_top=0.92)
        nb.add_box(
            mats["surf"], mx, my, z_bot + wall_h,
            L + width * 0.35 + cap_ov * 2.0, width + cap_ov * 2.0, cap_h, yaw,
            c_uv, ao_bot=0.88, ao_top=1.0,
        )

    # Corner stone cap piers at polyline joints so turns never leave wedges
    corner_range = range(n) if closed else range(n)
    for i in corner_range:
        px, py = pts[i]
        nb.add_box(mats["surf"], px, py, z_bot, width + 0.02, width + 0.02, wall_h, 0.0, w_uv, ao_bot=0.72, ao_top=0.92)
        nb.add_box(mats["surf"], px, py, z_bot + wall_h, width + cap_ov * 2.0 + 0.02, width + cap_ov * 2.0 + 0.02, cap_h + 0.004, 0.0, c_uv, ao_bot=0.88, ao_top=1.0)


def add_granite_stairs(
    nb,
    cx: float,
    cy: float,
    z_bot: float,
    z_top: float,
    width: float,
    depth: float,
    yaw_face_rad: float,
    n_steps: int,
    mats: dict,
    uv_consts: dict,
    cheek_walls: bool = True,
) -> None:
    """
    Granite outdoor stairs centered on the upper edge (cx, cy), descending toward +ly (rotated by yaw_face_rad).
    Step 0 is highest (touching upper edge at ly=0), descending outward to ly=+depth.
    """
    total_h = z_top - z_bot
    if total_h <= 0.02 or n_steps < 1:
        return
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def rot(lx: float, ly: float) -> Vec2:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs)

    step_d = depth / n_steps
    for si in range(n_steps):
        frac = (n_steps - si) / n_steps
        h_s = total_h * frac
        ly_mid = (si + 0.5) * step_d
        p = rot(0.0, ly_mid)
        # Step riser body + crisp slightly projecting granite tread slab
        riser_h = max(0.02, h_s - 0.045)
        nb.add_box(mats["surf"], p[0], p[1], z_bot, width, step_d + 0.02, riser_h, yaw_face_rad, uv_consts["UV_QINGZHUAN"], ao_bot=0.74, ao_top=0.90)
        p_tr = rot(0.0, ly_mid + 0.015)
        nb.add_box(mats["surf"], p_tr[0], p_tr[1], z_bot + riser_h, width + 0.02, step_d + 0.04, 0.045, yaw_face_rad, uv_consts["UV_PLAZA_TILE"], ao_bot=0.90, ao_top=1.0)

    if cheek_walls:
        cw_w = 0.24
        for side_s in (-1.0, 1.0):
            cp = rot(side_s * (width * 0.5 + cw_w * 0.5), depth * 0.5)
            nb.add_box(mats["surf"], cp[0], cp[1], z_bot, cw_w, depth + 0.06, total_h, yaw_face_rad, uv_consts["UV_QINGZHUAN"], ao_bot=0.74, ao_top=0.92)
            nb.add_box(mats["surf"], cp[0], cp[1], z_top, cw_w + 0.05, depth + 0.12, 0.06, yaw_face_rad, uv_consts["UV_PLAZA_TILE"], ao_bot=0.90, ao_top=1.0)


def add_accessible_ramp_wedge(
    nb,
    cx: float,
    cy: float,
    z_bot: float,
    z_top: float,
    width: float,
    depth: float,
    yaw_face_rad: float,
    mats: dict,
    uv_consts: dict,
) -> None:
    """Smooth granite/concrete accessible ramp descending from ly=0 (z_top) to ly=+depth (z_bot)."""
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def wp(lx: float, ly: float, z: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, z)

    hw = width * 0.5
    # Sloped top surface
    nb.quad_enu(
        mats["surf"],
        wp(-hw, 0.0, z_top), wp(hw, 0.0, z_top),
        wp(hw, depth, z_bot + 0.015), wp(-hw, depth, z_bot + 0.015),
        uv_consts["UV_PLAZA_TILE"], 0.90, 0.98,
    )
    # Left & right triangular vertical cheeks
    nb.tri_enu(
        mats["surf"],
        wp(-hw, 0.0, z_bot), wp(-hw, depth, z_bot), wp(-hw, 0.0, z_top),
        (0.1, 0.9), (0.9, 0.9), (0.1, 0.1), 0.76, 0.78, 0.92,
    )
    nb.tri_enu(
        mats["surf"],
        wp(hw, depth, z_bot), wp(hw, 0.0, z_bot), wp(hw, 0.0, z_top),
        (0.1, 0.9), (0.9, 0.9), (0.9, 0.1), 0.76, 0.78, 0.92,
    )
    # Low granite curb rails flanking the ramp
    for sx in (-hw - 0.09, hw + 0.09):
        add_rect_beam(nb, mats["surf"], wp(sx, 0.0, z_top + 0.05), wp(sx, depth, z_bot + 0.06), 0.16, 0.10, uv_consts["UV_PLAZA_TILE"])


# ---------------------------------------------------------------------------
# 5. Full-Stone Curved Ramp Railings & Structure (Scheme A for W-R1)
# ---------------------------------------------------------------------------
def add_stone_curved_ramp(
    nb,
    ramp_pts: List[Vec3],
    half_w: float,
    mats: dict,
    uv_consts: dict,
) -> None:
    """
    Rebuilds West Campus W-R1 curved ramp with Scheme A Full-Stone Architectural Railings:
      - Solid curved asphalt deck + thick beveled box-girder concrete/stone soffit
      - Continuous carved stone side fascia beam + lower stone plinth curb
      - Beveled square stone newel posts (望柱) with pyramidal granite caps every 2 segments
      - Stone balustrade spindles + sub-rail between every pair of newel posts
      - Continuous smooth thick curved granite handrail coping beam
      - Hollow molded stone planter troughs with soil & botanical flowers on outer brackets
      - Cylindrical structural piers with beveled granite pedestal bases & cap beams
    """
    segs_r = len(ramp_pts) - 1
    stone_mat, stone_uv = mats["surf"], uv_consts["UV_PLAZA_TILE"]
    marble_mat, marble_uv = mats["gates"], uv_consts["UV_MARBLE"]
    brick_uv = uv_consts["UV_QINGZHUAN"]

    # Compute smooth per-vertex horizontal normals along the Bezier curve for miter-clean stone joints
    v_normals: List[Vec2] = []
    v_tangents: List[Vec2] = []
    for k in range(segs_r + 1):
        p_prev = ramp_pts[max(0, k - 1)]
        p_next = ramp_pts[min(segs_r, k + 1)]
        dx, dy = p_next[0] - p_prev[0], p_next[1] - p_prev[1]
        ll = max(math.hypot(dx, dy), 1e-4)
        tx, ty = dx / ll, dy / ll
        v_tangents.append((tx, ty))
        v_normals.append((ty, -tx))  # right-hand outward normal

    rail_t = 0.24   # solid stone railing thickness
    half_in = half_w - 0.02
    half_out = half_w + rail_t

    for k in range(segs_r):
        a0, a1 = ramp_pts[k], ramp_pts[k + 1]
        n0x, n0y = v_normals[k]
        n1x, n1y = v_normals[k + 1]

        # 1. Ramp deck top surface (asphalt non-slip) & solid stone box-girder underside
        l0 = (a0[0] - n0x * half_in, a0[1] - n0y * half_in, a0[2])
        r0 = (a0[0] + n0x * half_in, a0[1] + n0y * half_in, a0[2])
        l1 = (a1[0] - n1x * half_in, a1[1] - n1y * half_in, a1[2])
        r1 = (a1[0] + n1x * half_in, a1[1] + n1y * half_in, a1[2])
        nb.quad_enu(mats["surf"], l0, r0, r1, l1, uv_consts["UV_ASPHALT"], 0.94, 0.98)

        # Box-girder soffit underside (0.36m deep)
        sof = 0.36
        sl0 = (a0[0] - n0x * (half_out - 0.06), a0[1] - n0y * (half_out - 0.06), max(0.0, a0[2] - sof))
        sr0 = (a0[0] + n0x * (half_out - 0.06), a0[1] + n0y * (half_out - 0.06), max(0.0, a0[2] - sof))
        sl1 = (a1[0] - n1x * (half_out - 0.06), a1[1] - n1y * (half_out - 0.06), max(0.0, a1[2] - sof))
        sr1 = (a1[0] + n1x * (half_out - 0.06), a1[1] + n1y * (half_out - 0.06), max(0.0, a1[2] - sof))
        nb.quad_enu(stone_mat, sr0, sl0, sl1, sr1, stone_uv, 0.68, 0.72)

        # 2. Both Left (-1) and Right (+1) Full-Stone Railings
        for sgn in (-1.0, 1.0):
            # Centerline of railing along this side
            r_mid = half_w + rail_t * 0.5
            m0 = (a0[0] + sgn * n0x * r_mid, a0[1] + sgn * n0y * r_mid, a0[2])
            m1 = (a1[0] + sgn * n1x * r_mid, a1[1] + sgn * n1y * r_mid, a1[2])

            # (a) Thick solid curved outer stone fascia beam + lower stone plinth curb (z - 0.36 .. z + 0.32)
            z_bot0, z_bot1 = max(0.0, a0[2] - sof), max(0.0, a1[2] - sof)
            z_curb0, z_curb1 = a0[2] + 0.32, a1[2] + 0.32
            p0_in = (a0[0] + sgn * n0x * half_in, a0[1] + sgn * n0y * half_in)
            p1_in = (a1[0] + sgn * n1x * half_in, a1[1] + sgn * n1y * half_in)
            p0_out = (a0[0] + sgn * n0x * half_out, a0[1] + sgn * n0y * half_out)
            p1_out = (a1[0] + sgn * n1x * half_out, a1[1] + sgn * n1y * half_out)

            if sgn > 0:
                # Right side: outward is +n
                nb.quad_enu(stone_mat, (p0_out[0], p0_out[1], z_bot0), (p1_out[0], p1_out[1], z_bot1), (p1_out[0], p1_out[1], z_curb1), (p0_out[0], p0_out[1], z_curb0), stone_uv, 0.78, 0.96)
                nb.quad_enu(stone_mat, (p1_in[0], p1_in[1], a1[2]), (p0_in[0], p0_in[1], a0[2]), (p0_in[0], p0_in[1], z_curb0), (p1_in[0], p1_in[1], z_curb1), stone_uv, 0.80, 0.96)
                nb.quad_enu(marble_mat, (p0_in[0], p0_in[1], z_curb0), (p0_out[0], p0_out[1], z_curb0), (p1_out[0], p1_out[1], z_curb1), (p1_in[0], p1_in[1], z_curb1), marble_uv, 0.92, 1.0)
            else:
                # Left side: outward is -n
                nb.quad_enu(stone_mat, (p1_out[0], p1_out[1], z_bot1), (p0_out[0], p0_out[1], z_bot0), (p0_out[0], p0_out[1], z_curb0), (p1_out[0], p1_out[1], z_curb1), stone_uv, 0.78, 0.96)
                nb.quad_enu(stone_mat, (p0_in[0], p0_in[1], a0[2]), (p1_in[0], p1_in[1], a1[2]), (p1_in[0], p1_in[1], z_curb1), (p0_in[0], p0_in[1], z_curb0), stone_uv, 0.80, 0.96)
                nb.quad_enu(marble_mat, (p0_out[0], p0_out[1], z_curb0), (p0_in[0], p0_in[1], z_curb0), (p1_in[0], p1_in[1], z_curb1), (p1_out[0], p1_out[1], z_curb1), marble_uv, 0.92, 1.0)

            # (b) Continuous curved stone sub-rail & thick overhanging marble handrail coping (z+0.96..z+1.16)
            add_rect_beam(
                nb, stone_mat,
                (m0[0], m0[1], a0[2] + 0.96), (m1[0], m1[1], a1[2] + 0.96),
                rail_t * 0.78, 0.08, stone_uv, ao_bot=0.86, ao_top=0.96, caps=False,
            )
            add_rect_beam(
                nb, marble_mat,
                (m0[0], m0[1], a0[2] + 1.07), (m1[0], m1[1], a1[2] + 1.07),
                rail_t + 0.06, 0.12, marble_uv, ao_bot=0.92, ao_top=1.0, caps=(k == 0 or k == segs_r - 1),
            )

            # (c) Vertical carved stone balustrade spindles (proportionally spaced between carved newel posts)
            seg_yaw = math.atan2(a1[1] - a0[1], a1[0] - a0[0])
            for frac in (0.34, 0.68):
                bx = m0[0] + (m1[0] - m0[0]) * frac
                by = m0[1] + (m1[1] - m0[1]) * frac
                bz = a0[2] + (a1[2] - a0[2]) * frac
                # Tapered carved marble baluster shaft + stone base collar
                nb.add_box(stone_mat, bx, by, bz + 0.32, 0.125, 0.125, 0.07, seg_yaw, stone_uv, ao_bot=0.80, ao_top=0.94)
                nb.add_box(marble_mat, bx, by, bz + 0.39, 0.09, 0.09, 0.56, seg_yaw, marble_uv, ao_bot=0.86, ao_top=0.98)

            # (d) Outer stone planter troughs mounted neatly along exterior stone ledges (replaces all red boxes!)
            if k % 3 == 1 and k < segs_r - 1:
                pl_off = half_out + 0.18
                px = (a0[0] + a1[0]) * 0.5 + sgn * ((n0x + n1x) * 0.5) * pl_off
                py = (a0[1] + a1[1]) * 0.5 + sgn * ((n0y + n1y) * 0.5) * pl_off
                pz = (a0[2] + a1[2]) * 0.5
                # Stone corbel support ledge under planter
                nb.add_box(stone_mat, px, py, pz - 0.08, 1.08, 0.34, 0.08, seg_yaw, brick_uv, ao_bot=0.72, ao_top=0.90)
                add_planter_box(
                    nb, px, py, pz,
                    length=1.02, width=0.30, height=0.28, yaw_rad=seg_yaw,
                    mats=mats, uv_consts=uv_consts,
                    style="stone", plant_kind="rose", plant_h=0.38, seed=k * 13 + (1 if sgn > 0 else 2),
                )

        # 3. Carved Beveled Stone Newel Posts (石望柱) every 2 segments (and at both ends)
        if k % 2 == 0 or k == segs_r - 1:
            pt_idx = k if k % 2 == 0 else segs_r
            ap = ramp_pts[pt_idx]
            nx_p, ny_p = v_normals[pt_idx]
            tx_p, ty_p = v_tangents[pt_idx]
            pyaw = math.atan2(ty_p, tx_p)
            r_mid = half_w + rail_t * 0.5
            for sgn in (-1.0, 1.0):
                px = ap[0] + sgn * nx_p * r_mid
                py = ap[1] + sgn * ny_p * r_mid
                nb.add_beveled_box(marble_mat, px, py, ap[2] + 0.14, 0.29, 0.29, 1.04, pyaw, marble_uv, bevel=0.025, ao_bot=0.82, ao_top=0.98)
                # Stepped pyramidal granite cap stone on newel post
                nb.add_beveled_box(stone_mat, px, py, ap[2] + 1.18, 0.33, 0.33, 0.07, pyaw, stone_uv, bevel=0.02, ao_bot=0.90, ao_top=1.0)
                nb.add_beveled_box(marble_mat, px, py, ap[2] + 1.25, 0.21, 0.21, 0.06, pyaw, marble_uv, bevel=0.025, ao_bot=0.94, ao_top=1.0)

        # 4. Structural Support Piers (Granite base plinth + smooth concrete column + cap beam)
        if k > 0 and k % 4 == 0 and a0[2] > 0.72:
            col_top = a0[2] - sof
            tx_p, ty_p = v_tangents[k]
            cyaw = math.atan2(ty_p, tx_p)
            # Granite base pedestal
            nb.add_beveled_box(stone_mat, a0[0], a0[1], 0.0, 0.74, 0.74, 0.28, cyaw, brick_uv, bevel=0.03, ao_bot=0.72, ao_top=0.90)
            nb.add_beveled_box(stone_mat, a0[0], a0[1], 0.28, 0.62, 0.62, 0.12, cyaw, stone_uv, bevel=0.02, ao_bot=0.80, ao_top=0.94)
            # Smooth concrete column shaft
            if col_top > 0.45:
                nb.add_smooth_cylinder(stone_mat, a0[0], a0[1], 0.40, 0.24, 0.22, col_top - 0.40, segs=12, ao_bot=0.76, ao_top=0.94)
            # Transverse concrete pier cap beam beneath curved soffit
            nb.add_box(stone_mat, a0[0], a0[1], max(0.35, col_top - 0.18), 0.56, half_out * 1.85, 0.20, cyaw, stone_uv, ao_bot=0.78, ao_top=0.92)


# ---------------------------------------------------------------------------
# 6. Traditional Chinese Square Garden Pavilion (百草园四角攒尖亭)
# ---------------------------------------------------------------------------
def add_chinese_pavilion(nb, pv_x: float, pv_y: float, z0: float, mats: dict, uv_consts: dict) -> None:
    """
    Authentic Beijing garden square pavilion:
      - Two-tier Qingzhuan & granite stone platform + south entrance granite steps
      - 4 carved drum stone column bases + crimson timber columns
      - 3-sided traditional '美人靠' (Meirenkao) timber benches & inclined backrests
      - Architrave beams, corner bracket blocks (雀替) & hanging frieze (挂落)
      - 5-tier concave upturned flying-eave hipped grey-tile roof + 4 curved hip ridges + lotus-gourd finial
    """
    # 1. Two-tier stone platform
    nb.add_box(mats["surf"], pv_x, pv_y, z0, 4.90, 4.90, 0.16, 0.0, uv_consts["UV_QINGZHUAN"], ao_bot=0.74, ao_top=0.92, top_mat=mats["surf"], top_uv=uv_consts["UV_PLAZA_TILE"])
    nb.add_box(mats["surf"], pv_x, pv_y, z0 + 0.16, 4.35, 4.35, 0.18, 0.0, uv_consts["UV_QINGZHUAN"], ao_bot=0.78, ao_top=0.95, top_mat=mats["surf"], top_uv=uv_consts["UV_PLAZA_TILE"])
    z_deck = z0 + 0.34
    # South entrance 2-step granite stairs
    add_granite_stairs(nb, pv_x, pv_y - 2.18, z0, z_deck, 1.50, 0.70, math.pi, 2, mats, uv_consts, cheek_walls=False)

    # 2. 4 Drum stone column bases & crimson round timber columns
    col_span = 1.52
    col_h = 2.75
    for cx_s in (-col_span, col_span):
        for cy_s in (-col_span, col_span):
            px, py = pv_x + cx_s, pv_y + cy_s
            nb.add_box(mats["surf"], px, py, z_deck, 0.42, 0.42, 0.08, 0.0, uv_consts["UV_PLAZA_TILE"])
            nb.add_smooth_cylinder(mats["surf"], px, py, z_deck + 0.08, 0.19, 0.15, 0.14, segs=10)
            nb.add_smooth_cylinder(mats["pavilion_wood"], px, py, z_deck + 0.22, 0.13, 0.115, col_h - 0.22, segs=10, ao_bot=0.76, ao_top=0.96)

    # 3. 3-Sided Traditional '美人靠' (Meirenkao) timber benches & railings (leave South open)
    bench_z = z_deck + 0.46
    for side_name, bx, by, bw, bd, out_dx, out_dy in [
        ("N", pv_x, pv_y + col_span, col_span * 2.0 - 0.24, 0.44, 0.0, 1.0),
        ("W", pv_x - col_span, pv_y, 0.44, col_span * 2.0 - 0.24, -1.0, 0.0),
        ("E", pv_x + col_span, pv_y, 0.44, col_span * 2.0 - 0.24, 1.0, 0.0),
    ]:
        # Timber seat plank + support apron
        nb.add_box(mats["pavilion_wood"], bx, by, bench_z, bw, bd, 0.06, 0.0, ao_bot=0.80, ao_top=0.96)
        nb.add_box(mats["pavilion_wood"], bx, by, z_deck + 0.02, bw * 0.92, bd * 0.72, 0.44, 0.0, ao_bot=0.72, ao_top=0.88)
        # Slightly outward-leaning backrest rail + vertical spindles
        rx = bx + out_dx * 0.24
        ry = by + out_dy * 0.24
        nb.add_box(mats["pavilion_wood"], rx, ry, bench_z + 0.56, bw if out_dy else 0.07, bd if out_dx else 0.07, 0.06, 0.0)
        nb.add_box(mats["pavilion_wood"], rx - out_dx * 0.04, ry - out_dy * 0.04, bench_z + 0.30, bw if out_dy else 0.05, bd if out_dx else 0.05, 0.045, 0.0)
        for bi in range(7):
            u = -0.44 + bi * (0.88 / 6.0)
            sx = rx + (bw * u if out_dy else 0.0)
            sy = ry + (bd * u if out_dx else 0.0)
            nb.add_limb(mats["pavilion_wood"], (sx - out_dx * 0.06, sy - out_dy * 0.06, bench_z + 0.05), (sx, sy, bench_z + 0.58), 0.018, 0.018, segs=5)

    # 4. Upper Architrave Beams (额枋), Hanging Frieze (挂落) & Corner Brackets (雀替)
    z_beam = z_deck + col_h - 0.22
    for bx, by, bw, bd in [
        (pv_x, pv_y - col_span, col_span * 2.0 + 0.32, 0.18),
        (pv_x, pv_y + col_span, col_span * 2.0 + 0.32, 0.18),
        (pv_x - col_span, pv_y, 0.18, col_span * 2.0 + 0.32),
        (pv_x + col_span, pv_y, 0.18, col_span * 2.0 + 0.32),
    ]:
        nb.add_box(mats["pavilion_wood"], bx, by, z_beam, bw, bd, 0.20, 0.0, ao_bot=0.82, ao_top=0.98)
        # Decorative lower lattice bar (挂落)
        nb.add_box(mats["gold_trim"], bx, by, z_beam - 0.22, bw * 0.92, bd * 0.55, 0.045, 0.0)
    # Corner diagonal bracket braces (雀替)
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            cx_c, cy_c = pv_x + sx * col_span, pv_y + sy * col_span
            nb.add_limb(mats["pavilion_wood"], (cx_c, cy_c, z_beam - 0.35), (cx_c - sx * 0.45, cy_c, z_beam + 0.04), 0.032, 0.032, segs=5)
            nb.add_limb(mats["pavilion_wood"], (cx_c, cy_c, z_beam - 0.35), (cx_c, cy_c - sy * 0.45, z_beam + 0.04), 0.032, 0.032, segs=5)

    # 5. Concave Upturned Flying-Eave Square Pyramidal Roof (四角攒尖起翘灰瓦顶)
    # 5 radial rings: (half_extent, z_height, corner_upturn_dz)
    z_eave = z_deck + col_h
    tiers = [
        (2.58, z_eave - 0.02, 0.28),   # outer flying eaves (corners sweep upward!)
        (2.12, z_eave + 0.12, 0.10),
        (1.52, z_eave + 0.48, 0.03),
        (0.86, z_eave + 0.98, 0.01),
        (0.24, z_eave + 1.56, 0.00),
    ]
    z_apex = z_eave + 1.72
    tile_uv = uv_consts["UV_GREY_TILE"]

    def tier_ring(ext: float, zh: float, up: float) -> List[Vec3]:
        # 8 points per side (actually 3 points per edge: corner, mid, corner) so corner upturn curves smoothly!
        pts: List[Vec3] = []
        corners2d = [(-ext, -ext), (ext, -ext), (ext, ext), (-ext, ext)]
        for k in range(4):
            a, b = corners2d[k], corners2d[(k + 1) % 4]
            pts.append((pv_x + a[0], pv_y + a[1], zh + up))
            pts.append((pv_x + (a[0] + b[0]) * 0.5, pv_y + (a[1] + b[1]) * 0.5, zh))
        return pts

    rings = [tier_ring(e, z, u) for e, z, u in tiers]
    for ri in range(len(rings) - 1):
        r_lo, r_hi = rings[ri], rings[ri + 1]
        for k in range(8):
            kn = (k + 1) % 8
            nb.quad_enu(mats["surf"], r_lo[k], r_lo[kn], r_hi[kn], r_hi[k], tile_uv, 0.84 + ri * 0.03, 0.90 + ri * 0.025, double_sided=True)
    # Top cap triangles meeting apex
    top_r = rings[-1]
    for k in range(8):
        kn = (k + 1) % 8
        nb.tri_enu(mats["surf"], top_r[k], top_r[kn], (pv_x, pv_y, z_apex), (0.1, 0.9), (0.9, 0.9), (0.5, 0.1), 0.94, 0.94, 1.0, double_sided=True)

    # Eave fascia trim & 4 curved hip ridges (垂脊) with upturned corner beasts
    for k in range(8):
        kn = (k + 1) % 8
        add_rect_beam(nb, mats["pavilion_wood"], rings[0][k], rings[0][kn], 0.08, 0.12, caps=False)
    for corner_idx in (0, 2, 4, 6):
        for ri in range(len(rings) - 1):
            add_rect_beam(nb, mats["surf"], rings[ri][corner_idx], rings[ri + 1][corner_idx], 0.14, 0.15, tile_uv, ao_bot=0.88, ao_top=1.0)
        add_rect_beam(nb, mats["surf"], rings[-1][corner_idx], (pv_x, pv_y, z_apex + 0.04), 0.13, 0.14, tile_uv)
        # Upturned corner eave finial tip
        tip = rings[0][corner_idx]
        nb.add_smooth_cylinder(mats["surf"], tip[0], tip[1], tip[2] + 0.02, 0.06, 0.02, 0.18, segs=6)

    # 6. Sculpted Lotus-Gourd Peak Finial (葫芦宝顶)
    nb.add_smooth_cylinder(mats["surf"], pv_x, pv_y, z_apex - 0.04, 0.30, 0.24, 0.16, segs=10)
    nb.add_sphere(mats["gold_trim"], pv_x, pv_y, z_apex + 0.20, 0.14, 0.13, 0.14, segs=10, rings=6, ao=1.0)
    nb.add_sphere(mats["gold_trim"], pv_x, pv_y, z_apex + 0.40, 0.09, 0.10, 0.09, segs=10, rings=5, ao=1.0)
    nb.add_smooth_cylinder(mats["gold_trim"], pv_x, pv_y, z_apex + 0.48, 0.04, 0.008, 0.24, segs=8)


# ---------------------------------------------------------------------------
# 7. Realistic Basketball Hoops (Hollow Orange Rim + Braided Openwork Net + 3D Truss)
# ---------------------------------------------------------------------------
def add_realistic_basketball_hoop(
    nb,
    cx: float,
    cy_n: float,
    yaw_face_rad: float,
    mats: dict,
    uv_consts: dict,
    z_base: float = 0.06,
    style: str = "west_green",
) -> None:
    """
    Upgraded outdoor basketball hoop (both West Kelly-green truss & East dark-steel gooseneck):
      - Base anchor plate + padded protective column wrap + upper steel column
      - 3D tubular/box overhang arm & 3D diagonal tension struts (no 0-thickness paper quads)
      - Metal perimeter frame + tempered glass backboard (UV_GLASS_BACKBOARD)
      - TRUE hollow torus orange rim + braided openwork zigzag white net strands
    """
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def pt(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs, z_base + lz)

    is_west = (style == "west_green")
    main_mat = mats["hoop_green"] if (is_west and "hoop_green" in mats) else mats["dark_steel"]
    pad_mat = mats["hoop_pad"] if (is_west and "hoop_pad" in mats) else mats["blue_steel"]

    # Base flange plate + column protective padding + upper steel column
    nb.add_box(mats["dark_steel"], cx, cy_n, z_base, 0.58, 0.58, 0.055, yaw_face_rad)
    nb.add_beveled_box(pad_mat, cx, cy_n, z_base + 0.055, 0.34, 0.34, 1.82, yaw_face_rad, bevel=0.03, ao_bot=0.78, ao_top=0.96)
    nb.add_box(main_mat, cx, cy_n, z_base + 1.875, 0.22, 0.22, 1.62, yaw_face_rad, ao_bot=0.84, ao_top=0.98)

    # 3D overhang boom arm + 3D tubular diagonal struts
    add_rect_beam(nb, main_mat, pt(0.0, 0.0, 3.16), pt(0.0, 1.24, 3.16), 0.17, 0.14)
    for sx in (-0.15, 0.15):
        nb.add_limb(main_mat, pt(sx, 0.04, 3.46), pt(sx, 1.21, 3.80), 0.022, 0.020, segs=6)
        nb.add_limb(main_mat, pt(sx, 0.06, 2.50), pt(sx, 0.78, 3.14), 0.024, 0.022, segs=6)

    # Outer frame of 1.80m x 1.05m backboard (at ly = 1.24)
    bb_xy = pt(0.0, 1.24, 0.0)
    nb.add_box(main_mat, bb_xy[0], bb_xy[1], z_base + 2.82, 1.84, 0.055, 0.055, yaw_face_rad)
    nb.add_box(main_mat, bb_xy[0], bb_xy[1], z_base + 3.85, 1.84, 0.055, 0.055, yaw_face_rad)
    for bx_s in (-0.895, 0.895):
        post_xy = pt(bx_s, 1.24, 0.0)
        nb.add_box(main_mat, post_xy[0], post_xy[1], z_base + 2.82, 0.055, 0.055, 1.08, yaw_face_rad)
    # Protective bottom backboard padding bar
    nb.add_box(pad_mat, bb_xy[0], bb_xy[1], z_base + 2.77, 1.86, 0.07, 0.055, yaw_face_rad)

    # Semi-transparent tempered glass backboard with shooter's square
    bb_mat = mats["details_alpha"] if "details_alpha" in mats else mats["white_alu"]
    nb.quad_enu(
        bb_mat,
        pt(0.88, 1.265, 2.86), pt(-0.88, 1.265, 2.86),
        pt(-0.88, 1.265, 3.85), pt(0.88, 1.265, 3.85),
        uv_consts["UV_GLASS_BACKBOARD"], 0.98, 1.0, double_sided=True,
    )

    # Rim mounting bracket + TRUE hollow torus orange rim
    brk_xy = pt(0.0, 1.32, 0.0)
    nb.add_box(mats["orange_hoop"], brk_xy[0], brk_xy[1], z_base + 2.97, 0.14, 0.14, 0.08, yaw_face_rad)
    rim_c = pt(0.0, 1.52, 3.01)
    add_torus_ring(nb, mats["orange_hoop"], rim_c, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), 0.225, 0.017, major_segs=14, minor_segs=6)

    # Openwork braided white net (8 criss-cross diamond cord strands, NOT an opaque white cylinder!)
    n_net = 8
    r_top, r_mid, r_bot = 0.215, 0.155, 0.135
    z_top_n, z_mid_n, z_bot_n = rim_c[2] - 0.015, rim_c[2] - 0.22, rim_c[2] - 0.42
    for ni in range(n_net):
        a0 = (2.0 * math.pi * ni) / n_net
        a_m_plus = (2.0 * math.pi * (ni + 0.5)) / n_net
        a_m_minus = (2.0 * math.pi * (ni - 0.5)) / n_net
        p_t = (rim_c[0] + r_top * math.cos(a0), rim_c[1] + r_top * math.sin(a0), z_top_n)
        p_mp = (rim_c[0] + r_mid * math.cos(a_m_plus), rim_c[1] + r_mid * math.sin(a_m_plus), z_mid_n)
        p_mm = (rim_c[0] + r_mid * math.cos(a_m_minus), rim_c[1] + r_mid * math.sin(a_m_minus), z_mid_n)
        p_b = (rim_c[0] + r_bot * math.cos(a0), rim_c[1] + r_bot * math.sin(a0), z_bot_n)
        nb.add_limb(mats["white_alu"], p_t, p_mp, 0.0055, 0.0055, segs=3)
        nb.add_limb(mats["white_alu"], p_t, p_mm, 0.0055, 0.0055, segs=3)
        nb.add_limb(mats["white_alu"], p_mp, p_b, 0.005, 0.005, segs=3)
        nb.add_limb(mats["white_alu"], p_mm, p_b, 0.005, 0.005, segs=3)


def add_realistic_double_basketball_hoop(
    nb,
    cx: float,
    cy_n: float,
    yaw_axis_rad: float,
    mats: dict,
    uv_consts: dict,
    z_base: float = 0.06,
) -> None:
    """West Campus back-to-back connected twin Kelly-green 3D truss hoops sharing one central column (PR #18 + realistic rim/net)."""
    main_mat = mats["hoop_green"] if "hoop_green" in mats else mats["dark_steel"]
    pad_mat = mats["hoop_pad"] if "hoop_pad" in mats else mats["blue_steel"]
    bb_mat = mats["details_alpha"] if "details_alpha" in mats else mats["white_alu"]

    # Shared reinforced steel base plate, beveled green protective column pad & central column + tie cap
    nb.add_box(mats["dark_steel"], cx, cy_n, z_base, 0.62, 0.92, 0.055, yaw_axis_rad)
    nb.add_beveled_box(pad_mat, cx, cy_n, z_base + 0.055, 0.34, 0.54, 1.82, yaw_axis_rad, bevel=0.03, ao_bot=0.78, ao_top=0.96)
    nb.add_box(main_mat, cx, cy_n, z_base + 1.875, 0.24, 0.42, 1.62, yaw_axis_rad, ao_bot=0.84, ao_top=0.98)
    nb.add_box(main_mat, cx, cy_n, z_base + 3.495, 0.28, 0.48, 0.08, yaw_axis_rad, ao_bot=0.88, ao_top=0.98)

    for yaw_face in (yaw_axis_rad, yaw_axis_rad + math.pi):
        cs, sn = math.cos(yaw_face), math.sin(yaw_face)

        def pt(lx: float, ly: float, lz: float) -> Vec3:
            return (cx + lx * cs - ly * sn, cy_n + lx * sn + ly * cs, z_base + lz)

        # 3D overhang boom + tubular tension/compression diagonal struts
        add_rect_beam(nb, main_mat, pt(0.0, 0.14, 3.16), pt(0.0, 1.32, 3.16), 0.18, 0.14)
        for sx in (-0.15, 0.15):
            nb.add_limb(main_mat, pt(sx, 0.14, 3.46), pt(sx, 1.29, 3.80), 0.022, 0.020, segs=5)
            nb.add_limb(main_mat, pt(sx, 0.16, 2.50), pt(sx, 0.84, 3.14), 0.024, 0.022, segs=5)

        # Outer perimeter frame + protective bottom pad + tempered glass backboard (at ly = 1.32)
        bb_xy = pt(0.0, 1.32, 0.0)
        nb.add_box(main_mat, bb_xy[0], bb_xy[1], z_base + 2.82, 1.84, 0.055, 0.055, yaw_face)
        nb.add_box(main_mat, bb_xy[0], bb_xy[1], z_base + 3.85, 1.84, 0.055, 0.055, yaw_face)
        for bx_s in (-0.895, 0.895):
            post_xy = pt(bx_s, 1.32, 0.0)
            nb.add_box(main_mat, post_xy[0], post_xy[1], z_base + 2.82, 0.055, 0.055, 1.08, yaw_face)
        nb.add_box(pad_mat, bb_xy[0], bb_xy[1], z_base + 2.77, 1.86, 0.07, 0.055, yaw_face)
        nb.quad_enu(
            bb_mat,
            pt(0.88, 1.345, 2.86), pt(-0.88, 1.345, 2.86),
            pt(-0.88, 1.345, 3.85), pt(0.88, 1.345, 3.85),
            uv_consts["UV_GLASS_BACKBOARD"], 0.98, 1.0, double_sided=True,
        )

        # Mounting bracket + hollow torus orange rim + braided openwork net (at ly = 1.60)
        brk_xy = pt(0.0, 1.40, 0.0)
        nb.add_box(mats["orange_hoop"], brk_xy[0], brk_xy[1], z_base + 2.97, 0.14, 0.14, 0.08, yaw_face)
        rim_c = pt(0.0, 1.60, 3.01)
        add_torus_ring(nb, mats["orange_hoop"], rim_c, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), 0.225, 0.017, major_segs=12, minor_segs=5)
        n_net = 8
        r_top, r_mid, r_bot = 0.215, 0.155, 0.135
        z_top_n, z_mid_n, z_bot_n = rim_c[2] - 0.015, rim_c[2] - 0.22, rim_c[2] - 0.42
        for ni in range(n_net):
            a0 = (2.0 * math.pi * ni) / n_net
            a_m_plus = (2.0 * math.pi * (ni + 0.5)) / n_net
            a_m_minus = (2.0 * math.pi * (ni - 0.5)) / n_net
            p_t = (rim_c[0] + r_top * math.cos(a0), rim_c[1] + r_top * math.sin(a0), z_top_n)
            p_mp = (rim_c[0] + r_mid * math.cos(a_m_plus), rim_c[1] + r_mid * math.sin(a_m_plus), z_mid_n)
            p_mm = (rim_c[0] + r_mid * math.cos(a_m_minus), rim_c[1] + r_mid * math.sin(a_m_minus), z_mid_n)
            p_b = (rim_c[0] + r_bot * math.cos(a0), rim_c[1] + r_bot * math.sin(a0), z_bot_n)
            nb.add_limb(mats["white_alu"], p_t, p_mp, 0.0055, 0.0055, segs=3)
            nb.add_limb(mats["white_alu"], p_t, p_mm, 0.0055, 0.0055, segs=3)
            nb.add_limb(mats["white_alu"], p_mp, p_b, 0.005, 0.005, segs=3)
            nb.add_limb(mats["white_alu"], p_mm, p_b, 0.005, 0.005, segs=3)


# ---------------------------------------------------------------------------
# 8. Realistic Outdoor Ping-Pong Table (Tubular Frame + Clamps + Translucent Mesh Net)
# ---------------------------------------------------------------------------
def add_realistic_pingpong_table(
    nb,
    cx: float,
    cy: float,
    yaw_rad: float,
    mats: dict,
    uv_consts: dict,
    z_base: float = 0.028,
) -> None:
    """Standard 2.74m x 1.525m outdoor ping-pong table with tubular steel legs & fine mesh net."""
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

    def wp(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, z_base + lz)

    # Royal-blue beveled table top + steel apron skirt beneath
    nb.add_beveled_box(
        mats["blue_steel"], cx, cy, z_base + 0.70, 2.74, 1.525, 0.055, yaw_rad, bevel=0.015,
        ao_bot=0.78, ao_top=0.98, top_mat=mats["details"], top_uv=uv_consts["UV_PINGPONG_TOP"],
    )
    nb.add_box(mats["dark_steel"], cx, cy, z_base + 0.65, 2.54, 1.36, 0.05, yaw_rad, ao_bot=0.72, ao_top=0.86)

    # Tubular crimson arched leg frames + horizontal stretcher & center brace
    for lx in (-0.96, 0.96):
        for ly in (-0.54, 0.54):
            nb.add_limb(mats["crimson"], wp(lx, ly, 0.02), wp(lx, ly, 0.68), 0.026, 0.026, segs=8)
            nb.add_smooth_cylinder(mats["dark_steel"], wp(lx, ly, 0.0)[0], wp(lx, ly, 0.0)[1], z_base, 0.038, 0.036, 0.035, segs=8)
        nb.add_limb(mats["crimson"], wp(lx, -0.54, 0.22), wp(lx, 0.54, 0.22), 0.022, 0.022, segs=6)
        nb.add_limb(mats["crimson"], wp(lx, -0.54, 0.22), wp(lx * 0.45, -0.54, 0.66), 0.018, 0.018, segs=6)
        nb.add_limb(mats["crimson"], wp(lx, 0.54, 0.22), wp(lx * 0.45, 0.54, 0.66), 0.018, 0.018, segs=6)
    nb.add_limb(mats["crimson"], wp(-0.96, 0.0, 0.22), wp(0.96, 0.0, 0.22), 0.020, 0.020, segs=6)

    # Metal net clamp posts + fine translucent mesh net + crisp white cotton top tape
    for py_end in (-0.82, 0.82):
        nb.add_limb(mats["dark_steel"], wp(0.0, py_end, 0.72), wp(0.0, py_end, 0.91), 0.014, 0.014, segs=6)
    add_rect_beam(nb, mats["white_alu"], wp(0.0, -0.82, 0.90), wp(0.0, 0.82, 0.90), 0.016, 0.022)
    net_mat = mats["fence_mesh"] if "fence_mesh" in mats else mats["details_alpha"]
    nb.quad_enu(
        net_mat,
        wp(0.0, -0.81, 0.76), wp(0.0, 0.81, 0.76),
        wp(0.0, 0.81, 0.89), wp(0.0, -0.81, 0.89),
        (0.0, 0.0, 1.0, 1.0), 0.92, 0.98, double_sided=True,
    )


# ---------------------------------------------------------------------------
# 9. Wheeled 3D A-Frame Barricade (东门实景拒马, east-gate-2023.webp)
# ---------------------------------------------------------------------------
def add_wheeled_aframe_barricade(
    nb,
    cx: float,
    cy: float,
    z_base: float,
    yaw_rad: float,
    mats: dict,
) -> None:
    """Photo-faithful 3D triangular steel-pipe A-frame traffic barricade on 4 swivel caster wheels."""
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

    def wp(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, z_base + lz)

    hl, hw = 0.86, 0.36
    z_frame = 0.13
    z_top = 1.04
    r_main = 0.028
    r_brace = 0.020

    # 4 swiveling caster wheels (dark wheel + metal fork)
    for sx in (-hl + 0.08, hl - 0.08):
        for sy in (-hw + 0.04, hw - 0.04):
            w_c = wp(sx, sy, 0.05)
            w_u = _vsub(wp(sx + 1.0, sy, 0.05), w_c)
            w_v = _vsub(wp(sx, sy, 1.05), w_c)
            add_torus_ring(nb, mats["dark_steel"], w_c, w_u, w_v, 0.036, 0.015, major_segs=8, minor_segs=4)
            nb.add_limb(mats["stainless"], wp(sx, sy, 0.07), wp(sx, sy, z_frame), 0.015, 0.015, segs=5)

    # Rectangular steel base frame
    b_pts = [wp(-hl, -hw, z_frame), wp(hl, -hw, z_frame), wp(hl, hw, z_frame), wp(-hl, hw, z_frame)]
    for k in range(4):
        nb.add_limb(mats["white_alu"], b_pts[k], b_pts[(k + 1) % 4], r_main, r_main, segs=6)

    # Top longitudinal tubular ridge pipe + red warning stripes
    nb.add_limb(mats["white_alu"], wp(-hl, 0.0, z_top), wp(hl, 0.0, z_top), r_main * 1.15, r_main * 1.15, segs=8)
    for rx in (-0.42, 0.42):
        nb.add_limb(mats["sign_red"], wp(rx - 0.14, 0.0, z_top), wp(rx + 0.14, 0.0, z_top), r_main * 1.22, r_main * 1.22, segs=8)

    # End A-frames + longitudinal V-truss diagonal braces on both sloped sides
    for sx in (-hl, hl):
        nb.add_limb(mats["white_alu"], wp(sx, -hw, z_frame), wp(sx, 0.0, z_top), r_main, r_main, segs=6)
        nb.add_limb(mats["white_alu"], wp(sx, hw, z_frame), wp(sx, 0.0, z_top), r_main, r_main, segs=6)
    xs_bot = [-hl, -hl * 0.33, hl * 0.33, hl]
    xs_top = [-hl * 0.66, 0.0, hl * 0.66]
    for sy in (-hw, hw):
        for ti, xt in enumerate(xs_top):
            nb.add_limb(mats["white_alu"], wp(xs_bot[ti], sy, z_frame), wp(xt, 0.0, z_top), r_brace, r_brace, segs=5)
            nb.add_limb(mats["white_alu"], wp(xs_bot[ti + 1], sy, z_frame), wp(xt, 0.0, z_top), r_brace, r_brace, segs=5)


# ---------------------------------------------------------------------------
# 10. Multi-Head Tilted Stadium Floodlight Mast & Detailed AC Outdoor Unit
# ---------------------------------------------------------------------------
def add_detailed_stadium_floodlight(
    nb,
    lx: float,
    ly: float,
    z_base: float,
    yaw_in: float,
    pole_h: float,
    mats: dict,
    n_heads: int = 2,
) -> None:
    """Tapered steel sports floodlight mast with base plinth, braced crossbar & tilted LED hoods."""
    cs, sn = math.cos(yaw_in), math.sin(yaw_in)

    def wp(dx_fwd: float, dy_side: float, dz: float) -> Vec3:
        return (lx + dx_fwd * cs - dy_side * sn, ly + dx_fwd * sn + dy_side * cs, z_base + dz)

    # Concrete pedestal + bolted flange plate + tapered smooth column
    nb.add_beveled_box(mats["dark_steel"], lx, ly, z_base, 0.44, 0.44, 0.24, yaw_in, bevel=0.025, ao_bot=0.72, ao_top=0.90)
    nb.add_smooth_cylinder(mats["dark_steel"], lx, ly, z_base + 0.24, 0.125, 0.075, pole_h - 0.24, segs=10)

    # Crossbar & twin V-braces
    bar_w = 1.45 if n_heads == 2 else 1.95
    add_rect_beam(nb, mats["dark_steel"], wp(0.0, -bar_w * 0.5, pole_h - 0.05), wp(0.0, bar_w * 0.5, pole_h - 0.05), 0.09, 0.09)
    for sy in (-bar_w * 0.36, bar_w * 0.36):
        nb.add_limb(mats["dark_steel"], wp(0.0, 0.0, pole_h - 0.58), wp(0.0, sy, pole_h - 0.06), 0.026, 0.026, segs=6)

    # Tilted LED floodlight heads with finned dark housing, luminous face & anti-glare visor hood
    offsets = (-0.48, 0.48) if n_heads == 2 else (-0.70, 0.0, 0.70)
    for sy in offsets:
        # Support yoke
        nb.add_limb(mats["dark_steel"], wp(0.0, sy, pole_h - 0.02), wp(0.06, sy, pole_h + 0.18), 0.024, 0.024, segs=5)
        # Tilted body (angled downward ~28 deg toward +dx_fwd)
        add_rect_beam(nb, mats["dark_steel"], wp(-0.08, sy, pole_h + 0.34), wp(0.18, sy, pole_h + 0.20), 0.48, 0.30)
        # Glowing LED lens face on front of tilted fixture
        add_rect_beam(nb, mats["floodlight"], wp(0.16, sy, pole_h + 0.21), wp(0.21, sy, pole_h + 0.185), 0.42, 0.23)
        # Top anti-glare rain visor overhanging lens
        add_rect_beam(nb, mats["dark_steel"], wp(0.04, sy, pole_h + 0.38), wp(0.32, sy, pole_h + 0.29), 0.50, 0.03)


def add_detailed_ac_unit(nb, cx: float, cy: float, z_bot: float, yaw_face_rad: float, mats: dict, uv_consts: dict) -> None:
    """Upgraded split AC outdoor condenser with wall L-brackets, diagonal braces, top cap & insulated copper pipe."""
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def pt(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, z_bot + lz)

    # Twin steel L-brackets (horizontal rail + vertical wall plate + diagonal brace)
    for bx in (-0.30, 0.30):
        add_rect_beam(nb, mats["dark_steel"], pt(bx, -0.19, -0.025), pt(bx, 0.19, -0.025), 0.04, 0.035)
        add_rect_beam(nb, mats["dark_steel"], pt(bx, -0.18, -0.34), pt(bx, -0.18, 0.14), 0.04, 0.03)
        nb.add_limb(mats["dark_steel"], pt(bx, -0.17, -0.30), pt(bx, 0.12, -0.03), 0.013, 0.013, segs=4)

    # Condenser housing + slightly overhanging stamped top cover
    nb.add_box(mats["white_alu"], cx, cy, z_bot, 0.82, 0.32, 0.55, yaw_face_rad, ao_bot=0.82, ao_top=0.98)
    nb.add_box(mats["white_alu"], cx, cy, z_bot + 0.545, 0.85, 0.35, 0.03, yaw_face_rad, ao_bot=0.90, ao_top=1.0)
    # Recessed dark fan grille border + textured fan front
    nb.quad_enu(
        mats["details"],
        pt(0.39, 0.168, 0.03), pt(-0.39, 0.168, 0.03),
        pt(-0.39, 0.168, 0.53), pt(0.39, 0.168, 0.53),
        uv_consts["UV_AC_UNIT_FRONT"], 0.90, 1.0,
    )
    # White insulated copper refrigerant conduit curving back into wall on right side
    nb.add_limb(mats["white_alu"], pt(0.41, 0.02, 0.14), pt(0.50, -0.04, 0.10), 0.024, 0.024, segs=5)
    nb.add_limb(mats["white_alu"], pt(0.50, -0.04, 0.10), pt(0.48, -0.18, 0.24), 0.024, 0.024, segs=5)


# ---------------------------------------------------------------------------
# 11. Beijing Hutong Two-Slope Tile Wall Run, Building Entrance Portals & Penthouses
# ---------------------------------------------------------------------------
def add_detailed_wall_run(
    nb,
    a: Vec2,
    b: Vec2,
    h: float,
    thick: float,
    mats: dict,
    uv_consts: dict,
    wall_uv_key: str = "UV_QINGZHUAN",
    z_base: float = 0.0,
    hutong_tile_cap: bool = True,
) -> None:
    """Beijing masonry compound wall with stone base plinth, periodic pilasters & pitched two-slope grey tile wall cap."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    if L < 0.08:
        return
    yaw = math.atan2(dy, dx)
    cs, sn = math.cos(yaw), math.sin(yaw)
    cx, cy = (a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5
    w_uv = uv_consts[wall_uv_key]

    # Base plinth kick + main brick wall
    nb.add_box(mats["surf"], cx, cy, z_base, L, thick + 0.07, 0.34, yaw, uv_consts["UV_PLAZA_TILE"], ao_bot=0.70, ao_top=0.88)
    nb.add_box(mats["surf"], cx, cy, z_base + 0.34, L, thick, max(0.2, h - 0.34), yaw, w_uv, ao_bot=0.78, ao_top=0.96)

    # Periodic structural pilasters
    n_pil = max(2, int(L // 4.5) + 1)
    for pi in range(n_pil):
        t = pi / (n_pil - 1)
        px, py = a[0] + dx * t, a[1] + dy * t
        nb.add_box(mats["surf"], px, py, z_base, 0.42, thick + 0.12, h + 0.04, yaw, w_uv, ao_bot=0.74, ao_top=0.96)

    if hutong_tile_cap:
        # Authentic Beijing hutong two-slope pitched grey-tile wall cap + ridge roll
        half_cap = thick * 0.5 + 0.16
        z_eave = z_base + h - 0.02
        z_ridge = z_base + h + 0.24
        tx, ty = cs, sn
        nx, ny = -sn, cs  # +local Y

        def wp(s_along: float, s_lat: float, z: float) -> Vec3:
            return (a[0] + tx * s_along + nx * s_lat, a[1] + ty * s_along + ny * s_lat, z)

        nb.quad_enu(mats["surf"], wp(-0.08, -half_cap, z_eave), wp(L + 0.08, -half_cap, z_eave), wp(L + 0.08, 0.0, z_ridge), wp(-0.08, 0.0, z_ridge), uv_consts["UV_GREY_TILE"], 0.86, 1.0, double_sided=True)
        nb.quad_enu(mats["surf"], wp(L + 0.08, half_cap, z_eave), wp(-0.08, half_cap, z_eave), wp(-0.08, 0.0, z_ridge), wp(L + 0.08, 0.0, z_ridge), uv_consts["UV_GREY_TILE"], 0.86, 1.0, double_sided=True)
        add_rect_beam(nb, mats["surf"], wp(-0.08, 0.0, z_ridge + 0.02), wp(L + 0.08, 0.0, z_ridge + 0.02), 0.13, 0.11, uv_consts["UV_GREY_TILE"])
    else:
        nb.add_beveled_box(mats["surf"], cx, cy, z_base + h, L + 0.08, thick + 0.14, 0.11, yaw, uv_consts["UV_PLAZA_TILE"], bevel=0.02, ao_bot=0.88, ao_top=1.0)


def add_building_entrance_portal(
    nb,
    cx: float,
    cy: float,
    z_base: float,
    yaw_face_rad: float,
    mats: dict,
    uv_consts: dict,
    width: float = 3.60,
    steps: int = 2,
    light_records: Optional[List[dict]] = None,
    add_wall_sconce_fn=None,
) -> None:
    """
    Complete ground-floor architectural building entrance facing +ly (rotated by yaw_face_rad):
      - Granite steps, beveled marble portal frame, double aluminum-framed glass doors + push bars
      - Cantilevered awning canopy with 3D steel tie-rods & anchor plates + optional soffit downlight
    """
    cs, sn = math.cos(yaw_face_rad), math.sin(yaw_face_rad)

    def wp(lx: float, ly: float, lz: float) -> Vec3:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs, z_base + lz)

    def rxy(lx: float, ly: float) -> Vec2:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs)

    step_h = 0.14 * steps if steps > 0 else 0.06
    if steps > 0:
        add_granite_stairs(nb, rxy(0.0, 0.35)[0], rxy(0.0, 0.35)[1], z_base, z_base + step_h, width + 0.45, 0.42 * steps, yaw_face_rad, steps, mats, uv_consts, cheek_walls=False)
    # Landing stone slab
    p_land = rxy(0.0, 0.25)
    nb.add_box(mats["surf"], p_land[0], p_land[1], z_base, width + 0.45, 0.55, step_h, yaw_face_rad, uv_consts["UV_PLAZA_TILE"], ao_bot=0.78, ao_top=0.96)

    # Marble jamb piers & stucco lintel header
    hw = width * 0.5
    door_h = 2.85
    for sx in (-(hw - 0.22), hw - 0.22):
        jp = rxy(sx, 0.16)
        nb.add_beveled_box(mats["gates"], jp[0], jp[1], z_base + step_h, 0.44, 0.36, door_h + 0.72, yaw_face_rad, uv_consts["UV_MARBLE"], bevel=0.02, ao_bot=0.80, ao_top=0.98)
    hp = rxy(0.0, 0.16)
    nb.add_box(mats["surf"], hp[0], hp[1], z_base + step_h + door_h, width, 0.36, 0.72, yaw_face_rad, uv_consts["UV_STUCCO"], ao_bot=0.84, ao_top=0.98)

    # Dark recess frame + glass double doors (physical glass in enhanced, UV_GLASS_WINDOW in classic)
    bp = rxy(0.0, 0.08)
    nb.add_box(mats["dark_steel"], bp[0], bp[1], z_base + step_h, width - 0.88, 0.24, door_h, yaw_face_rad)
    g_hw = hw - 0.48
    use_phys = (not getattr(nb, "classic_mode", False)) and ("glass_phys" in mats)
    g_mat = mats["glass_phys"] if use_phys else mats["glass"]
    g_uv = (0.0, 0.0, 1.0, 1.0) if use_phys else uv_consts["UV_GLASS_WINDOW"]
    # Face outward toward +ly -> p0=(+g_hw), p1=(-g_hw) gives outward +ly normal
    nb.quad_enu(g_mat, wp(g_hw, 0.21, step_h + 0.08), wp(-g_hw, 0.21, step_h + 0.08), wp(-g_hw, 0.21, step_h + 2.26), wp(g_hw, 0.21, step_h + 2.26), g_uv, 0.90, 1.0)
    nb.quad_enu(g_mat, wp(g_hw, 0.21, step_h + 2.34), wp(-g_hw, 0.21, step_h + 2.34), wp(-g_hw, 0.21, step_h + door_h - 0.06), wp(g_hw, 0.21, step_h + door_h - 0.06), g_uv, 0.90, 1.0)
    # Aluminum mullions + vertical stainless door push handles
    for mx, mw, mz0, mz1 in [(-g_hw - 0.03, 0.07, 0.0, door_h), (0.0, 0.065, 0.0, door_h), (g_hw + 0.03, 0.07, 0.0, door_h)]:
        mp = rxy(mx, 0.23)
        nb.add_box(mats["white_alu"], mp[0], mp[1], z_base + step_h + mz0, mw, 0.07, mz1 - mz0, yaw_face_rad)
    tr_p = rxy(0.0, 0.23)
    nb.add_box(mats["white_alu"], tr_p[0], tr_p[1], z_base + step_h + 2.27, g_hw * 2.0 + 0.10, 0.07, 0.075, yaw_face_rad)
    for hx in (-0.14, 0.14):
        nb.add_limb(mats["stainless"] if "stainless" in mats else mats["white_alu"], wp(hx, 0.29, step_h + 0.88), wp(hx, 0.29, step_h + 1.38), 0.016, 0.016, segs=6)

    # Cantilevered canopy + 3D cylindrical steel tie rods
    can_p = rxy(0.0, 0.78)
    z_can = z_base + step_h + door_h + 0.06
    nb.add_beveled_box(mats["white_alu"], can_p[0], can_p[1], z_can, width + 0.45, 1.48, 0.18, yaw_face_rad, bevel=0.02, ao_bot=0.86, ao_top=1.0, top_mat=mats["surf"], top_uv=uv_consts["UV_PLAZA_TILE"])
    for tx in (-(hw - 0.22), hw - 0.22):
        nb.add_limb(mats["dark_steel"], wp(tx, 0.22, step_h + door_h + 0.78), wp(tx, 1.34, step_h + door_h + 0.22), 0.020, 0.020, segs=6)

    if light_records is not None and add_wall_sconce_fn is not None:
        lp = rxy(0.0, 0.74)
        add_wall_sconce_fn(nb, lp[0], lp[1], z_can - 0.02, mats, light_records, color="#ffd8a0", intensity=11.0, distance=11.0)


def add_rooftop_penthouse(
    nb,
    cx: float,
    cy: float,
    z_roof: float,
    w: float,
    d: float,
    h: float,
    yaw_rad: float,
    mats: dict,
    uv_consts: dict,
    wall_uv_key: str = "UV_STUCCO",
) -> None:
    """Realistic rooftop stairwell/elevator machine room with overhanging cap, steel service door & exhaust cowls."""
    cs, sn = math.cos(yaw_rad), math.sin(yaw_rad)

    def rxy(lx: float, ly: float) -> Vec2:
        return (cx + lx * cs - ly * sn, cy + lx * sn + ly * cs)

    nb.add_box(mats["surf"], cx, cy, z_roof, w, d, h, yaw_rad, uv_consts[wall_uv_key], ao_bot=0.82, ao_top=0.98)
    nb.add_beveled_box(mats["surf"], cx, cy, z_roof + h, w + 0.32, d + 0.32, 0.22, yaw_rad, uv_consts["UV_PLAZA_TILE"], bevel=0.03, ao_bot=0.90, ao_top=1.0)
    # Dark steel rooftop maintenance access door on front (+ly) face
    dp = rxy(0.0, d * 0.5 + 0.03)
    nb.add_box(mats["dark_steel"], dp[0], dp[1], z_roof + 0.08, 1.05, 0.07, min(2.05, h - 0.35), yaw_rad)
    # Louvered vent grille on opposite (-ly) face
    vp = rxy(0.0, -(d * 0.5 + 0.03))
    nb.add_box(mats["dark_steel"], vp[0], vp[1], z_roof + h * 0.52, min(1.5, w * 0.45), 0.06, 0.55, yaw_rad)
    # Twin compact stainless exhaust vents on top of machine room
    for ex in (-w * 0.25, w * 0.25):
        ep = rxy(ex, 0.0)
        nb.add_smooth_cylinder(mats["white_alu"], ep[0], ep[1], z_roof + h + 0.22, 0.18, 0.16, 0.42, segs=8)
        nb.add_smooth_cylinder(mats["dark_steel"], ep[0], ep[1], z_roof + h + 0.62, 0.28, 0.06, 0.10, segs=8)

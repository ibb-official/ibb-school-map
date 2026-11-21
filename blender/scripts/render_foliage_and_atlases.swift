import AppKit
import CoreGraphics
import Foundation

// Generates crisp 1024x1024 alpha-cutout botanical foliage cluster cards
// (albedo + height map for Sobel normal baking) and a 4x4 interior parallax room atlas
// for distant surrounding context buildings.

let args = CommandLine.arguments
let outDir: String = args.count > 1
    ? args[1]
    : FileManager.default.currentDirectoryPath + "/foliage_out"

try FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)

func makeCtx(size: Int = 1024) -> (NSBitmapImageRep, CGContext) {
    let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: size,
        pixelsHigh: size,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    )!
    let nsCtx = NSGraphicsContext(bitmapImageRep: rep)!
    NSGraphicsContext.current = nsCtx
    let ctx = nsCtx.cgContext
    ctx.setAllowsAntialiasing(true)
    ctx.setShouldAntialias(true)
    ctx.clear(CGRect(x: 0, y: 0, width: size, height: size))
    return (rep, ctx)
}

func savePNG(_ rep: NSBitmapImageRep, to path: String) throws {
    guard let data = rep.representation(using: .png, properties: [:]) else {
        throw NSError(domain: "render_foliage", code: 1)
    }
    try data.write(to: URL(fileURLWithPath: path))
    print("Saved: \(path) (\(data.count) bytes)")
}

func rgba(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1.0) -> CGColor {
    CGColor(red: r, green: g, blue: b, alpha: a)
}

func drawLeafShape(_ ctx: CGContext, cx: CGFloat, cy: CGFloat, len: CGFloat, wid: CGFloat, angle: CGFloat, fill: CGColor, vein: CGColor?) {
    ctx.saveGState()
    ctx.translateBy(x: cx, y: cy)
    ctx.rotate(by: angle)
    ctx.setFillColor(fill)
    ctx.beginPath()
    ctx.move(to: CGPoint(x: 0, y: 0))
    ctx.addCurve(
        to: CGPoint(x: len, y: 0),
        control1: CGPoint(x: len * 0.28, y: wid),
        control2: CGPoint(x: len * 0.72, y: wid * 0.75)
    )
    ctx.addCurve(
        to: CGPoint(x: 0, y: 0),
        control1: CGPoint(x: len * 0.72, y: -wid * 0.75),
        control2: CGPoint(x: len * 0.28, y: -wid)
    )
    ctx.closePath()
    ctx.fillPath()
    if let vCol = vein {
        ctx.setStrokeColor(vCol)
        ctx.setLineWidth(max(1.2, wid * 0.08))
        ctx.move(to: CGPoint(x: len * 0.06, y: 0))
        ctx.addLine(to: CGPoint(x: len * 0.88, y: 0))
        ctx.strokePath()
    }
    ctx.restoreGState()
}

func drawGinkgoFan(_ ctx: CGContext, cx: CGFloat, cy: CGFloat, rad: CGFloat, angle: CGFloat, fill: CGColor, vein: CGColor?) {
    ctx.saveGState()
    ctx.translateBy(x: cx, y: cy)
    ctx.rotate(by: angle)
    ctx.setFillColor(fill)
    ctx.beginPath()
    ctx.move(to: CGPoint(x: 0, y: 0))
    ctx.addCurve(to: CGPoint(x: rad * 0.85, y: rad * 0.62), control1: CGPoint(x: rad * 0.3, y: rad * 0.1), control2: CGPoint(x: rad * 0.65, y: rad * 0.55))
    ctx.addQuadCurve(to: CGPoint(x: rad * 0.74, y: 0), control: CGPoint(x: rad * 1.05, y: rad * 0.28))
    ctx.addQuadCurve(to: CGPoint(x: rad * 0.85, y: -rad * 0.62), control: CGPoint(x: rad * 1.05, y: -rad * 0.28))
    ctx.addCurve(to: CGPoint(x: 0, y: 0), control1: CGPoint(x: rad * 0.65, y: -rad * 0.55), control2: CGPoint(x: rad * 0.3, y: -rad * 0.1))
    ctx.closePath()
    ctx.fillPath()
    if let vCol = vein {
        ctx.setStrokeColor(vCol)
        ctx.setLineWidth(1.4)
        for da in stride(from: -0.45, through: 0.45, by: 0.18) {
            ctx.move(to: CGPoint(x: rad * 0.08, y: 0))
            ctx.addLine(to: CGPoint(x: rad * 0.82 * cos(da), y: rad * 0.82 * sin(da)))
        }
        ctx.strokePath()
    }
    ctx.restoreGState()
}

func drawTwigs(_ ctx: CGContext, size: CGFloat, seed: Int, isHeight: Bool, branches: Int = 9) {
    srand48(seed)
    let cx = size * 0.5
    let cy = size * 0.5
    ctx.setLineCap(.round)
    for i in 0..<branches {
        let ang = (CGFloat(i) / CGFloat(branches)) * .pi * 2.0 + CGFloat(drand48() - 0.5) * 0.35
        let len = size * (0.28 + CGFloat(drand48()) * 0.15)
        let ex = cx + cos(ang) * len
        let ey = cy + sin(ang) * len
        ctx.setStrokeColor(isHeight ? rgba(0.32, 0.32, 0.32, 1.0) : rgba(0.30, 0.22, 0.15, 1.0))
        ctx.setLineWidth(10.0)
        ctx.move(to: CGPoint(x: cx, y: cy))
        ctx.addQuadCurve(
            to: CGPoint(x: ex, y: ey),
            control: CGPoint(x: (cx + ex) * 0.5 + CGFloat(drand48() - 0.5) * 40, y: (cy + ey) * 0.5 + CGFloat(drand48() - 0.5) * 40)
        )
        ctx.strokePath()
    }
}

// -------------------------------------------------------------------------
// 1. Broadleaf Foliage Cluster (Deciduous / Pagoda / Scholar Trees)
// -------------------------------------------------------------------------
func renderBroadFoliage(name: String, seed: Int, baseR: CGFloat, baseG: CGFloat, baseB: CGFloat, accentType: String? = nil) throws {
    let S = 1024
    let (repA, ctxA) = makeCtx(size: S)
    let (repH, ctxH) = makeCtx(size: S)
    let sf = CGFloat(S)

    drawTwigs(ctxA, size: sf, seed: seed, isHeight: false, branches: 10)
    drawTwigs(ctxH, size: sf, seed: seed, isHeight: true, branches: 10)

    srand48(seed + 101)
    let totalLeaves = 460
    for idx in 0..<totalLeaves {
        let layer = CGFloat(idx) / CGFloat(totalLeaves)
        // Radial Gaussian-ish cluster so card edges feather organically with no square clip
        let u1 = max(0.001, drand48())
        let rDist = sqrt(-2.0 * log(u1)) * 0.175
        let clampedR = min(0.42, rDist) * sf
        let theta = CGFloat(drand48()) * .pi * 2.0
        let lx = sf * 0.5 + cos(theta) * clampedR
        let ly = sf * 0.5 + sin(theta) * clampedR
        let ang = theta + CGFloat(drand48() - 0.5) * 1.4
        let len = (42.0 + CGFloat(drand48()) * 44.0) * (1.12 - clampedR / sf)
        let wid = len * (0.34 + CGFloat(drand48()) * 0.14)

        let shade = 0.62 + 0.45 * layer + CGFloat(drand48() - 0.5) * 0.14
        let warm = CGFloat(drand48() - 0.5) * 0.08
        let col = rgba(
            min(1, max(0, baseR * shade + warm)),
            min(1, max(0, baseG * shade + warm * 0.4)),
            min(1, max(0, baseB * shade - warm * 0.3)),
            1.0
        )
        let vein = rgba(
            min(1, baseR * shade * 1.22),
            min(1, baseG * shade * 1.24),
            min(1, baseB * shade * 1.15),
            0.55
        )
        let hVal = 0.25 + 0.72 * layer
        let hCol = rgba(hVal, hVal, hVal, 1.0)
        let hVein = rgba(min(1, hVal + 0.10), min(1, hVal + 0.10), min(1, hVal + 0.10), 0.7)

        if accentType == "ginkgo" {
            drawGinkgoFan(ctxA, cx: lx, cy: ly, rad: len * 0.78, angle: ang, fill: col, vein: vein)
            drawGinkgoFan(ctxH, cx: lx, cy: ly, rad: len * 0.78, angle: ang, fill: hCol, vein: hVein)
        } else {
            drawLeafShape(ctxA, cx: lx, cy: ly, len: len, wid: wid, angle: ang, fill: col, vein: vein)
            drawLeafShape(ctxH, cx: lx, cy: ly, len: len, wid: wid, angle: ang, fill: hCol, vein: hVein)
        }
    }

    // Optional blossoms or persimmon fruits layered on top of outer leaves
    if let acc = accentType, acc == "magnolia" || acc == "persimmon" || acc == "rose" {
        srand48(seed + 777)
        let count = acc == "rose" ? 36 : (acc == "magnolia" ? 28 : 22)
        for _ in 0..<count {
            let r = CGFloat(0.08 + drand48() * 0.28) * sf
            let th = CGFloat(drand48()) * .pi * 2.0
            let bx = sf * 0.5 + cos(th) * r
            let by = sf * 0.5 + sin(th) * r
            if acc == "persimmon" {
                let rad = 16.0 + CGFloat(drand48()) * 10.0
                ctxA.setFillColor(rgba(0.92, 0.40, 0.06, 1.0))
                ctxA.fillEllipse(in: CGRect(x: bx - rad, y: by - rad * 0.88, width: rad * 2, height: rad * 1.76))
                ctxA.setFillColor(rgba(1.0, 0.64, 0.22, 0.55))
                ctxA.fillEllipse(in: CGRect(x: bx - rad * 0.45, y: by - rad * 0.48, width: rad * 0.7, height: rad * 0.55))
                ctxH.setFillColor(rgba(0.96, 0.96, 0.96, 1.0))
                ctxH.fillEllipse(in: CGRect(x: bx - rad, y: by - rad * 0.88, width: rad * 2, height: rad * 1.76))
            } else {
                let isRose = (acc == "rose")
                let petals = isRose ? 6 : 5
                let pr: CGFloat = isRose ? 15.0 : 21.0
                for pi in 0..<petals {
                    let pa = CGFloat(pi) * (.pi * 2.0 / CGFloat(petals)) + CGFloat(drand48()) * 0.25
                    let px = bx + cos(pa) * pr * 0.55
                    let py = by + sin(pa) * pr * 0.55
                    ctxA.setFillColor(isRose ? rgba(0.84, 0.11, 0.18, 1.0) : rgba(0.98, 0.96, 0.91, 1.0))
                    ctxA.fillEllipse(in: CGRect(x: px - pr * 0.55, y: py - pr * 0.45, width: pr * 1.1, height: pr * 0.9))
                    ctxH.setFillColor(rgba(0.95, 0.95, 0.95, 1.0))
                    ctxH.fillEllipse(in: CGRect(x: px - pr * 0.55, y: py - pr * 0.45, width: pr * 1.1, height: pr * 0.9))
                }
                ctxA.setFillColor(isRose ? rgba(0.55, 0.04, 0.09, 1.0) : rgba(0.92, 0.78, 0.36, 1.0))
                ctxA.fillEllipse(in: CGRect(x: bx - 5, y: by - 5, width: 10, height: 10))
            }
        }
    }

    try savePNG(repA, to: "\(outDir)/foliage_\(name)_albedo.png")
    try savePNG(repH, to: "\(outDir)/foliage_\(name)_height.png")
}

// -------------------------------------------------------------------------
// 2. Pine / Cedar Needle Bough Cluster (Layered Conifer Sprays)
// -------------------------------------------------------------------------
func renderConiferFoliage(name: String, seed: Int, baseR: CGFloat, baseG: CGFloat, baseB: CGFloat) throws {
    let S = 1024
    let (repA, ctxA) = makeCtx(size: S)
    let (repH, ctxH) = makeCtx(size: S)
    let sf = CGFloat(S)

    drawTwigs(ctxA, size: sf, seed: seed, isHeight: false, branches: 12)
    drawTwigs(ctxH, size: sf, seed: seed, isHeight: true, branches: 12)

    srand48(seed + 303)
    let tufts = 175
    for ti in 0..<tufts {
        let layer = CGFloat(ti) / CGFloat(tufts)
        let u1 = max(0.001, drand48())
        let rDist = min(0.41, sqrt(-2.0 * log(u1)) * 0.17) * sf
        let th = CGFloat(drand48()) * .pi * 2.0
        let bx = sf * 0.5 + cos(th) * rDist
        let by = sf * 0.5 + sin(th) * rDist

        let shade = 0.58 + 0.50 * layer + CGFloat(drand48() - 0.5) * 0.12
        let col = rgba(min(1, baseR * shade), min(1, baseG * shade), min(1, baseB * shade), 1.0)
        let tipCol = rgba(min(1, baseR * shade * 1.28), min(1, baseG * shade * 1.24), min(1, baseB * shade * 1.12), 1.0)
        let hVal = 0.25 + 0.72 * layer
        let hCol = rgba(hVal, hVal, hVal, 1.0)

        let needles = 18
        for ni in 0..<needles {
            let na = th + (CGFloat(ni) / CGFloat(needles) - 0.5) * 2.6 + CGFloat(drand48() - 0.5) * 0.22
            let nLen = (36.0 + CGFloat(drand48()) * 42.0) * (1.10 - rDist / sf)
            let nx = bx + cos(na) * nLen
            let ny = by + sin(na) * nLen

            ctxA.setLineCap(.round)
            ctxA.setStrokeColor(ni % 3 == 0 ? tipCol : col)
            ctxA.setLineWidth(4.2)
            ctxA.move(to: CGPoint(x: bx, y: by))
            ctxA.addLine(to: CGPoint(x: nx, y: ny))
            ctxA.strokePath()

            ctxH.setLineCap(.round)
            ctxH.setStrokeColor(hCol)
            ctxH.setLineWidth(4.2)
            ctxH.move(to: CGPoint(x: bx, y: by))
            ctxH.addLine(to: CGPoint(x: nx, y: ny))
            ctxH.strokePath()
        }
    }

    try savePNG(repA, to: "\(outDir)/foliage_\(name)_albedo.png")
    try savePNG(repH, to: "\(outDir)/foliage_\(name)_height.png")
}

// -------------------------------------------------------------------------
// 3. Context Building Parallax Interior Room Atlas (1024x1024, 4x4 rooms)
// -------------------------------------------------------------------------
func renderInteriorParallaxAtlas() throws {
    let S = 1024
    let (rep, ctx) = makeCtx(size: S)
    // Flip to Y-down for easier room composition
    ctx.translateBy(x: 0, y: CGFloat(S))
    ctx.scaleBy(x: 1, y: -1)

    let cell = 256
    srand48(2026)
    let wallPalettes: [(CGFloat, CGFloat, CGFloat)] = [
        (0.95, 0.88, 0.74), // warm living room
        (0.92, 0.90, 0.84), // study / classroom beige
        (0.88, 0.82, 0.72), // timber warm apartment
        (0.94, 0.95, 0.96), // crisp cool classroom
    ]

    for row in 0..<4 {
        for col in 0..<4 {
            let rx = CGFloat(col * cell)
            let ry = CGFloat(row * cell)
            let rect = CGRect(x: rx, y: ry, width: CGFloat(cell), height: CGFloat(cell))
            let pal = wallPalettes[(row * 3 + col) % wallPalettes.count]

            // Back wall base
            ctx.setFillColor(rgba(pal.0 * 0.82, pal.1 * 0.80, pal.2 * 0.76, 1.0))
            ctx.fill(rect)

            // Ceiling band with bright overhead fluorescent/pendant light strip
            ctx.setFillColor(rgba(0.96, 0.95, 0.92, 1.0))
            ctx.fill(CGRect(x: rx, y: ry, width: 256, height: 52))
            ctx.setFillColor(rgba(1.0, 0.97, 0.88, 1.0))
            ctx.fill(CGRect(x: rx + 56, y: ry + 14, width: 144, height: 22))

            // Floor strip
            ctx.setFillColor(rgba(0.46, 0.36, 0.28, 1.0))
            ctx.fill(CGRect(x: rx, y: ry + 206, width: 256, height: 50))

            // Side wall depth shading
            ctx.setFillColor(rgba(0.18, 0.16, 0.14, 0.24))
            ctx.fill(CGRect(x: rx, y: ry, width: 28, height: 256))
            ctx.fill(CGRect(x: rx + 228, y: ry, width: 28, height: 256))

            // Furniture silhouette (bookshelf / desk / painting / cabinet)
            let style = (row * 4 + col) % 4
            if style == 0 {
                // Bookshelf + warm desk lamp glow
                ctx.setFillColor(rgba(0.36, 0.25, 0.18, 1.0))
                ctx.fill(CGRect(x: rx + 36, y: ry + 78, width: 68, height: 128))
                for sy in stride(from: ry + 96, to: ry + 196, by: 24) {
                    ctx.setFillColor(rgba(0.68, 0.56, 0.42, 0.85))
                    ctx.fill(CGRect(x: rx + 42, y: sy, width: 56, height: 14))
                }
                // Warm table lamp halo on right
                ctx.setFillColor(rgba(1.0, 0.82, 0.45, 0.42))
                ctx.fillEllipse(in: CGRect(x: rx + 132, y: ry + 110, width: 76, height: 76))
                ctx.setFillColor(rgba(1.0, 0.92, 0.68, 0.95))
                ctx.fill(CGRect(x: rx + 158, y: ry + 138, width: 24, height: 20))
            } else if style == 1 {
                // Classroom chalkboard & desks
                ctx.setFillColor(rgba(0.16, 0.28, 0.22, 1.0))
                ctx.fill(CGRect(x: rx + 46, y: ry + 76, width: 164, height: 72))
                ctx.setStrokeColor(rgba(0.62, 0.48, 0.30, 1.0))
                ctx.setLineWidth(4)
                ctx.stroke(CGRect(x: rx + 46, y: ry + 76, width: 164, height: 72))
                ctx.setFillColor(rgba(0.55, 0.42, 0.30, 1.0))
                ctx.fill(CGRect(x: rx + 42, y: ry + 178, width: 172, height: 26))
            } else if style == 2 {
                // Framed artwork + sofa silhouette
                ctx.setFillColor(rgba(0.32, 0.38, 0.44, 1.0))
                ctx.fill(CGRect(x: rx + 82, y: ry + 78, width: 92, height: 58))
                ctx.setStrokeColor(rgba(0.75, 0.64, 0.42, 1.0))
                ctx.setLineWidth(4)
                ctx.stroke(CGRect(x: rx + 82, y: ry + 78, width: 92, height: 58))
                ctx.setFillColor(rgba(0.38, 0.32, 0.28, 1.0))
                ctx.fill(CGRect(x: rx + 52, y: ry + 162, width: 152, height: 46))
            } else {
                // Semi-drawn curtains & warm glowing middle
                ctx.setFillColor(rgba(0.98, 0.90, 0.72, 0.85))
                ctx.fill(CGRect(x: rx + 64, y: ry + 54, width: 128, height: 152))
                ctx.setFillColor(rgba(0.72, 0.66, 0.58, 0.95))
                ctx.fill(CGRect(x: rx + 18, y: ry + 48, width: 54, height: 184))
                ctx.fill(CGRect(x: rx + 184, y: ry + 48, width: 54, height: 184))
            }
        }
    }

    try savePNG(rep, to: "\(outDir)/interior_atlas.png")
}

try renderBroadFoliage(name: "broad", seed: 101, baseR: 0.24, baseG: 0.44, baseB: 0.20)
try renderConiferFoliage(name: "pine", seed: 202, baseR: 0.14, baseG: 0.32, baseB: 0.19)
try renderBroadFoliage(name: "ginkgo", seed: 303, baseR: 0.82, baseG: 0.68, baseB: 0.16, accentType: "ginkgo")
try renderBroadFoliage(name: "magnolia", seed: 404, baseR: 0.22, baseG: 0.40, baseB: 0.21, accentType: "magnolia")
try renderBroadFoliage(name: "persimmon", seed: 505, baseR: 0.28, baseG: 0.43, baseB: 0.18, accentType: "persimmon")
try renderBroadFoliage(name: "rose", seed: 606, baseR: 0.20, baseG: 0.40, baseB: 0.18, accentType: "rose")
try renderInteriorParallaxAtlas()

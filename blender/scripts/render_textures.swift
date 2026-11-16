import AppKit
import CoreGraphics
import Foundation

// Generates three 1024x1024 architectural PBR texture atlases for glTF campus models.
// Coordinates match glTF UV space: (0, 0) top-left -> (1, 1) bottom-right.

let args = CommandLine.arguments
let outDir: String = args.count > 1
    ? args[1]
    : FileManager.default.currentDirectoryPath + "/tex_out"

try FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true)

func makeAtlasContext(size: Int = 1024) -> (NSBitmapImageRep, CGContext) {
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
    // Transform CGContext so (0, 0) is TOP-LEFT and +Y goes DOWN (direct 1:1 with glTF UV)
    ctx.translateBy(x: 0, y: CGFloat(size))
    ctx.scaleBy(x: 1, y: -1)
    return (rep, ctx)
}

func savePNG(_ rep: NSBitmapImageRep, to path: String) throws {
    guard let data = rep.representation(using: .png, properties: [:]) else {
        throw NSError(domain: "render_textures", code: 1)
    }
    try data.write(to: URL(fileURLWithPath: path))
    print("Saved texture atlas: \(path) (\(data.count) bytes)")
}

func rgb(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1.0) -> CGColor {
    CGColor(red: r, green: g, blue: b, alpha: a)
}

func drawFlippedText(_ text: String, in rect: CGRect, fontName: String, size: CGFloat, color: NSColor, align: NSTextAlignment = .center, bold: Bool = false) {
    guard let ctx = NSGraphicsContext.current?.cgContext else { return }
    ctx.saveGState()
    // Flip locally back upright for CoreText/AppKit string drawing inside Y-down atlas
    ctx.translateBy(x: rect.minX, y: rect.maxY)
    ctx.scaleBy(x: 1, y: -1)
    let font = NSFont(name: fontName, size: size) ?? (bold ? NSFont.boldSystemFont(ofSize: size) : NSFont.systemFont(ofSize: size))
    let para = NSMutableParagraphStyle()
    para.alignment = align
    para.lineBreakMode = .byWordWrapping
    let attrs: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: color,
        .paragraphStyle: para
    ]
    let str = NSAttributedString(string: text, attributes: attrs)
    let bounds = str.boundingRect(with: NSSize(width: rect.width, height: rect.height), options: [.usesLineFragmentOrigin])
    let dy = max(0, (rect.height - bounds.height) * 0.5)
    str.draw(with: NSRect(x: 0, y: 0, width: rect.width, height: rect.height - dy), options: [.usesLineFragmentOrigin])
    ctx.restoreGState()
}

func drawVerticalChars(_ chars: [String], centerX: CGFloat, startY: CGFloat, stepY: CGFloat, fontName: String, size: CGFloat, color: NSColor) {
    for (idx, ch) in chars.enumerated() {
        let r = CGRect(x: centerX - size * 0.7, y: startY + CGFloat(idx) * stepY, width: size * 1.4, height: stepY)
        drawFlippedText(ch, in: r, fontName: fontName, size: size, color: color, align: .center, bold: true)
    }
}

// =========================================================================
// 1. tex_signage_gates.png (1024x1024)
// =========================================================================
do {
    let (rep, ctx) = makeAtlasContext(size: 1024)
    ctx.setFillColor(rgb(0.86, 0.86, 0.85))
    ctx.fill(CGRect(x: 0, y: 0, width: 1024, height: 1024))

    // Tile A: West Gate Brownish-Red Metal Fascia + Orange LED Banner (u: 0..1, v: 0..0.22 -> y: 0..225)
    let fascia = CGRect(x: 0, y: 0, width: 1024, height: 225)
    ctx.setFillColor(rgb(0.39, 0.23, 0.22))
    ctx.fill(fascia)
    for sx in stride(from: 64, to: 1024, by: 64) {
        ctx.setFillColor(rgb(0.24, 0.13, 0.12))
        ctx.fill(CGRect(x: sx - 2, y: 0, width: 4, height: 225))
    }
    let ledBox = CGRect(x: 170, y: 42, width: 684, height: 140)
    ctx.setFillColor(rgb(0.11, 0.09, 0.09))
    ctx.fill(ledBox)
    ctx.setStrokeColor(rgb(0.26, 0.22, 0.20))
    ctx.setLineWidth(6)
    ctx.stroke(ledBox)
    drawFlippedText(
        "北京市第一六六中学教育集团",
        in: CGRect(x: 176, y: 66, width: 672, height: 96),
        fontName: "STKaiti",
        size: 50,
        color: NSColor(red: 1.0, green: 0.42, blue: 0.10, alpha: 1.0),
        align: .center,
        bold: true
    )

    // Tile B: Gold-Framed Student Calligraphy Vertical Plaque (u: 0..0.28, v: 0.24..0.76 -> x:0..286, y:246..778)
    let plRect = CGRect(x: 8, y: 246, width: 270, height: 532)
    ctx.setFillColor(rgb(0.76, 0.62, 0.26))
    ctx.fill(plRect)
    let plInner = plRect.insetBy(dx: 16, dy: 16)
    ctx.setFillColor(rgb(0.95, 0.94, 0.91))
    ctx.fill(plInner)
    ctx.setStrokeColor(rgb(0.45, 0.36, 0.16))
    ctx.setLineWidth(3)
    ctx.stroke(plInner)
    drawVerticalChars(
        ["北","京","市","第","一","六","六","中","学"],
        centerX: plInner.midX + 12,
        startY: plInner.minY + 34,
        stepY: 48,
        fontName: "STKaiti",
        size: 40,
        color: NSColor(red: 0.12, green: 0.12, blue: 0.12, alpha: 1.0)
    )
    drawVerticalChars(
        ["甲","辰","年","仲","春","月"],
        centerX: plInner.minX + 38,
        startY: plInner.minY + 120,
        stepY: 28,
        fontName: "STKaiti",
        size: 16,
        color: NSColor(red: 0.32, green: 0.25, blue: 0.20, alpha: 1.0)
    )

    // Tile C: Shendu Granite Motto Stone Front (u: 0.30..0.62, v: 0.24..0.76 -> x:307..634, y:246..778)
    let stRect = CGRect(x: 307, y: 246, width: 327, height: 532)
    ctx.setFillColor(rgb(0.68, 0.69, 0.67))
    ctx.fill(stRect)
    srand48(42)
    for _ in 0..<2600 {
        let rx = stRect.minX + CGFloat(drand48()) * stRect.width
        let ry = stRect.minY + CGFloat(drand48()) * stRect.height
        let v = 0.42 + CGFloat(drand48()) * 0.44
        ctx.setFillColor(rgb(v, v, v - 0.01, 0.65))
        ctx.fill(CGRect(x: rx, y: ry, width: 3.5, height: 3.5))
    }
    drawFlippedText("慎", in: CGRect(x: stRect.minX + 20, y: stRect.minY + 90, width: stRect.width - 40, height: 165), fontName: "STKaiti", size: 138, color: NSColor(red: 0.76, green: 0.09, blue: 0.09, alpha: 1.0), align: .center, bold: true)
    drawFlippedText("獨", in: CGRect(x: stRect.minX + 20, y: stRect.minY + 265, width: stRect.width - 40, height: 165), fontName: "STKaiti", size: 138, color: NSColor(red: 0.76, green: 0.09, blue: 0.09, alpha: 1.0), align: .center, bold: true)

    // Tile D: Veined White-Grey Marble Slab (u: 0.64..1.0, v: 0.24..0.52 -> x:655..1024, y:246..532)
    let mbRect = CGRect(x: 655, y: 246, width: 369, height: 286)
    ctx.setFillColor(rgb(0.86, 0.87, 0.88))
    ctx.fill(mbRect)
    ctx.saveGState()
    ctx.clip(to: mbRect)
    for k in 0..<18 {
        ctx.setStrokeColor(rgb(0.55, 0.57, 0.60, 0.24))
        ctx.setLineWidth(1.5 + CGFloat(k % 3))
        let sy = mbRect.minY + CGFloat(k) * 18
        ctx.move(to: CGPoint(x: mbRect.minX, y: sy))
        ctx.addCurve(
            to: CGPoint(x: mbRect.maxX, y: sy + 36),
            control1: CGPoint(x: mbRect.minX + 120, y: sy - 24),
            control2: CGPoint(x: mbRect.minX + 250, y: sy + 52)
        )
        ctx.strokePath()
    }
    ctx.restoreGState()

    // Tile E: Burgundy Metal Portal + Address Plates (u: 0.64..1.0, v: 0.54..0.76 -> x:655..1024, y:553..778)
    let bgRect = CGRect(x: 655, y: 553, width: 369, height: 225)
    ctx.setFillColor(rgb(0.39, 0.14, 0.13))
    ctx.fill(bgRect)
    for gy in stride(from: 565, to: 778, by: 28) {
        ctx.setFillColor(rgb(0.28, 0.09, 0.09))
        ctx.fill(CGRect(x: 655, y: gy, width: 369, height: 2))
    }

    // Tile F: Black-Slate Horizontal/Vertical School Gate Plaque (u: 0..0.50, v: 0.78..1.0 -> x:0..512, y:798..1024)
    let bkRect = CGRect(x: 8, y: 798, width: 496, height: 218)
    ctx.setFillColor(rgb(0.18, 0.20, 0.22))
    ctx.fill(bkRect)
    ctx.setStrokeColor(rgb(0.76, 0.66, 0.42))
    ctx.setLineWidth(6)
    ctx.stroke(bkRect.insetBy(dx: 8, dy: 8))
    drawFlippedText("北京市第一六六中学", in: CGRect(x: 24, y: 842, width: 464, height: 70), fontName: "STKaiti", size: 42, color: NSColor(red: 0.96, green: 0.94, blue: 0.88, alpha: 1.0), align: .center, bold: true)
    drawFlippedText("东四六条甲44号 · 同福夹道3号", in: CGRect(x: 24, y: 924, width: 464, height: 42), fontName: "PingFangSC-Regular", size: 22, color: NSColor(red: 0.82, green: 0.84, blue: 0.86, alpha: 1.0), align: .center)

    // Tile G: Ground Speed Limit 5 Roundel (u: 0.52..0.76, v: 0.78..1.0 -> x:532..778, y:798..1024)
    let spBox = CGRect(x: 532, y: 798, width: 246, height: 226)
    ctx.setFillColor(rgb(0.26, 0.28, 0.30))
    ctx.fill(spBox)
    let disc = CGRect(x: spBox.midX - 86, y: spBox.midY - 86, width: 172, height: 172)
    ctx.setFillColor(rgb(0.95, 0.95, 0.94))
    ctx.fillEllipse(in: disc)
    ctx.setStrokeColor(rgb(0.80, 0.14, 0.14))
    ctx.setLineWidth(20)
    ctx.strokeEllipse(in: disc.insetBy(dx: 12, dy: 12))
    drawFlippedText("5", in: CGRect(x: disc.minX, y: disc.minY + 12, width: disc.width, height: disc.height - 20), fontName: "HelveticaNeue-Bold", size: 108, color: .black, align: .center, bold: true)

    // Tile H: Crimson Flag Cloth + Five Gold Stars (u: 0.78..1.0, v: 0.78..1.0 -> x:798..1024, y:798..1024)
    let flRect = CGRect(x: 798, y: 798, width: 226, height: 226)
    ctx.setFillColor(rgb(0.84, 0.12, 0.11))
    ctx.fill(flRect)
    for sy in stride(from: 808, to: 1020, by: 24) {
        ctx.setFillColor(rgb(0.72, 0.08, 0.08, 0.55))
        ctx.fill(CGRect(x: 798, y: sy, width: 226, height: 8))
    }
    func fillStar(center: CGPoint, outerR: CGFloat, innerR: CGFloat, tilt: CGFloat = 0) {
        ctx.beginPath()
        for k in 0..<10 {
            let r = (k % 2 == 0) ? outerR : innerR
            let ang = -CGFloat.pi / 2.0 + tilt + CGFloat(k) * (.pi / 5.0)
            let pt = CGPoint(x: center.x + r * cos(ang), y: center.y + r * sin(ang))
            if k == 0 {
                ctx.move(to: pt)
            } else {
                ctx.addLine(to: pt)
            }
        }
        ctx.closePath()
        ctx.fillPath()
    }
    ctx.setFillColor(rgb(0.98, 0.84, 0.16))
    let mainStar = CGPoint(x: 834, y: 842)
    fillStar(center: mainStar, outerR: 22, innerR: 8.6)
    for pt in [
        CGPoint(x: 868, y: 818),
        CGPoint(x: 880, y: 832),
        CGPoint(x: 880, y: 852),
        CGPoint(x: 868, y: 868),
    ] {
        let angToMain = atan2(mainStar.y - pt.y, mainStar.x - pt.x) + .pi / 2.0
        fillStar(center: pt, outerR: 7.5, innerR: 2.9, tilt: angToMain)
    }

    try savePNG(rep, to: "\(outDir)/tex_signage_gates.png")
}

// =========================================================================
// 2. tex_plaques_stage.png (1024x1024)
// =========================================================================
do {
    let (rep, ctx) = makeAtlasContext(size: 1024)
    ctx.setFillColor(rgb(0.90, 0.89, 0.86))
    ctx.fill(CGRect(x: 0, y: 0, width: 1024, height: 1024))

    // Tile A: Playground Chairman Stage Wide LED (u: 0..0.72, v: 0..0.32 -> x:0..737, y:0..328)
    let ledRect = CGRect(x: 0, y: 0, width: 737, height: 328)
    ctx.setFillColor(rgb(0.10, 0.25, 0.48))
    ctx.fill(ledRect)
    ctx.setFillColor(rgb(0.82, 0.16, 0.18))
    ctx.fill(CGRect(x: 0, y: 245, width: 737, height: 83))
    ctx.setFillColor(rgb(0.96, 0.97, 0.99))
    ctx.fill(CGRect(x: 18, y: 18, width: 701, height: 218))
    drawFlippedText("求实进取  ·  敬业乐群", in: CGRect(x: 30, y: 54, width: 677, height: 76), fontName: "STKaiti", size: 52, color: NSColor(red: 0.72, green: 0.10, blue: 0.12, alpha: 1.0), align: .center, bold: true)
    drawFlippedText("北京市第一六六中学（非官方 3D 校园地图参考场景）", in: CGRect(x: 30, y: 150, width: 677, height: 50), fontName: "PingFangSC-Medium", size: 22, color: NSColor(red: 0.10, green: 0.30, blue: 0.56, alpha: 1.0), align: .center)

    // Tile B & C: Flanking Stone Motto Pillars (u: 0.74..0.86 & 0.88..1.0, v: 0..0.52)
    for (px, chars) in [(758, ["求","實","進","取"]), (901, ["敬","業","樂","群"])] {
        let r = CGRect(x: px, y: 0, width: 123, height: 532)
        ctx.setFillColor(rgb(0.83, 0.78, 0.73))
        ctx.fill(r)
        ctx.setStrokeColor(rgb(0.68, 0.62, 0.58))
        ctx.setLineWidth(4)
        ctx.stroke(r.insetBy(dx: 4, dy: 4))
        drawVerticalChars(chars, centerX: r.midX, startY: 56, stepY: 110, fontName: "STKaiti", size: 74, color: NSColor(red: 0.64, green: 0.13, blue: 0.12, alpha: 1.0))
    }

    // Tile D: B-Wing Vertical Gable Inscription + Emblem (u: 0..0.34, v: 0.34..1.0 -> x:0..348, y:348..1024)
    let gwRect = CGRect(x: 0, y: 348, width: 348, height: 676)
    ctx.setFillColor(rgb(0.95, 0.94, 0.91))
    ctx.fill(gwRect)
    // Emblem Circle at top
    let emb = CGRect(x: gwRect.midX - 54, y: 374, width: 108, height: 108)
    ctx.setFillColor(rgb(0.09, 0.33, 0.58))
    ctx.fillEllipse(in: emb)
    ctx.setStrokeColor(rgb(0.95, 0.94, 0.91))
    ctx.setLineWidth(5)
    ctx.strokeEllipse(in: emb.insetBy(dx: 10, dy: 10))
    drawFlippedText("166", in: CGRect(x: emb.minX, y: emb.minY + 26, width: emb.width, height: 56), fontName: "HelveticaNeue-Bold", size: 32, color: .white, align: .center, bold: true)
    drawVerticalChars(["北","京","市","第","一","六","六","中","学"], centerX: gwRect.midX + 46, startY: 500, stepY: 54, fontName: "STKaiti", size: 42, color: NSColor(white: 0.18, alpha: 1.0))
    drawVerticalChars(["(","原","贝","满","女","中","、","女","十","二","中",")"], centerX: gwRect.midX - 42, startY: 515, stepY: 41, fontName: "STKaiti", size: 30, color: NSColor(white: 0.24, alpha: 1.0))

    // Tile E1 & E2: Red Book Plaques "B" & "D" (u: 0.36..0.68, v: 0.34..0.66)
    for (bx, letter, sub) in [(369, "B", "教学楼"), (534, "D", "校史馆")] {
        let bRect = CGRect(x: bx, y: 348, width: 152, height: 328)
        ctx.setFillColor(rgb(0.94, 0.93, 0.90))
        ctx.fill(bRect)
        let card = bRect.insetBy(dx: 10, dy: 64)
        ctx.setFillColor(rgb(0.66, 0.21, 0.19))
        ctx.fill(card)
        ctx.setStrokeColor(rgb(0.96, 0.95, 0.92))
        ctx.setLineWidth(4)
        ctx.stroke(card.insetBy(dx: 8, dy: 8))
        drawFlippedText(letter, in: CGRect(x: card.minX, y: card.minY + 14, width: card.width, height: 112), fontName: "TimesNewRomanPS-BoldMT", size: 96, color: .white, align: .center, bold: true)
        drawFlippedText(sub, in: CGRect(x: card.minX, y: card.maxY - 56, width: card.width, height: 42), fontName: "PingFangSC-Semibold", size: 28, color: .white, align: .center, bold: true)
    }

    // Tile E3: Red Book Plaque "C 教学楼" (u: 0.6875..0.8086, v: 0.5293..0.6680 -> x:704..828, y:542..684)
    do {
        let cRect = CGRect(x: 704, y: 542, width: 124, height: 142)
        ctx.setFillColor(rgb(0.94, 0.93, 0.90))
        ctx.fill(cRect)
        let card = cRect.insetBy(dx: 8, dy: 10)
        ctx.setFillColor(rgb(0.66, 0.21, 0.19))
        ctx.fill(card)
        ctx.setStrokeColor(rgb(0.96, 0.95, 0.92))
        ctx.setLineWidth(3.5)
        ctx.stroke(card.insetBy(dx: 6, dy: 6))
        drawFlippedText("C", in: CGRect(x: card.minX, y: card.minY + 6, width: card.width, height: 74), fontName: "TimesNewRomanPS-BoldMT", size: 64, color: .white, align: .center, bold: true)
        drawFlippedText("教学楼", in: CGRect(x: card.minX, y: card.maxY - 40, width: card.width, height: 32), fontName: "PingFangSC-Semibold", size: 22, color: .white, align: .center, bold: true)
    }

    // Tile E4: Outdoor PA Speaker Front Grille (u: 0.6855..0.7344, v: 0.3340..0.5215 -> x:700..754, y:340..536)
    do {
        let spkRect = CGRect(x: 700, y: 340, width: 54, height: 196)
        ctx.setFillColor(rgb(0.12, 0.13, 0.15))
        ctx.fill(spkRect)
        let inner = spkRect.insetBy(dx: 4, dy: 6)
        ctx.setFillColor(rgb(0.16, 0.17, 0.20))
        ctx.fill(inner)
        // Perforated protective metal grille ribs
        for gy in stride(from: inner.minY + 3, to: inner.maxY - 2, by: 4) {
            ctx.setFillColor(rgb(0.10, 0.11, 0.13))
            ctx.fill(CGRect(x: inner.minX + 1, y: gy, width: inner.width - 2, height: 1.5))
        }
        // Upper high-frequency horn waveguide
        let horn = CGRect(x: spkRect.midX - 16, y: 354, width: 32, height: 28)
        ctx.setFillColor(rgb(0.08, 0.09, 0.11))
        ctx.fill(horn)
        ctx.setStrokeColor(rgb(0.28, 0.30, 0.34))
        ctx.setLineWidth(1.5)
        ctx.stroke(horn)
        // Dual mid/low-frequency speaker cones
        for cy in [418.0, 476.0] as [CGFloat] {
            let outerC = CGRect(x: spkRect.midX - 18, y: cy - 18, width: 36, height: 36)
            ctx.setFillColor(rgb(0.26, 0.28, 0.32))
            ctx.fillEllipse(in: outerC)
            ctx.setFillColor(rgb(0.08, 0.09, 0.11))
            ctx.fillEllipse(in: outerC.insetBy(dx: 4, dy: 4))
            ctx.setFillColor(rgb(0.22, 0.24, 0.27))
            ctx.fillEllipse(in: outerC.insetBy(dx: 12, dy: 12))
        }
        // Bottom silver badge
        ctx.setFillColor(rgb(0.72, 0.74, 0.78))
        ctx.fill(CGRect(x: spkRect.midX - 9, y: 516, width: 18, height: 5))
    }

    // Tile H: Cafeteria Signboard "学生食堂" (u: 0.8223..0.9922, v: 0.5430..0.6543 -> x:842..1016, y:556..670)
    do {
        let sRect = CGRect(x: 842, y: 556, width: 174, height: 114)
        ctx.setFillColor(rgb(0.10, 0.28, 0.46))
        ctx.fill(sRect)
        ctx.setStrokeColor(rgb(0.84, 0.72, 0.44))
        ctx.setLineWidth(4)
        ctx.stroke(sRect.insetBy(dx: 6, dy: 6))
        drawFlippedText("学生食堂", in: CGRect(x: sRect.minX + 8, y: sRect.minY + 20, width: sRect.width - 16, height: 48), fontName: "PingFangSC-Semibold", size: 32, color: .white, align: .center, bold: true)
        drawFlippedText("DINING HALL", in: CGRect(x: sRect.minX + 8, y: sRect.minY + 72, width: sRect.width - 16, height: 26), fontName: "HelveticaNeue-Bold", size: 14, color: NSColor(red: 0.96, green: 0.86, blue: 0.58, alpha: 1.0), align: .center, bold: true)
    }

    // Tile F: Music Corridor Header Sign (u: 0.36..0.7617, v: 0.68..0.832 -> x:368..780, y:696..852)
    let mcRect = CGRect(x: 368, y: 696, width: 412, height: 156)
    ctx.setFillColor(rgb(0.14, 0.16, 0.18))
    ctx.fill(mcRect)
    ctx.setFillColor(rgb(0.90, 0.65, 0.15))
    ctx.fillEllipse(in: CGRect(x: 386, y: 726, width: 96, height: 96))
    ctx.setFillColor(rgb(0.14, 0.16, 0.18))
    ctx.fillEllipse(in: CGRect(x: 405, y: 745, width: 58, height: 58))
    ctx.setFillColor(rgb(0.96, 0.96, 0.95))
    ctx.fill(CGRect(x: 498, y: 724, width: 268, height: 100))
    drawFlippedText("音乐长廊", in: CGRect(x: 500, y: 728, width: 264, height: 58), fontName: "PingFangSC-Semibold", size: 40, color: .black, align: .center, bold: true)
    drawFlippedText("MUSIC CORRIDOR", in: CGRect(x: 500, y: 786, width: 264, height: 32), fontName: "HelveticaNeue-Bold", size: 17, color: NSColor(white: 0.25, alpha: 1.0), align: .center)

    // Tile I: School History Museum Entrance Plaque "校史馆" (u: 0.7734..0.9922, v: 0.6797..0.7539 -> x:792..1016, y:696..772)
    do {
        let hRect = CGRect(x: 792, y: 696, width: 224, height: 76)
        ctx.setFillColor(rgb(0.42, 0.11, 0.12))
        ctx.fill(hRect)
        ctx.setStrokeColor(rgb(0.87, 0.73, 0.40))
        ctx.setLineWidth(3)
        ctx.stroke(hRect.insetBy(dx: 4, dy: 4))
        ctx.setLineWidth(1.2)
        ctx.stroke(hRect.insetBy(dx: 8, dy: 8))
        drawFlippedText("校 史 馆", in: CGRect(x: hRect.minX + 10, y: hRect.minY + 10, width: hRect.width - 20, height: 38), fontName: "STKaiti", size: 30, color: NSColor(red: 0.97, green: 0.90, blue: 0.66, alpha: 1.0), align: .center, bold: true)
        drawFlippedText("SCHOOL HISTORY", in: CGRect(x: hRect.minX + 10, y: hRect.minY + 49, width: hRect.width - 20, height: 18), fontName: "HelveticaNeue-Bold", size: 10, color: NSColor(red: 0.90, green: 0.79, blue: 0.52, alpha: 1.0), align: .center, bold: true)
    }

    // Tile J: Library Entrance Plaque "图书馆" (u: 0.7734..0.9922, v: 0.7617..0.8359 -> x:792..1016, y:780..856)
    do {
        let lRect = CGRect(x: 792, y: 780, width: 224, height: 76)
        ctx.setFillColor(rgb(0.14, 0.23, 0.35))
        ctx.fill(lRect)
        ctx.setStrokeColor(rgb(0.85, 0.72, 0.42))
        ctx.setLineWidth(3)
        ctx.stroke(lRect.insetBy(dx: 4, dy: 4))
        ctx.setLineWidth(1.2)
        ctx.stroke(lRect.insetBy(dx: 8, dy: 8))
        drawFlippedText("图 书 馆", in: CGRect(x: lRect.minX + 10, y: lRect.minY + 10, width: lRect.width - 20, height: 38), fontName: "PingFangSC-Semibold", size: 28, color: NSColor(red: 0.98, green: 0.95, blue: 0.86, alpha: 1.0), align: .center, bold: true)
        drawFlippedText("LIBRARY", in: CGRect(x: lRect.minX + 10, y: lRect.minY + 49, width: lRect.width - 20, height: 18), fontName: "HelveticaNeue-Bold", size: 11, color: NSColor(red: 0.90, green: 0.79, blue: 0.52, alpha: 1.0), align: .center, bold: true)
    }

    // Tile G: Bronze Art Relief Wall (u: 0.36..1.0, v: 0.86..1.0 -> x:368..1024, y:880..1024)
    let relRect = CGRect(x: 368, y: 880, width: 656, height: 144)
    ctx.setFillColor(rgb(0.30, 0.23, 0.21))
    ctx.fill(relRect)
    for wx in stride(from: 380, to: 1010, by: 48) {
        ctx.setStrokeColor(rgb(0.54, 0.42, 0.34, 0.72))
        ctx.setLineWidth(5)
        ctx.move(to: CGPoint(x: wx, y: 950))
        ctx.addCurve(to: CGPoint(x: wx + 48, y: 950), control1: CGPoint(x: wx + 16, y: 900), control2: CGPoint(x: wx + 32, y: 1000))
        ctx.strokePath()
    }
    drawFlippedText("尚 美 · 美 育 浮 雕", in: CGRect(x: 420, y: 924, width: 552, height: 56), fontName: "STKaiti", size: 38, color: NSColor(red: 0.84, green: 0.68, blue: 0.44, alpha: 0.9), align: .center, bold: true)

    try savePNG(rep, to: "\(outDir)/tex_plaques_stage.png")
}

// =========================================================================
// 3. tex_surfaces.png (1024x1024, crisp 4x4 256px grid)
// =========================================================================
do {
    let (rep, ctx) = makeAtlasContext(size: 1024)
    func cell(_ col: Int, _ row: Int) -> CGRect {
        CGRect(x: col * 256, y: row * 256, width: 256, height: 256)
    }

    // (0,0) Terracotta Red Split-Brick Running Bond
    do {
        let r = cell(0, 0)
        ctx.setFillColor(rgb(0.58, 0.31, 0.25))
        ctx.fill(r)
        srand48(101)
        for rowIdx in 0..<16 {
            let y = r.minY + CGFloat(rowIdx) * 16
            let offset = (rowIdx % 2 == 0) ? 0.0 : 32.0
            for bx in stride(from: -32.0 + offset, to: 256.0, by: 64.0) {
                let delta = CGFloat(drand48() * 0.08 - 0.04)
                ctx.setFillColor(rgb(0.62 + delta, 0.34 + delta * 0.7, 0.27 + delta * 0.5))
                ctx.fill(CGRect(x: max(r.minX, r.minX + bx + 1.5), y: y + 1.5, width: min(61, r.maxX - (r.minX + bx + 1.5)), height: 13))
            }
        }
    }

    // (1,0) Grey Horizontal Ribbed Cladding
    do {
        let r = cell(1, 0)
        ctx.setFillColor(rgb(0.63, 0.64, 0.66))
        ctx.fill(r)
        for gy in stride(from: r.minY, to: r.maxY, by: 16) {
            ctx.setFillColor(rgb(0.50, 0.51, 0.54))
            ctx.fill(CGRect(x: r.minX, y: gy, width: 256, height: 3))
            ctx.setFillColor(rgb(0.73, 0.74, 0.76))
            ctx.fill(CGRect(x: r.minX, y: gy + 3, width: 256, height: 3))
        }
    }

    // (2,0) Beijing Qingzhuan Staggered Grey Brick
    do {
        let r = cell(2, 0)
        ctx.setFillColor(rgb(0.45, 0.47, 0.49))
        ctx.fill(r)
        srand48(202)
        for rowIdx in 0..<16 {
            let y = r.minY + CGFloat(rowIdx) * 16
            let off = (rowIdx % 2 == 0) ? 0.0 : 32.0
            for bx in stride(from: -32.0 + off, to: 256.0, by: 64.0) {
                let d = CGFloat(drand48() * 0.10 - 0.05)
                ctx.setFillColor(rgb(0.52 + d, 0.54 + d, 0.56 + d))
                ctx.fill(CGRect(x: max(r.minX, r.minX + bx + 2), y: y + 2, width: min(60, r.maxX - (r.minX + bx + 2)), height: 12))
            }
        }
    }

    // (3,0) Off-White Plaster / Architectural Stucco
    do {
        let r = cell(3, 0)
        ctx.setFillColor(rgb(0.92, 0.91, 0.88))
        ctx.fill(r)
        srand48(303)
        for _ in 0..<1200 {
            let v = 0.87 + CGFloat(drand48() * 0.09)
            ctx.setFillColor(rgb(v, v - 0.01, v - 0.03, 0.5))
            ctx.fill(CGRect(x: r.minX + CGFloat(drand48()) * 252, y: r.minY + CGFloat(drand48()) * 252, width: 4, height: 4))
        }
    }

    // (0,1) Traditional Grey Barrel Roof Tiles (筒瓦)
    do {
        let r = cell(0, 1)
        ctx.setFillColor(rgb(0.32, 0.34, 0.37))
        ctx.fill(r)
        for gx in stride(from: r.minX, to: r.maxX, by: 16) {
            ctx.setFillColor(rgb(0.44, 0.47, 0.50))
            ctx.fill(CGRect(x: gx + 3, y: r.minY, width: 8, height: 256))
            ctx.setFillColor(rgb(0.22, 0.24, 0.26))
            ctx.fill(CGRect(x: gx + 12, y: r.minY, width: 4, height: 256))
        }
        for gy in stride(from: r.minY, to: r.maxY, by: 24) {
            ctx.setFillColor(rgb(0.18, 0.20, 0.22, 0.6))
            ctx.fill(CGRect(x: r.minX, y: gy, width: 256, height: 2))
        }
    }

    // (1,1) Purple-Red Corrugated Tile Roof
    do {
        let r = cell(1, 1)
        ctx.setFillColor(rgb(0.56, 0.28, 0.30))
        ctx.fill(r)
        for gx in stride(from: r.minX, to: r.maxX, by: 16) {
            ctx.setFillColor(rgb(0.68, 0.36, 0.38))
            ctx.fill(CGRect(x: gx + 2, y: r.minY, width: 8, height: 256))
            ctx.setFillColor(rgb(0.40, 0.19, 0.20))
            ctx.fill(CGRect(x: gx + 11, y: r.minY, width: 4, height: 256))
        }
    }

    // (2,1) Green Eco-Roofing (East Campus Main Roofs)
    do {
        let r = cell(2, 1)
        ctx.setFillColor(rgb(0.40, 0.53, 0.36))
        ctx.fill(r)
        srand48(404)
        for _ in 0..<1000 {
            let g = 0.45 + CGFloat(drand48() * 0.16)
            ctx.setFillColor(rgb(g * 0.78, g, g * 0.68, 0.65))
            ctx.fill(CGRect(x: r.minX + CGFloat(drand48()) * 250, y: r.minY + CGFloat(drand48()) * 250, width: 6, height: 6))
        }
        for gy in stride(from: r.minY, to: r.maxY, by: 32) {
            ctx.setFillColor(rgb(0.32, 0.42, 0.28, 0.5))
            ctx.fill(CGRect(x: r.minX, y: gy, width: 256, height: 2))
        }
    }

    // (3,1) Herringbone Red Brick Walkway (East Campus Axis)
    do {
        let r = cell(3, 1)
        ctx.setFillColor(rgb(0.64, 0.39, 0.31))
        ctx.fill(r)
        srand48(505)
        for row in 0..<16 {
            let y = r.minY + CGFloat(row) * 16
            let off = (row % 2 == 0) ? 0.0 : 16.0
            for bx in stride(from: -16.0 + off, to: 256.0, by: 32.0) {
                let d = CGFloat(drand48() * 0.10 - 0.05)
                ctx.setFillColor(rgb(0.68 + d, 0.42 + d, 0.33 + d))
                ctx.fill(CGRect(x: max(r.minX, r.minX + bx + 1), y: y + 1, width: min(30, r.maxX - (r.minX + bx + 1)), height: 14))
            }
        }
    }

    // (0,2) Running Track Terracotta EPDM (subtle granular texture; lane stripes drawn as clean geometry)
    do {
        let r = cell(0, 2)
        ctx.setFillColor(rgb(0.73, 0.28, 0.21))
        ctx.fill(r)
        srand48(606)
        for _ in 0..<1100 {
            ctx.setFillColor(rgb(0.65, 0.24, 0.18, 0.42))
            ctx.fill(CGRect(x: r.minX + CGFloat(drand48()) * 254, y: r.minY + CGFloat(drand48()) * 254, width: 3, height: 3))
        }
        for _ in 0..<450 {
            ctx.setFillColor(rgb(0.80, 0.34, 0.26, 0.25))
            ctx.fill(CGRect(x: r.minX + CGFloat(drand48()) * 254, y: r.minY + CGFloat(drand48()) * 254, width: 2, height: 2))
        }
    }

    // (1,2) Green Basketball Court Surface
    do {
        let r = cell(1, 2)
        ctx.setFillColor(rgb(0.15, 0.48, 0.30))
        ctx.fill(r)
        srand48(707)
        for _ in 0..<600 {
            ctx.setFillColor(rgb(0.18, 0.54, 0.34, 0.45))
            ctx.fill(CGRect(x: r.minX + CGFloat(drand48()) * 252, y: r.minY + CGFloat(drand48()) * 252, width: 4, height: 4))
        }
    }

    // (2,2) Grey Plaza Stone Paving Tiles
    do {
        let r = cell(2, 2)
        ctx.setFillColor(rgb(0.66, 0.67, 0.68))
        ctx.fill(r)
        for row in 0..<8 {
            for col in 0..<8 {
                let v: CGFloat = ((row + col) % 2 == 0) ? 0.68 : 0.63
                ctx.setFillColor(rgb(v, v + 0.01, v + 0.02))
                ctx.fill(CGRect(x: r.minX + CGFloat(col * 32) + 1.5, y: r.minY + CGFloat(row * 32) + 1.5, width: 29, height: 29))
            }
        }
    }

    // (3,2) Sunlit Lawn Grass
    do {
        let r = cell(3, 2)
        ctx.setFillColor(rgb(0.32, 0.54, 0.25))
        ctx.fill(r)
        srand48(808)
        for _ in 0..<1200 {
            let g = 0.42 + CGFloat(drand48() * 0.22)
            ctx.setFillColor(rgb(g * 0.58, g, g * 0.44, 0.6))
            ctx.fill(CGRect(x: r.minX + CGFloat(drand48()) * 252, y: r.minY + CGFloat(drand48()) * 252, width: 4, height: 5))
        }
    }

    // (0,3) Architectural Glass + Safety Bars Reflection
    do {
        let r = cell(0, 3)
        ctx.setFillColor(rgb(0.24, 0.36, 0.48))
        ctx.fill(r)
        ctx.saveGState()
        ctx.clip(to: r)
        ctx.setFillColor(rgb(0.42, 0.58, 0.72, 0.35))
        ctx.beginPath()
        ctx.move(to: CGPoint(x: r.minX, y: r.minY + 140))
        ctx.addLine(to: CGPoint(x: r.minX + 160, y: r.minY))
        ctx.addLine(to: CGPoint(x: r.maxX, y: r.minY))
        ctx.addLine(to: CGPoint(x: r.minX, y: r.maxY))
        ctx.closePath()
        ctx.fillPath()
        // Fine lower safety guard bars
        ctx.setFillColor(rgb(0.75, 0.78, 0.80, 0.65))
        ctx.fill(CGRect(x: r.minX, y: r.minY + 166, width: 256, height: 5))
        for bx in stride(from: r.minX + 16, to: r.maxX, by: 24) {
            ctx.fill(CGRect(x: bx, y: r.minY + 168, width: 3, height: 88))
        }
        ctx.restoreGState()
    }

    // (1,3) Tree Canopy Foliage
    do {
        let r = cell(1, 3)
        ctx.setFillColor(rgb(0.22, 0.38, 0.20))
        ctx.fill(r)
        srand48(909)
        for _ in 0..<700 {
            let g = 0.28 + CGFloat(drand48() * 0.28)
            ctx.setFillColor(rgb(g * 0.65, g, g * 0.48, 0.75))
            let rad = 4.0 + CGFloat(drand48() * 8.0)
            ctx.fillEllipse(in: CGRect(x: r.minX + CGFloat(drand48()) * 246, y: r.minY + CGFloat(drand48()) * 246, width: rad, height: rad))
        }
    }

    // (2,3) Hutong Asphalt Pavement
    do {
        let r = cell(2, 3)
        ctx.setFillColor(rgb(0.28, 0.29, 0.31))
        ctx.fill(r)
        srand48(1010)
        for _ in 0..<1200 {
            let v = 0.22 + CGFloat(drand48() * 0.14)
            ctx.setFillColor(rgb(v, v, v + 0.01, 0.65))
            ctx.fill(CGRect(x: r.minX + CGFloat(drand48()) * 253, y: r.minY + CGFloat(drand48()) * 253, width: 3, height: 3))
        }
    }

    // (3,3) Skylight / Tensile Membrane Frosted Grid
    do {
        let r = cell(3, 3)
        ctx.setFillColor(rgb(0.92, 0.94, 0.97))
        ctx.fill(r)
        for gx in stride(from: r.minX, to: r.maxX, by: 64) {
            ctx.setFillColor(rgb(0.76, 0.80, 0.85))
            ctx.fill(CGRect(x: gx, y: r.minY, width: 4, height: 256))
        }
        for gy in stride(from: r.minY, to: r.maxY, by: 64) {
            ctx.setFillColor(rgb(0.76, 0.80, 0.85))
            ctx.fill(CGRect(x: r.minX, y: gy, width: 256, height: 4))
        }
    }

    try savePNG(rep, to: "\(outDir)/tex_surfaces.png")
}

// =========================================================================
// 4. tex_west_details.png (1024x1024, fine West Campus details + alpha tiles)
// =========================================================================
do {
    let (rep, ctx) = makeAtlasContext(size: 1024)
    ctx.clear(CGRect(x: 0, y: 0, width: 1024, height: 1024))

    // Tile 1: C-Wing 5-Story White Classical Column & Faces Bas-Relief (x: 8..312, y: 8..760)
    do {
        let r = CGRect(x: 8, y: 8, width: 304, height: 752)
        ctx.setFillColor(rgb(0.90, 0.90, 0.92, 1.0))
        ctx.fill(r)
        ctx.setStrokeColor(rgb(0.76, 0.77, 0.80, 1.0))
        ctx.setLineWidth(6)
        ctx.stroke(r.insetBy(dx: 4, dy: 4))

        // Recessed inner relief ground
        let inner = r.insetBy(dx: 14, dy: 14)
        ctx.setFillColor(rgb(0.86, 0.87, 0.89, 1.0))
        ctx.fill(inner)

        // Right-half Classical Fluted Ionic Column (x: 184..286, y: 34..736)
        let colShaft = CGRect(x: 192, y: 88, width: 88, height: 590)
        ctx.setFillColor(rgb(0.93, 0.93, 0.95, 1.0))
        ctx.fill(colShaft)
        for fi in 0..<7 {
            let fx = colShaft.minX + 6 + CGFloat(fi) * 11.2
            ctx.setFillColor(rgb(0.78, 0.79, 0.82, 1.0))
            ctx.fill(CGRect(x: fx, y: colShaft.minY + 6, width: 4.5, height: colShaft.height - 12))
            ctx.setFillColor(rgb(0.97, 0.97, 0.98, 1.0))
            ctx.fill(CGRect(x: fx + 4.5, y: colShaft.minY + 6, width: 3.5, height: colShaft.height - 12))
        }
        // Ionic Volute Capital at top of column
        ctx.setFillColor(rgb(0.94, 0.94, 0.96, 1.0))
        ctx.fill(CGRect(x: 178, y: 38, width: 116, height: 24))
        for vx in [188.0, 284.0] as [CGFloat] {
            let vol = CGRect(x: vx - 20, y: 50, width: 40, height: 40)
            ctx.setFillColor(rgb(0.80, 0.81, 0.84, 1.0))
            ctx.fillEllipse(in: vol.offsetBy(dx: 2, dy: 3))
            ctx.setFillColor(rgb(0.95, 0.95, 0.97, 1.0))
            ctx.fillEllipse(in: vol)
            ctx.setStrokeColor(rgb(0.76, 0.77, 0.80, 1.0))
            ctx.setLineWidth(3)
            ctx.strokeEllipse(in: vol.insetBy(dx: 8, dy: 8))
        }
        // Stepped Column Pedestal at bottom
        ctx.setFillColor(rgb(0.92, 0.92, 0.94, 1.0))
        ctx.fill(CGRect(x: 184, y: 678, width: 104, height: 24))
        ctx.fill(CGRect(x: 176, y: 702, width: 118, height: 34))
        // Small dark bronze dedication plaque at bottom right
        ctx.setFillColor(rgb(0.26, 0.24, 0.23, 1.0))
        ctx.fill(CGRect(x: 196, y: 710, width: 44, height: 22))

        // Sweeping Ribbon & Floral Reliefs (upper & mid left)
        ctx.saveGState()
        ctx.clip(to: inner)
        for (cy, c1y, c2y) in [(130.0, 60.0, 210.0), (260.0, 190.0, 340.0), (390.0, 320.0, 460.0)] as [(CGFloat, CGFloat, CGFloat)] {
            ctx.setStrokeColor(rgb(0.75, 0.76, 0.80, 0.85))
            ctx.setLineWidth(14)
            ctx.move(to: CGPoint(x: 24, y: cy + 3))
            ctx.addCurve(to: CGPoint(x: 205, y: cy + 38), control1: CGPoint(x: 85, y: c1y), control2: CGPoint(x: 145, y: c2y))
            ctx.strokePath()
            ctx.setStrokeColor(rgb(0.96, 0.96, 0.98, 0.95))
            ctx.setLineWidth(10)
            ctx.move(to: CGPoint(x: 24, y: cy))
            ctx.addCurve(to: CGPoint(x: 205, y: cy + 34), control1: CGPoint(x: 85, y: c1y - 4), control2: CGPoint(x: 145, y: c2y - 4))
            ctx.strokePath()
        }
        // Sculpted 5-petal blossoms along column edge
        for (bx, by, br) in [(76.0, 96.0, 24.0), (146.0, 178.0, 20.0), (178.0, 310.0, 22.0), (190.0, 368.0, 18.0), (168.0, 424.0, 22.0)] as [(CGFloat, CGFloat, CGFloat)] {
            for pi in 0..<5 {
                let ang = CGFloat(pi) * (.pi * 2.0 / 5.0)
                let px = bx + cos(ang) * br * 0.65
                let py = by + sin(ang) * br * 0.65
                ctx.setFillColor(rgb(0.77, 0.78, 0.82, 0.9))
                ctx.fillEllipse(in: CGRect(x: px - br * 0.45 + 2, y: py - br * 0.45 + 3, width: br * 0.9, height: br * 0.9))
                ctx.setFillColor(rgb(0.96, 0.96, 0.98, 1.0))
                ctx.fillEllipse(in: CGRect(x: px - br * 0.45, y: py - br * 0.45, width: br * 0.9, height: br * 0.9))
            }
            ctx.setFillColor(rgb(0.84, 0.85, 0.88, 1.0))
            ctx.fillEllipse(in: CGRect(x: bx - 6, y: by - 6, width: 12, height: 12))
        }

        // Three Overlapping Sculpted Youth Portrait Reliefs (lower-left: y 470..680)
        for (fx, fy, fw, fh, shade) in [
            (118.0, 488.0, 72.0, 118.0, 0.91),
            (84.0, 482.0, 76.0, 124.0, 0.94),
            (44.0, 476.0, 82.0, 132.0, 0.97)
        ] as [(CGFloat, CGFloat, CGFloat, CGFloat, CGFloat)] {
            // Drop shadow
            ctx.setFillColor(rgb(0.73, 0.74, 0.78, 0.9))
            ctx.fillEllipse(in: CGRect(x: fx + 4, y: fy + 5, width: fw, height: fh))
            // Sculpted head & hair cap
            ctx.setFillColor(rgb(shade, shade, shade + 0.01, 1.0))
            ctx.fillEllipse(in: CGRect(x: fx, y: fy, width: fw, height: fh))
            ctx.setFillColor(rgb(shade - 0.06, shade - 0.06, shade - 0.04, 1.0))
            ctx.fillEllipse(in: CGRect(x: fx - 2, y: fy - 4, width: fw + 4, height: fh * 0.42))
            // Subtle eye/brow/nose relief shadows
            ctx.setFillColor(rgb(0.76, 0.77, 0.80, 0.85))
            ctx.fill(CGRect(x: fx + fw * 0.22, y: fy + fh * 0.44, width: fw * 0.20, height: 5))
            ctx.fill(CGRect(x: fx + fw * 0.56, y: fy + fh * 0.44, width: fw * 0.20, height: 5))
            ctx.fill(CGRect(x: fx + fw * 0.44, y: fy + fh * 0.46, width: 6, height: fh * 0.20))
            ctx.fill(CGRect(x: fx + fw * 0.34, y: fy + fh * 0.74, width: fw * 0.28, height: 5))
        }
        // Lower floral/scroll base beneath portraits
        for bi in 0..<4 {
            let lx = 36.0 + CGFloat(bi) * 34.0
            ctx.setFillColor(rgb(0.94, 0.94, 0.96, 1.0))
            ctx.fillEllipse(in: CGRect(x: lx, y: 632, width: 42, height: 68))
            ctx.setStrokeColor(rgb(0.77, 0.78, 0.81, 1.0))
            ctx.setLineWidth(3)
            ctx.strokeEllipse(in: CGRect(x: lx, y: 632, width: 42, height: 68))
        }
        ctx.restoreGState()
    }

    // Tile 2: Dark Grey Slate Podium Veneer (x: 328..584, y: 8..264)
    do {
        let r = CGRect(x: 328, y: 8, width: 256, height: 256)
        ctx.setFillColor(rgb(0.24, 0.25, 0.27, 1.0))
        ctx.fill(r)
        srand48(2026)
        for row in 0..<8 {
            let y = r.minY + CGFloat(row) * 32
            let off: CGFloat = (row % 2 == 0) ? 0 : 32
            for bx in stride(from: -32.0 + off, to: 256.0, by: 64.0) {
                let d = CGFloat(drand48() * 0.07 - 0.035)
                let x0 = max(r.minX, r.minX + bx + 2)
                let w0 = min(60, r.maxX - x0)
                if w0 > 2 {
                    ctx.setFillColor(rgb(0.30 + d, 0.31 + d, 0.33 + d, 1.0))
                    ctx.fill(CGRect(x: x0, y: y + 2, width: w0, height: 28))
                }
            }
        }
    }

    // Tile 3: Tempered Glass Basketball Backboard with Opaque White Borders (x: 600..1016, y: 8..256, ALPHA)
    do {
        let r = CGRect(x: 600, y: 8, width: 416, height: 248)
        ctx.clear(r)
        ctx.setFillColor(rgb(0.76, 0.86, 0.92, 0.28))
        ctx.fill(r)
        // Diagonal sky sheen
        ctx.saveGState()
        ctx.clip(to: r)
        ctx.setFillColor(rgb(0.94, 0.98, 1.0, 0.20))
        ctx.beginPath()
        ctx.move(to: CGPoint(x: r.minX + 40, y: r.maxY))
        ctx.addLine(to: CGPoint(x: r.minX + 190, y: r.minY))
        ctx.addLine(to: CGPoint(x: r.minX + 275, y: r.minY))
        ctx.addLine(to: CGPoint(x: r.minX + 125, y: r.maxY))
        ctx.closePath()
        ctx.fillPath()
        ctx.restoreGState()
        // Crisp opaque white outer border + inner shooter's target square
        ctx.setStrokeColor(rgb(0.97, 0.98, 0.99, 0.98))
        ctx.setLineWidth(12)
        ctx.stroke(r.insetBy(dx: 10, dy: 10))
        let targetBox = CGRect(x: r.midX - 68, y: r.maxY - 122, width: 136, height: 96)
        ctx.setLineWidth(9)
        ctx.stroke(targetBox)
    }

    // Tile 4: Crazy-Paving Cracked-Ice Stone Medallion (x: 328..584, y: 276..532)
    do {
        let r = CGRect(x: 328, y: 276, width: 256, height: 256)
        // Warm granite border frame
        ctx.setFillColor(rgb(0.68, 0.62, 0.58, 1.0))
        ctx.fill(r)
        let inner = r.insetBy(dx: 22, dy: 22)
        ctx.setFillColor(rgb(0.74, 0.72, 0.69, 1.0))
        ctx.fill(inner)
        let polys: [[CGPoint]] = [
            [CGPoint(x: 4, y: 4), CGPoint(x: 86, y: 4), CGPoint(x: 72, y: 68), CGPoint(x: 4, y: 58)],
            [CGPoint(x: 92, y: 4), CGPoint(x: 162, y: 4), CGPoint(x: 148, y: 74), CGPoint(x: 78, y: 66)],
            [CGPoint(x: 168, y: 4), CGPoint(x: 208, y: 4), CGPoint(x: 208, y: 82), CGPoint(x: 154, y: 72)],
            [CGPoint(x: 4, y: 64), CGPoint(x: 72, y: 74), CGPoint(x: 88, y: 138), CGPoint(x: 4, y: 142)],
            [CGPoint(x: 78, y: 72), CGPoint(x: 150, y: 80), CGPoint(x: 138, y: 146), CGPoint(x: 94, y: 138)],
            [CGPoint(x: 156, y: 78), CGPoint(x: 208, y: 88), CGPoint(x: 208, y: 154), CGPoint(x: 144, y: 146)],
            [CGPoint(x: 4, y: 148), CGPoint(x: 88, y: 144), CGPoint(x: 74, y: 208), CGPoint(x: 4, y: 208)],
            [CGPoint(x: 94, y: 144), CGPoint(x: 142, y: 152), CGPoint(x: 152, y: 208), CGPoint(x: 80, y: 208)],
            [CGPoint(x: 148, y: 152), CGPoint(x: 208, y: 160), CGPoint(x: 208, y: 208), CGPoint(x: 158, y: 208)],
        ]
        for (pi, pts) in polys.enumerated() {
            let v = 0.25 + CGFloat(pi % 3) * 0.05
            ctx.setFillColor(rgb(v, v + 0.02, v + 0.04, 1.0))
            ctx.beginPath()
            for ( idx, p ) in pts.enumerated() {
                let gp = CGPoint(x: inner.minX + p.x, y: inner.minY + p.y)
                if idx == 0 { ctx.move(to: gp) } else { ctx.addLine(to: gp) }
            }
            ctx.closePath()
            ctx.fillPath()
        }
    }

    // Tile 5: White River Pebbles Tree Pit Bed (x: 600..792, y: 276..532)
    do {
        let r = CGRect(x: 600, y: 276, width: 192, height: 256)
        ctx.setFillColor(rgb(0.24, 0.22, 0.20, 1.0))
        ctx.fill(r)
        srand48(1116)
        for _ in 0..<420 {
            let px = r.minX + 6 + CGFloat(drand48()) * (r.width - 22)
            let py = r.minY + 6 + CGFloat(drand48()) * (r.height - 22)
            let pw = 7.0 + CGFloat(drand48()) * 9.0
            let ph = 5.0 + CGFloat(drand48()) * 7.0
            let v = 0.74 + CGFloat(drand48()) * 0.22
            ctx.setFillColor(rgb(v, v, v - 0.02, 0.95))
            ctx.fillEllipse(in: CGRect(x: px, y: py, width: pw, height: ph))
        }
    }

    // Tile 6A: Red Fire Extinguisher Box "灭火器箱 火警 119" (x: 808..1016, y: 276..412)
    do {
        let r = CGRect(x: 808, y: 276, width: 208, height: 136)
        ctx.setFillColor(rgb(0.84, 0.09, 0.10, 1.0))
        ctx.fill(r)
        ctx.setFillColor(rgb(0.62, 0.05, 0.06, 1.0))
        ctx.fill(CGRect(x: r.minX, y: r.minY, width: r.width, height: 12))
        ctx.setStrokeColor(rgb(0.95, 0.22, 0.22, 1.0))
        ctx.setLineWidth(3)
        ctx.stroke(r.insetBy(dx: 8, dy: 14))
        drawFlippedText("灭火器箱", in: CGRect(x: r.minX + 12, y: r.minY + 20, width: r.width - 24, height: 34), fontName: "PingFangSC-Semibold", size: 24, color: .white, align: .center, bold: true)
        drawFlippedText("FIRE EXTINGUISHER BOX", in: CGRect(x: r.minX + 8, y: r.minY + 54, width: r.width - 16, height: 16), fontName: "HelveticaNeue-Bold", size: 9.5, color: .white, align: .center, bold: true)
        drawFlippedText("火警 119", in: CGRect(x: r.minX + 12, y: r.minY + 84, width: r.width - 24, height: 28), fontName: "PingFangSC-Semibold", size: 20, color: .white, align: .center, bold: true)
    }

    // Tile 6B: Classroom Doorplate "高二(3)班" (x: 808..904, y: 420..532)
    do {
        let r = CGRect(x: 808, y: 420, width: 96, height: 112)
        ctx.setFillColor(rgb(0.93, 0.89, 0.76, 1.0))
        ctx.fill(r)
        ctx.setStrokeColor(rgb(0.68, 0.58, 0.34, 1.0))
        ctx.setLineWidth(3)
        ctx.stroke(r.insetBy(dx: 4, dy: 4))
        let crest = CGRect(x: r.midX - 11, y: r.minY + 10, width: 22, height: 22)
        ctx.setFillColor(rgb(0.10, 0.32, 0.56, 1.0))
        ctx.fillEllipse(in: crest)
        drawFlippedText("高二(3)班", in: CGRect(x: r.minX + 6, y: r.minY + 38, width: r.width - 12, height: 42), fontName: "PingFangSC-Semibold", size: 15, color: NSColor(white: 0.15, alpha: 1.0), align: .center, bold: true)
        drawFlippedText("P114", in: CGRect(x: r.minX + 6, y: r.minY + 82, width: r.width - 12, height: 20), fontName: "HelveticaNeue-Bold", size: 11, color: NSColor(white: 0.32, alpha: 1.0), align: .center)
    }

    // Tile 6C: Salmon-Pink Residential Accent Cladding (x: 912..1016, y: 420..532)
    do {
        let r = CGRect(x: 912, y: 420, width: 104, height: 112)
        ctx.setFillColor(rgb(0.87, 0.58, 0.49, 1.0))
        ctx.fill(r)
        for gy in stride(from: r.minY + 14, to: r.maxY, by: 18) {
            ctx.setFillColor(rgb(0.78, 0.49, 0.41, 0.65))
            ctx.fill(CGRect(x: r.minX, y: gy, width: r.width, height: 2))
        }
    }

    // Tile 7: School History Entrance Glazed Partition & Frosted Strip (x: 328..720, y: 544..768, ALPHA)
    do {
        let r = CGRect(x: 328, y: 544, width: 392, height: 224)
        ctx.clear(r)
        ctx.setFillColor(rgb(0.11, 0.15, 0.19, 0.64))
        ctx.fill(r)
        // Warm interior ambient reflection band
        ctx.setFillColor(rgb(0.72, 0.64, 0.46, 0.18))
        ctx.fill(CGRect(x: r.midX + 20, y: r.minY + 36, width: 140, height: 148))
        // Frosted horizontal safety band with school title
        let band = CGRect(x: r.minX, y: r.minY + 114, width: r.width, height: 24)
        ctx.setFillColor(rgb(0.84, 0.88, 0.90, 0.78))
        ctx.fill(band)
        drawFlippedText("北京市第一六六中学  ·  校史馆", in: band, fontName: "STKaiti", size: 15, color: NSColor(red: 0.14, green: 0.22, blue: 0.32, alpha: 0.95), align: .center, bold: true)
        // Red oval warning badge ("小心玻璃")
        let badge = CGRect(x: r.midX + 34, y: r.minY + 64, width: 46, height: 20)
        ctx.setFillColor(rgb(0.78, 0.14, 0.14, 0.92))
        ctx.fillEllipse(in: badge)
        ctx.setStrokeColor(rgb(0.96, 0.94, 0.90, 0.95))
        ctx.setLineWidth(1.5)
        ctx.strokeEllipse(in: badge.insetBy(dx: 2, dy: 2))
    }

    // Tile 8A: Track Lane Numbers "1" "2" "3" "4" (x: 736..1016, y: 548..656, ALPHA)
    for (idx, numStr) in ["1", "2", "3", "4"].enumerated() {
        let r = CGRect(x: 736 + idx * 70, y: 548, width: 68, height: 108)
        ctx.clear(r)
        drawFlippedText(numStr, in: r, fontName: "HelveticaNeue-Bold", size: 78, color: NSColor(white: 0.97, alpha: 0.92), align: .center, bold: true)
    }

    // Tile 8B: Split AC Outdoor Condenser Front Grille (x: 736..1016, y: 664..768)
    do {
        let r = CGRect(x: 736, y: 664, width: 280, height: 104)
        ctx.setFillColor(rgb(0.91, 0.91, 0.89, 1.0))
        ctx.fill(r)
        ctx.setStrokeColor(rgb(0.74, 0.75, 0.74, 1.0))
        ctx.setLineWidth(4)
        ctx.stroke(r.insetBy(dx: 3, dy: 3))
        let fan = CGRect(x: r.minX + 18, y: r.minY + 10, width: 84, height: 84)
        ctx.setFillColor(rgb(0.18, 0.20, 0.22, 1.0))
        ctx.fillEllipse(in: fan)
        for gy in stride(from: fan.minY + 6, to: fan.maxY - 4, by: 7) {
            ctx.setFillColor(rgb(0.68, 0.70, 0.72, 0.75))
            ctx.fill(CGRect(x: fan.minX + 6, y: gy, width: fan.width - 12, height: 2))
        }
        ctx.setFillColor(rgb(0.76, 0.77, 0.76, 1.0))
        ctx.fill(CGRect(x: r.minX + 196, y: r.minY + 8, width: 3, height: r.height - 16))
        ctx.setFillColor(rgb(0.16, 0.36, 0.62, 1.0))
        ctx.fill(CGRect(x: r.minX + 218, y: r.minY + 22, width: 36, height: 12))
    }

    // Tile 9A: Warm Ochre-Beige Rusticated Facade for 灯市口小学 North Building (x: 8..256, y: 780..1016)
    do {
        let r = CGRect(x: 8, y: 780, width: 248, height: 236)
        ctx.setFillColor(rgb(0.81, 0.74, 0.55, 1.0))
        ctx.fill(r)
        for gy in stride(from: r.minY + 12, to: r.maxY, by: 22) {
            ctx.setFillColor(rgb(0.70, 0.63, 0.45, 0.85))
            ctx.fill(CGRect(x: r.minX, y: gy, width: r.width, height: 3))
            ctx.setFillColor(rgb(0.87, 0.81, 0.63, 0.65))
            ctx.fill(CGRect(x: r.minX, y: gy + 3, width: r.width, height: 2))
        }
    }

    // Tile 9B: Cream Facade with Terracotta Red Diamond Medallion for 灯市口小学 South Annex (x: 268..516, y: 780..1016)
    do {
        let r = CGRect(x: 268, y: 780, width: 248, height: 236)
        ctx.setFillColor(rgb(0.89, 0.88, 0.79, 1.0))
        ctx.fill(r)
        ctx.setStrokeColor(rgb(0.80, 0.79, 0.70, 1.0))
        ctx.setLineWidth(4)
        ctx.stroke(r.insetBy(dx: 8, dy: 8))
        let cx = r.midX, cy = r.midY, dr: CGFloat = 34
        ctx.setFillColor(rgb(0.68, 0.28, 0.24, 1.0))
        ctx.beginPath()
        ctx.move(to: CGPoint(x: cx, y: cy - dr))
        ctx.addLine(to: CGPoint(x: cx + dr, y: cy))
        ctx.addLine(to: CGPoint(x: cx, y: cy + dr))
        ctx.addLine(to: CGPoint(x: cx - dr, y: cy))
        ctx.closePath()
        ctx.fillPath()
    }

    // Tile 10: Cobalt-Blue Glazed Barrel Tile Roof (x: 528..768, y: 780..1016)
    do {
        let r = CGRect(x: 528, y: 780, width: 240, height: 236)
        ctx.setFillColor(rgb(0.14, 0.39, 0.68, 1.0))
        ctx.fill(r)
        for gx in stride(from: r.minX, to: r.maxX, by: 16) {
            ctx.setFillColor(rgb(0.22, 0.50, 0.82, 1.0))
            ctx.fill(CGRect(x: gx + 2, y: r.minY, width: 8, height: r.height))
            ctx.setFillColor(rgb(0.09, 0.27, 0.49, 1.0))
            ctx.fill(CGRect(x: gx + 11, y: r.minY, width: 4, height: r.height))
        }
    }

    // Tile 11A: Outdoor Ping-Pong Table Royal-Blue Top (x: 780..1016, y: 780..896)
    do {
        let r = CGRect(x: 780, y: 780, width: 236, height: 116)
        ctx.setFillColor(rgb(0.12, 0.35, 0.66, 1.0))
        ctx.fill(r)
        ctx.setStrokeColor(rgb(0.96, 0.97, 0.99, 1.0))
        ctx.setLineWidth(5)
        ctx.stroke(r.insetBy(dx: 7, dy: 7))
        ctx.setFillColor(rgb(0.96, 0.97, 0.99, 1.0))
        ctx.fill(CGRect(x: r.minX + 7, y: r.midY - 1.5, width: r.width - 14, height: 3))
        ctx.fill(CGRect(x: r.midX - 2, y: r.minY + 7, width: 4, height: r.height - 14))
    }

    // Tile 11B: Volleyball Net Mesh with White Top Band (x: 780..1016, y: 904..1016, ALPHA)
    do {
        let r = CGRect(x: 780, y: 904, width: 236, height: 112)
        ctx.clear(r)
        ctx.setFillColor(rgb(0.10, 0.12, 0.14, 0.14))
        ctx.fill(r)
        for gx in stride(from: r.minX + 4, to: r.maxX, by: 10) {
            ctx.setFillColor(rgb(0.12, 0.13, 0.15, 0.78))
            ctx.fill(CGRect(x: gx, y: r.minY + 14, width: 2, height: r.height - 20))
        }
        for gy in stride(from: r.minY + 20, to: r.maxY - 6, by: 10) {
            ctx.setFillColor(rgb(0.12, 0.13, 0.15, 0.78))
            ctx.fill(CGRect(x: r.minX, y: gy, width: r.width, height: 2))
        }
        // Crisp white top canvas tape & bottom cord
        ctx.setFillColor(rgb(0.97, 0.97, 0.98, 0.98))
        ctx.fill(CGRect(x: r.minX, y: r.minY + 4, width: r.width, height: 11))
        ctx.fill(CGRect(x: r.minX, y: r.maxY - 7, width: r.width, height: 5))
    }

    try savePNG(rep, to: "\(outDir)/tex_west_details.png")
}

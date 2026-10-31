// Store-style framing for scripts/screenshots.sh.
// Usage: frame_screenshot <screenshot.png> <out.png> <title> [subtitle]
// Draws the screenshot inside an iPhone frame (bezel, rounded screen, Dynamic
// Island, side buttons) on the app's background, with a headline above it.
import Foundation
import AppKit

guard CommandLine.arguments.count > 3 else {
  fputs("usage: frame_screenshot <image> <out> <title> [subtitle]\n", stderr)
  exit(2)
}

let inURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outURL = URL(fileURLWithPath: CommandLine.arguments[2])
let title = CommandLine.arguments[3]
let subtitle = CommandLine.arguments.count > 4 ? CommandLine.arguments[4] : ""

guard
  let image = NSImage(contentsOf: inURL),
  let shot = image.cgImage(forProposedRect: nil, context: nil, hints: nil)
else {
  fputs("error: cannot load \(inURL.path)\n", stderr)
  exit(2)
}

func hex(_ value: UInt32, _ alpha: CGFloat = 1) -> CGColor {
  CGColor(
    srgbRed: CGFloat((value >> 16) & 0xFF) / 255,
    green: CGFloat((value >> 8) & 0xFF) / 255,
    blue: CGFloat(value & 0xFF) / 255,
    alpha: alpha)
}

// Palette from src/presentation/theme/colors.ts
let backgroundTop = hex(0x1E1650)
let backgroundBottom = hex(0x140E36)
let orange = hex(0xFF9D2C)
let text = NSColor(cgColor: hex(0xF5F3FF))!
let textMuted = NSColor(cgColor: hex(0xA9A4C7))!
let titanium = hex(0x3A3A40)
let titaniumEdge = hex(0x6B6B74)

// Canvas: portrait panel, about 3x the size it is shown at in the README
let width: CGFloat = 600
let height: CGFloat = 1300
let colorSpace = CGColorSpace(name: CGColorSpace.sRGB)!
guard
  let ctx = CGContext(
    data: nil, width: Int(width), height: Int(height), bitsPerComponent: 8, bytesPerRow: 0,
    space: colorSpace, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)
else {
  fputs("error: cannot create canvas\n", stderr)
  exit(2)
}
ctx.interpolationQuality = .high

// --- background (origin is bottom-left) --------------------------------------

let gradient = CGGradient(
  colorsSpace: colorSpace, colors: [backgroundTop, backgroundBottom] as CFArray,
  locations: [0, 1])!
ctx.drawLinearGradient(
  gradient, start: CGPoint(x: 0, y: height), end: CGPoint(x: 0, y: 0), options: [])

let glow = CGGradient(
  colorsSpace: colorSpace, colors: [hex(0xFF9D2C, 0.22), hex(0xFF9D2C, 0)] as CFArray,
  locations: [0, 1])!
ctx.drawRadialGradient(
  glow, startCenter: CGPoint(x: width / 2, y: height * 0.38), startRadius: 0,
  endCenter: CGPoint(x: width / 2, y: height * 0.38), endRadius: width * 0.75, options: [])

// --- headline ----------------------------------------------------------------

NSGraphicsContext.current = NSGraphicsContext(cgContext: ctx, flipped: false)

let centered = NSMutableParagraphStyle()
centered.alignment = .center
centered.lineBreakMode = .byWordWrapping

func drawText(_ string: String, font: NSFont, color: NSColor, top: CGFloat) -> CGFloat {
  let attributes: [NSAttributedString.Key: Any] = [
    .font: font, .foregroundColor: color, .paragraphStyle: centered,
  ]
  let box = CGSize(width: width - 64, height: .greatestFiniteMagnitude)
  let size = (string as NSString).boundingRect(
    with: box, options: [.usesLineFragmentOrigin], attributes: attributes
  ).size
  let rect = CGRect(x: 32, y: height - top - ceil(size.height), width: width - 64, height: ceil(size.height))
  (string as NSString).draw(with: rect, options: [.usesLineFragmentOrigin], attributes: attributes)
  return top + ceil(size.height)
}

var cursor: CGFloat = 70
cursor = drawText(title, font: .systemFont(ofSize: 46, weight: .heavy), color: text, top: cursor)
if !subtitle.isEmpty {
  cursor = drawText(subtitle, font: .systemFont(ofSize: 24, weight: .medium), color: textMuted, top: cursor + 12)
}

// Short orange rule under the headline, like the app's active tab
ctx.setFillColor(orange)
ctx.addPath(CGPath(
  roundedRect: CGRect(x: width / 2 - 28, y: height - cursor - 30, width: 56, height: 6),
  cornerWidth: 3, cornerHeight: 3, transform: nil))
ctx.fillPath()

// --- device ------------------------------------------------------------------

let screenAspect = CGFloat(shot.height) / CGFloat(shot.width)
let bottomMargin: CGFloat = 56
let available = height - (cursor + 70) - bottomMargin
let bezel: CGFloat = 13
var screenWidth = width * 0.72
if screenWidth * screenAspect + bezel * 2 > available {
  screenWidth = (available - bezel * 2) / screenAspect
}
let screenHeight = screenWidth * screenAspect
let screenRadius = screenWidth * 0.135
let screen = CGRect(
  x: (width - screenWidth) / 2, y: bottomMargin + bezel, width: screenWidth, height: screenHeight)
let body = screen.insetBy(dx: -bezel, dy: -bezel)
let bodyRadius = screenRadius + bezel

// Side buttons: action + volume on the left, power on the right
ctx.setFillColor(titaniumEdge)
for (y, h) in [(0.80, 0.045), (0.71, 0.075), (0.62, 0.075)] {
  ctx.addPath(CGPath(
    roundedRect: CGRect(x: body.minX - 4, y: body.minY + body.height * y, width: 6, height: body.height * h),
    cornerWidth: 2, cornerHeight: 2, transform: nil))
}
ctx.addPath(CGPath(
  roundedRect: CGRect(x: body.maxX - 2, y: body.minY + body.height * 0.66, width: 6, height: body.height * 0.11),
  cornerWidth: 2, cornerHeight: 2, transform: nil))
ctx.fillPath()

// Body with a soft drop shadow, a lighter rim and a black bezel
ctx.saveGState()
ctx.setShadow(offset: CGSize(width: 0, height: -18), blur: 40, color: hex(0x000000, 0.55))
ctx.setFillColor(titanium)
ctx.addPath(CGPath(roundedRect: body, cornerWidth: bodyRadius, cornerHeight: bodyRadius, transform: nil))
ctx.fillPath()
ctx.restoreGState()

ctx.setStrokeColor(titaniumEdge)
ctx.setLineWidth(1.5)
ctx.addPath(CGPath(
  roundedRect: body.insetBy(dx: 0.75, dy: 0.75), cornerWidth: bodyRadius, cornerHeight: bodyRadius,
  transform: nil))
ctx.strokePath()

let bezelRect = body.insetBy(dx: 4, dy: 4)
ctx.setFillColor(hex(0x000000))
ctx.addPath(CGPath(
  roundedRect: bezelRect, cornerWidth: bodyRadius - 4, cornerHeight: bodyRadius - 4, transform: nil))
ctx.fillPath()

// Screenshot clipped to the rounded display
ctx.saveGState()
ctx.addPath(CGPath(roundedRect: screen, cornerWidth: screenRadius, cornerHeight: screenRadius, transform: nil))
ctx.clip()
ctx.draw(shot, in: screen)
ctx.restoreGState()

// Dynamic Island
let islandWidth = screenWidth * 0.31
let islandHeight = screenWidth * 0.09
let island = CGRect(
  x: screen.midX - islandWidth / 2, y: screen.maxY - screenWidth * 0.03 - islandHeight,
  width: islandWidth, height: islandHeight)
ctx.setFillColor(hex(0x000000))
ctx.addPath(CGPath(
  roundedRect: island, cornerWidth: islandHeight / 2, cornerHeight: islandHeight / 2, transform: nil))
ctx.fillPath()

// --- write -------------------------------------------------------------------

guard
  let output = ctx.makeImage(),
  let png = NSBitmapImageRep(cgImage: output).representation(using: .png, properties: [:])
else {
  fputs("error: cannot encode PNG\n", stderr)
  exit(2)
}
do {
  try png.write(to: outURL)
} catch {
  fputs("error: cannot write \(outURL.path): \(error)\n", stderr)
  exit(2)
}

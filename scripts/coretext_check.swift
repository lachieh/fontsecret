// Shape and draw text with CoreText, the engine Ghostty, iTerm2 and TextEdit use on macOS.
//
//   swift scripts/coretext_check.swift POSTSCRIPT_NAME [FEATURE_TAG] OUT.png < lines.txt
//
// Prints each line as drawn (• for a mask glyph) and writes an offscreen render to OUT.png.
// Offscreen drawing needs no Screen Recording permission.
import CoreText
import Foundation
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
let psName = args[1]
let tag: String? = args.count > 3 ? args[2] : nil
let out = args.last!

var attributes: [CFString: Any] = [kCTFontNameAttribute: psName]
if let tag {
    attributes[kCTFontFeatureSettingsAttribute] = [
        [kCTFontOpenTypeFeatureTag: tag, kCTFontOpenTypeFeatureValue: 1]
    ]
}
let descriptor = CTFontDescriptorCreateWithAttributes(attributes as CFDictionary)
let font = CTFontCreateWithFontDescriptor(descriptor, 28, nil)
let resolved = CTFontCopyPostScriptName(font) as String
guard resolved == psName else {
    print("font not found: asked for \(psName), CoreText gave \(resolved)")
    exit(1)
}

let lines = String(data: FileHandle.standardInput.readDataToEndOfFile(), encoding: .utf8)!
    .split(separator: "\n", omittingEmptySubsequences: false).map(String.init).filter { !$0.isEmpty }

var ctLines: [CTLine] = []
for text in lines {
    let attributed = NSAttributedString(
        string: text,
        attributes: [
            NSAttributedString.Key(kCTFontAttributeName as String): font,
            NSAttributedString.Key(kCTForegroundColorAttributeName as String): CGColor(red: 0.91, green: 0.9, blue: 0.89, alpha: 1),
        ])
    let line = CTLineCreateWithAttributedString(attributed)
    ctLines.append(line)
    // Rebuild the line from glyphs: a character whose glyph is a mask shows as •.
    var drawn = Array(text.utf16).map { _ in "?" }
    let utf16 = Array(text.utf16)
    for run in CTLineGetGlyphRuns(line) as! [CTRun] {
        let count = CTRunGetGlyphCount(run)
        var glyphs = [CGGlyph](repeating: 0, count: count)
        var indices = [CFIndex](repeating: 0, count: count)
        CTRunGetGlyphs(run, CFRange(location: 0, length: count), &glyphs)
        CTRunGetStringIndices(run, CFRange(location: 0, length: count), &indices)
        let runFont = (CTRunGetAttributes(run) as NSDictionary)[kCTFontAttributeName] as! CTFont
        for (glyph, index) in zip(glyphs, indices) {
            let name = CTFontCopyNameForGlyph(runFont, glyph) as String? ?? ""
            drawn[index] = name.hasPrefix("sm.mask.") ? "•" : String(utf16CodeUnits: [utf16[index]], count: 1)
        }
    }
    // Characters merged into a ligature have no glyph of their own; show them as typed.
    for (i, ch) in drawn.enumerated() where ch == "?" { drawn[i] = String(utf16CodeUnits: [utf16[i]], count: 1) }
    print(drawn.joined())
}

let width = 1200, lineHeight = 40, height = lineHeight * ctLines.count + 40
let context = CGContext(
    data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0,
    space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
context.setFillColor(CGColor(red: 0.12, green: 0.12, blue: 0.14, alpha: 1))
context.fill(CGRect(x: 0, y: 0, width: width, height: height))
context.setFillColor(CGColor(red: 0.91, green: 0.9, blue: 0.89, alpha: 1))
for (i, line) in ctLines.enumerated() {
    context.textPosition = CGPoint(x: 24, y: height - 40 - i * lineHeight)
    CTLineDraw(line, context)
}
let image = context.makeImage()!
let dest = CGImageDestinationCreateWithURL(
    URL(fileURLWithPath: out) as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dest, image, nil)
CGImageDestinationFinalize(dest)

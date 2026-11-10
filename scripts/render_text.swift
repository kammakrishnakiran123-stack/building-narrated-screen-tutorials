// Draws text blocks as transparent PNGs with CoreText, so Indic and other complex scripts shape correctly.
// Input JSON: [{"out": path, "w": 800, "h": 400, "header": str, "body": str, "header_px": 24, "body_px": 34,
//               "min_px": 20, "header_rgb": [r,g,b], "body_rgb": [r,g,b], "align": "center" | "left"}]
// The header sits at the top, the body directly under it; the body font shrinks until the block fits in h.
import AppKit

func num(_ v: Any?, _ d: Double) -> CGFloat { CGFloat((v as? NSNumber)?.doubleValue ?? d) }
func col(_ v: Any?) -> NSColor {
    let a = (v as? [NSNumber]) ?? [255, 255, 255]
    return NSColor(deviceRed: CGFloat(a[0].doubleValue) / 255, green: CGFloat(a[1].doubleValue) / 255,
                   blue: CGFloat(a[2].doubleValue) / 255, alpha: 1)
}

let data = try! Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let jobs = try! JSONSerialization.jsonObject(with: data) as! [[String: Any]]
let opts: NSString.DrawingOptions = [.usesLineFragmentOrigin]
for j in jobs {
    let w = Int(num(j["w"], 800)), h = Int(num(j["h"], 400))
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: w, pixelsHigh: h, bitsPerSample: 8, samplesPerPixel: 4,
                               hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let ps = NSMutableParagraphStyle()
    ps.alignment = (j["align"] as? String) == "left" ? .left : .center
    ps.lineBreakMode = .byWordWrapping
    ps.lineSpacing = 4
    let width = CGFloat(w)
    var top = CGFloat(h)
    var bpx = num(j["body_px"], 34)
    let header = j["header"] as? String ?? "", body = j["body"] as? String ?? ""
    if !header.isEmpty {
        let hs = NSAttributedString(string: header, attributes: [
            .font: NSFont.systemFont(ofSize: num(j["header_px"], 24), weight: .bold),
            .foregroundColor: col(j["header_rgb"]), .paragraphStyle: ps])
        let hr = hs.boundingRect(with: NSSize(width: width, height: 10000), options: opts)
        hs.draw(with: NSRect(x: 0, y: top - ceil(hr.height), width: width, height: ceil(hr.height)), options: opts)
        top -= ceil(hr.height) + bpx * 0.3
    }
    if !body.isEmpty {
        let minPx = num(j["min_px"], 20)
        var bs: NSAttributedString
        var br: NSRect
        while true {
            bs = NSAttributedString(string: body, attributes: [
                .font: NSFont.systemFont(ofSize: bpx, weight: .medium),
                .foregroundColor: col(j["body_rgb"]), .paragraphStyle: ps])
            br = bs.boundingRect(with: NSSize(width: width, height: 10000), options: opts)
            if br.height <= top || bpx <= minPx { break }
            bpx -= 2
        }
        bs.draw(with: NSRect(x: 0, y: top - ceil(br.height), width: width, height: ceil(br.height)), options: opts)
    }
    NSGraphicsContext.restoreGraphicsState()
    try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: j["out"] as! String))
}
print("rendered \(jobs.count)")

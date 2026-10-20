// OCR helper for scripts/screenshots.sh.
// Usage: verify_screen <screenshot.png> <expected substring>
// Prints recognized text and exits 1 when the expected text is missing.
import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 2 else {
  fputs("usage: verify_screen <image> <expected>\n", stderr)
  exit(2)
}

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
let expected = CommandLine.arguments[2]

guard
  let image = NSImage(contentsOf: imageURL),
  let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil)
else {
  fputs("error: cannot load \(imageURL.path)\n", stderr)
  exit(2)
}

var lines: [String] = []

let request = VNRecognizeTextRequest { request, _ in
  guard let observations = request.results as? [VNRecognizedTextObservation] else {
    return
  }
  for observation in observations {
    if let candidate = observation.topCandidates(1).first {
      lines.append(candidate.string)
    }
  }
}
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false

try? VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])

let text = lines.joined(separator: "\n")
print(text)

if !text.localizedCaseInsensitiveContains(expected) {
  fputs("error: expected text not found: \(expected)\n", stderr)
  exit(1)
}

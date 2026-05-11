import AppKit
import Foundation
import ApplicationServices
import Vision

enum QwenDesktopError: Error, CustomStringConvertible {
    case appNotRunning
    case mainWindowNotFound
    case inputBoxNotFound
    case invalidImagePath(String)
    case invalidCommand(String)

    var description: String {
        switch self {
        case .appNotRunning:
            return "Qianwen 桌面客户端未运行。"
        case .mainWindowNotFound:
            return "未找到 Qianwen 主窗口。"
        case .inputBoxNotFound:
            return "未找到 Qianwen 输入框。"
        case let .invalidImagePath(message):
            return message
        case let .invalidCommand(message):
            return message
        }
    }
}

struct QwenSendResult: Codable {
    let ok: Bool
    let status: String
    let reason: String
    let submitted: Bool
    let answer_text: String
    let transcript_text: String
    let interaction_policy: QwenInteractionPolicy
}

struct QwenInteractionPolicy: Codable {
    let mode: String
    let control_surface: String
    let may_steal_focus: Bool
    let uses_global_mouse: Bool
    let uses_global_keyboard: Bool
    let uses_clipboard: Bool
}

struct QwenDiagnoseResult: Codable {
    let ok: Bool
    let env_pid: Int32?
    let env_bounds: String?
    let nsworkspace_pid: Int32?
    let system_events_pid: Int32?
    let resolved_pid: Int32?
    let window_count: Int
    let sample_windows: [String]
    let qwen_window_count: Int
    let qwen_windows: [String]
}

private let qwenBundleIds: Set<String> = ["com.alibaba.tongyi"]
private let qwenNames: Set<String> = ["Qianwen", "千问", "Qwen", "通义千问"]
private let noninteractivePolicy = QwenInteractionPolicy(
    mode: "noninteractive_applescript_javascript",
    control_surface: "qianwen_applescript_execute_javascript",
    may_steal_focus: false,
    uses_global_mouse: false,
    uses_global_keyboard: false,
    uses_clipboard: false
)
private let interactivePolicy = QwenInteractionPolicy(
    mode: "interactive_ax",
    control_surface: "accessibility_plus_hid_events",
    may_steal_focus: true,
    uses_global_mouse: true,
    uses_global_keyboard: true,
    uses_clipboard: true
)
private let imageUploadPolicy = QwenInteractionPolicy(
    mode: "interactive_image_upload_ax",
    control_surface: "accessibility_clipboard_image_upload",
    may_steal_focus: true,
    uses_global_mouse: false,
    uses_global_keyboard: true,
    uses_clipboard: true
)
private let imageUploadCoordinatePolicy = QwenInteractionPolicy(
    mode: "interactive_image_upload_coordinate",
    control_surface: "coordinate_clipboard_image_upload",
    may_steal_focus: true,
    uses_global_mouse: true,
    uses_global_keyboard: true,
    uses_clipboard: true
)

private func makeSendResult(
    ok: Bool,
    status: String,
    reason: String,
    submitted: Bool,
    answerText: String,
    transcriptText: String,
    policy: QwenInteractionPolicy
) -> QwenSendResult {
    QwenSendResult(
        ok: ok,
        status: status,
        reason: reason,
        submitted: submitted,
        answer_text: answerText,
        transcript_text: transcriptText,
        interaction_policy: policy
    )
}

private func copyAttribute(_ element: AXUIElement, name: String) -> Any? {
    var value: CFTypeRef?
    guard AXUIElementCopyAttributeValue(element, name as CFString, &value) == .success else {
        return nil
    }
    return value
}

private func children(of element: AXUIElement) -> [AXUIElement] {
    guard let raw = copyAttribute(element, name: kAXChildrenAttribute as String) as? [Any] else {
        return []
    }
    return raw.compactMap { $0 as! AXUIElement? }
}

private func windows(of element: AXUIElement) -> [AXUIElement] {
    if let raw = copyAttribute(element, name: kAXWindowsAttribute as String) as? [Any] {
        return raw.compactMap { $0 as! AXUIElement? }
    }
    return children(of: element).filter {
        (copyAttribute($0, name: kAXRoleAttribute as String) as? String) == kAXWindowRole as String
    }
}

private func collectElements(
    from element: AXUIElement,
    roles: Set<String>,
    depth: Int = 0,
    maxDepth: Int = 40,
    output: inout [AXUIElement]
) {
    if let currentRole = copyAttribute(element, name: kAXRoleAttribute as String) as? String,
       roles.contains(currentRole) {
        output.append(element)
    }
    if depth >= maxDepth {
        return
    }
    for child in children(of: element) {
        collectElements(from: child, roles: roles, depth: depth + 1, maxDepth: maxDepth, output: &output)
    }
}

private func isValueSettable(_ element: AXUIElement) -> Bool {
    var settable = DarwinBoolean(false)
    guard AXUIElementIsAttributeSettable(
        element,
        kAXValueAttribute as CFString,
        &settable
    ) == .success else {
        return false
    }
    return settable.boolValue
}

private func collectComposerCandidates(
    from element: AXUIElement,
    depth: Int = 0,
    maxDepth: Int = 50,
    output: inout [AXUIElement]
) {
    let role = stringAttribute(element, name: kAXRoleAttribute as String)
    let label = elementLabel(element)
    let roleLooksEditable = [
        kAXTextAreaRole as String,
        kAXTextFieldRole as String,
        "AXTextArea",
        "AXTextField",
    ].contains(role)
    let labelLooksEditable = label.contains("向千问提问")
        || label.contains("问千问")
        || label.contains("输入问题或任务")
        || label.contains("输入消息")
        || label.contains("和千问")
        || label.lowercased().contains("ask qwen")
        || label.lowercased().contains("ask qianwen")
    if roleLooksEditable || labelLooksEditable || isValueSettable(element) {
        output.append(element)
    }
    if depth >= maxDepth {
        return
    }
    for child in children(of: element) {
        collectComposerCandidates(from: child, depth: depth + 1, maxDepth: maxDepth, output: &output)
    }
}

private func stringAttribute(_ element: AXUIElement, name: String) -> String {
    if let value = copyAttribute(element, name: name) as? String {
        return value
    }
    return ""
}

private func elementLabel(_ element: AXUIElement) -> String {
    let names = [
        kAXTitleAttribute as String,
        kAXDescriptionAttribute as String,
        kAXHelpAttribute as String,
        kAXValueAttribute as String,
        "AXPlaceholderValue",
    ]
    return names.map { stringAttribute(element, name: $0) }
        .filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        .joined(separator: " ")
}

private func cgPointAttribute(_ element: AXUIElement, name: String) -> CGPoint? {
    guard let value = copyAttribute(element, name: name) else {
        return nil
    }
    let axValue = value as! AXValue
    guard AXValueGetType(axValue) == .cgPoint else {
        return nil
    }
    var point = CGPoint.zero
    guard AXValueGetValue(axValue, .cgPoint, &point) else {
        return nil
    }
    return point
}

private func cgSizeAttribute(_ element: AXUIElement, name: String) -> CGSize? {
    guard let value = copyAttribute(element, name: name) else {
        return nil
    }
    let axValue = value as! AXValue
    guard AXValueGetType(axValue) == .cgSize else {
        return nil
    }
    var size = CGSize.zero
    guard AXValueGetValue(axValue, .cgSize, &size) else {
        return nil
    }
    return size
}

private func elementRect(_ element: AXUIElement) -> CGRect? {
    guard let position = cgPointAttribute(element, name: kAXPositionAttribute as String),
          let size = cgSizeAttribute(element, name: kAXSizeAttribute as String),
          size.width > 0,
          size.height > 0
    else {
        return nil
    }
    return CGRect(origin: position, size: size)
}

private func qwenApp() -> NSRunningApplication? {
    let apps = NSWorkspace.shared.runningApplications.filter { app in
        if let bundleIdentifier = app.bundleIdentifier,
           qwenBundleIds.contains(bundleIdentifier) || bundleIdentifier.lowercased().contains("tongyi") {
            return true
        }
        if let name = app.localizedName {
            return qwenNames.contains(name) || name.lowercased().contains("qianwen") || name.lowercased().contains("qwen")
        }
        return false
    }
    return apps.first(where: { $0.bundleIdentifier == "com.alibaba.tongyi" }) ?? apps.first
}

private func qwenEnvPid() -> pid_t? {
    guard let value = ProcessInfo.processInfo.environment["QWEN_DESKTOP_PID"],
          let raw = Int32(value),
          raw > 0
    else {
        return nil
    }
    return raw
}

private func qwenEnvBounds() -> CGRect? {
    guard let value = ProcessInfo.processInfo.environment["QWEN_DESKTOP_BOUNDS"] else {
        return nil
    }
    let parts = value.split(separator: ",").compactMap { Double($0.trimmingCharacters(in: .whitespacesAndNewlines)) }
    guard parts.count == 4, parts[2] > 120, parts[3] > 120 else {
        return nil
    }
    return CGRect(x: parts[0], y: parts[1], width: parts[2], height: parts[3])
}

private func qwenSystemEventsPid() -> pid_t? {
    let script = """
    tell application "System Events"
      set matches to every application process whose bundle identifier is "com.alibaba.tongyi"
      if (count of matches) is 0 then set matches to every application process whose name is "Qianwen"
      if (count of matches) is 0 then set matches to every application process whose name is "千问"
      if (count of matches) is 0 then set matches to every application process whose name is "Qwen"
      if (count of matches) is 0 then return ""
      return unix id of item 1 of matches as text
    end tell
    """
    let process = Process()
    let stdout = Pipe()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
    process.arguments = ["-e", script]
    process.standardOutput = stdout
    process.standardError = Pipe()
    do {
        try process.run()
        let deadline = Date().addingTimeInterval(4.0)
        while process.isRunning && Date() < deadline {
            Thread.sleep(forTimeInterval: 0.05)
        }
        if process.isRunning {
            process.terminate()
            process.waitUntilExit()
            return nil
        }
        process.waitUntilExit()
    } catch {
        return nil
    }
    guard process.terminationStatus == 0 else {
        return nil
    }
    let data = stdout.fileHandleForReading.readDataToEndOfFile()
    let value = String(data: data, encoding: .utf8)?
        .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    guard let raw = Int32(value), raw > 0 else {
        return nil
    }
    return raw
}

private func qwenPid() -> pid_t? {
    if let pid = qwenEnvPid() {
        return pid
    }
    if let pid = qwenApp()?.processIdentifier {
        return pid
    }
    if let pid = qwenSystemEventsPid() {
        return pid
    }
    guard let infoList = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else {
        return nil
    }
    let target = infoList.first { info in
        guard let ownerName = info[kCGWindowOwnerName as String] as? String else {
            return false
        }
        return qwenNames.contains(ownerName) || ownerName.lowercased().contains("qianwen") || ownerName.lowercased().contains("qwen")
    }
    return (target?[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value
}

private func qwenRunningApplication() -> NSRunningApplication? {
    if let app = qwenApp() {
        return app
    }
    if let pid = qwenPid() {
        return NSRunningApplication(processIdentifier: pid)
    }
    return nil
}

private func activateProcessViaSystemEvents(pid: pid_t) -> Bool {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
    process.arguments = [
        "-e",
        "tell application \"System Events\" to set frontmost of first application process whose unix id is \(pid) to true",
    ]
    process.standardOutput = Pipe()
    process.standardError = Pipe()
    do {
        try process.run()
        process.waitUntilExit()
        return process.terminationStatus == 0
    } catch {
        return false
    }
}

private func activateQwen() throws {
    if let app = qwenRunningApplication() {
        if #available(macOS 14.0, *) {
            app.activate()
        } else {
            app.activate(options: [.activateIgnoringOtherApps])
        }
        Thread.sleep(forTimeInterval: 0.35)
        return
    }
    if let pid = qwenPid() {
        _ = activateProcessViaSystemEvents(pid: pid)
        Thread.sleep(forTimeInterval: 0.35)
        return
    }
    throw QwenDesktopError.appNotRunning
}

private func mainWindowElement() throws -> AXUIElement {
    guard let pid = qwenPid() else {
        throw QwenDesktopError.appNotRunning
    }
    let app = AXUIElementCreateApplication(pid)
    let candidates = windows(of: app)
    if let focused = candidates.first(where: {
        (copyAttribute($0, name: kAXFocusedAttribute as String) as? Bool) == true
    }) {
        return focused
    }
    guard let window = candidates.first else {
        throw QwenDesktopError.mainWindowNotFound
    }
    return window
}

private func composer(in window: AXUIElement) throws -> AXUIElement {
    var candidates: [AXUIElement] = []
    collectComposerCandidates(from: window, output: &candidates)
    if let explicit = candidates.last(where: {
        let label = elementLabel($0)
        return label.contains("向千问提问")
            || label.contains("问千问")
            || label.contains("输入问题或任务")
            || label.contains("输入消息")
            || label.contains("和千问")
            || label.lowercased().contains("ask qwen")
            || label.lowercased().contains("ask qianwen")
    }) {
        return explicit
    }

    let scored = candidates.compactMap { element -> (AXUIElement, CGFloat)? in
        guard let rect = elementRect(element), rect.width >= 120, rect.height >= 20 else {
            return nil
        }
        let label = elementLabel(element)
        var score = rect.maxY + min(rect.width, 800) * 0.05
        if label.contains("输入") || label.lowercased().contains("ask") {
            score += 400
        }
        if isValueSettable(element) {
            score += 180
        }
        if label.contains("向千问提问") {
            score += 500
        }
        return (element, score)
    }
    if let best = scored.sorted(by: { $0.1 < $1.1 }).last?.0 {
        return best
    }
    guard let fallback = candidates.last else {
        throw QwenDesktopError.inputBoxNotFound
    }
    return fallback
}

private func sendKey(_ keyCode: CGKeyCode, flags: CGEventFlags = []) {
    let source = CGEventSource(stateID: .hidSystemState)
    let down = CGEvent(keyboardEventSource: source, virtualKey: keyCode, keyDown: true)
    down?.flags = flags
    down?.post(tap: .cghidEventTap)
    let up = CGEvent(keyboardEventSource: source, virtualKey: keyCode, keyDown: false)
    up?.flags = flags
    up?.post(tap: .cghidEventTap)
}

private func composerValue(_ element: AXUIElement) -> String {
    return stringAttribute(element, name: kAXValueAttribute as String)
}

private func promptProbe(_ prompt: String) -> String {
    let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
    if trimmed.count <= 160 {
        return trimmed
    }
    return String(trimmed.prefix(160))
}

private func composerContainsPrompt(_ element: AXUIElement, prompt: String) -> Bool {
    let value = composerValue(element)
    let probe = promptProbe(prompt)
    return !probe.isEmpty && value.contains(probe)
}

private func pastePrompt(_ input: AXUIElement, prompt: String) -> String {
    _ = AXUIElementSetAttributeValue(input, kAXFocusedAttribute as CFString, kCFBooleanTrue)
    Thread.sleep(forTimeInterval: 0.15)
    return pastePromptToFocused(prompt)
}

private func pastePromptToFocused(_ prompt: String) -> String {
    let pasteboard = NSPasteboard.general
    let previousString = pasteboard.string(forType: .string)
    pasteboard.clearContents()
    pasteboard.setString(prompt, forType: .string)
    sendKey(0, flags: .maskCommand)
    Thread.sleep(forTimeInterval: 0.08)
    sendKey(9, flags: .maskCommand)
    Thread.sleep(forTimeInterval: 0.25)
    if let previousString {
        pasteboard.clearContents()
        pasteboard.setString(previousString, forType: .string)
    }
    return "clipboard-paste"
}

private func restoreClipboardString(_ previousString: String?) {
    guard let previousString else {
        return
    }
    let pasteboard = NSPasteboard.general
    pasteboard.clearContents()
    pasteboard.setString(previousString, forType: .string)
}

private func pngData(from image: NSImage) -> Data? {
    guard let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff)
    else {
        return nil
    }
    return bitmap.representation(using: .png, properties: [:])
}

private func renderPromptScreenshot(_ prompt: String) throws -> URL {
    let font = NSFont.monospacedSystemFont(ofSize: 25, weight: .regular)
    let titleFont = NSFont.systemFont(ofSize: 30, weight: .semibold)
    let paragraph = NSMutableParagraphStyle()
    paragraph.lineSpacing = 8
    paragraph.paragraphSpacing = 14
    paragraph.lineBreakMode = .byWordWrapping

    let width: CGFloat = 1600
    let horizontalPadding: CGFloat = 72
    let bodyWidth = width - horizontalPadding * 2
    let title = "AI Judge screenshot fallback prompt\n\n"
    let body = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
    let attributed = NSMutableAttributedString(
        string: title,
        attributes: [
            .font: titleFont,
            .foregroundColor: NSColor.black,
            .paragraphStyle: paragraph,
        ]
    )
    attributed.append(
        NSAttributedString(
            string: body.isEmpty ? "(empty prompt)" : body,
            attributes: [
                .font: font,
                .foregroundColor: NSColor.black,
                .paragraphStyle: paragraph,
            ]
        )
    )
    let bounds = attributed.boundingRect(
        with: CGSize(width: bodyWidth, height: 100_000),
        options: [.usesLineFragmentOrigin, .usesFontLeading]
    )
    let height = min(max(900, ceil(bounds.height + 160)), 6200)
    let image = NSImage(size: CGSize(width: width, height: height))
    image.lockFocus()
    NSColor.white.setFill()
    NSRect(x: 0, y: 0, width: width, height: height).fill()
    attributed.draw(
        with: NSRect(
            x: horizontalPadding,
            y: horizontalPadding,
            width: bodyWidth,
            height: height - horizontalPadding * 2
        ),
        options: [.usesLineFragmentOrigin, .usesFontLeading]
    )
    image.unlockFocus()

    guard let data = pngData(from: image) else {
        throw QwenDesktopError.invalidCommand("Failed to render prompt screenshot PNG")
    }
    let url = URL(fileURLWithPath: "/private/tmp")
        .appendingPathComponent("qwen-ai-judge-screenshot-\(UUID().uuidString).png")
    try data.write(to: url, options: .atomic)
    return url
}

private func pasteImageFileToFocused(_ imageURL: URL) throws -> String {
    guard FileManager.default.fileExists(atPath: imageURL.path) else {
        throw QwenDesktopError.invalidImagePath("Image file does not exist: \(imageURL.path)")
    }
    let pasteboard = NSPasteboard.general
    let previousString = pasteboard.string(forType: .string)
    pasteboard.clearContents()
    var wrote = pasteboard.writeObjects([imageURL as NSURL])
    if let data = try? Data(contentsOf: imageURL) {
        pasteboard.declareTypes([.fileURL, .png], owner: nil)
        pasteboard.setString(imageURL.absoluteString, forType: .fileURL)
        pasteboard.setData(data, forType: .png)
        wrote = true
    }
    guard wrote else {
        restoreClipboardString(previousString)
        throw QwenDesktopError.invalidImagePath("Failed to place image on pasteboard: \(imageURL.path)")
    }
    sendKey(9, flags: .maskCommand)
    Thread.sleep(forTimeInterval: 1.8)
    restoreClipboardString(previousString)
    return "clipboard-image-paste"
}

private func qwenWindowInfo() -> (id: CGWindowID, bounds: CGRect)? {
    if let bounds = qwenEnvBounds() {
        return (CGWindowID(0), bounds)
    }
    guard let infoList = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else {
        return nil
    }
    let pid = qwenPid()
    for info in infoList {
        let ownerName = info[kCGWindowOwnerName as String] as? String ?? ""
        let title = info[kCGWindowName as String] as? String ?? ""
        let ownerPid = (info[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value
        let isTargetPid = pid != nil && ownerPid == pid
        let searchable = "\(ownerName) \(title)".lowercased()
        let isTargetName = qwenNames.contains(ownerName)
            || ownerName.contains("千问")
            || ownerName.contains("通义")
            || searchable.contains("qianwen")
            || searchable.contains("qwen")
            || searchable.contains("tongyi")
        guard (isTargetPid || isTargetName),
              let windowNumber = info[kCGWindowNumber as String] as? NSNumber,
              let boundsDict = info[kCGWindowBounds as String] as? [String: Any]
        else {
            continue
        }
        let x = CGFloat((boundsDict["X"] as? NSNumber)?.doubleValue ?? 0)
        let y = CGFloat((boundsDict["Y"] as? NSNumber)?.doubleValue ?? 0)
        let width = CGFloat((boundsDict["Width"] as? NSNumber)?.doubleValue ?? 0)
        let height = CGFloat((boundsDict["Height"] as? NSNumber)?.doubleValue ?? 0)
        if width > 120 && height > 120 {
            return (CGWindowID(windowNumber.uint32Value), CGRect(x: x, y: y, width: width, height: height))
        }
    }
    return nil
}

private func clickAt(_ point: CGPoint) {
    let source = CGEventSource(stateID: .hidSystemState)
    CGEvent(mouseEventSource: source, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left)?
        .post(tap: .cghidEventTap)
    CGEvent(mouseEventSource: source, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left)?
        .post(tap: .cghidEventTap)
}

private func currentMouseLocation() -> CGPoint? {
    CGEvent(source: nil)?.location
}

private func restoreMouseLocation(_ point: CGPoint?) {
    guard let point else {
        return
    }
    CGWarpMouseCursorPosition(point)
}

private func screenshotQwenWindowImage() -> CGImage? {
    guard let window = qwenWindowInfo() else {
        return nil
    }
    let target = URL(fileURLWithPath: NSTemporaryDirectory())
        .appendingPathComponent("qwen-ai-judge-\(UUID().uuidString).png")
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
    if window.id == 0 {
        let region = [
            Int(window.bounds.origin.x.rounded()),
            Int(window.bounds.origin.y.rounded()),
            Int(window.bounds.width.rounded()),
            Int(window.bounds.height.rounded()),
        ]
            .map(String.init)
            .joined(separator: ",")
        process.arguments = ["-x", "-R", region, target.path]
    } else {
        process.arguments = ["-x", "-l", "\(window.id)", target.path]
    }
    process.standardOutput = Pipe()
    process.standardError = Pipe()
    do {
        try process.run()
        process.waitUntilExit()
    } catch {
        return nil
    }
    defer { try? FileManager.default.removeItem(at: target) }
    guard process.terminationStatus == 0,
          let image = NSImage(contentsOf: target)
    else {
        return nil
    }
    var rect = CGRect(origin: .zero, size: image.size)
    return image.cgImage(forProposedRect: &rect, context: nil, hints: nil)
}

private func ocrTextFromQwenWindow() -> String {
    guard let image = screenshotQwenWindowImage() else {
        return ""
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    let handler = VNImageRequestHandler(cgImage: image)
    do {
        try handler.perform([request])
    } catch {
        return ""
    }
    let observations = (request.results ?? []).sorted {
        if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.02 {
            return $0.boundingBox.midY > $1.boundingBox.midY
        }
        return $0.boundingBox.minX < $1.boundingBox.minX
    }
    return observations.compactMap { $0.topCandidates(1).first?.string }
        .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
        .filter { !$0.isEmpty }
        .joined(separator: "\n")
}

private func badButtonLabel(_ label: String) -> Bool {
    let lowered = label.lowercased()
    let blocked = [
        "停止", "取消", "麦克风", "语音", "话筒", "上传", "附件", "文件", "更多", "菜单",
        "stop", "cancel", "mic", "microphone", "voice", "upload", "attach", "file", "more", "menu"
    ]
    return blocked.contains(where: { lowered.contains($0.lowercased()) })
}

private func submitButton(in window: AXUIElement, near input: AXUIElement) -> AXUIElement? {
    var buttons: [AXUIElement] = []
    collectElements(from: window, roles: [kAXButtonRole as String], output: &buttons)
    let inputRect = elementRect(input)
    let candidates = buttons.compactMap { button -> (AXUIElement, CGFloat)? in
        let label = elementLabel(button)
        if badButtonLabel(label) {
            return nil
        }
        let lowered = label.lowercased()
        var score: CGFloat = 0
        if lowered.contains("发送") || lowered.contains("提交") || lowered.contains("send") || lowered.contains("submit") {
            score += 1000
        }
        guard let rect = elementRect(button) else {
            return score > 0 ? (button, score) : nil
        }
        let longer = max(rect.width, rect.height)
        let shorter = max(1, min(rect.width, rect.height))
        if longer >= 18 && longer <= 82 && longer / shorter <= 2.8 {
            score += 80
        }
        if let inputRect {
            let center = CGPoint(x: rect.midX, y: rect.midY)
            if center.x >= inputRect.midX && abs(center.y - inputRect.midY) <= max(80, inputRect.height * 1.5) {
                score += 180
            }
            if center.x >= inputRect.maxX - 120 && center.x <= inputRect.maxX + 160 {
                score += 120
            }
        }
        return score >= 160 ? (button, score) : nil
    }
    return candidates.sorted(by: { $0.1 < $1.1 }).last?.0
}

private func controlMatchingLabel(
    in root: AXUIElement,
    labels: [String],
    roles: Set<String>,
    depth: Int = 0,
    maxDepth: Int = 50
) -> AXUIElement? {
    let role = stringAttribute(root, name: kAXRoleAttribute as String)
    let label = elementLabel(root)
    if (roles.isEmpty || roles.contains(role)),
       labels.contains(where: { !label.isEmpty && label.localizedCaseInsensitiveContains($0) }) {
        return root
    }
    if depth >= maxDepth {
        return nil
    }
    for child in children(of: root) {
        if let match = controlMatchingLabel(
            in: child,
            labels: labels,
            roles: roles,
            depth: depth + 1,
            maxDepth: maxDepth
        ) {
            return match
        }
    }
    return nil
}

private func qwenApplicationElement() -> AXUIElement? {
    guard let pid = qwenPid() else {
        return nil
    }
    return AXUIElementCreateApplication(pid)
}

private func pressNewConversationIfAvailable() {
    guard let app = qwenApplicationElement(),
          let button = controlMatchingLabel(
              in: app,
              labels: ["新建对话", "New chat", "New conversation"],
              roles: [kAXButtonRole as String]
          )
    else {
        return
    }
    _ = AXUIElementPerformAction(button, kAXPressAction as CFString)
    Thread.sleep(forTimeInterval: 1.0)
}

private func attachmentButton(in window: AXUIElement, near input: AXUIElement) -> AXUIElement? {
    var controls: [AXUIElement] = []
    collectElements(
        from: window,
        roles: [kAXButtonRole as String, kAXPopUpButtonRole as String],
        output: &controls
    )
    let inputRect = elementRect(input)
    let candidates = controls.compactMap { control -> (AXUIElement, CGFloat)? in
        let label = elementLabel(control)
        let lowered = label.lowercased()
        var score: CGFloat = 0
        if label.contains("添加附件") || label.contains("上传") || lowered.contains("attach") || lowered.contains("upload") {
            score += 800
        }
        guard let rect = elementRect(control) else {
            return score > 0 ? (control, score) : nil
        }
        if let inputRect {
            let center = CGPoint(x: rect.midX, y: rect.midY)
            if center.x <= inputRect.midX && abs(center.y - inputRect.midY) <= max(90, inputRect.height * 1.6) {
                score += 220
            }
            if center.x >= inputRect.minX - 120 && center.x <= inputRect.minX + 160 {
                score += 120
            }
        }
        let longer = max(rect.width, rect.height)
        if longer >= 18 && longer <= 90 {
            score += 50
        }
        return score >= 160 ? (control, score) : nil
    }
    return candidates.sorted(by: { $0.1 < $1.1 }).last?.0
}

private func selectUploadImageMenuItem(windowInfo: (id: CGWindowID, bounds: CGRect)?) -> String {
    Thread.sleep(forTimeInterval: 0.4)
    if let app = qwenApplicationElement(),
       let menuItem = controlMatchingLabel(
           in: app,
           labels: ["上传图片", "Upload image", "图片"],
           roles: [kAXMenuItemRole as String, kAXButtonRole as String, kAXStaticTextRole as String]
       ) {
        let role = stringAttribute(menuItem, name: kAXRoleAttribute as String)
        if role != kAXStaticTextRole as String,
           AXUIElementPerformAction(menuItem, kAXPressAction as CFString) == .success {
            Thread.sleep(forTimeInterval: 0.5)
            return "upload-image-menu-axpress"
        }
        sendKey(125)
        Thread.sleep(forTimeInterval: 0.08)
        sendKey(125)
        Thread.sleep(forTimeInterval: 0.08)
        sendKey(36)
        Thread.sleep(forTimeInterval: 0.7)
        return "upload-image-menu-keyboard"
    }
    sendKey(125)
    Thread.sleep(forTimeInterval: 0.08)
    sendKey(125)
    Thread.sleep(forTimeInterval: 0.08)
    sendKey(36)
    Thread.sleep(forTimeInterval: 0.7)
    if let app = qwenApplicationElement(),
       controlMatchingLabel(
           in: app,
           labels: ["上传文档", "上传图片", "截屏提问"],
           roles: [kAXMenuRole as String, kAXMenuItemRole as String, kAXStaticTextRole as String]
       ) == nil {
        return "upload-image-menu-keyboard"
    }
    if let app = qwenApplicationElement(),
       let menuItem = controlMatchingLabel(
           in: app,
           labels: ["上传图片", "Upload image", "图片"],
           roles: [kAXMenuItemRole as String, kAXButtonRole as String, kAXStaticTextRole as String]
       ) {
        if let rect = elementRect(menuItem) {
            clickAt(CGPoint(x: rect.midX, y: rect.midY))
            Thread.sleep(forTimeInterval: 0.5)
            return "upload-image-menu-coordinate"
        }
    }
    if let windowInfo {
        let point = CGPoint(
            x: windowInfo.bounds.minX + max(110, min(165, windowInfo.bounds.width * 0.22)),
            y: windowInfo.bounds.maxY - max(210, min(250, windowInfo.bounds.height * 0.34))
        )
        clickAt(point)
        Thread.sleep(forTimeInterval: 0.5)
        return "upload-image-menu-coordinate-estimate"
    }
    return "upload-image-menu-not-found"
}

private func chooseFileInOpenPanel(_ imageURL: URL) -> String {
    Thread.sleep(forTimeInterval: 1.4)
    sendKey(5, flags: [.maskCommand, .maskShift])
    Thread.sleep(forTimeInterval: 1.0)
    _ = pastePromptToFocused(imageURL.path)
    Thread.sleep(forTimeInterval: 0.6)
    sendKey(36)
    Thread.sleep(forTimeInterval: 1.5)
    sendKey(36)
    Thread.sleep(forTimeInterval: 3.0)
    return "open-panel-go-to-file"
}

private func uploadImageFileViaAttachmentMenu(
    _ imageURL: URL,
    window: AXUIElement,
    input: AXUIElement
) throws -> String {
    guard FileManager.default.fileExists(atPath: imageURL.path) else {
        throw QwenDesktopError.invalidImagePath("Image file does not exist: \(imageURL.path)")
    }
    let windowInfo = qwenWindowInfo()
    var steps: [String] = []
    if let button = attachmentButton(in: window, near: input),
       AXUIElementPerformAction(button, kAXPressAction as CFString) == .success {
        steps.append("attach-axpress")
    } else if let rect = elementRect(input) {
        clickAt(CGPoint(x: max(20, rect.minX + 28), y: rect.midY))
        steps.append("attach-coordinate-from-input")
    } else if let windowInfo {
        clickAt(CGPoint(x: windowInfo.bounds.minX + 58, y: windowInfo.bounds.maxY - 66))
        steps.append("attach-coordinate-estimate")
    } else {
        throw QwenDesktopError.inputBoxNotFound
    }
    steps.append(selectUploadImageMenuItem(windowInfo: windowInfo))
    steps.append(chooseFileInOpenPanel(imageURL))
    return steps.joined(separator: "/")
}

private func hasStopButton(in window: AXUIElement) -> Bool {
    var buttons: [AXUIElement] = []
    collectElements(from: window, roles: [kAXButtonRole as String], output: &buttons)
    return buttons.contains(where: {
        let label = elementLabel($0)
        return label.contains("停止生成") || label.contains("停止回答") || label == "停止" || label.lowercased().contains("stop")
    })
}

private func collectTextContent(
    from element: AXUIElement,
    depth: Int = 0,
    maxDepth: Int = 40,
    output: inout [String]
) {
    let textRoles = [
        kAXStaticTextRole as String,
        kAXTextAreaRole as String,
        kAXTextFieldRole as String,
    ]
    if let role = copyAttribute(element, name: kAXRoleAttribute as String) as? String,
       textRoles.contains(role) {
        let label = elementLabel(element)
        let trimmed = label.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty {
            output.append(trimmed)
        }
    }
    if depth >= maxDepth {
        return
    }
    for child in children(of: element) {
        collectTextContent(from: child, depth: depth + 1, maxDepth: maxDepth, output: &output)
    }
}

private func transcriptText(in window: AXUIElement) -> String {
    var raw: [String] = []
    collectTextContent(from: window, output: &raw)
    var seen: Set<String> = []
    var lines: [String] = []
    let ignored = [
        "输入问题或任务",
        "向千问提问",
        "内容由千问 AI 生成",
        "AI 生成",
        "内容由AI生成",
        "先思考后回答",
        "任务助理",
        "深度思考",
        "深度研究",
        "更多",
        "超能模式",
        "上传文件",
    ]
    for value in raw {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty || ignored.contains(where: { trimmed.contains($0) }) {
            continue
        }
        if seen.insert(trimmed).inserted {
            lines.append(trimmed)
        }
    }
    return lines.joined(separator: "\n")
}

private func readableText(in window: AXUIElement) -> String {
    let axText = transcriptText(in: window)
    if !axText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
        return axText
    }
    return ocrTextFromQwenWindow()
}

private func extractImageAnswer(imageName: String, beforeTranscript: String, transcript: String) -> String {
    var value = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
    let before = beforeTranscript.trimmingCharacters(in: .whitespacesAndNewlines)
    if !before.isEmpty, value.hasPrefix(before) {
        value = String(value.dropFirst(before.count)).trimmingCharacters(in: .whitespacesAndNewlines)
    }
    let markers = [
        imageName,
        "帮我分析一下图片内容",
        "请分析图片内容",
        "分析一下图片内容",
    ].filter { !$0.isEmpty }
    for marker in markers {
        if let range = value.range(of: marker, options: [.backwards]) {
            value = String(value[range.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
        }
    }
    return value
}

private func extractAnswer(prompt: String, beforeTranscript: String, transcript: String) -> String {
    let trimmedPrompt = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
    let trimmedBefore = beforeTranscript.trimmingCharacters(in: .whitespacesAndNewlines)
    let trimmedTranscript = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !trimmedTranscript.isEmpty else {
        return ""
    }
    if !trimmedPrompt.isEmpty,
       let range = trimmedTranscript.range(of: trimmedPrompt, options: [.backwards]) {
        return String(trimmedTranscript[range.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
    }
    let firstLine = trimmedPrompt.components(separatedBy: .newlines).first ?? ""
    if firstLine.count >= 12,
       let range = trimmedTranscript.range(of: firstLine, options: [.backwards]) {
        return String(trimmedTranscript[range.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
    }
    if !trimmedBefore.isEmpty,
       trimmedTranscript.hasPrefix(trimmedBefore) {
        return String(trimmedTranscript.dropFirst(trimmedBefore.count)).trimmingCharacters(in: .whitespacesAndNewlines)
    }
    return trimmedTranscript
}

private func printJSON(_ result: QwenSendResult) throws {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.withoutEscapingSlashes]
    let data = try encoder.encode(result)
    print(String(data: data, encoding: .utf8) ?? "{}")
}

private func printDiagnoseJSON() throws {
    let infoList = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
    let sampleWindows = infoList.prefix(8).map { info -> String in
        let ownerName = info[kCGWindowOwnerName as String] as? String ?? ""
        let title = info[kCGWindowName as String] as? String ?? ""
        let ownerPid = (info[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value ?? 0
        return "\(ownerPid)|\(ownerName)|\(title)"
    }
    let qwenWindows = infoList.compactMap { info -> String? in
        let ownerName = info[kCGWindowOwnerName as String] as? String ?? ""
        let title = info[kCGWindowName as String] as? String ?? ""
        let searchable = "\(ownerName) \(title)".lowercased()
        guard ownerName.contains("千问")
            || title.contains("千问")
            || searchable.contains("qianwen")
            || searchable.contains("qwen")
            || searchable.contains("tongyi")
        else {
            return nil
        }
        let ownerPid = (info[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value ?? 0
        let windowNumber = (info[kCGWindowNumber as String] as? NSNumber)?.intValue ?? 0
        return "\(ownerPid)|\(windowNumber)|\(ownerName)|\(title)"
    }
    let result = QwenDiagnoseResult(
        ok: true,
        env_pid: qwenEnvPid(),
        env_bounds: ProcessInfo.processInfo.environment["QWEN_DESKTOP_BOUNDS"],
        nsworkspace_pid: qwenApp()?.processIdentifier,
        system_events_pid: qwenSystemEventsPid(),
        resolved_pid: qwenPid(),
        window_count: infoList.count,
        sample_windows: sampleWindows,
        qwen_window_count: qwenWindows.count,
        qwen_windows: qwenWindows
    )
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.withoutEscapingSlashes]
    let data = try encoder.encode(result)
    print(String(data: data, encoding: .utf8) ?? "{}")
}

struct ScriptResult {
    let status: Int32
    let stdout: String
    let stderr: String
}

struct QwenJavaScriptSubmitResult: Codable {
    let ok: Bool?
    let status: String?
    let reason: String?
    let submitted: Bool?
    let before_text: String?
    let after_text: String?
}

struct QwenJavaScriptReadResult: Codable {
    let ok: Bool?
    let text: String?
    let reason: String?
}

private func jsonStringLiteral(_ value: String) -> String {
    let data = (try? JSONEncoder().encode(value)) ?? Data("\"\"".utf8)
    return String(data: data, encoding: .utf8) ?? "\"\""
}

private func appleScriptStringLiteral(_ value: String) -> String {
    let escaped = value
        .replacingOccurrences(of: "\\", with: "\\\\")
        .replacingOccurrences(of: "\"", with: "\\\"")
        .replacingOccurrences(of: "\r", with: "\\r")
        .replacingOccurrences(of: "\n", with: "\\n")
    return "\"\(escaped)\""
}

private func runAppleScript(_ script: String, timeoutSeconds: Double = 20.0) -> ScriptResult {
    let process = Process()
    let stdout = Pipe()
    let stderr = Pipe()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
    process.arguments = ["-e", script]
    process.standardOutput = stdout
    process.standardError = stderr
    do {
        try process.run()
    } catch {
        return ScriptResult(status: 127, stdout: "", stderr: "\(error)")
    }
    let deadline = Date().addingTimeInterval(max(1.0, timeoutSeconds))
    while process.isRunning && Date() < deadline {
        Thread.sleep(forTimeInterval: 0.05)
    }
    if process.isRunning {
        process.terminate()
    }
    process.waitUntilExit()
    let out = String(data: stdout.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
    let err = String(data: stderr.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
    return ScriptResult(
        status: process.terminationStatus,
        stdout: out.trimmingCharacters(in: .whitespacesAndNewlines),
        stderr: err.trimmingCharacters(in: .whitespacesAndNewlines)
    )
}

private func executeQwenJavaScript(_ javascript: String) -> ScriptResult {
    let appSpecifiers = [
        "id \"com.alibaba.tongyi\"",
        "\"Qianwen\"",
        "\"千问\"",
        "\"Qwen\"",
        "\"通义千问\"",
    ]
    var failures: [String] = []
    for specifier in appSpecifiers {
        let script = """
        tell application \(specifier)
          set jsResult to execute javascript \(appleScriptStringLiteral(javascript)) in active tab of front window
          return jsResult
        end tell
        """
        let result = runAppleScript(script)
        if result.status == 0 {
            return result
        }
        let detail = [result.stderr, result.stdout]
            .filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            .joined(separator: " ")
        failures.append("\(specifier): \(detail)")
    }
    return ScriptResult(status: 1, stdout: "", stderr: failures.joined(separator: " | "))
}

private func decodeJSON<T: Decodable>(_ type: T.Type, from text: String) -> T? {
    let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
    guard let data = trimmed.data(using: .utf8) else {
        return nil
    }
    return try? JSONDecoder().decode(type, from: data)
}

private func compactAppleScriptFailure(_ message: String) -> String {
    let lowered = message.lowercased()
    if message.contains("-1723") || message.contains("不允许访问") || lowered.contains("not allowed") {
        return "Qianwen AppleScript JavaScript access is disabled or denied. Enable Qianwen's developer setting for JavaScript from Apple Events, then retry. No interactive fallback was attempted."
    }
    if message.contains("-1719") || message.contains("无效的索引") {
        return "Qianwen has no scriptable active tab/window available to the AppleScript bridge. No interactive fallback was attempted."
    }
    if message.contains("-2741") || message.contains("syntax error") || message.contains("语法错误") {
        return "Qianwen AppleScript bridge rejected the generated JavaScript command. No interactive fallback was attempted."
    }
    let trimmed = message.trimmingCharacters(in: .whitespacesAndNewlines)
    if trimmed.count <= 800 {
        return trimmed
    }
    return String(trimmed.prefix(800)) + "... [truncated]"
}

private func qwenSubmitJavaScript(prompt: String) -> String {
    let promptLiteral = jsonStringLiteral(prompt)
    return """
    (() => {
      const prompt = \(promptLiteral);
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return rect.width > 4 && rect.height > 4 && style.visibility !== 'hidden' && style.display !== 'none';
      };
      const bodyText = () => (document.body && document.body.innerText) || '';
      const beforeText = bodyText();
      const editors = Array.from(document.querySelectorAll('textarea,input:not([type]),input[type="text"],[contenteditable="true"],[role="textbox"]'))
        .filter(visible)
        .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
      const composer = editors[editors.length - 1];
      if (!composer) {
        return JSON.stringify({ok:false,status:'blocked',reason:'Qianwen webview composer not found',submitted:false,before_text:beforeText,after_text:bodyText()});
      }
      composer.focus({preventScroll:true});
      if ('value' in composer) {
        composer.value = prompt;
      } else if (composer.isContentEditable) {
        composer.textContent = prompt;
      } else {
        composer.textContent = prompt;
      }
      for (const eventName of ['input', 'change', 'compositionend']) {
        composer.dispatchEvent(new Event(eventName, {bubbles:true}));
      }
      const rect = composer.getBoundingClientRect();
      const bad = /stop|cancel|mic|microphone|voice|upload|attach|file|more|menu|new|clear|history|setting|停止|取消|麦克风|语音|上传|附件|文件|更多|菜单|新建|清空|历史|设置/i;
      const good = /send|submit|arrow|paper|发送|提交|上箭头/i;
      const controls = Array.from(document.querySelectorAll('button,[role="button"],[aria-label],[title]'))
        .filter(visible)
        .filter((el) => !el.disabled && !el.getAttribute('aria-disabled'))
        .map((el) => {
          const r = el.getBoundingClientRect();
          const label = [el.innerText, el.getAttribute('aria-label'), el.getAttribute('title'), el.className].join(' ');
          let score = 0;
          if (good.test(label)) score += 1000;
          if (!bad.test(label)) score += 100;
          if (r.left >= rect.left && r.top >= rect.top - 30 && r.top <= rect.bottom + 80) score += 200;
          score -= Math.abs(r.right - rect.right) * 0.5 + Math.abs(r.top - rect.bottom) * 0.2;
          return {el, score, label};
        })
        .filter((item) => item.score > -200 && !bad.test(item.label))
        .sort((a, b) => b.score - a.score);
      const target = controls[0] && controls[0].el;
      if (target) {
        target.click();
        return JSON.stringify({ok:true,status:'submitted',reason:'submitted via Qianwen AppleScript JavaScript; no global mouse, keyboard, clipboard, or app activation used',submitted:true,before_text:beforeText,after_text:bodyText()});
      }
      const form = composer.closest('form');
      if (form && typeof form.requestSubmit === 'function') {
        form.requestSubmit();
        return JSON.stringify({ok:true,status:'submitted',reason:'submitted form via Qianwen AppleScript JavaScript; no global mouse, keyboard, clipboard, or app activation used',submitted:true,before_text:beforeText,after_text:bodyText()});
      }
      return JSON.stringify({ok:false,status:'submit_not_confirmed',reason:'Qianwen send control not found in webview DOM; no interactive fallback attempted',submitted:false,before_text:beforeText,after_text:bodyText()});
    })();
    """
}

private func qwenFreshConversationJavaScript() -> String {
    """
    (() => {
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return rect.width > 4 && rect.height > 4 && style.visibility !== 'hidden' && style.display !== 'none';
      };
      const good = /new chat|new conversation|新建对话|新对话|新聊天/i;
      const bad = /clear|delete|history|setting|upload|attach|api|search|清空|删除|历史|设置|上传|附件|接口|搜索/i;
      const controls = Array.from(document.querySelectorAll('button,[role="button"],[aria-label],[title]'))
        .filter(visible)
        .filter((el) => !el.disabled && !el.getAttribute('aria-disabled'))
        .map((el) => {
          const rect = el.getBoundingClientRect();
          const label = [el.innerText, el.getAttribute('aria-label'), el.getAttribute('title'), el.className].join(' ');
          let score = 0;
          if (good.test(label)) score += 1000;
          if (rect.left < 320) score += 80;
          if (rect.top < 260) score += 40;
          return {el, label, score};
        })
        .filter((item) => item.score >= 1000 && !bad.test(item.label))
        .sort((a, b) => b.score - a.score);
      const target = controls[0] && controls[0].el;
      if (target) {
        target.click();
        return JSON.stringify({ok:true,status:'clicked_new_conversation',label:controls[0].label});
      }
      return JSON.stringify({ok:true,status:'new_conversation_control_not_found'});
    })();
    """
}

private func qwenReadJavaScript() -> String {
    """
    (() => JSON.stringify({ok:true,text:(document.body && document.body.innerText) || ''}))();
    """
}

private func sendPrompt(_ prompt: String, waitSeconds: Double) throws -> QwenSendResult {
    let freshConversation = executeQwenJavaScript(qwenFreshConversationJavaScript())
    if freshConversation.status == 0 {
        Thread.sleep(forTimeInterval: 1.2)
    }
    let submitted = executeQwenJavaScript(qwenSubmitJavaScript(prompt: prompt))
    guard submitted.status == 0 else {
        let compactFailure = compactAppleScriptFailure(submitted.stderr)
        return makeSendResult(
            ok: true,
            status: "blocked",
            reason: "Qianwen AppleScript JavaScript bridge unavailable: \(compactFailure) No mouse, keyboard, clipboard, foreground activation, or coordinate fallback was attempted.",
            submitted: false,
            answerText: "",
            transcriptText: "",
            policy: noninteractivePolicy
        )
    }
    guard let submitPayload = decodeJSON(QwenJavaScriptSubmitResult.self, from: submitted.stdout) else {
        return makeSendResult(
            ok: true,
            status: "blocked",
            reason: "Qianwen AppleScript JavaScript bridge returned non-JSON output. No interactive fallback attempted.",
            submitted: false,
            answerText: "",
            transcriptText: submitted.stdout,
            policy: noninteractivePolicy
        )
    }
    let beforeTranscript = submitPayload.before_text ?? ""
    if submitPayload.submitted != true {
        return makeSendResult(
            ok: true,
            status: submitPayload.status ?? "submit_not_confirmed",
            reason: "\(submitPayload.reason ?? "Qianwen JavaScript submit was not confirmed"). No interactive fallback attempted.",
            submitted: false,
            answerText: "",
            transcriptText: submitPayload.after_text ?? beforeTranscript,
            policy: noninteractivePolicy
        )
    }

    let deadline = Date().addingTimeInterval(max(1.0, waitSeconds))
    var lastTranscript = ""
    var stableRounds = 0
    var latestTranscript = submitPayload.after_text ?? beforeTranscript
    var latestAnswer = extractAnswer(prompt: prompt, beforeTranscript: beforeTranscript, transcript: latestTranscript)
    while Date() < deadline {
        Thread.sleep(forTimeInterval: 1.0)
        let read = executeQwenJavaScript(qwenReadJavaScript())
        if read.status != 0 {
            continue
        }
        guard let readPayload = decodeJSON(QwenJavaScriptReadResult.self, from: read.stdout) else {
            continue
        }
        let currentTranscript = readPayload.text ?? ""
        latestTranscript = currentTranscript
        latestAnswer = extractAnswer(prompt: prompt, beforeTranscript: beforeTranscript, transcript: currentTranscript)
        let generating = currentTranscript.contains("思考中")
            || currentTranscript.contains("正在生成")
            || currentTranscript.contains("停止生成")
            || currentTranscript.lowercased().contains("thinking")
        if currentTranscript == lastTranscript {
            stableRounds += 1
        } else {
            stableRounds = 0
            lastTranscript = currentTranscript
        }
        if !latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !generating && stableRounds >= 1 {
            return makeSendResult(
                ok: true,
                status: "answered",
                reason: "submitted via Qianwen AppleScript JavaScript; readback stable; no global mouse, keyboard, clipboard, or app activation used",
                submitted: true,
                answerText: latestAnswer,
                transcriptText: latestTranscript,
                policy: noninteractivePolicy
            )
        }
    }
    return makeSendResult(
        ok: true,
        status: latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "submitted_no_answer" : "partial_or_changed",
        reason: "Qianwen AppleScript JavaScript submit completed, but answer did not stabilize before timeout; no interactive fallback attempted",
        submitted: true,
        answerText: latestAnswer,
        transcriptText: latestTranscript,
        policy: noninteractivePolicy
    )
}

private func sendPromptInteractive(_ prompt: String, waitSeconds: Double) throws -> QwenSendResult {
    if qwenEnvBounds() != nil {
        guard ProcessInfo.processInfo.environment["QWEN_DESKTOP_ALLOW_GLOBAL_INPUT"] == "1" else {
            return makeSendResult(
                ok: true,
                status: "blocked",
                reason: "QWEN_DESKTOP_BOUNDS is set, but QWEN_DESKTOP_ALLOW_GLOBAL_INPUT is not 1. Qianwen coordinate fallback is disabled by default because this desktop client has no scriptable tab and global CG mouse events can hang without explicit local permission.",
                submitted: false,
                answerText: "",
                transcriptText: "",
                policy: interactivePolicy
            )
        }
        return try sendPromptByCoordinateFallback(
            prompt,
            waitSeconds: waitSeconds,
            setupReason: "QWEN_DESKTOP_BOUNDS",
            activateFirst: false
        )
    }
    try activateQwen()
    pressNewConversationIfAvailable()
    var window: AXUIElement
    do {
        window = try mainWindowElement()
    } catch {
        return try sendPromptByCoordinateFallback(prompt, waitSeconds: waitSeconds, setupReason: "\(error)")
    }
    let input: AXUIElement
    do {
        input = try composer(in: window)
    } catch {
        return try sendPromptByCoordinateFallback(prompt, waitSeconds: waitSeconds, setupReason: "\(error)")
    }
    let beforeTranscript = readableText(in: window)
    let fillMethod = pastePrompt(input, prompt: prompt)
    Thread.sleep(forTimeInterval: 0.25)

    sendKey(36)
    Thread.sleep(forTimeInterval: 1.0)
    window = try mainWindowElement()
    var currentInput = try? composer(in: window)
    var submitMethod = "return-key"

    if let inputAfterReturn = currentInput, composerContainsPrompt(inputAfterReturn, prompt: prompt) {
        if let button = submitButton(in: window, near: inputAfterReturn) {
            let pressResult = AXUIElementPerformAction(button, kAXPressAction as CFString)
            submitMethod = "button-press:\(pressResult.rawValue)"
            Thread.sleep(forTimeInterval: 1.0)
            window = try mainWindowElement()
            currentInput = try? composer(in: window)
        }
    }

    if let currentInput, composerContainsPrompt(currentInput, prompt: prompt) {
        return makeSendResult(
            ok: true,
            status: "submit_not_confirmed",
            reason: "Qianwen desktop app prompt filled via \(fillMethod), but prompt remained in composer after \(submitMethod)",
            submitted: false,
            answerText: "",
            transcriptText: readableText(in: window),
            policy: interactivePolicy
        )
    }

    let deadline = Date().addingTimeInterval(max(1.0, waitSeconds))
    var lastTranscript = ""
    var stableRounds = 0
    var latestTranscript = ""
    var latestAnswer = ""
    var observedStop = false
    while Date() < deadline {
        Thread.sleep(forTimeInterval: 1.0)
        window = try mainWindowElement()
        let currentTranscript = readableText(in: window)
        latestTranscript = currentTranscript
        latestAnswer = extractAnswer(prompt: prompt, beforeTranscript: beforeTranscript, transcript: currentTranscript)
        let generating = hasStopButton(in: window)
        observedStop = observedStop || generating
        if currentTranscript == lastTranscript {
            stableRounds += 1
        } else {
            stableRounds = 0
            lastTranscript = currentTranscript
        }
        if !latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !generating && stableRounds >= 1 {
            return makeSendResult(
                ok: true,
                status: "answered",
                reason: "submitted via Qianwen desktop app AX \(submitMethod); readback stable",
                submitted: true,
                answerText: latestAnswer,
                transcriptText: latestTranscript,
                policy: interactivePolicy
            )
        }
    }
    return makeSendResult(
        ok: true,
        status: latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "submitted_no_answer" : "partial_or_changed",
        reason: observedStop
            ? "Qianwen desktop app submitted via \(submitMethod), but answer did not stabilize before timeout"
            : "Qianwen desktop app submitted via \(submitMethod), but no answer was detected before timeout",
        submitted: true,
        answerText: latestAnswer,
        transcriptText: latestTranscript,
        policy: interactivePolicy
    )
}

private func sendPromptViaScreenshot(_ prompt: String, waitSeconds: Double, imageURL providedImageURL: URL? = nil) throws -> QwenSendResult {
    let imageURL = try providedImageURL ?? renderPromptScreenshot(prompt)
    let shouldRemoveImage = providedImageURL == nil
    defer {
        if shouldRemoveImage {
            try? FileManager.default.removeItem(at: imageURL)
        }
    }

    try activateQwen()
    pressNewConversationIfAvailable()
    var window: AXUIElement
    let input: AXUIElement
    do {
        window = try mainWindowElement()
        input = try composer(in: window)
    } catch {
        guard ProcessInfo.processInfo.environment["QWEN_DESKTOP_ALLOW_GLOBAL_INPUT"] == "1" else {
            return makeSendResult(
                ok: true,
                status: "blocked",
                reason: "Qianwen screenshot image upload fallback could not find an AX composer: \(error). Coordinate/global-input recovery is disabled by default; set QWEN_DESKTOP_ALLOW_GLOBAL_INPUT=1 only for an explicit diagnostic run.",
                submitted: false,
                answerText: "",
                transcriptText: "",
                policy: imageUploadPolicy
            )
        }
        return try sendPromptViaScreenshotCoordinate(
            prompt,
            waitSeconds: waitSeconds,
            imageURL: imageURL,
            setupReason: "\(error)"
        )
    }
    let beforeTranscript = readableText(in: window)
    let fillMethod = try uploadImageFileViaAttachmentMenu(imageURL, window: window, input: input)
    Thread.sleep(forTimeInterval: 0.8)

    window = try mainWindowElement()
    let inputAfterPaste = (try? composer(in: window)) ?? input
    var submitMethod = "button-press"
    if let button = submitButton(in: window, near: inputAfterPaste) {
        let pressResult = AXUIElementPerformAction(button, kAXPressAction as CFString)
        submitMethod = "button-press:\(pressResult.rawValue)"
    } else {
        sendKey(36)
        submitMethod = "return-key"
    }

    let deadline = Date().addingTimeInterval(max(1.0, waitSeconds))
    var lastTranscript = ""
    var stableRounds = 0
    var latestTranscript = readableText(in: window)
    var latestAnswer = extractImageAnswer(
        imageName: imageURL.lastPathComponent,
        beforeTranscript: beforeTranscript,
        transcript: latestTranscript
    )
    var observedStop = false
    while Date() < deadline {
        Thread.sleep(forTimeInterval: 1.5)
        window = try mainWindowElement()
        let currentTranscript = readableText(in: window)
        latestTranscript = currentTranscript
        latestAnswer = extractImageAnswer(
            imageName: imageURL.lastPathComponent,
            beforeTranscript: beforeTranscript,
            transcript: currentTranscript
        )
        let generating = hasStopButton(in: window)
            || currentTranscript.contains("思考中")
            || currentTranscript.contains("正在生成")
            || currentTranscript.lowercased().contains("thinking")
        observedStop = observedStop || generating
        if currentTranscript == lastTranscript {
            stableRounds += 1
        } else {
            stableRounds = 0
            lastTranscript = currentTranscript
        }
        if !latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !generating && stableRounds >= 1 {
            return makeSendResult(
                ok: true,
                status: "answered",
                reason: "submitted via Qianwen screenshot image upload fallback \(fillMethod)/\(submitMethod); no local Qwen/Ollama/Apple Events JavaScript used; this late fallback may bring Qianwen to the foreground and uses clipboard plus keyboard paste",
                submitted: true,
                answerText: latestAnswer,
                transcriptText: latestTranscript,
                policy: imageUploadPolicy
            )
        }
    }
    return makeSendResult(
        ok: true,
        status: latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "submitted_no_answer" : "partial_or_changed",
        reason: observedStop
            ? "Qianwen screenshot image upload fallback submitted via \(fillMethod)/\(submitMethod), but answer did not stabilize before timeout"
            : "Qianwen screenshot image upload fallback submitted via \(fillMethod)/\(submitMethod), but no answer was detected before timeout",
        submitted: true,
        answerText: latestAnswer,
        transcriptText: latestTranscript,
        policy: imageUploadPolicy
    )
}

private func sendPromptViaScreenshotCoordinate(
    _ prompt: String,
    waitSeconds: Double,
    imageURL: URL,
    setupReason: String
) throws -> QwenSendResult {
    try activateQwen()
    let beforeTranscript = ocrTextFromQwenWindow()
    guard let windowInfo = qwenWindowInfo() else {
        return makeSendResult(
            ok: true,
            status: "blocked",
            reason: "Qianwen screenshot image upload coordinate fallback could not find a visible window after: \(setupReason)",
            submitted: false,
            answerText: "",
            transcriptText: beforeTranscript,
            policy: imageUploadCoordinatePolicy
        )
    }

    let savedMouse = currentMouseLocation()
    let attachPoint = CGPoint(
        x: windowInfo.bounds.minX + 58,
        y: windowInfo.bounds.maxY - max(40, min(76, windowInfo.bounds.height * 0.095))
    )
    clickAt(attachPoint)
    Thread.sleep(forTimeInterval: 0.4)
    let menuMethod = selectUploadImageMenuItem(windowInfo: windowInfo)
    let fileMethod = chooseFileInOpenPanel(imageURL)
    Thread.sleep(forTimeInterval: 1.2)
    let sendPoint = CGPoint(
        x: windowInfo.bounds.maxX - max(42, min(72, windowInfo.bounds.width * 0.095)),
        y: windowInfo.bounds.maxY - max(40, min(76, windowInfo.bounds.height * 0.095))
    )
    clickAt(sendPoint)
    restoreMouseLocation(savedMouse)

    let deadline = Date().addingTimeInterval(max(1.0, waitSeconds))
    var lastTranscript = ""
    var stableRounds = 0
    var latestTranscript = ""
    var latestAnswer = ""
    while Date() < deadline {
        Thread.sleep(forTimeInterval: 2.0)
        let currentTranscript = ocrTextFromQwenWindow()
        latestTranscript = currentTranscript
        latestAnswer = extractImageAnswer(
            imageName: imageURL.lastPathComponent,
            beforeTranscript: beforeTranscript,
            transcript: currentTranscript
        )
        let generating = currentTranscript.contains("思考中")
            || currentTranscript.contains("正在生成")
            || currentTranscript.contains("停止生成")
            || currentTranscript.lowercased().contains("thinking")
        if currentTranscript == lastTranscript {
            stableRounds += 1
        } else {
            stableRounds = 0
            lastTranscript = currentTranscript
        }
        if !latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !generating && stableRounds >= 1 {
            return makeSendResult(
                ok: true,
                status: "answered",
                reason: "submitted via Qianwen screenshot image upload coordinate fallback attach-coordinate/\(menuMethod)/\(fileMethod); no local Qwen/Ollama/Apple Events JavaScript used; mouse position restored after bounded UI click; ax_setup=\(setupReason)",
                submitted: true,
                answerText: latestAnswer,
                transcriptText: latestTranscript,
                policy: imageUploadCoordinatePolicy
            )
        }
    }
    return makeSendResult(
        ok: true,
        status: latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "submitted_no_answer" : "partial_or_changed",
        reason: "Qianwen screenshot image upload coordinate fallback submitted via attach-coordinate/\(menuMethod)/\(fileMethod), but answer did not stabilize before timeout; ax_setup=\(setupReason)",
        submitted: true,
        answerText: latestAnswer,
        transcriptText: latestTranscript,
        policy: imageUploadCoordinatePolicy
    )
}

private func sendPromptByCoordinateFallback(
    _ prompt: String,
    waitSeconds: Double,
    setupReason: String,
    activateFirst: Bool = true
) throws -> QwenSendResult {
    if activateFirst {
        try activateQwen()
    }
    let envBoundsMode = qwenEnvBounds() != nil
    let forceOCR = ProcessInfo.processInfo.environment["QWEN_DESKTOP_FORCE_OCR"] == "1"
    let beforeTranscript = envBoundsMode && !forceOCR ? "" : ocrTextFromQwenWindow()
    guard let windowInfo = qwenWindowInfo() else {
        return makeSendResult(
            ok: true,
            status: "blocked",
            reason: "Qianwen desktop app AX fallback could not find a visible window after: \(setupReason)",
            submitted: false,
            answerText: "",
            transcriptText: beforeTranscript,
            policy: interactivePolicy
        )
    }
    let inputPoint = CGPoint(
        x: windowInfo.bounds.midX,
        y: windowInfo.bounds.maxY - max(34, min(76, windowInfo.bounds.height * 0.12))
    )
    clickAt(inputPoint)
    Thread.sleep(forTimeInterval: 0.25)
    let fillMethod = pastePromptToFocused(prompt)
    Thread.sleep(forTimeInterval: 0.25)
    sendKey(36)

    if envBoundsMode && !forceOCR {
        return makeSendResult(
            ok: true,
            status: "submitted_no_answer",
            reason: "submitted via Qianwen desktop app coordinate fallback \(fillMethod); QWEN_DESKTOP_BOUNDS mode skipped OCR readback unless QWEN_DESKTOP_FORCE_OCR=1; ax_setup=\(setupReason)",
            submitted: true,
            answerText: "",
            transcriptText: "",
            policy: interactivePolicy
        )
    }

    let deadline = Date().addingTimeInterval(max(1.0, waitSeconds))
    var lastTranscript = ""
    var stableRounds = 0
    var latestTranscript = ""
    var latestAnswer = ""
    while Date() < deadline {
        Thread.sleep(forTimeInterval: 2.0)
        let currentTranscript = ocrTextFromQwenWindow()
        latestTranscript = currentTranscript
        latestAnswer = extractAnswer(prompt: prompt, beforeTranscript: beforeTranscript, transcript: currentTranscript)
        let generating = currentTranscript.contains("思考中")
            || currentTranscript.contains("正在生成")
            || currentTranscript.contains("停止生成")
            || currentTranscript.lowercased().contains("thinking")
        if currentTranscript == lastTranscript {
            stableRounds += 1
        } else {
            stableRounds = 0
            lastTranscript = currentTranscript
        }
        if !latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !generating && stableRounds >= 1 {
            return makeSendResult(
                ok: true,
                status: "answered",
                reason: "submitted via Qianwen desktop app coordinate fallback \(fillMethod); readback via window OCR; ax_setup=\(setupReason)",
                submitted: true,
                answerText: latestAnswer,
                transcriptText: latestTranscript,
                policy: interactivePolicy
            )
        }
    }
    return makeSendResult(
        ok: true,
        status: latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "submitted_no_answer" : "partial_or_changed",
        reason: "Qianwen desktop app coordinate fallback submitted via Return, but OCR answer did not stabilize before timeout; ax_setup=\(setupReason)",
        submitted: true,
        answerText: latestAnswer,
        transcriptText: latestTranscript,
        policy: interactivePolicy
    )
}

private func printUsage() {
    print(
        """
        Usage:
          swift ops/qwen_desktop_controller.swift send-json <wait-seconds> <prompt>
          swift ops/qwen_desktop_controller.swift send-json-interactive <wait-seconds> <prompt>
          swift ops/qwen_desktop_controller.swift send-json-screenshot <wait-seconds> <prompt>
          swift ops/qwen_desktop_controller.swift send-json-image <wait-seconds> <image-path> [prompt]
        """
    )
}

do {
    let args = Array(CommandLine.arguments.dropFirst())
    guard let command = args.first else {
        printUsage()
        throw QwenDesktopError.invalidCommand("Missing command")
    }
    switch command {
    case "diagnose-json":
        try printDiagnoseJSON()
    case "send-json":
        guard args.count >= 3 else {
            printUsage()
            throw QwenDesktopError.invalidCommand("send-json requires <wait-seconds> and <prompt>")
        }
        let waitSeconds = Double(args[1]) ?? 300.0
        let prompt = args.dropFirst(2).joined(separator: " ")
        try printJSON(try sendPrompt(prompt, waitSeconds: waitSeconds))
    case "send-json-interactive":
        guard args.count >= 3 else {
            printUsage()
            throw QwenDesktopError.invalidCommand("send-json-interactive requires <wait-seconds> and <prompt>")
        }
        let waitSeconds = Double(args[1]) ?? 300.0
        let prompt = args.dropFirst(2).joined(separator: " ")
        try printJSON(try sendPromptInteractive(prompt, waitSeconds: waitSeconds))
    case "send-json-screenshot":
        guard args.count >= 3 else {
            printUsage()
            throw QwenDesktopError.invalidCommand("send-json-screenshot requires <wait-seconds> and <prompt>")
        }
        let waitSeconds = Double(args[1]) ?? 300.0
        let prompt = args.dropFirst(2).joined(separator: " ")
        try printJSON(try sendPromptViaScreenshot(prompt, waitSeconds: waitSeconds))
    case "send-json-image":
        guard args.count >= 3 else {
            printUsage()
            throw QwenDesktopError.invalidCommand("send-json-image requires <wait-seconds> and <image-path> [prompt]")
        }
        let waitSeconds = Double(args[1]) ?? 300.0
        let imageURL = URL(fileURLWithPath: args[2])
        let prompt = args.count > 3 ? args.dropFirst(3).joined(separator: " ") : ""
        try printJSON(try sendPromptViaScreenshot(prompt, waitSeconds: waitSeconds, imageURL: imageURL))
    default:
        printUsage()
        throw QwenDesktopError.invalidCommand("Unknown command: \(command)")
    }
} catch {
    let fallback = makeSendResult(
        ok: false,
        status: "blocked",
        reason: "\(error)",
        submitted: false,
        answerText: "",
        transcriptText: "",
        policy: noninteractivePolicy
    )
    try? printJSON(fallback)
    exit(1)
}

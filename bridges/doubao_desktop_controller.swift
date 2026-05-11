import AppKit
import Foundation
import ApplicationServices
import Vision

enum DoubaoDesktopError: Error, CustomStringConvertible {
    case appNotRunning
    case mainWindowNotFound
    case inputBoxNotFound
    case invalidCommand(String)

    var description: String {
        switch self {
        case .appNotRunning:
            return "Doubao 桌面客户端未运行。"
        case .mainWindowNotFound:
            return "未找到 Doubao 主窗口。"
        case .inputBoxNotFound:
            return "未找到 Doubao 输入框。"
        case let .invalidCommand(message):
            return message
        }
    }
}

struct DoubaoSendResult: Codable {
    let ok: Bool
    let status: String
    let reason: String
    let submitted: Bool
    let answer_text: String
    let transcript_text: String
}

private let doubaoBundleIds: Set<String> = ["com.bot.neotix.doubao"]
private let doubaoNames: Set<String> = ["Doubao", "豆包"]

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
    maxDepth: Int = 14,
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

private func controlMatchingLabel(
    in root: AXUIElement,
    labels: [String],
    roles: Set<String>,
    depth: Int = 0,
    maxDepth: Int = 40
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

private func doubaoApplicationElement() -> AXUIElement? {
    guard let pid = doubaoPid() else {
        return nil
    }
    return AXUIElementCreateApplication(pid)
}

private func pressNewConversationIfAvailable() {
    guard let app = doubaoApplicationElement(),
          let button = controlMatchingLabel(
              in: app,
              labels: ["新建对话", "新对话", "新聊天", "New chat", "New conversation"],
              roles: [kAXButtonRole as String]
          )
    else {
        return
    }
    _ = AXUIElementPerformAction(button, kAXPressAction as CFString)
    Thread.sleep(forTimeInterval: 1.0)
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

private func doubaoApp() -> NSRunningApplication? {
    let apps = NSWorkspace.shared.runningApplications.filter { app in
        if let bundleIdentifier = app.bundleIdentifier,
           doubaoBundleIds.contains(bundleIdentifier) || bundleIdentifier.lowercased().contains("doubao") {
            return true
        }
        if let name = app.localizedName {
            return doubaoNames.contains(name) || name.lowercased().contains("doubao")
        }
        return false
    }
    return apps.first(where: { $0.bundleIdentifier == "com.bot.neotix.doubao" }) ?? apps.first
}

private func doubaoEnvPid() -> pid_t? {
    guard let value = ProcessInfo.processInfo.environment["DOUBAO_DESKTOP_PID"],
          let raw = Int32(value),
          raw > 0
    else {
        return nil
    }
    return raw
}

private func doubaoPid() -> pid_t? {
    if let pid = doubaoEnvPid() {
        return pid
    }
    if let pid = doubaoApp()?.processIdentifier {
        return pid
    }
    guard let infoList = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else {
        return nil
    }
    let target = infoList.first { info in
        guard let ownerName = info[kCGWindowOwnerName as String] as? String else {
            return false
        }
        return doubaoNames.contains(ownerName) || ownerName.lowercased().contains("doubao")
    }
    return (target?[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value
}

private func activateDoubao() throws {
    guard let app = doubaoApp() else {
        if doubaoEnvPid() != nil {
            return
        }
        throw DoubaoDesktopError.appNotRunning
    }
    if #available(macOS 14.0, *) {
        app.activate()
    } else {
        app.activate(options: [.activateIgnoringOtherApps])
    }
    Thread.sleep(forTimeInterval: 0.35)
}

private func mainWindowElement() throws -> AXUIElement {
    guard let pid = doubaoPid() else {
        throw DoubaoDesktopError.appNotRunning
    }
    let app = AXUIElementCreateApplication(pid)
    let candidates = windows(of: app)
    if let focused = candidates.first(where: {
        (copyAttribute($0, name: kAXFocusedAttribute as String) as? Bool) == true
    }) {
        return focused
    }
    guard let window = candidates.first else {
        throw DoubaoDesktopError.mainWindowNotFound
    }
    return window
}

private func ensureReadableWindowSize(_ window: AXUIElement) {
    guard let rect = elementRect(window), rect.width < 860 || rect.height < 700 else {
        return
    }
    var size = CGSize(width: max(rect.width, 900), height: max(rect.height, 760))
    if let value = AXValueCreate(.cgSize, &size) {
        AXUIElementSetAttributeValue(window, kAXSizeAttribute as CFString, value)
        Thread.sleep(forTimeInterval: 0.25)
    }
}

private func composer(in window: AXUIElement) throws -> AXUIElement {
    var candidates: [AXUIElement] = []
    collectElements(
        from: window,
        roles: [kAXTextAreaRole as String, kAXTextFieldRole as String],
        maxDepth: 40,
        output: &candidates
    )
    if let explicit = candidates.last(where: {
        let label = elementLabel($0)
        return label.contains("输入问题或任务")
            || label.contains("输入消息")
            || label.contains("和豆包")
            || label.contains("与豆包沟通")
            || label.contains("跟豆包")
            || label.contains("呼唤豆包")
            || label.lowercased().contains("ask doubao")
    }) {
        return explicit
    }

    let scored = candidates.compactMap { element -> (AXUIElement, CGFloat) in
        guard let rect = elementRect(element), rect.width >= 120, rect.height >= 20 else {
            return (element, 0)
        }
        let label = elementLabel(element)
        var score = rect.maxY + min(rect.width, 800) * 0.05
        if label.contains("输入") || label.lowercased().contains("ask") {
            score += 400
        }
        return (element, score)
    }
    if let best = scored.sorted(by: { $0.1 < $1.1 }).last?.0 {
        return best
    }
    guard let fallback = candidates.last else {
        throw DoubaoDesktopError.inputBoxNotFound
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

private func doubaoWindowInfo() -> (id: CGWindowID, bounds: CGRect)? {
    guard let pid = doubaoPid(),
          let infoList = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]]
    else {
        return nil
    }
    for info in infoList {
        guard (info[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value == pid,
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

private func ocrTextFromDoubaoWindow() -> String {
    guard let image = screenshotDoubaoWindowImage() else {
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

private func screenshotDoubaoWindowImage() -> CGImage? {
    guard let window = doubaoWindowInfo() else {
        return nil
    }
    let target = URL(fileURLWithPath: NSTemporaryDirectory())
        .appendingPathComponent("doubao-ai-judge-\(UUID().uuidString).png")
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
    process.arguments = ["-x", "-l", "\(window.id)", target.path]
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
    maxDepth: Int = 14,
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
        "内容由豆包 AI 生成",
        "AI 生成",
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
    return ocrTextFromDoubaoWindow()
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

private func printJSON(_ result: DoubaoSendResult) throws {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.withoutEscapingSlashes]
    let data = try encoder.encode(result)
    print(String(data: data, encoding: .utf8) ?? "{}")
}

private func sendPrompt(_ prompt: String, waitSeconds: Double) throws -> DoubaoSendResult {
    try activateDoubao()
    pressNewConversationIfAvailable()
    var window = try mainWindowElement()
    ensureReadableWindowSize(window)
    window = try mainWindowElement()
    let input: AXUIElement
    do {
        input = try composer(in: window)
    } catch {
        if ProcessInfo.processInfo.environment["DOUBAO_DESKTOP_ALLOW_COORDINATE_FALLBACK"] != "1" {
            return DoubaoSendResult(
                ok: true,
                status: "blocked",
                reason: "Doubao desktop app AX input not found; coordinate/OCR fallback disabled because it can read stale UI instead of the active answer: \(error)",
                submitted: false,
                answer_text: "",
                transcript_text: readableText(in: window)
            )
        }
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
        return DoubaoSendResult(
            ok: true,
            status: "submit_not_confirmed",
            reason: "Doubao desktop app prompt filled via \(fillMethod), but prompt remained in composer after \(submitMethod)",
            submitted: false,
            answer_text: "",
            transcript_text: readableText(in: window)
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
            return DoubaoSendResult(
                ok: true,
                status: "answered",
                reason: "submitted via Doubao desktop app AX \(submitMethod); readback stable",
                submitted: true,
                answer_text: latestAnswer,
                transcript_text: latestTranscript
            )
        }
    }
    return DoubaoSendResult(
        ok: true,
        status: latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "submitted_no_answer" : "partial_or_changed",
        reason: observedStop
            ? "Doubao desktop app submitted via \(submitMethod), but answer did not stabilize before timeout"
            : "Doubao desktop app submitted via \(submitMethod), but no answer was detected before timeout",
        submitted: true,
        answer_text: latestAnswer,
        transcript_text: latestTranscript
    )
}

private func sendPromptByCoordinateFallback(_ prompt: String, waitSeconds: Double, setupReason: String) throws -> DoubaoSendResult {
    try activateDoubao()
    var window = try mainWindowElement()
    ensureReadableWindowSize(window)
    window = try mainWindowElement()
    let beforeTranscript = readableText(in: window)
    guard let windowInfo = doubaoWindowInfo() else {
        return DoubaoSendResult(
            ok: true,
            status: "blocked",
            reason: "Doubao desktop app AX fallback could not find a visible window after: \(setupReason)",
            submitted: false,
            answer_text: "",
            transcript_text: beforeTranscript
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

    let deadline = Date().addingTimeInterval(max(1.0, waitSeconds))
    var lastTranscript = ""
    var stableRounds = 0
    var latestTranscript = ""
    var latestAnswer = ""
    while Date() < deadline {
        Thread.sleep(forTimeInterval: 2.0)
        window = try mainWindowElement()
        let currentTranscript = readableText(in: window)
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
            return DoubaoSendResult(
                ok: true,
                status: "answered",
                reason: "submitted via Doubao desktop app coordinate fallback \(fillMethod); readback via window OCR; ax_setup=\(setupReason)",
                submitted: true,
                answer_text: latestAnswer,
                transcript_text: latestTranscript
            )
        }
    }
    return DoubaoSendResult(
        ok: true,
        status: latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "submitted_no_answer" : "partial_or_changed",
        reason: "Doubao desktop app coordinate fallback submitted via Return, but OCR answer did not stabilize before timeout; ax_setup=\(setupReason)",
        submitted: true,
        answer_text: latestAnswer,
        transcript_text: latestTranscript
    )
}

private func printUsage() {
    print(
        """
        Usage:
          swift ops/doubao_desktop_controller.swift send-json <wait-seconds> <prompt>
        """
    )
}

do {
    let args = Array(CommandLine.arguments.dropFirst())
    guard let command = args.first else {
        printUsage()
        throw DoubaoDesktopError.invalidCommand("Missing command")
    }
    switch command {
    case "send-json":
        guard args.count >= 3 else {
            printUsage()
            throw DoubaoDesktopError.invalidCommand("send-json requires <wait-seconds> and <prompt>")
        }
        let waitSeconds = Double(args[1]) ?? 300.0
        let prompt = args.dropFirst(2).joined(separator: " ")
        try printJSON(try sendPrompt(prompt, waitSeconds: waitSeconds))
    default:
        printUsage()
        throw DoubaoDesktopError.invalidCommand("Unknown command: \(command)")
    }
} catch {
    let fallback = DoubaoSendResult(
        ok: false,
        status: "blocked",
        reason: "\(error)",
        submitted: false,
        answer_text: "",
        transcript_text: ""
    )
    try? printJSON(fallback)
    exit(1)
}

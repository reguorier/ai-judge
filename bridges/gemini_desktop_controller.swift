import AppKit
import Foundation
import ApplicationServices

enum GeminiDesktopError: Error, CustomStringConvertible {
    case appNotRunning
    case mainWindowNotFound
    case inputBoxNotFound
    case submitButtonNotFound
    case invalidCommand(String)

    var description: String {
        switch self {
        case .appNotRunning:
            return "Gemini 桌面客户端未运行。"
        case .mainWindowNotFound:
            return "未找到 Gemini 主窗口。"
        case .inputBoxNotFound:
            return "未找到 Gemini 输入框。"
        case .submitButtonNotFound:
            return "未找到 Gemini 提交按钮。"
        case let .invalidCommand(message):
            return message
        }
    }
}

struct GeminiSendResult: Codable {
    let ok: Bool
    let status: String
    let reason: String
    let submitted: Bool
    let answer_text: String
    let transcript_text: String
}

private let geminiBundleIds: Set<String> = ["com.google.GeminiMacOS", "com.google.GeminiMacOS.launcher"]

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
    return raw.map { $0 as! AXUIElement }
}

private func collectElements(
    from element: AXUIElement,
    role: String,
    depth: Int = 0,
    maxDepth: Int = 12,
    output: inout [AXUIElement]
) {
    if let currentRole = copyAttribute(element, name: kAXRoleAttribute as String) as? String, currentRole == role {
        output.append(element)
    }
    if depth >= maxDepth {
        return
    }
    for child in children(of: element) {
        collectElements(from: child, role: role, depth: depth + 1, maxDepth: maxDepth, output: &output)
    }
}

private func elementLabel(_ element: AXUIElement) -> String {
    let names = [
        kAXTitleAttribute as String,
        kAXDescriptionAttribute as String,
        kAXHelpAttribute as String,
        kAXValueAttribute as String,
    ]
    return names.compactMap { copyAttribute(element, name: $0) as? String }
        .filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        .joined(separator: " ")
}

private func geminiApp() -> NSRunningApplication? {
    let apps = NSWorkspace.shared.runningApplications.filter { app in
        guard let bundleIdentifier = app.bundleIdentifier else {
            return app.localizedName == "Gemini"
        }
        return geminiBundleIds.contains(bundleIdentifier)
    }
    return apps.first(where: { $0.bundleIdentifier == "com.google.GeminiMacOS" }) ?? apps.first
}

private func geminiEnvPid() -> pid_t? {
    guard let value = ProcessInfo.processInfo.environment["GEMINI_DESKTOP_PID"],
          let raw = Int32(value),
          raw > 0
    else {
        return nil
    }
    return raw
}

private func geminiPid() -> pid_t? {
    if let pid = geminiEnvPid() {
        return pid
    }
    if let pid = geminiApp()?.processIdentifier {
        return pid
    }
    guard let infoList = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else {
        return nil
    }
    let target = infoList.first { info in
        let ownerName = info[kCGWindowOwnerName as String] as? String
        return ownerName == "Gemini"
    }
    return (target?[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value
}

private func activateGemini() throws {
    guard let app = geminiApp() else {
        if geminiEnvPid() != nil {
            return
        }
        throw GeminiDesktopError.appNotRunning
    }
    if #available(macOS 14.0, *) {
        app.activate()
    } else {
        app.activate(options: [.activateIgnoringOtherApps])
    }
    Thread.sleep(forTimeInterval: 0.35)
}

private func mainWindowElement() throws -> AXUIElement {
    guard let pid = geminiPid() else {
        throw GeminiDesktopError.appNotRunning
    }
    let app = AXUIElementCreateApplication(pid)
    let windows = children(of: app)
    guard let window = windows.first else {
        throw GeminiDesktopError.mainWindowNotFound
    }
    return window
}

private func composer(in window: AXUIElement) throws -> AXUIElement {
    var textAreas: [AXUIElement] = []
    var textFields: [AXUIElement] = []
    collectElements(from: window, role: kAXTextAreaRole as String, output: &textAreas)
    collectElements(from: window, role: kAXTextFieldRole as String, output: &textFields)
    let candidates = textAreas + textFields
    if let explicit = candidates.last(where: {
        let label = elementLabel($0)
        return label.contains("输入给 Gemini 的提示") || label.contains("问问 Gemini")
    }) {
        return explicit
    }
    guard let fallback = candidates.last else {
        throw GeminiDesktopError.inputBoxNotFound
    }
    return fallback
}

private func submitButton(in window: AXUIElement) -> AXUIElement? {
    var buttons: [AXUIElement] = []
    collectElements(from: window, role: kAXButtonRole as String, output: &buttons)
    return buttons.first(where: {
        let label = elementLabel($0)
        return (label.contains("提交") || label.contains("发送")) && !label.contains("停止")
    })
}

private func hasStopButton(in window: AXUIElement) -> Bool {
    var buttons: [AXUIElement] = []
    collectElements(from: window, role: kAXButtonRole as String, output: &buttons)
    return buttons.contains(where: { elementLabel($0).contains("停止回答") || elementLabel($0).contains("停止") })
}

private func collectTextContent(
    from element: AXUIElement,
    depth: Int = 0,
    maxDepth: Int = 12,
    output: inout [String]
) {
    let textRoles = [
        kAXStaticTextRole as String,
        kAXTextAreaRole as String,
        kAXTextFieldRole as String,
    ]
    if let role = copyAttribute(element, name: kAXRoleAttribute as String) as? String,
       textRoles.contains(role),
       let value = copyAttribute(element, name: kAXValueAttribute as String) as? String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
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
    for value in raw {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty || trimmed == "问问 Gemini" || trimmed == "Gemini 是一款 AI 工具，其回答未必正确无误。" {
            continue
        }
        if seen.insert(trimmed).inserted {
            lines.append(trimmed)
        }
    }
    return lines.joined(separator: "\n")
}

private func extractAnswer(prompt: String, transcript: String) -> String {
    let trimmedPrompt = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
    let trimmedTranscript = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !trimmedPrompt.isEmpty, !trimmedTranscript.isEmpty else {
        return ""
    }
    if let range = trimmedTranscript.range(of: trimmedPrompt, options: [.backwards]) {
        return String(trimmedTranscript[range.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
    }
    let firstLine = trimmedPrompt.components(separatedBy: .newlines).first ?? ""
    if firstLine.count >= 12, let range = trimmedTranscript.range(of: firstLine, options: [.backwards]) {
        return String(trimmedTranscript[range.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
    }
    return trimmedTranscript
}

private func printJSON(_ result: GeminiSendResult) throws {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.withoutEscapingSlashes]
    let data = try encoder.encode(result)
    print(String(data: data, encoding: .utf8) ?? "{}")
}

private func sendPrompt(_ prompt: String, waitSeconds: Double) throws -> GeminiSendResult {
    try activateGemini()
    var window = try mainWindowElement()
    let input = try composer(in: window)
    _ = AXUIElementSetAttributeValue(input, kAXFocusedAttribute as CFString, kCFBooleanTrue)
    _ = AXUIElementSetAttributeValue(input, kAXValueAttribute as CFString, prompt as CFString)
    Thread.sleep(forTimeInterval: 0.25)
    window = try mainWindowElement()
    guard let button = submitButton(in: window) else {
        return GeminiSendResult(
            ok: true,
            status: "submit_not_confirmed",
            reason: "Gemini desktop app prompt filled but submit button was not found",
            submitted: false,
            answer_text: "",
            transcript_text: transcriptText(in: window)
        )
    }
    let pressResult = AXUIElementPerformAction(button, kAXPressAction as CFString)
    guard pressResult == .success else {
        return GeminiSendResult(
            ok: true,
            status: "submit_not_confirmed",
            reason: "Gemini desktop app submit button press failed: \(pressResult.rawValue)",
            submitted: false,
            answer_text: "",
            transcript_text: transcriptText(in: window)
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
        let currentTranscript = transcriptText(in: window)
        latestTranscript = currentTranscript
        latestAnswer = extractAnswer(prompt: prompt, transcript: currentTranscript)
        let generating = hasStopButton(in: window)
        observedStop = observedStop || generating
        if currentTranscript == lastTranscript {
            stableRounds += 1
        } else {
            stableRounds = 0
            lastTranscript = currentTranscript
        }
        if !latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !generating && stableRounds >= 1 {
            return GeminiSendResult(
                ok: true,
                status: "answered",
                reason: "submitted via Gemini desktop app AX; readback stable",
                submitted: true,
                answer_text: latestAnswer,
                transcript_text: latestTranscript
            )
        }
    }
    return GeminiSendResult(
        ok: true,
        status: latestAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "submitted_no_answer" : "partial_or_changed",
        reason: observedStop ? "Gemini desktop app submitted but answer did not stabilize before timeout" : "Gemini desktop app submitted but no answer was detected before timeout",
        submitted: true,
        answer_text: latestAnswer,
        transcript_text: latestTranscript
    )
}

private func printUsage() {
    print(
        """
        Usage:
          swift ops/gemini_desktop_controller.swift send-json <wait-seconds> <prompt>
        """
    )
}

do {
    let args = Array(CommandLine.arguments.dropFirst())
    guard let command = args.first else {
        printUsage()
        throw GeminiDesktopError.invalidCommand("Missing command")
    }
    switch command {
    case "send-json":
        guard args.count >= 3 else {
            printUsage()
            throw GeminiDesktopError.invalidCommand("send-json requires <wait-seconds> and <prompt>")
        }
        let waitSeconds = Double(args[1]) ?? 300.0
        let prompt = args.dropFirst(2).joined(separator: " ")
        try printJSON(try sendPrompt(prompt, waitSeconds: waitSeconds))
    default:
        printUsage()
        throw GeminiDesktopError.invalidCommand("Unknown command: \(command)")
    }
} catch {
    let fallback = GeminiSendResult(
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

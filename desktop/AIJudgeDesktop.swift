import Cocoa
import Foundation
import WebKit

struct AppleScriptPayload: Codable {
    let lines: [String]
}

func runAppleScriptHelper() -> Int32 {
    let input = FileHandle.standardInput.readDataToEndOfFile()
    do {
        let payload = try JSONDecoder().decode(AppleScriptPayload.self, from: input)
        let source = payload.lines.joined(separator: "\n")
        guard let script = NSAppleScript(source: source) else {
            FileHandle.standardError.write(Data("Could not compile AppleScript.\n".utf8))
            return 2
        }
        var error: NSDictionary?
        let result = script.executeAndReturnError(&error)
        if let error {
            let message = (error[NSAppleScript.errorMessage] as? String) ?? "\(error)"
            FileHandle.standardError.write(Data(message.utf8))
            FileHandle.standardError.write(Data("\n".utf8))
            return 1
        }
        if let value = result.stringValue, !value.isEmpty {
            FileHandle.standardOutput.write(Data(value.utf8))
            FileHandle.standardOutput.write(Data("\n".utf8))
        }
        return 0
    } catch {
        FileHandle.standardError.write(Data("Invalid AppleScript helper payload: \(error.localizedDescription)\n".utf8))
        return 2
    }
}

struct AIJudgeConfig: Codable {
    let projectRoot: String
    let host: String
    let port: Int
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow!
    private var webView: WKWebView!
    private var serverProcess: Process?
    private var logHandle: FileHandle?
    private var ownsServer = false
    private var config: AIJudgeConfig!

    func applicationDidFinishLaunching(_ notification: Notification) {
        config = loadConfig()
        applyAppIcon()
        buildMenu()
        buildWindow()
        startOrConnectServer()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        if ownsServer, let process = serverProcess, process.isRunning {
            process.terminate()
        }
        try? logHandle?.close()
    }

    private func buildMenu() {
        let menu = NSMenu()

        let appItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(NSMenuItem(title: "Reload AI Judge", action: #selector(reloadDashboard(_:)), keyEquivalent: "r"))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Quit AI Judge", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        appItem.submenu = appMenu
        menu.addItem(appItem)

        let editItem = NSMenuItem()
        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(NSMenuItem(title: "Undo", action: Selector(("undo:")), keyEquivalent: "z"))
        let redoItem = NSMenuItem(title: "Redo", action: Selector(("redo:")), keyEquivalent: "Z")
        redoItem.keyEquivalentModifierMask = [.command, .shift]
        editMenu.addItem(redoItem)
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(NSMenuItem(title: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x"))
        editMenu.addItem(NSMenuItem(title: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c"))
        editMenu.addItem(NSMenuItem(title: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v"))
        let pastePlainItem = NSMenuItem(title: "Paste and Match Style", action: #selector(NSTextView.pasteAsPlainText(_:)), keyEquivalent: "V")
        pastePlainItem.keyEquivalentModifierMask = [.command, .option, .shift]
        editMenu.addItem(pastePlainItem)
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(NSMenuItem(title: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a"))
        editItem.submenu = editMenu
        menu.addItem(editItem)

        NSApp.mainMenu = menu
    }

    @objc private func reloadDashboard(_ sender: Any?) {
        loadDashboard()
    }

    private func applyAppIcon() {
        let size = NSSize(width: 1024, height: 1024)
        let image = NSImage(size: size)
        image.lockFocus()

        let iconRect = NSRect(x: 84, y: 84, width: 856, height: 856)
        let iconPath = NSBezierPath(roundedRect: iconRect, xRadius: 214, yRadius: 214)
        let gradient = NSGradient(colors: [
            NSColor(calibratedRed: 0.10, green: 0.13, blue: 0.20, alpha: 1),
            NSColor(calibratedRed: 0.05, green: 0.07, blue: 0.12, alpha: 1),
        ])
        gradient?.draw(in: iconPath, angle: 315)

        NSColor(calibratedWhite: 1, alpha: 0.08).setStroke()
        iconPath.lineWidth = 7
        iconPath.stroke()

        let font = NSFont.systemFont(ofSize: 386, weight: .heavy)
        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = .center
        let attributes: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: NSColor.white,
            .paragraphStyle: paragraph,
            .kern: -12,
        ]
        let glyph = NSAttributedString(string: "AJ", attributes: attributes)
        glyph.draw(in: NSRect(x: 120, y: 284, width: 784, height: 430))

        NSColor(calibratedRed: 1.0, green: 0.68, blue: 0.20, alpha: 1).setFill()
        NSBezierPath(ovalIn: NSRect(x: 704, y: 700, width: 88, height: 88)).fill()

        NSColor(calibratedWhite: 1, alpha: 0.18).setStroke()
        let orbit = NSBezierPath()
        orbit.move(to: NSPoint(x: 256, y: 250))
        orbit.curve(to: NSPoint(x: 776, y: 776), controlPoint1: NSPoint(x: 520, y: 104), controlPoint2: NSPoint(x: 850, y: 410))
        orbit.lineWidth = 12
        orbit.lineCapStyle = .round
        orbit.stroke()

        image.unlockFocus()
        NSApp.applicationIconImage = image
    }

    private func buildWindow() {
        let frame = NSRect(x: 0, y: 0, width: 1420, height: 920)
        window = NSWindow(
            contentRect: frame,
            styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        window.title = "AI Judge - 双模式客户端"
        window.center()
        window.minSize = NSSize(width: 1080, height: 720)

        let preferences = WKPreferences()
        preferences.javaScriptCanOpenWindowsAutomatically = true
        let webConfig = WKWebViewConfiguration()
        webConfig.preferences = preferences
        webView = WKWebView(frame: frame, configuration: webConfig)
        webView.customUserAgent = "AIJudgeDesktop/3.6.1 macOS DraftArena"
        webView.autoresizingMask = [.width, .height]
        window.contentView = webView
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func loadConfig() -> AIJudgeConfig {
        let fallback = AIJudgeConfig(
            projectRoot: FileManager.default.currentDirectoryPath,
            host: "127.0.0.1",
            port: 8501
        )
        guard let resourceURL = Bundle.main.resourceURL else {
            return fallback
        }
        let configURL = resourceURL.appendingPathComponent("config.json")
        guard let data = try? Data(contentsOf: configURL),
              let decoded = try? JSONDecoder().decode(AIJudgeConfig.self, from: data) else {
            return fallback
        }
        return decoded
    }

    private func startOrConnectServer() {
        checkHealth { [weak self] ok in
            guard let self else { return }
            DispatchQueue.main.async {
                if ok {
                    self.loadDashboard()
                } else {
                    self.startServer()
                    self.waitForServer(attempts: 180)
                }
            }
        }
    }

    private func startServer() {
        let root = config.projectRoot
        let pythonCandidates = [
            "\(root)/python/bin/python3.12",
            "\(root)/python/bin/python3",
            "\(root)/python/bin/python",
            "\(root)/.venv/bin/python",
            "\(root)/.venv/bin/python3",
            "/opt/homebrew/bin/python3.14",
            "/opt/homebrew/bin/python3",
            "/usr/bin/python3"
        ]
        guard let python = pythonCandidates.first(where: { FileManager.default.isExecutableFile(atPath: $0) }) else {
            showStartupError("Python runtime was not found.")
            return
        }

        let serverScript = "\(root)/product/api_server.py"
        guard FileManager.default.fileExists(atPath: serverScript) else {
            showStartupError("AI Judge API server was not found at \(serverScript).")
            return
        }

        let dataDir = "\(root)/data"
        try? FileManager.default.createDirectory(atPath: dataDir, withIntermediateDirectories: true)
        let logPath = "\(dataDir)/desktop-server.log"
        FileManager.default.createFile(atPath: logPath, contents: nil)
        logHandle = FileHandle(forWritingAtPath: logPath)
        logHandle?.seekToEndOfFile()

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/zsh")
        let launchCommand = [
            "cd \(shellQuote(root))",
            "exec \(shellQuote(python)) \(shellQuote(serverScript)) --host \(shellQuote(config.host)) --port \(shellQuote(String(config.port)))"
        ].joined(separator: " && ")
        process.arguments = ["-c", launchCommand]
        process.currentDirectoryURL = URL(fileURLWithPath: root)
        var environment = ProcessInfo.processInfo.environment
        environment["AI_JUDGE_APP_URL"] = baseURL()
        environment["AI_JUDGE_DESKTOP_CLIENT"] = "1"
        environment["AI_JUDGE_CHROME_HELPER"] = Bundle.main.executablePath ?? ""
        environment["PYTHONUNBUFFERED"] = "1"
        environment.removeValue(forKey: "__PYVENV_LAUNCHER__")
        let venvSite = "\(root)/.venv/lib/python3.14/site-packages"
        let currentPythonPath = environment["PYTHONPATH"] ?? ""
        environment["PYTHONPATH"] = currentPythonPath.isEmpty ? venvSite : "\(venvSite):\(currentPythonPath)"
        let currentPath = environment["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin"
        environment["PATH"] = "\(root)/.venv/bin:\(currentPath)"
        process.environment = environment
        process.standardOutput = logHandle
        process.standardError = logHandle

        do {
            try process.run()
            serverProcess = process
            ownsServer = true
        } catch {
            showStartupError("Could not start AI Judge API server: \(error.localizedDescription)")
        }
    }

    private func waitForServer(attempts: Int) {
        guard attempts > 0 else {
            showStartupError("AI Judge API did not become ready. See data/desktop-server.log in the project folder.")
            return
        }
        checkHealth { [weak self] ok in
            guard let self else { return }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                ok ? self.loadDashboard() : self.waitForServer(attempts: attempts - 1)
            }
        }
    }

    private func checkHealth(completion: @escaping (Bool) -> Void) {
        guard let url = URL(string: "\(baseURL())/api/health") else {
            completion(false)
            return
        }
        var request = URLRequest(url: url)
        request.timeoutInterval = 1.2
        URLSession.shared.dataTask(with: request) { _, response, _ in
            let ok = (response as? HTTPURLResponse)?.statusCode == 200
            completion(ok)
        }.resume()
    }

    private func loadDashboard() {
        guard let url = URL(string: baseURL()) else {
            showStartupError("Invalid AI Judge URL.")
            return
        }
        webView.load(URLRequest(url: url))
    }

    private func baseURL() -> String {
        return "http://\(config.host):\(config.port)"
    }

    private func shellQuote(_ value: String) -> String {
        return "'" + value.replacingOccurrences(of: "'", with: "'\\''") + "'"
    }

    private func showStartupError(_ message: String) {
        let escaped = message
            .replacingOccurrences(of: "&", with: "&amp;")
            .replacingOccurrences(of: "<", with: "&lt;")
            .replacingOccurrences(of: ">", with: "&gt;")
        let html = """
        <!doctype html><html><head><meta charset="utf-8">
        <style>
        body { margin: 0; background: #090b10; color: #f2f5fb; font: 15px -apple-system, BlinkMacSystemFont, sans-serif; }
        main { max-width: 720px; margin: 80px auto; padding: 24px; border: 1px solid #283244; border-radius: 10px; background: #121722; }
        code { color: #f4c542; }
        </style></head><body><main>
        <h1>AI Judge could not start</h1>
        <p>\(escaped)</p>
        <p>Project root: <code>\(config.projectRoot)</code></p>
        </main></body></html>
        """
        webView.loadHTMLString(html, baseURL: nil)
    }
}

if CommandLine.arguments.contains("--run-applescript-json") {
    exit(runAppleScriptHelper())
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()

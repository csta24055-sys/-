import XCTest

/// Drives the real Mobile Safari of the iOS Simulator (not a physical iPhone):
/// open the deployed web app, add it to the Home Screen and launch it from the new icon.
final class AddToHomeScreenTests: XCTestCase {
    let url = ProcessInfo.processInfo.environment["PWA_URL"] ?? "https://tajima-lab.pages.dev/"
    let label = "田嶋研究室"
    let safari = XCUIApplication(bundleIdentifier: "com.apple.mobilesafari")
    let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")

    func shot(_ name: String) {
        let a = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        a.name = name
        a.lifetime = .keepAlways
        add(a)
    }
    func first(_ candidates: [XCUIElement], timeout: TimeInterval = 2) -> XCUIElement? {
        let deadline = Date().addingTimeInterval(timeout)
        repeat {
            for c in candidates where c.exists { return c }
            usleep(250_000)
        } while Date() < deadline
        return nil
    }
    func dismissSafariWelcome() {
        for title in ["Continue", "Not Now", "Close", "OK", "Done"] {
            let b = safari.buttons[title]
            if b.exists && b.isHittable { b.tap() }
        }
    }
    func text(_ app: XCUIApplication, containing s: String) -> XCUIElement {
        app.descendants(matching: .any).matching(NSPredicate(format: "label CONTAINS %@", s)).firstMatch
    }

    func testAddToHomeScreenAndLaunchStandalone() throws {
        safari.launch()
        dismissSafariWelcome()
        // 1) Open the URL from the address bar
        let bar = first([safari.textFields["TabBarItemTitle"], safari.buttons["TabBarItemTitle"], safari.textFields["Address"], safari.buttons["Address"], safari.textFields["URL"], safari.buttons["URL"]], timeout: 15)
        XCTAssertNotNil(bar, "Safari address bar")
        bar?.tap()
        let field = first([safari.textFields["URL"], safari.textFields["Address"], safari.textFields["TabBarItemTitle"]], timeout: 8)
        XCTAssertNotNil(field, "URL field")
        field?.typeText(url + "\n")
        XCTAssertTrue(text(safari, containing: "研究ダッシュボード").waitForExistence(timeout: 60), "web app loaded in Safari")
        sleep(4) // let the service worker finish caching
        shot("01-safari-first-visit")

        // 2) Share → Add to Home Screen (button location differs between iOS versions)
        var share = first([safari.buttons["ShareButton"], safari.buttons["Share"]], timeout: 4)
        if share == nil, let more = first([safari.buttons["MoreButton"], safari.buttons["More"], safari.buttons["PageFormatMenuButton"], safari.buttons["Page Menu"], safari.buttons["TabBarItemMoreButton"]], timeout: 4) {
            more.tap()
            share = first([safari.buttons["Share"], safari.buttons["ShareButton"], safari.cells["Share"], safari.staticTexts["Share"]], timeout: 6)
        }
        XCTAssertNotNil(share, "Share button")
        share?.tap()
        sleep(2)
        shot("02-share-sheet")
        var addAction: XCUIElement? = nil
        for _ in 0..<8 {
            addAction = first([safari.buttons["Add to Home Screen"], safari.cells["Add to Home Screen"], safari.staticTexts["Add to Home Screen"], safari.otherElements["Add to Home Screen"]], timeout: 2)
            if let a = addAction, a.isHittable { break }
            let sheet = safari.otherElements["ActivityListView"].exists ? safari.otherElements["ActivityListView"] : safari.collectionViews.firstMatch
            sheet.swipeUp()
        }
        XCTAssertNotNil(addAction, "Add to Home Screen action")
        addAction?.tap()
        sleep(2)
        shot("03-add-to-home-screen-sheet")
        let nameField = safari.textFields.firstMatch
        if nameField.exists, let value = nameField.value as? String { XCTAssertEqual(value, label, "suggested Home Screen name") }
        let addButton = first([safari.buttons["Add"], safari.navigationBars.buttons["Add"]], timeout: 10)
        XCTAssertNotNil(addButton, "Add button")
        addButton?.tap()
        sleep(3)

        // 3) Home Screen icon → launch
        XCUIDevice.shared.press(.home)
        sleep(2)
        let icon = springboard.icons[label]
        if !icon.waitForExistence(timeout: 10) { springboard.swipeLeft(); sleep(1) }
        XCTAssertTrue(icon.waitForExistence(timeout: 15), "Home Screen icon 「田嶋研究室」")
        shot("04-home-screen-icon")
        icon.tap()
        sleep(10)
        shot("05-launched-from-home-screen")

        // 4) In the launched app: Settings shows 「ホーム画面のアプリとして起動中です」 only in standalone mode
        let webApp = XCUIApplication(bundleIdentifier: "com.apple.webapp")
        let target: XCUIApplication = text(webApp, containing: "研究ダッシュボード").waitForExistence(timeout: 10) ? webApp : springboard
        let more = first([target.buttons["その他"]], timeout: 10)
        XCTAssertNotNil(more, "bottom tab その他 in the launched app")
        more?.tap()
        let settings = first([target.buttons["設定・ホーム画面への追加方法"]], timeout: 10)
        settings?.tap()
        XCTAssertTrue(text(target, containing: "ホーム画面のアプリとして起動中です").waitForExistence(timeout: 15), "standalone display mode detected")
        shot("06-standalone-settings")
    }
}

# Regenerating screenshots

`scripts/screenshots.sh` recaptures every screen of the app on the booted iOS
simulator and writes them to `screenshots/` (home, explore, superstar, detail,
settings), plus a store-style version of each in `screenshots/framed/` that the
README shows. Run it whenever the UI changes so the README stays accurate.

## Prerequisites

- macOS with Xcode (`xcrun simctl`), the app already built once: `yarn ios`
- A booted simulator with the app installed (`xcrun simctl list devices`)
- Metro on port 8081 (the script starts it if it is not running)
- `python3`, `sips` (ships with macOS); `swiftc` is used for OCR verification

## Usage

```sh
scripts/screenshots.sh                  # capture into screenshots/
scripts/screenshots.sh --wait 30        # slower devices / cold API
scripts/screenshots.sh --out /tmp/shots # dry run somewhere else
scripts/screenshots.sh --no-verify      # skip the OCR check
scripts/screenshots.sh --no-frame       # skip the framed versions
scripts/screenshots.sh --frame-only     # re-frame existing captures (no simulator)
```

Environment overrides: `UDID`, `BUNDLE_ID`, `HERO_ID` (hero opened by the
`detail` screenshot, default `8` = Juggernaut), `WAIT_SECONDS`, `MAX_HEIGHT`
(max PNG height passed to `sips`, default 1200), `METRO_PORT`.

The script restores `App.tsx` on exit (even on failure), so nothing it does
should ever end up in a commit.

## How it works

1. **Navigate without taps.** Xcode 27 runs simulators headless (no Simulator
   window), so there is nothing to click on. Instead, the script temporarily
   patches `App.tsx` (`scripts/patch_app_for_screenshots.py`) to seed React
   Navigation with an `initialState` for the requested screen and to force a
   remount with `key={SHOT_ROUTE}`. `LogBox.ignoreAllLogs()` is injected so the
   yellow dev warning box never lands in a screenshot. Metro fast-refreshes the
   running app; a fixed wait lets the OpenDota/Valve requests settle.
2. **Capture.** `xcrun simctl io <udid> screenshot` grabs the device
   framebuffer (1206x2622 on the iPhone 18 Pro).
3. **Verify.** `scripts/verify_screen.swift` runs Vision OCR
   (`VNRecognizeTextRequest`) on the PNG and fails the run if the expected text
   for that screen is missing (e.g. `Dota 2 Heroes` on home,
   `Juggernaut` on detail). This is the substitute for eyeballing the images.
4. **Resize.** `sips -Z 1200` downscales to ~552x1200 so the repo stays small.
5. **Frame.** `scripts/frame_screenshot.swift` (CoreGraphics, no extra
   dependencies) draws each capture inside an iPhone frame (rounded display,
   Dynamic Island, side buttons) on the app's background colors, with the
   headline from `store_title` in the script above it, and writes a 600x1300
   PNG to `screenshots/framed/`. The frame is drawn, not an Apple bezel image,
   so there is nothing to license.

## Manual fallback

Same steps, without the automation:

```sh
# seed a screen (home | explore | superstar | settings | detail)
python3 scripts/patch_app_for_screenshots.py superstar
sleep 20
xcrun simctl io booted screenshot superstar.png
swiftc -O -o verify scripts/verify_screen.swift && ./verify superstar.png Superstar
sips -Z 1200 superstar.png --out screenshots/superstar.png
git checkout -- App.tsx
```

## Limitations / future work

- **iOS only.** Android would need an emulator + `adb exec-out screencap`, same
  driver patch (Metro serves both platforms).
- **No gestures.** Without a Simulator window there are no taps or scrolls, so
  scrolled states, filters applied mid-session and `demo.gif` cannot be
  recorded. Options: `fb-idb` (`idb ui tap/swipe` works headless) or permanent
  React Navigation deep links (`dota2app://hero/8`) driven with
  `xcrun simctl openurl`.
- **Dev build.** Screens come from the debug bundle with LogBox silenced. A
  Release build (`npx react-native run-ios --mode Release`) removes the perf
  caveat but needs a rebuild whenever the navigation state changes.
- The patcher anchors on exact snippets of `App.tsx`
  (`<NavigationContainer theme={MyTheme}>`, the `App` component body). If those
  change, the script exits with a message pointing here; update the anchors in
  `scripts/patch_app_for_screenshots.py`.

# Gesture Control — Touchless Keyboard & Mouse

Control your computer with hand gestures through a webcam — no keyboard, mouse, or touch required. Built for accessibility and hygiene-sensitive environments.

<!-- Add a demo GIF here: ![demo](demo.gif) -->

## Features

- **Two hands → Virtual keyboard.** Hover your index finger over a key, tap index and middle fingers together to type.
- **One hand → Mouse.** Pinch thumb and index to move the cursor; tap to left-click.
- **Automatic mode switching** based on how many hands are visible — no buttons or menus.
- **C-sign gesture to exit** — distinctive enough that it never fires by accident.
- **Live visual feedback** — keys highlight blue on hover and flash green on tap.

## How It Works

```
Camera → Hand Tracker → Gesture Recognizer → Interactor → OS Input
          (MediaPipe,     (tap / pinch /      (mode logic,   (PyAutoGUI)
          21 landmarks)    C-sign)             cooldowns)
```

Key engineering decisions:
- **Depth-adjusted thresholds** — tap/pinch sensitivity scales with hand distance from the camera, so gestures register reliably near or far.
- **Exponential smoothing + deadzone** — filters natural hand tremor for a steady, non-jittery cursor.
- **Input range expansion** — the center 70% of the camera view maps to 100% of the screen, so edges are reachable without over-reaching.
- **200 ms per-key cooldown** — prevents double-typing when a tap spans multiple frames.

## Performance

| Metric | Value |
|---|---|
| Frame rate | 30 FPS |
| Tap-to-keystroke latency | ~33–66 ms |
| CPU | ~25–35% of one core |
| Memory | ~200 MB |

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Requires Python 3.9–3.12 (MediaPipe) and a webcam. Camera, smoothing, and keyboard settings are saved in `settings.json`.

## Tech Stack

Python · OpenCV · MediaPipe · PyAutoGUI · NumPy

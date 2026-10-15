<div align="center">

# 🖱️ GlideX
**Real-Time Cinematic Cursor Physics & Smooth Animations for Windows 11**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/UI-PySide6%20(Qt6)-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://wiki.qt.io/Qt_for_Python)
[![Platform](https://img.shields.io/badge/Platform-Windows%2011%2F10-0078D6?style=for-the-badge&logo=windows&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-6366F1?style=for-the-badge)]()

*Transform your everyday Windows mouse pointer into a fluid, physics-driven visual experience—live on your desktop.*

</div>

---

## ✨ Overview

Have you ever watched high-production tech videos on YouTube (made with tools like *Screen Studio*) and wished your actual Windows cursor moved that smoothly in real time? 

**GlideX** is a lightweight, high-performance Windows desktop utility built with **Python**, **PySide6**, and **Win32/Magnification APIs**. Instead of replacing your cursors with generic shapes, GlideX extracts your **actual active Windows cursors** (including dynamic browser/app cursors like `grab` and `grabbing`), scales them up cleanly, and injects 60+ FPS physics, directional tilt, and tactile click-bounce animations directly onto your screen.

---

## 🚀 Key Features

* **🌊 Smooth Glide Interpolation:** Eliminates raw mouse jitter by smoothly interpolating cursor movement with adjustable damping—from zero-latency instant tracking to ultra-cinematic glide.
* **✈️ Velocity-Based Tilt & Squash/Stretch:** The cursor dynamically leans into horizontal movements (banking left/right) and subtly stretches during fast swipes before springing back to rest.
* **👆 Tactile Click-Bounce & Ripple Effects:** Compresses smoothly on mouse press and springs back with a subtle overshoot on release, paired with optional shockwave ripples and synthesized click sounds.
* **🔍 100% System & Dynamic Cursor Support:** Automatically extracts and scales all 17 native Windows cursor states (`Arrow`, `IBeam`, `Hand`, `.ani` loading cursors, resize arrows) plus on-the-fly custom application `HCURSOR`s (such as Open/Closed Hand in browsers and design software).
* **🔦 Spotlight & Halo Mode:** Highlight your cursor with a customizable ambient glow or dim the surrounding screen during presentations and tutorials.
* **🎨 Modern Dark Dashboard:** Features a sleek `#0F0F12` sidebar interface with 6 categorized pages, live interactive preview, per-cursor gallery manager, and one-click presets.
* **🛡️ Built-in Failsafe Protection:** Uses the Windows Magnification API to hide the native hardware cursor cleanly, backed by automatic crash recovery and an instant emergency restore hotkey (`Ctrl + Shift + Q`).

---

## 🛠️ Project Structure

```text
GlideX/
├── app/
│   ├── config.py             # Configuration manager, presets & JSON persistence
│   ├── core/
│   │   ├── win32_api.py      # Magnification API cursor hiding & safety failsafes
│   │   ├── cursor_manager.py # System & dynamic HCURSOR extraction + .ani support
│   │   └── input_hook.py     # Global mouse/keyboard hooks & synthesized audio
│   ├── overlay/
│   │   └── overlay_window.py # Click-through translucent overlay & 60+ FPS physics loop
│   └── ui/
│       ├── main_window.py    # Modern dark dashboard with Left Sidebar navigation
│       ├── styles.py         # Custom QSS styling & reusable UI components
│       └── tray_icon.py      # System Tray integration & quick toggles
├── assets/
│   └── cursors/              # Directory for custom .cur / .ani / .png overrides
├── main.py                   # Clean application entry point
├── requirements.txt          # Python dependencies
├── .gitignore                # Git ignore rules
└── README.md                 # Project documentation
```

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
- **OS:** Windows 10 or Windows 11 (64-bit recommended)
- **Python:** 3.10 or newer

### 2. Clone Repository
```bash
git clone https://github.com/pakan3291/GlideX.git
cd GlideX
```

### 3. Install Requirements
```bash
pip install -r requirements.txt
```

### 4. Run GlideX
```bash
python main.py
```

---

## ⌨️ Global Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Ctrl + Shift + Q`** | **Emergency Failsafe** | Instantly restores all native Windows cursors and pauses overlay. |
| **`Ctrl + Shift + S`** | **Toggle Overlay** | Toggles custom animated cursor overlay On / Off. |
| **`Ctrl + Shift + F`** | **Toggle Spotlight** | Toggles screen spotlight presentation focus mode. |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

"""
GlideX - Automated Installer & Uninstaller Suite Builder
======================================================
Builds the standalone uninstaller.exe, the setup_runtime/installer.exe,
the root installer.exe launcher, and populates the payload/ directory
inside installer/ (which is excluded from Git).
"""

import os
import sys
import shutil
import subprocess

def run_cmd(cmd_list):
    print(f"Running: {' '.join(cmd_list)}")
    res = subprocess.run(cmd_list, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error executing {' '.join(cmd_list)}:\n{res.stderr}")
        raise RuntimeError(f"Command failed: {res.stderr}")
    return res.stdout

def build_installer_suite():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    build_dir = os.path.join(base_dir, "build")
    installer_dir = os.path.join(base_dir, "installer")
    portable_dir = os.path.join(base_dir, "portable", "GlideX")
    icon_path = os.path.join(base_dir, "assets", "GlideX.ico")

    setup_runtime_dir = os.path.join(installer_dir, "setup_runtime")
    payload_dir = os.path.join(installer_dir, "payload")

    # 1. Clean previous builds
    for d in [installer_dir, dist_dir, build_dir]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)

    os.makedirs(setup_runtime_dir, exist_ok=True)
    os.makedirs(payload_dir, exist_ok=True)

    # 2. Build uninstaller.exe (--onefile)
    print("\n[1/3] Building uninstaller.exe...")
    run_cmd([
        "pyinstaller", "--onefile", "--noconsole", "--clean",
        f"--icon={icon_path}",
        "--name", "uninstaller",
        os.path.join(base_dir, "uninstaller.py")
    ])

    # 3. Build installer_core (--onedir for fast instant launch)
    print("\n[2/3] Building installer_core runtime...")
    run_cmd([
        "pyinstaller", "--onedir", "--noconsole", "--clean",
        f"--icon={icon_path}",
        "--name", "installer_core",
        os.path.join(base_dir, "installer_wizard.py")
    ])

    # 4. Build root installer launcher
    print("\n[3/3] Building root installer launcher...")
    temp_launcher = os.path.join(base_dir, "_temp_launcher.py")
    with open(temp_launcher, "w", encoding="utf-8") as f:
        f.write('''import os, sys, subprocess
def main():
    root = os.path.dirname(os.path.abspath(sys.argv[0]))
    target = os.path.join(root, "setup_runtime", "installer.exe")
    if os.path.exists(target):
        subprocess.Popen([target] + sys.argv[1:], cwd=root,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0))
if __name__ == "__main__":
    main()
''')
    try:
        run_cmd([
            "pyinstaller", "--onefile", "--noconsole", "--clean",
            f"--icon={icon_path}",
            "--name", "installer_launcher",
            temp_launcher
        ])
    finally:
        if os.path.exists(temp_launcher):
            os.remove(temp_launcher)

    # 5. Populate setup_runtime/
    dist_core = os.path.join(dist_dir, "installer_core")
    for item in os.listdir(dist_core):
        s = os.path.join(dist_core, item)
        if item.lower() == "installer_core.exe":
            shutil.copy2(s, os.path.join(setup_runtime_dir, "installer.exe"))
        else:
            d = os.path.join(setup_runtime_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

    # 6. Copy root installer.exe
    shutil.copy2(os.path.join(dist_dir, "installer_launcher.exe"), os.path.join(installer_dir, "installer.exe"))

    # 7. Populate payload/
    if not os.path.exists(portable_dir):
        raise FileNotFoundError(f"Portable directory not found at {portable_dir}. Please build portable first.")

    shutil.copytree(os.path.join(portable_dir, "bin"), os.path.join(payload_dir, "bin"))
    shutil.copytree(os.path.join(portable_dir, "assets"), os.path.join(payload_dir, "assets"))
    shutil.copytree(os.path.join(portable_dir, "config"), os.path.join(payload_dir, "config"))
    shutil.copy2(os.path.join(portable_dir, "GlideX.exe"), os.path.join(payload_dir, "GlideX.exe"))
    shutil.copy2(os.path.join(dist_dir, "uninstaller.exe"), os.path.join(payload_dir, "uninstaller.exe"))

    with open(os.path.join(payload_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write("GlideX - Ultra-Smooth Physics-Based Windows Cursor Enhancement Suite\nhttps://github.com/pakan3291/GlideX\n")

    # 8. Clean up build/, dist/, and *.spec
    print("\nCleaning up temporary build artifacts...")
    for d in [dist_dir, build_dir]:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)

    for item in os.listdir(base_dir):
        if item.endswith(".spec"):
            try:
                os.remove(os.path.join(base_dir, item))
            except Exception:
                pass

    print(f"\nSUCCESS: GlideX Installer suite built cleanly at: {installer_dir}")

if __name__ == "__main__":
    build_installer_suite()

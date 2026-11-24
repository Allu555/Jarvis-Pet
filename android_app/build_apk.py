#!/usr/bin/env python3
"""
build_apk.py – Standalone Android APK Builder for JARVIS Remote.
Compiles resources, Java sources, converts to DEX, aligns, and signs without heavy Gradle overhead.
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR
BUILD_DIR = PROJECT_DIR / "build"
DIST_DIR = ROOT_DIR.parent / "dist"
ASSETS_DIR = ROOT_DIR.parent / "assets"

ANDROID_SDK = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk")
BUILD_TOOLS_VERSION = "34.0.0"
PLATFORM_VERSION = "android-34"

BUILD_TOOLS_DIR = Path(ANDROID_SDK) / "build-tools" / BUILD_TOOLS_VERSION
ANDROID_JAR = Path(ANDROID_SDK) / "platforms" / PLATFORM_VERSION / "android.jar"

AAPT2 = BUILD_TOOLS_DIR / "aapt2.exe"
D8 = BUILD_TOOLS_DIR / "d8.bat"
ZIPALIGN = BUILD_TOOLS_DIR / "zipalign.exe"
APKSIGNER = BUILD_TOOLS_DIR / "apksigner.bat"

JAVA_HOME = Path(os.environ.get("JAVA_HOME", r"C:\Program Files\Java\jdk-17"))
JAVAC = JAVA_HOME / "bin" / "javac.exe"
KEYTOOL = JAVA_HOME / "bin" / "keytool.exe"


def run_cmd(cmd, desc):
    print(f"[*] {desc}...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print(f"[!] Error during: {desc}")
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
        sys.exit(res.returncode)
    return res.stdout


def main():
    print("=" * 60)
    print("  JARVIS Remote – Android APK Builder")
    print("=" * 60)

    if not ANDROID_JAR.exists():
        sys.exit(f"Error: android.jar not found at {ANDROID_JAR}")
    if not AAPT2.exists():
        sys.exit(f"Error: aapt2 not found at {AAPT2}")
    if not JAVAC.exists():
        sys.exit(f"Error: javac not found at {JAVAC}")

    # Prepare directories
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    (BUILD_DIR / "compiled_res").mkdir(parents=True, exist_ok=True)
    (BUILD_DIR / "gen").mkdir(parents=True, exist_ok=True)
    (BUILD_DIR / "classes").mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Compile resources with AAPT2
    res_dir = PROJECT_DIR / "res"
    compiled_res_dir = BUILD_DIR / "compiled_res"
    run_cmd(
        f'"{AAPT2}" compile --dir "{res_dir}" -o "{compiled_res_dir}"',
        "Compiling Android resources with AAPT2"
    )

    # Find compiled zip or flat files
    flat_files = [str(f) for f in compiled_res_dir.glob("*.flat")]
    flat_args = " ".join([f'"{f}"' for f in flat_files])

    # 2. Link resources and generate R.java + unaligned base APK
    manifest_xml = PROJECT_DIR / "AndroidManifest.xml"
    unaligned_apk = BUILD_DIR / "app-unaligned.apk"
    gen_dir = BUILD_DIR / "gen"

    run_cmd(
        f'"{AAPT2}" link {flat_args} -I "{ANDROID_JAR}" --manifest "{manifest_xml}" '
        f'--min-sdk-version 26 --target-sdk-version 34 --version-code 5 --version-name 2.3.0 --replace-version '
        f'--java "{gen_dir}" -o "{unaligned_apk}" --auto-add-overlay',
        "Linking resources and generating R.java"
    )

    # 3. Compile Java source code
    classes_dir = BUILD_DIR / "classes"
    src_dir = PROJECT_DIR / "src"
    java_files = list(src_dir.rglob("*.java")) + list(gen_dir.rglob("*.java"))
    java_files_args = " ".join([f'"{f}"' for f in java_files])

    run_cmd(
        f'"{JAVAC}" -encoding UTF-8 -source 1.8 -target 1.8 -cp "{ANDROID_JAR}" -d "{classes_dir}" {java_files_args}',
        "Compiling Java sources to bytecode (.class)"
    )

    # 4. Convert classes to DEX with D8
    class_files = list(classes_dir.rglob("*.class"))
    class_files_args = " ".join([f'"{f}"' for f in class_files])
    dex_dir = BUILD_DIR / "dex"
    dex_dir.mkdir(parents=True, exist_ok=True)

    run_cmd(
        f'"{D8}" --release --min-api 26 --lib "{ANDROID_JAR}" --output "{dex_dir}" {class_files_args}',
        "Converting Java bytecode to Dalvik executable (classes.dex)"
    )

    # 5. Pack classes.dex into unaligned APK
    dex_file = dex_dir / "classes.dex"
    print("[*] Packaging classes.dex into APK...")
    with zipfile.ZipFile(unaligned_apk, "a") as zip_apk:
        zip_apk.write(dex_file, "classes.dex")

    # 6. Align APK with zipalign
    aligned_apk = BUILD_DIR / "app-aligned.apk"
    run_cmd(
        f'"{ZIPALIGN}" -f 4 "{unaligned_apk}" "{aligned_apk}"',
        "Aligning APK (4-byte alignment)"
    )

    # 7. Generate debug keystore if not exists
    keystore_file = PROJECT_DIR / "debug.keystore"
    if not keystore_file.exists():
        run_cmd(
            f'"{KEYTOOL}" -genkey -v -keystore "{keystore_file}" -alias androiddebugkey '
            '-storepass android -keypass android -keyalg RSA -keysize 2048 -validity 10000 '
            '-dname "CN=JARVIS, OU=Dev, O=JARVIS, L=City, S=State, C=US"',
            "Generating debug signing keystore"
        )

    # 8. Sign APK with apksigner
    final_apk = DIST_DIR / "JarvisRemote.apk"
    if final_apk.exists():
        final_apk.unlink()

    run_cmd(
        f'"{APKSIGNER}" sign --ks "{keystore_file}" --ks-pass pass:android '
        f'--ks-key-alias androiddebugkey --key-pass pass:android '
        f'--out "{final_apk}" "{aligned_apk}"',
        "Signing APK with apksigner (V1 + V2 + V3)"
    )

    # Copy to assets for in-app download serving
    assets_apk = ASSETS_DIR / "JarvisRemote.apk"
    shutil.copyfile(final_apk, assets_apk)

    size_mb = final_apk.stat().st_size / (1024 * 1024)
    print("\n" + "=" * 60)
    print(f"  BUILD SUCCESSFUL!")
    print(f"  Artifact: {final_apk}")
    print(f"  Size:     {size_mb:.2f} MB")
    print(f"  Available at: {assets_apk}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

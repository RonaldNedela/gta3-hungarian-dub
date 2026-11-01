#!/usr/bin/env python3
"""
GTA III Hungarian Dub Master Processor - High-Presence Broadcast Edition
Builds, mixes, normalizes, slices, and deploys all 174 audio files:
- 70 Cutscene MP3s: Background track lowered by -7.5dB with heavy -8dB sidechain ducking under dialogue,
  vocal stem boosted with 3.2kHz presence EQ and dynamic broadcast compand (~-10.5dB active RMS).
- 104 In-Game WAVs: Pure vocal stem with 80Hz highpass, 3.2kHz presence boost, dynamic compand, and peak limiter
  (~-10.0dB active RMS), encoded to exact original engine codec (ADPCM IMA / PCM S16LE).
- JB.mp3: Callagan Bridge intro cutscene dominant mix.
"""

import os
import sys
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = "/Users/Ronci/Downloads/GTA3_Master_Dubbing"
MANIFEST_PATH = os.path.join(BASE_DIR, "master_manifest.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "final_hungarian_dub_mastered")

VOX_MASTER = os.path.join(BASE_DIR, "hungarian dub final no background noise.mp3")
BG_MASTER = "/Users/Ronci/Library/Application Support/OmniVoice/dub_jobs/9686b9aa-e685-4209-abab-9b185c058679/no_vocals.wav"

VOX_JB = os.path.join(BASE_DIR, "JB no background audio.mp3")
BG_JB = os.path.join(BASE_DIR, "JB_no_vocals.wav")

BACKUP_DIR = "/Applications/Grand Theft Auto III.app/Contents/Resources/GameData/audio_original_backup"
TARGET_GAME_DIRS = [
    "/Applications/Grand Theft Auto III.app/Contents/Resources/GameData/audio",
    "/Users/Ronci/Library/Application Support/CrossOver/Bottles/GTAIII/drive_c/Program Files (x86)/Grand Theft Auto 3/audio"
]

def probe_spec(filepath):
    """Probe audio specs from original file."""
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_name,sample_rate,channels",
            "-of", "json", filepath
        ], stderr=subprocess.DEVNULL)
        info = json.loads(out)["streams"][0]
        return {
            "codec": info.get("codec_name"),
            "sample_rate": int(info.get("sample_rate", 44100)),
            "channels": int(info.get("channels", 2))
        }
    except Exception:
        return None

def process_jb(output_dir):
    """Mix and master JB.mp3 with heavy speech presence and ducked background."""
    out_file = os.path.join(output_dir, "JB.mp3")
    filter_complex = (
        "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,"
        "highpass=f=80,equalizer=f=3200:width_type=o:w=1.2:g=4.0,"
        "compand=attacks=0.005:decays=0.06:points=-80/-80|-50/-22|-30/-10|-12/-2|0/0:gain=7,"
        "volume=4dB,asplit=2[v1][v2]; "
        "[0:a]volume=-7.5dB[bg_low]; "
        "[bg_low][v1]sidechaincompress=threshold=0.015:ratio=6:attack=10:release=350[ducked_bg]; "
        "[ducked_bg][v2]amix=inputs=2:weights=1 1:normalize=0,alimiter=limit=0.85[outa]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", BG_JB,
        "-i", VOX_JB,
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        out_file
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0:
        return False, f"JB.mp3 failed: {res.stderr.decode('utf-8', errors='ignore')}"
    return True, "JB.mp3 (intro cutscene) -> Success"

def process_entry(entry, output_dir):
    """Process a single manifest entry."""
    fname = entry["filename"]
    start = entry["start"]
    dur = entry["duration"]
    out_file = os.path.join(output_dir, fname)
    orig_path = os.path.join(BACKUP_DIR, fname)
    spec = probe_spec(orig_path)

    if fname.lower().endswith(".mp3"):
        # Cutscene: Attenuate background, heavily duck under speech, boost voice presence
        filter_complex = (
            "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            "highpass=f=80,equalizer=f=3200:width_type=o:w=1.2:g=4.0,"
            "compand=attacks=0.005:decays=0.06:points=-80/-80|-50/-22|-30/-10|-12/-2|0/0:gain=7,"
            "volume=4dB,asplit=2[v1][v2]; "
            "[0:a]volume=-7.5dB[bg_low]; "
            "[bg_low][v1]sidechaincompress=threshold=0.015:ratio=6:attack=10:release=350[ducked_bg]; "
            "[ducked_bg][v2]amix=inputs=2:weights=1 1:normalize=0,alimiter=limit=0.85[outa]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-t", str(dur), "-i", BG_MASTER,
            "-ss", str(start), "-t", str(dur), "-i", VOX_MASTER,
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            out_file
        ]
    else:
        # Dialogue WAV: Highpass 80Hz, 3.2kHz presence boost, fast broadcast compand, peak limiter
        codec = spec["codec"] if spec and spec.get("codec") else "adpcm_ima_wav"
        sr = spec["sample_rate"] if spec and spec.get("sample_rate") else 12000
        ch = spec["channels"] if spec and spec.get("channels") else 1

        af = (
            "highpass=f=80,"
            "equalizer=f=3200:width_type=o:w=1.2:g=4.0,"
            "compand=attacks=0.005:decays=0.06:points=-80/-80|-50/-22|-30/-10|-12/-2|0/0:gain=8,"
            "alimiter=limit=0.98"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-t", str(dur), "-i", VOX_MASTER,
            "-af", af,
            "-c:a", codec,
            "-ar", str(sr),
            "-ac", str(ch),
            out_file
        ]

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0:
        return False, f"{fname} failed: {res.stderr.decode('utf-8', errors='ignore')}"
    return True, f"{fname} -> Success"

def main():
    print("=" * 70)
    print("  GTA III HUNGARIAN DUB - HIGH-PRESENCE BROADCAST MASTERING")
    print("=" * 70)

    for path, name in [
        (VOX_MASTER, "Continuous Vocal Master"),
        (BG_MASTER, "Continuous Backing Track"),
        (VOX_JB, "JB Vocal Track"),
        (BG_JB, "JB Backing Track"),
        (MANIFEST_PATH, "Master Manifest"),
        (BACKUP_DIR, "Original Audio Backup")
    ]:
        if not os.path.exists(path):
            print(f"❌ Missing required input: {name} at {path}")
            sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    total_tasks = len(manifest) + 1
    print(f"Mastering {total_tasks} files with High-Presence Broadcast Chain (8 threads)...")

    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_entry, e, OUTPUT_DIR): e["filename"] for e in manifest}
        futures[executor.submit(process_jb, OUTPUT_DIR)] = "JB.mp3"

        completed = 0
        for future in as_completed(futures):
            fname = futures[future]
            completed += 1
            ok, msg = future.result()
            results.append((ok, msg))
            if not ok:
                print(f"[{completed}/{total_tasks}] ❌ {msg}")
            elif completed % 25 == 0 or completed == total_tasks:
                print(f"[{completed}/{total_tasks}] Processed ({fname})")

    successes = [r for r in results if r[0]]
    failures = [r for r in results if not r[0]]
    print(f"\nProcessing Complete! Successes: {len(successes)} / {total_tasks}. Failures: {len(failures)}.")

    if failures:
        print("Stopping due to failures.")
        sys.exit(1)

    # Deployment
    print("\n" + "=" * 70)
    print("  DEPLOYING HIGH-PRESENCE AUDIO TO GTA III DIRECTORIES")
    print("=" * 70)

    for target_dir in TARGET_GAME_DIRS:
        if not os.path.exists(target_dir):
            print(f"⚠️ Target dir does not exist (skipping): {target_dir}")
            continue

        print(f"Deploying to: {target_dir}")
        copied_count = 0
        for fname in os.listdir(OUTPUT_DIR):
            if fname.lower().endswith((".mp3", ".wav")):
                src = os.path.join(OUTPUT_DIR, fname)
                dst = os.path.join(target_dir, fname)
                shutil.copy2(src, dst)
                copied_count += 1
        print(f"✅ Successfully deployed {copied_count} files to {target_dir}")

    print("\nBroadcast Mastering & Deployment Finished Successfully!")

if __name__ == "__main__":
    main()

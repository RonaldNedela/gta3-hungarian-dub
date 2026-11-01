#!/usr/bin/env python3
"""
GTA III Dub Slicer & Game Engine Compressor
Slices a continuous dubbed master audio file back into individual GTA III audio files
matching the EXACT original codecs, sample rates, channels, and compression
required by the GTA III game engine (Miles Sound System / DirectSound).
"""

import os
import sys
import json
import shutil
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(SCRIPT_DIR, "master_manifest.json")
DEFAULT_OUTPUT_DIR = os.path.join(SCRIPT_DIR, "sliced_hungarian_dub")
GAME_AUDIO_DIR = "/Users/Ronci/Library/Application Support/CrossOver/Bottles/GTAIII/drive_c/Program Files (x86)/Grand Theft Auto 3/audio"
GAME_BACKUP_DIR = "/Users/Ronci/Library/Application Support/CrossOver/Bottles/GTAIII/drive_c/Program Files (x86)/Grand Theft Auto 3/audio_original_backup"

def get_original_spec(filename):
    """Probe the original file in GTA III audio dir for exact codec, sample rate, channels."""
    if not os.path.exists(GAME_AUDIO_DIR):
        return None
    orig_path = os.path.join(GAME_AUDIO_DIR, filename)
    if not os.path.exists(orig_path):
        return None
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_name,sample_rate,channels",
            "-of", "json", orig_path
        ], stderr=subprocess.DEVNULL)
        info = json.loads(out)["streams"][0]
        return {
            "codec": info.get("codec_name"),
            "sample_rate": int(info.get("sample_rate", 44100)),
            "channels": int(info.get("channels", 2))
        }
    except Exception:
        return None

def slice_master(master_file, output_dir=DEFAULT_OUTPUT_DIR):
    if not os.path.exists(master_file):
        print(f"❌ Error: Master file not found: {master_file}")
        sys.exit(1)

    if not os.path.exists(MANIFEST_PATH):
        print(f"❌ Error: Manifest not found: {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    print("=" * 60)
    print(" GTA III HUNGARIAN DUB SLICER & ENGINE COMPRESSOR")
    print("=" * 60)
    print(f"Input Master : {master_file}")
    print(f"Total Files  : {len(manifest)}")
    print(f"Output Dir   : {output_dir}")
    print("-" * 60)

    success_count = 0
    errors = []

    for entry in manifest:
        idx = entry["index"]
        fname = entry["filename"]
        start = entry["start"]
        dur = entry["duration"]
        
        target_path = os.path.join(output_dir, fname)
        spec = get_original_spec(fname)
        
        # Build ffmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(dur),
            "-i", master_file
        ]
        
        if fname.lower().endswith(".mp3"):
            sr = spec["sample_rate"] if spec else 44100
            ch = spec["channels"] if spec else 2
            cmd += ["-c:a", "libmp3lame", "-b:a", "128k", "-ar", str(sr), "-ac", str(ch)]
            codec_label = f"MP3 128k {sr}Hz {ch}ch"
        else: # .wav
            codec = spec["codec"] if spec else "adpcm_ima_wav"
            sr = spec["sample_rate"] if spec else 12000
            ch = spec["channels"] if spec else 1
            
            if codec == "adpcm_ima_wav":
                cmd += ["-c:a", "adpcm_ima_wav", "-ar", str(sr), "-ac", str(ch)]
                codec_label = f"ADPCM IMA {sr}Hz {ch}ch"
            else:
                cmd += ["-c:a", "pcm_s16le", "-ar", str(sr), "-ac", str(ch)]
                codec_label = f"PCM S16LE {sr}Hz {ch}ch"
            
        cmd.append(target_path)
        
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode == 0 and os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            success_count += 1
            print(f"[{idx+1:03d}/{len(manifest):03d}] ✓ {fname:<15} ({dur:>5.2f}s) -> {codec_label}")
        else:
            err_msg = res.stderr.decode()
            errors.append((fname, err_msg))
            print(f"[{idx+1:03d}/{len(manifest):03d}] ✗ ERROR extracting {fname}: {err_msg[:80]}")

    print("-" * 60)
    print(f"Done! {success_count}/{len(manifest)} files successfully sliced and formatted.")
    if errors:
        print(f"⚠️ {len(errors)} errors encountered.")
    print(f"Output files ready at:\n  {output_dir}")
    print("=" * 60)

def backup_and_install(output_dir=DEFAULT_OUTPUT_DIR):
    if not os.path.exists(GAME_AUDIO_DIR):
        print(f"❌ Error: GTA III game audio directory not found: {GAME_AUDIO_DIR}")
        return False

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Step 1: Backup original files if backup dir does not exist
    os.makedirs(GAME_BACKUP_DIR, exist_ok=True)
    backed_up = 0
    for entry in manifest:
        fname = entry["filename"]
        src = os.path.join(GAME_AUDIO_DIR, fname)
        dst = os.path.join(GAME_BACKUP_DIR, fname)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            backed_up += 1

    print(f"📦 Backed up {backed_up} original audio files to:\n  {GAME_BACKUP_DIR}")

    # Step 2: Copy sliced dubbed files into game audio directory
    installed = 0
    for entry in manifest:
        fname = entry["filename"]
        src = os.path.join(output_dir, fname)
        dst = os.path.join(GAME_AUDIO_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            installed += 1

    print(f"🎮 Successfully installed {installed}/{len(manifest)} Hungarian dub files into:\n  {GAME_AUDIO_DIR}")
    return True

if __name__ == "__main__":
    master = "/Users/Ronci/Downloads/GTA3_Master_Dubbing/gta3.mp3"
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        master = sys.argv[1]
        
    slice_master(master)
    
    if "--install" in sys.argv:
        backup_and_install()

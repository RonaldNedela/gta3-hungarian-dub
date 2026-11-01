# Grand Theft Auto III - Full Hungarian Voice & Subtitle Dub

A complete, studio-mastered Hungarian voiceover and subtitle localization for Grand Theft Auto III (2001), built for both the native macOS application wrapper and standard PC / CrossOver installations.

This project delivers 174 synchronized audio files (70 cutscene MP3 streams and 104 in-game gameplay WAV files) along with complete SRT subtitle files, replacing the original English dialogue with full Hungarian dubbing while preserving every environmental sound effect, vehicle audio layer, and cutscene backing track.

---

## Installation

### macOS Native Wrapper
1. Navigate to:
   `/Applications/Grand Theft Auto III.app/Contents/Resources/GameData/audio/`
2. Create a backup copy of your existing `audio/` directory (e.g., name it `audio_original_backup/`).
3. Copy all files from the `audio/` directory of this repository into `/Applications/Grand Theft Auto III.app/Contents/Resources/GameData/audio/`, replacing existing files.

### Windows / CrossOver / Wine
1. Navigate to your GTA III installation directory:
   `.../Grand Theft Auto 3/audio/`
2. Create a backup copy of your original `audio/` folder.
3. Overwrite the files in `audio/` with the files provided in this repository's `audio/` directory.

### In-Game Audio Recommendation
In the GTA III Audio Setup menu:
- SFX Volume: 75% - 85%
- Radio Volume: 60% - 70%

---

## Project Specifications & Hardware

- Production Time: Approximately 12 hours (single afternoon engineering sprint, from raw asset extraction to final game engine integration).
- Workstation Hardware:
  - Model: Apple MacBook Air 13" / 15"
  - Processor: Apple M2 (8-core CPU, 10-core GPU, 16-core Neural Engine)
  - Memory: 16 GB Unified Memory
  - Operating System: macOS Darwin (Apple Silicon arm64)

---

## Audio Sources & Pipeline Architecture

Every asset in this localization was created through a multi-stage neural audio and digital signal processing pipeline:

1. Original Source Extraction:
   - Dialogue stems extracted directly from original 2001 GTA III game archives (`audio/` directory, DirectSound / Miles Sound System sound banks).
2. Transcription & Time-Coding:
   - Faster-Whisper (OpenAI Whisper base model, int8 quantization running on Apple Silicon CPU/ANE) for phoneme-accurate segment alignment and SRT generation.
3. Neural Translation & Linguistic Adaptation:
   - Initial translations generated with Meta NLLB-200 (No Language Left Behind), followed by context-guided LLM passes to adapt literal translations into colloquial, gritty 2001 Liberty City street dialogue.
4. Voice Cloning & Synthesis:
   - Multi-speaker neural text-to-speech with reference timbre matching. Target voices were modeled after iconic Hungarian voice actors:
     - Agnes Bertalan (Liberty Tree TV / News Anchor)
     - Zoltan Schneider (Cartel enforcer)
     - Artur Kalid (8-Ball)
     - Additional distinctive character models for Luigi Goterelli, Joey Leone, Salvatore Leone, Catalina, and street contacts.
5. Stem Separation:
   - Facebook Research Demucs (`htdemucs` architecture) running locally on Apple Silicon to isolate clean music and environmental effects from original English cutscene dialogue with zero vocal bleed.
6. Game Engine Slicing & Codec Compression:
   - Custom Python and FFmpeg automated build harness targeting the exact audio codecs required by GTA III's sound engine.

---

## Technical Challenges & Engineering Solutions

### 1. The Missing Intro Ambush (`JB.mp3` - Callahan Bridge)
- Challenge: The initial dialogue master compilation extracted the 173 standard mission files but omitted `JB.mp3`—the critical 1-minute-53-second introductory cutscene on the Callahan Bridge where the Colombian Cartel ambushes the police convoy.
- Solution: The original `JB.mp3` was extracted from game backup and processed through Demucs (`htdemucs`) to separate dialogue from the high-energy backing track (sirens, police dispatch chatter, helicopter rotors, vehicle crashes, and bridge explosions). A dedicated three-character Hungarian dub script was translated, synthesized, and sidechain-mixed over the pristine backing track.

### 2. The Dynamic Loudness & Crest Factor Gap
- Challenge: Initial in-game testing revealed that the synthetic dialogue sounded noticeably quiet during gameplay, despite peak volume meters hitting 0 dBFS. The player heard screaming car engines, tire screeches, and gunshots, while spoken dialogue was barely audible underneath.
- Root Cause Analysis:
  - Synthetic neural TTS produces high crest factor audio (peak-to-RMS ratios exceeding 14 dB). Quiet syllables, unvoiced consonants, and breathing pauses dropped to -20 dB to -26 dB RMS.
  - In contrast, original GTA III sound effects (engine loops, shotgun blasts, ambient city traffic) are heavily squashed and sustain an RMS level of -10 dB to -12 dB.
  - Applying simple linear gain amplification was blocked by single-sample peaks hitting the digital ceiling (0 dBFS), leaving the average vowel body underpowered.
- Solution - High-Presence Broadcast Chain:
  - 80 Hz High-Pass Filter: Strips inaudible low-frequency rumble that eats limiter headroom without contributing to voice clarity.
  - 3.2 kHz Vocal Presence EQ (+4.0 dB boost, Q=1.2): Highlights the critical human intelligibility formant range, enabling voices to pierce through car engine rumble and gunfire.
  - Fast Broadcast Compander: An aggressive multi-point dynamic compressor (attack: 5ms, release: 60ms, 4:1 ratio) that elevates soft syllables by +6 dB to +10 dB while reigning in transient spikes.
  - Brickwall Peak Limiting: Maximizes dialogue loudness to a consistent -9.5 dB to -10.5 dB active speech RMS with zero digital clipping.

### 3. Cutscene Balance & Sidechain Ducking
- Challenge: In GTA III cutscenes (`.mp3` files), all audio—music, dialogue, and Foley—resides in a single stereo audio stream. Playing back the original music/SFX track at 100% volume competed directly with the dialogue frequencies.
- Solution:
  - The isolated background track was permanently attenuated by -7.5 dB.
  - A responsive sidechain compressor was introduced: whenever speech is active on the vocal stem, the background audio is ducked by an additional -8 dB (threshold: 0.015, ratio: 6:1, attack: 10ms, release: 350ms).
  - The result is a cinema-standard mix where dialogue is front-and-center, while explosions and music swell up naturally during dramatic pauses.

### 4. Miles Sound System Engine Compatibility
- Challenge: The 2001 game engine relies on Miles Sound System / DirectSound. If sample rates, channel configurations, or codecs deviate even slightly from expected specs, the engine either crashes, plays high-pitched noise, or drops dialogue altogether.
- Solution:
  - Cutscene MP3s: Strictly encoded as 44.1 kHz, 128 kbps CBR Stereo MP3 via `libmp3lame`.
  - Gameplay WAVs: Probed from original game files and reconstructed in exact legacy codecs—primarily IMA ADPCM (`adpcm_ima_wav`) or 16-bit PCM (`pcm_s16le`) across 12 kHz, 14 kHz, 16 kHz, and 44.1 kHz mono/stereo layouts.

---

## Measured Volume Comparison

The following table displays active speech RMS (energy measured during voiced speech segments) before and after the broadcast mastering upgrade:

| File Name | Role / Character | Previous Active RMS | New Broadcast RMS | Net Improvement |
| :--- | :--- | :--- | :--- | :--- |
| `cat1.wav` | Catalina intro shout | -14.72 dB | -9.85 dB | +4.87 dB louder |
| `lib_a.wav` | 8-Ball street dialogue | -14.36 dB | -10.70 dB | +3.66 dB louder |
| `j6_d.wav` | Joey Leone mission phone | -17.35 dB | -8.78 dB | +8.57 dB louder |
| `s1_c.wav` | Salvatore Leone line | -23.38 dB | -7.83 dB | +15.55 dB louder |
| `JB.mp3` | Callahan Bridge cutscene | -15.30 dB | -10.95 dB | +4.35 dB louder |
| `l1_lg.mp3` | Luigi club cutscene | -18.00 dB | -10.11 dB | +7.89 dB louder |

---

## On the Horizon: Are Voice Actors Replaceable?

A frequent question surrounding modern AI dubbing projects is whether traditional voice actors are becoming obsolete.

The reality today:
Voice actors are not replaceable today, not easily, and not by any commercial studio operating under professional production standards.

1. The Nuance Deficit:
   Human voice actors bring subtext, emotional vulnerability, micro-timing, localized comedic irony, and vocal improvisation that no zero-shot or few-shot TTS engine can autonomously generate. A human performer understands *why* a character hesitates, cracks their voice, or swallows a word in grief. Current neural systems still generate sound based on statistical phoneme likelihood rather than dramatic motivation.
2. The Engineering Burden:
   Producing a high-quality localized experience like this project required twelve continuous hours of manual intervention: phonetic script modifications, pronunciation corrections, dynamic stem separation, custom sidechain DSP filtering, and legacy codec reverse-engineering. It is far from an "upload script, get finished film" button.
3. The Industry & Legal Landscape:
   Commercial studios face strict union agreements (SAG-AFTRA and international equivalents), personality rights legislation, and ethical mandates. Direct replacement of working performers in mainstream releases remains legally and culturally untenable.

The 1 to 2 Year Trajectory:
However, dismissing this technology as a mere novelty would be a mistake.

Within the next twelve to twenty-four months, several converging breakthroughs will transform the field:
- Real-time multimodal reasoning models that parse scene context, physical character posture, and dramatic tension before uttering a syllable.
- Directable latent prosody control, allowing sound designers to tweak sarcasm, pitch contour, breathiness, and emotional intensity on a per-word level.
- Unified audio-to-audio neural codecs capable of preserving micro-tonal timbre with zero latency and zero artifacts.

When these technologies mature, studio-grade localization will no longer require multi-million dollar recording facilities, physical studio scheduling, and months of turnaround. A single sound engineer or indie developer on a consumer laptop—such as the 16 GB M2 MacBook Air used here—will be capable of producing a localized dub that rivals commercial releases from a decade ago. 

Voice actors who partner with AI technology, licensing their vocal identity and curating performance data, will thrive. Those relying solely on routine, repetitive voice work will find the barrier to entry for full video game and film localization permanently dismantled.

---

## Repository Structure

```
gta3-hungarian-dub/
├── audio/                          # Complete set of 174 finalized, broadcast-mastered game audio files
│   ├── BET.mp3
│   ├── JB.mp3
│   ├── cat1.wav
│   └── ... (174 files, 57 MB total)
├── subtitles/                      # Complete SRT subtitle files
│   ├── GTA3_ENGLISH_ORIGINAL.srt
│   ├── GTA3_HUNGARIAN_DUB.srt
│   ├── JB_ENGLISH_ORIGINAL.srt
│   └── JB_HUNGARIAN_DUB.srt
├── scripts/                        # Automated build, mastering, and deployment harnesses
│   ├── build_master_dub.py
│   └── slice_dubbed_master.py
├── data/                           # Manifests, time-codes, and transcription audits
│   ├── master_manifest.json
│   ├── GTA3_TRANSCRIPT_AUDIT.csv
│   ├── JB_job_data_backup.json
│   └── job_data_backup.json
├── .gitignore
├── LICENSE
└── README.md
```

---

## Legal & Fair Use Disclaimer

Grand Theft Auto III and all related trademarks, logos, and audio assets are the property of Rockstar Games and Take-Two Interactive. This fan-made localization project is created non-commercially for archival, educational, and preservation purposes under fair use doctrine.

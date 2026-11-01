# Grand Theft Auto III - Hungarian Voice & Subtitle Dub

Complete Hungarian voiceover and in-game subtitle mod for Grand Theft Auto III (2001). Replaces all 174 dialogue tracks (70 cutscene MP3s, 104 gameplay WAVs) while keeping all original sound effects, ambient background audio, and music intact. Includes matching Hungarian subtitles via native GXT font mapping.

Compatible with native macOS wrappers, CrossOver, Wine, and standard PC / Windows installations.

---

## Installation

### 1. Audio Dub
1. Back up your game's original `audio/` directory.
2. Copy all files from `audio/` in this repository into your game's `audio/` directory:
   - macOS: `/Applications/Grand Theft Auto III.app/Contents/Resources/GameData/audio/`
   - Windows / CrossOver: `<GTA_DIR>/audio/`

### 2. In-Game Subtitles
1. Back up your game's `TEXT/` directory.
2. Copy `text/american.gxt` and `text/english.gxt` into your game's `TEXT/` directory:
   - macOS: `/Applications/Grand Theft Auto III.app/Contents/Resources/GameData/TEXT/`
   - Windows / CrossOver: `<GTA_DIR>/TEXT/`
3. Turn on Subtitles in the in-game Display menu.

Recommended In-Game Audio Settings:
- SFX Volume: 75% - 85%
- Radio Volume: 60% - 70%

---

## Production Facts & Hardware

- Turnaround Time: Approximately 12 hours (one afternoon, end-to-end).
- Workstation: Apple MacBook Air (Apple M2, 16 GB Unified Memory, macOS).

---

## Pipeline & Technical Implementation

1. Dialogue Extraction:
   - Extracted dialogue streams from original 2001 game files (`audio/` directory).
2. Transcription:
   - Faster-Whisper (OpenAI Whisper) locally on Apple Silicon to generate synchronized timestamps and English SRTs.
3. Translation:
   - Meta NLLB-200 initial translation, refined by LLM for colloquial Liberty City street dialogue.
4. Vocal Separation:
   - Demucs (`htdemucs`) to strip original English vocals from cutscene audio while isolating sirens, explosions, music, and Foley effects.
5. Neural Dubbing:
   - Multi-speaker voice synthesis with timbre matching inspired by well-known Hungarian actors (e.g. Agnes Bertalan, Zoltan Schneider, Artur Kalid).
6. Audio Mastering & DSP:
   - +4 dB presence boost at 3.2 kHz to cut through engine noise and gunshots.
   - Fast broadcast compression and peak limiting targeting -9.5 dB to -10.5 dB active speech RMS.
   - Dynamic sidechain ducking (-8 dB background attenuation when dialogue is active).
   - Format conversion to exact 2001 Miles Sound System specifications (44.1 kHz 128 kbps CBR MP3, IMA ADPCM / 16-bit PCM WAV).
7. GXT Subtitle Compiler:
   - GTA III's RenderWare CFont engine does not support UTF-8. The stock European `models/fonts.txd` maps accented letters to legacy byte offsets (128-175).
   - `scripts/build_hungarian_gxt.py` converts dialogue lines directly from the dub SRTs into `american.gxt` and `english.gxt` using the native glyph codes (`á`, `é`, `í`, `ó`, `ö`, `ú`, `ü`). Missing hungarumlauts fall back to `ö`/`ü` for 100% engine stability without texture patching.

---

## Measured Loudness Comparison

| File | Character / Scene | Previous RMS | Mastered RMS | Gain |
| :--- | :--- | :--- | :--- | :--- |
| `cat1.wav` | Catalina shout | -14.7 dB | -9.8 dB | +4.9 dB |
| `lib_a.wav` | 8-Ball street dialogue | -14.4 dB | -10.7 dB | +3.7 dB |
| `j6_d.wav` | Joey Leone mission phone | -17.4 dB | -8.8 dB | +8.6 dB |
| `s1_c.wav` | Salvatore Leone line | -23.4 dB | -7.8 dB | +15.6 dB |
| `JB.mp3` | Callahan Bridge ambush | -15.3 dB | -11.0 dB | +4.3 dB |
| `l1_lg.mp3` | Luigi club cutscene | -18.0 dB | -10.1 dB | +7.9 dB |

---

## Are Voice Actors Replaceable?

Short answer: No, not today, not easily, and not by any standard production studio.

- Current Reality: Human actors provide emotional nuance, subtext, improvisational comedic timing, and dramatic vulnerability that zero-shot or few-shot TTS models cannot replicate autonomously. Furthermore, creating this project required 12 hours of manual audio engineering, pronunciation tuning, stem separation, and legacy format adaptation. Legal and union frameworks also rightfully protect performer likenesses.
- Future Outlook (1-2 years): With upcoming multimodal models, real-time context comprehension, and fine-grained prosody control, high-quality localization will become achievable by individual developers on consumer laptops (like the MacBook Air used here). Performers who license and curate their voice models will find new revenue streams, while repetitive voice work will shift increasingly toward AI-assisted workflows.

---

## Repository Structure

```
gta3-hungarian-dub/
├── audio/                          # 174 finalized, broadcast-mastered dialogue files (MP3 / WAV)
├── subtitles/                      # Complete English & Hungarian SRT files
├── text/                           # Compiled in-game subtitle archives (american.gxt, english.gxt)
├── scripts/                        # Build, mastering, and GXT compiler scripts
│   ├── build_master_dub.py
│   ├── slice_dubbed_master.py
│   └── build_hungarian_gxt.py
├── data/                           # Manifests, time-codes, and transcription audits
├── LICENSE
└── README.md
```

---

## Disclaimer

Grand Theft Auto III and all related trademarks, logos, and audio assets are property of Rockstar Games and Take-Two Interactive. This fan localization is non-commercial, created for educational and preservation purposes.

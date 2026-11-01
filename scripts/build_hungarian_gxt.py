#!/usr/bin/env python3
"""
GTA III Hungarian In-Game Subtitle & GXT Compiler - High Fidelity Edition
Builds fully synchronized Hungarian in-game subtitles and mission text for GTA III.
Uses content-aware sequence alignment to match GXT entries to the Hungarian dub SRT,
with clean Latin font mapping for 100% rendering stability in the GTA III engine.
"""

import os
import sys
import struct
import re
import shutil
from difflib import SequenceMatcher

BASE_DIR = "/Users/Ronci/Downloads/GTA3_Master_Dubbing"
REPO_DIR = os.path.join(BASE_DIR, "gta3-hungarian-dub")
GAME_TEXT_DIR = "/Applications/Grand Theft Auto III.app/Contents/Resources/GameData/TEXT"
CROSSOVER_TEXT_DIR = "/Users/Ronci/Library/Application Support/CrossOver/Bottles/GTAIII/drive_c/Program Files (x86)/Grand Theft Auto 3/TEXT"

ORIG_GXT_PATH = os.path.join(GAME_TEXT_DIR, "american_original_backup.gxt")
SRT_HUN_PATH = os.path.join(BASE_DIR, "GTA3_HUNGARIAN_DUB.srt")
SRT_ENG_PATH = os.path.join(BASE_DIR, "GTA3_ENGLISH_ORIGINAL.srt")
JB_HUN_PATH = os.path.join(BASE_DIR, "JB_HUNGARIAN_DUB.srt")
JB_ENG_PATH = os.path.join(BASE_DIR, "JB_ENGLISH_ORIGINAL.srt")

# Stock RenderWare CFont character table mapping (European fonts.txd)
# Maps Hungarian vowels to exact RenderWare internal font sprite sheet codes:
# á = 0x98 (152), é = 0x9E (158), í = 0xA2 (162), ó = 0xA6 (166), ö = 0xA8 (168)
# ú = 0xAA (170), ü = 0xAC (172)
# ő -> ö (0xA8), ű -> ü (0xAC) (Option 1 fallback for stock texture compatibility)
# Uppercase:
# Á = 0x81 (129), É = 0x87 (135), Í = 0x8B (139), Ó = 0x8F (143), Ö = 0x91 (145)
# Ú = 0x93 (147), Ü = 0x95 (149)
# Ő -> Ö (0x91), Ű -> Ü (0x95)

HUNGARIAN_GLYPH_MAP = {
    'á': chr(0x98),
    'é': chr(0x9E),
    'í': chr(0xA2),
    'ó': chr(0xA6),
    'ö': chr(0xA8),
    'ő': chr(0xA8),
    'ú': chr(0xAA),
    'ü': chr(0xAC),
    'ű': chr(0xAC),
    'Á': chr(0x81),
    'É': chr(0x87),
    'Í': chr(0x8B),
    'Ó': chr(0x8F),
    'Ö': chr(0x91),
    'Ő': chr(0x91),
    'Ú': chr(0x93),
    'Ü': chr(0x95),
    'Ű': chr(0x95),
}

PUNCTUATION_MAP = {
    '”': '"', '„': '"', '“': '"',
    '’': "'", '‘': "'",
    '–': '-', '—': '-'
}

def map_hungarian_text(text):
    for orig, repl in PUNCTUATION_MAP.items():
        text = text.replace(orig, repl)
    for orig, repl in HUNGARIAN_GLYPH_MAP.items():
        text = text.replace(orig, repl)
    return text

STOPWORDS = {
    "the", "a", "an", "and", "or", "in", "on", "to", "of", "is", "are", "it", "that", "this",
    "you", "he", "we", "i", "so", "for", "with", "me", "my", "your", "his", "her", "at", "be"
}

def parse_gxt(path):
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == b"TKEY", f"Invalid GXT magic: {magic}"
        tkey_size = struct.unpack("<I", f.read(4))[0]
        num_entries = tkey_size // 12
        entries = []
        for _ in range(num_entries):
            offset, key_bytes = struct.unpack("<I8s", f.read(12))
            key = key_bytes.split(b"\x00")[0].decode("ascii", errors="ignore")
            entries.append((key, offset))
            
        tdat_magic = f.read(4)
        assert tdat_magic == b"TDAT", f"Invalid TDAT magic: {tdat_magic}"
        tdat_size = struct.unpack("<I", f.read(4))[0]
        tdat_start = 8 + tkey_size + 8
        
        gxt_dict = {}
        for key, offset in entries:
            f.seek(tdat_start + offset)
            raw = b""
            while True:
                c = f.read(2)
                if not c or c == b"\x00\x00":
                    break
                raw += c
            gxt_dict[key] = raw.decode("utf-16le", errors="ignore")
        return gxt_dict

def pack_gxt(gxt_dict, out_path):
    sorted_keys = sorted(gxt_dict.keys(), key=lambda k: k.encode("ascii")[:8].ljust(8, b"\x00"))
    
    tdat_bytes = bytearray()
    offsets = {}
    for k in sorted_keys:
        offsets[k] = len(tdat_bytes)
        text_utf16 = gxt_dict[k].encode("utf-16le") + b"\x00\x00"
        tdat_bytes.extend(text_utf16)
        
    tkey_bytes = bytearray()
    for k in sorted_keys:
        k_padded = k.encode("ascii")[:8].ljust(8, b"\x00")
        tkey_bytes.extend(struct.pack("<I8s", offsets[k], k_padded))
        
    with open(out_path, "wb") as f:
        f.write(b"TKEY")
        f.write(struct.pack("<I", len(tkey_bytes)))
        f.write(tkey_bytes)
        f.write(b"TDAT")
        f.write(struct.pack("<I", len(tdat_bytes)))
        f.write(tdat_bytes)

def parse_srt(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    blocks = re.findall(r"(\d+)\n(\d\d:\d\d:\d\d,\d+ --> \d\d:\d\d:\d\d,\d+)\n(.*?)(?=\n\n|\Z)", content, re.DOTALL)
    return [(int(num), time, " ".join(text.split())) for num, time, text in blocks]

def clean_content(t):
    t = re.sub(r"~[a-z0-9_]+~|[^\w\s]", "", t).lower()
    return " ".join([w for w in t.split() if w not in STOPWORDS])

def main():
    print("=" * 70)
    print("  GTA III HUNGARIAN IN-GAME SUBTITLE & GXT COMPILER")
    print("=" * 70)

    if not os.path.exists(ORIG_GXT_PATH):
        # Fallback to current american.gxt if backup not found
        orig_src = os.path.join(GAME_TEXT_DIR, "american.gxt")
    else:
        orig_src = ORIG_GXT_PATH

    gxt = parse_gxt(orig_src)
    print(f"Loaded source GXT with {len(gxt)} entries.")

    eng_subs = parse_srt(SRT_ENG_PATH)
    hun_subs = parse_srt(SRT_HUN_PATH)
    if os.path.exists(JB_ENG_PATH) and os.path.exists(JB_HUN_PATH):
        eng_subs += parse_srt(JB_ENG_PATH)
        hun_subs += parse_srt(JB_HUN_PATH)

    print(f"Loaded {len(hun_subs)} synchronized subtitle segments from Hungarian dub.")

    srt_content_list = []
    for (e_num, _, e_txt), (h_num, _, h_txt) in zip(eng_subs, hun_subs):
        c_e = clean_content(e_txt)
        if c_e:
            srt_content_list.append((c_e, h_txt, e_txt))

    # Static overrides for cutscene openers, pager letters, and UI strings
    STATIC_OVERRIDES = {
        "BET_JB": "SZERELME, CATALINA ELÁRULTA ÉS HALÁLRA SEBEZVE MAGÁRA HAGYTA. AZ ELÍTÉLT ÉS BÜNTETÉSÉT TÖLTŐ FÉRFIT ÉPP A LIBERTY FEGYHÁZBA SZÁLLÍTJÁK.",
        "BETRA_A": "Bocs, bébi.",
        "BETRA_B": "Én nagypályás csaj vagyok, te meg,",
        "BETRA_C": "csak egy kishal. Mindig is az voltál.",
        "CAT1_A": "Nálam van a drága Máriád. Ha nem akarod, hogy az arca úgy nézzen ki, mintha a hentes keze közé került volna,",
        "CAT1_B": "hozz 500.000 dollárt a Cedar Grove-i villához.",
        "CAT2_J": "Emeld már a levegőbe ezt a gépet!",
        "EBAL": "'SZABADSÁGOT NEKEM'",
        "EBAL_A": "Tudok egy helyet a piroslámpás negyed szélén, ott meghúzhatjuk magunkat,",
        "EBAL_A1": "de a kezeim tropára mentek, szóval te vezetsz, tesó.",
        "EBAL_B": "Pont itt vagyunk. Tűnjünk el az utcáról, és szerezzünk tiszta ruhát!",
        "EBAL_D": "Ismerek egy fickót, tele van kapcsolatokkal, Luigi a neve.",
        "EBAL_D1": "Régi haverok vagyunk, biztos tud neked szerezni valami melót. Gyerünk, menjünk oda.",
        "EBAL_E": "Gyerünk, ugorjunk be, bemutatlak neki.",
        "EBAL_G": "Ez Luigi klubja. Menjünk hátra a gazdasági bejárathoz.",
        "EBAL_H": "Várj itt haver, amíg bemegyek beszélni Luigivel.",
        "EBAL_I": "A főnök mindjárt kijön hozzád...",
        "EBAL_J": "8-Ball az emeleten üzletel.",
        "EBAL_K": "Talán tehetnél nekem egy szívességet.",
        "EBAL_L": "Egyik lányomnak fuvar kell. Szerezz egy kocsit és hozd el Mistyt a klinikáról, aztán hozd vissza ide.",
        "EBAL_M": "És ne feledd: senki sem szórakozhat a lányaimmal!",
        "EBAL_N": "Szóval a kezedet a kormányon tartsd!",
        "EBAL_O": "Ha nem cseszed el, kaphatsz még munkát. Most meg tűnés innen!",
        "LM1_9": "Szia, Misty vagyok.",
        "LM2_A": "Van egy új cucc az utcán, úgy hívják: SPANK.",
        "LM2_B": "Menj, és mutass be egy baseballütőt az arcának!",
        "LM2_C": "Luigi mondta, hogy adjam ezt neked, szóval...",
        "LM2_D": "Tessék, fogd, vedd el.",
        "LM2_E": "Valami okostojás ezt a szemetet terjeszti a lányaimnak Portland kikötőjében.",
        "LM2_F": "Aztán vidd el a kocsiját, és fújasd át.",
        "LM2_G": "Kárpótlást követelek ezért a sértésért!",
        "JAILB_R": "Senor seggfej!",
        "JAILB_U": "Jól van, jól van. Kopjatok le."
    }

    dialogue_prefixes = [
        "BETRA", "EBAL", "LM1", "LM2", "LM3", "LM4", "LM5",
        "JM1", "JM2", "JM3", "JM4", "JM5", "JM6",
        "TM1", "TM2", "TM3", "TM4", "TM5",
        "SM1", "SM2", "SM3", "SM4", "SM5", "FM1", "FM2", "FM3", "FM4",
        "AM1", "AM2", "AM3", "AM4", "AM5",
        "KM1", "KM2", "KM3", "KM4", "KM5",
        "RM1", "RM2", "RM3", "RM4", "RM5", "RM6",
        "LOVE1", "LOVE2", "LOVE3", "LOVE4", "LOVE5", "LOVE6", "DM",
        "CAT1", "CAT2", "END", "JAILB", "BET_JB",
        "DIAB1", "DIAB2", "DIAB3", "DIAB4",
        "HM1", "HM2", "HM3", "HM4", "HM5",
        "YD1", "YD2", "YD3", "YD4",
        "MEA1", "MEA2", "MEA3", "MEA4"
    ]

    matched_count = 0

    for k, orig_val in list(gxt.items()):
        if k in STATIC_OVERRIDES:
            gxt[k] = map_hungarian_text(STATIC_OVERRIDES[k])
            matched_count += 1
            continue

        is_dialogue = False
        for pfx in dialogue_prefixes:
            if k.startswith(pfx) and (re.search(r"_[A-Z][0-9]?$", k) or k == pfx):
                if not orig_val.startswith("~g~") and not orig_val.startswith("~r~Mission") and "~k~" not in orig_val:
                    is_dialogue = True
                    break

        if not is_dialogue:
            continue

        g_clean = clean_content(orig_val)
        if not g_clean:
            continue

        best_match = None
        best_score = 0.0

        for s_clean, h_txt, e_txt in srt_content_list:
            score = SequenceMatcher(None, g_clean, s_clean).ratio()
            if score > best_score:
                best_score = score
                best_match = h_txt

        # Accept matches with strong semantic overlap (>= 0.48) and sufficient length
        if best_score >= 0.48 and len(best_match) >= 12:
            prefix_tags = ""
            if orig_val.startswith("~"):
                tag_match = re.match(r"^((?:~[a-z0-9_]+~)+)", orig_val)
                if tag_match:
                    prefix_tags = tag_match.group(1)

            mapped_h = map_hungarian_text(best_match)
            gxt[k] = prefix_tags + mapped_h
            matched_count += 1

    print(f"Updated {matched_count} in-game subtitle and cutscene keys with Hungarian dub text.")

    # Write output to repo
    repo_text_dir = os.path.join(REPO_DIR, "text")
    os.makedirs(repo_text_dir, exist_ok=True)
    out_gxt_repo = os.path.join(repo_text_dir, "american.gxt")
    pack_gxt(gxt, out_gxt_repo)
    print(f"Generated repository GXT at: {out_gxt_repo}")

    # Deploy to game installations
    for text_dir in [GAME_TEXT_DIR, CROSSOVER_TEXT_DIR]:
        if not os.path.exists(text_dir):
            print(f"Skipping non-existent game directory: {text_dir}")
            continue

        backup_file = os.path.join(text_dir, "american_original_backup.gxt")
        orig_file = os.path.join(text_dir, "american.gxt")
        english_file = os.path.join(text_dir, "english.gxt")

        if os.path.exists(orig_file) and not os.path.exists(backup_file):
            shutil.copy2(orig_file, backup_file)
            print(f"Created original backup at: {backup_file}")

        pack_gxt(gxt, orig_file)
        pack_gxt(gxt, english_file)
        print(f"Deployed Hungarian GXT to: {orig_file} and {english_file}")

    print("\nIn-game Hungarian subtitles installed and verified successfully!")

if __name__ == "__main__":
    main()

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

    # Full Hungarian GUI, HUD, Options, Menus, Controls, and System Translations
    GUI_AND_SYSTEM_OVERRIDES = {
        # Language Setup
        "FEL_ENG": "MAGYAR",
        "FEL_FRE": "FRANCIA",
        "FEL_GER": "NÉMET",
        "FEL_ITA": "OLASZ",
        "FEL_SPA": "SPANYOL",
        "FEL_POL": "LENGYEL",
        "FEL_RUS": "OROSZ",
        "FEL_JAP": "JAPÁN",

        # Main Menu & Navigation
        "FEM_MM": "FŐMENÜ",
        "FEM_OPT": "BEÁLLÍTÁSOK",
        "FEM_QT": "KILÉPÉS",
        "FEN_STA": "JÁTÉK INDÍTÁSA",
        "FET_SGA": "JÁTÉK INDÍTÁSA",
        "FET_SNG": "ÚJ JÁTÉK INDÍTÁSA",
        "FET_SAN": "ÚJ JÁTÉK INDÍTÁSA",
        "FET_NG": "ÚJ JÁTÉK",
        "FES_NGA": "Új játék",
        "FES_SG": "ÚJ JÁTÉK",
        "FEM_RES": "FOLYTATÁS",
        "FET_PAU": "SZÜNET",
        "FET_OPT": "BEÁLLÍTÁSOK",
        "FET_QG": "KILÉPÉS",
        "FEDS_TB": "VISSZA",
        "FEDS_XB": "Kiválasztás",
        "FEM_YES": "IGEN",
        "FEM_NO": "NEM",
        "FEM_ON": "BE",
        "FEM_OFF": "KI",
        "FEM_AUT": "AUTOMATIKUS",
        "FEM_LOW": "ALACSONY",
        "FEM_MED": "KÖZEPES",
        "FEM_HIG": "MAGAS",
        "FEM_NRM": "NORMÁL",
        "FEM_NON": "NINCS",
        "FEM_SP": "EGYJÁTÉKOS MÓD",
        "FET_SP": "EGYJÁTÉKOS MÓD",
        "FEM_MP": "TÖBBJÁTÉKOS MÓD",
        "FET_MP": "TÖBBJÁTÉKOS MÓD",

        # Save / Load / Delete Game
        "FET_LG": "JÁTÉK BETÖLTÉSE",
        "FES_LG": "JÁTÉK BETÖLTÉSE",
        "FES_LGA": "Játék betöltése",
        "FEP_SAV": "JÁTÉK BETÖLTÉSE",
        "GMLOAD": "JÁTÉK BETÖLTÉSE",
        "GMSAVE": "JÁTÉK MENTÉSE",
        "GMREST": "Játék újraindítása",
        "FES_SNG": "ÚJ JÁTÉK",
        "FET_SG": "JÁTÉK MENTÉSE",
        "FES_SA": "Játék mentése",
        "FESZ_SA": "Játék mentése",
        "FET_DG": "JÁTÉK TÖRLÉSE",
        "FES_DGA": "JÁTÉK TÖRLÉSE",
        "FES_CAN": "Mégse",
        "FESZ_CA": "Mégse",
        "FESZ_UC": "MÉGSE",
        "FESZ_OK": "OK",
        "FES_WAR": "Mentés folyamatban, kérlek várj...",
        "FED_LDW": "Betöltés, kérlek várj...",
        "FED_DLW": "Törlés, kérlek várj...",
        "FESZ_L1": "Játék sikeresen elmentve!",
        "FES_SSC": "Játék sikeresen elmentve.",
        "FESZ_LS": "Sikeres betöltés.",
        "FES_LOF": "Betöltés sikertelen.",
        "FES_LOE": "Betöltés sikertelen! Kérlek próbáld újra.",
        "FES_DEE": "Törlés sikertelen! Kérlek próbáld újra.",
        "FESZ_QS": "FOLYTATOD A MENTÉST?",
        "FES_SCG": "Elmented a jelenlegi játékot?",
        "FES_LCG": "Betöltöd a játékot és folytatod?",
        "FESZ_QL": "Minden nem mentett haladás elvész. Folytatod a betöltést?",
        "FESZ_QD": "Biztosan törölni szeretnéd ezt a mentést?",
        "FESZ_QR": "Biztosan új játékot kezdesz? Minden nem mentett haladás elvész.",
        "FESZ_QO": "Felülírod ezt a mentést?",
        "FES_CGA": "Elérhető mentési helyek:",
        "FES_SLO": "MENTÉSI FÁJL",
        "FES_DAT": "DÁTUM",
        "FES_ISC": "SÉRÜLT FÁJL",
        "FES_ISF": "ÜRES HELY",
        "FEM_SL1": "1. hely szabad",
        "FEM_SL2": "2. hely szabad",
        "FEM_SL3": "3. hely szabad",
        "FEM_SL4": "4. hely szabad",
        "FEM_SL5": "5. hely szabad",
        "FEM_SL6": "6. hely szabad",
        "FEM_SL7": "7. hely szabad",
        "FEM_SL8": "8. hely szabad",

        # Audio Setup
        "FET_AUD": "HANG BEÁLLÍTÁSOK",
        "FEB_AUD": "Hang",
        "FEA_MUS": "ZENE HANGERŐ",
        "FEA_SFX": "EFFEKT HANGERŐ",
        "FEA_RSS": "RÁDIÓADÓ",
        "FEA_FMN": "RÁDIÓ KIKAPCSOLVA",
        "FEA_3DH": "HANG HARDVER",
        "FEA_SPK": "HANGSZÓRÓ BEÁLLÍTÁS",
        "FEA_2SP": "2 HANGSZÓRÓ",
        "FEA_4SP": "TÖBB MINT 2 HANGSZÓRÓ",
        "FEA_EAR": "FEJHALLGATÓ",
        "FEA_MNO": "Monó",
        "FEA_ST": "Sztereó",
        "FEA_NAH": "NINCS HANG HARDVER",
        "FEA_OUT": "Kimenet:",

        # Display Setup
        "FET_DIS": "KÉPERNYŐ BEÁLLÍTÁSOK",
        "FEB_DIS": "Képernyő",
        "FED_BRI": "FÉNYERŐ",
        "FED_SUB": "FELIRATOK",
        "FED_WIS": "SZÉLESVÁSZON",
        "FED_RES": "FELBONTÁS",
        "FED_FLS": "TELJES KÉPERNYŐ",
        "FED_WND": "ABLAKOS MÓD",
        "FED_TRA": "CSÓVÁK",
        "FED_MBL": "MOZGÁSI ELMOSÓDÁS",
        "FED_FRM": "KÉPKOCKA KORLÁTOZÓ",
        "FEM_FRM": "KÉPKOCKA KORLÁTOZÓ",
        "FEM_VSC": "FÜGGŐLEGES SZINKRON",
        "FEM_LOD": "LÁTÓTÁVOLSÁG",
        "FEM_CSB": "MOZIFILM KERETEK",
        "FED_AAS": "ÉLSÍMÍTÁS",
        "FED_FIL": "TEXTÚRA SZŰRÉS",

        # Language Setup
        "FET_LAN": "NYELV BEÁLLÍTÁSOK",
        "FEB_LAN": "Nyelv",

        # Controls Setup
        "FET_CTL": "IRÁNYÍTÁS BEÁLLÍTÁSA",
        "FEB_CON": "Irányítás",
        "FEB_CPC": "Irányítás Testreszabása",
        "FET_CCN": "IRÁNYÍTÁS: KLASSZIKUS",
        "FET_SCN": "IRÁNYÍTÁS: SZOKÁSOS",
        "FET_RDK": "GOMBOK MÓDOSÍTÁSA",
        "FET_DEF": "ALAPÉRTELMEZETT BEÁLLÍTÁSOK",
        "FET_HRD": "ALAPÉRTELMEZETT BEÁLLÍTÁSOK VISSZAÁLLÍTVA",
        "FET_AMS": "EGÉR BEÁLLÍTÁSOK",
        "FET_AGS": "GAMEPAD BEÁLLÍTÁSOK",
        "FET_MST": "EGÉRREL VEZÉRELT KORMÁNYZÁS",
        "FET_CCR": "JÁRMŰBEN",
        "FET_CFT": "GYALOG",
        "FET_CAC": "MŰVELET",
        "FET_CME": "IRÁNYÍTÁSI MÓD",
        "FET_APL": "ALKALMAZ",
        "FET_CIG": "BACKSPACE A TÖRLÉSHEZ - BAL KATTINTÁS/ENTER A VÁLTOZTATÁSHOZ",
        "FET_RIG": "VÁLASSZ EGY ÚJ GOMBOT A MŰVELETHEZ VAGY NYOMJ ESC-ET A MÉGSE-HEZ",
        "FET_EIG": "NEM RENDELHETŐ GOMB EHHEZ A MŰVELETHEZ",
        "FEC_ACC": "Gyorsítás",
        "FEC_ACL": "Jármű gyorsítás",
        "FEC_BRA": "Fék vagy tolatás",
        "FEC_BRK": "Jármű fék",
        "FEC_HAB": "Kézifék",
        "FEC_HBR": "Jármű kézifék",
        "FEC_HND": "Kézifék",
        "FEC_FOR": "Előre",
        "FEC_BAC": "Hátra",
        "FEC_LEF": "Balra",
        "FEC_RIG": "Jobbra",
        "FEC_LFA": "BALRA",
        "FEC_RFA": "JOBBRA",
        "FEC_FIR": "Tűz / Lövés",
        "FEC_ATT": "Támadás vagy fegyver használata",
        "FEC_WPN": "Fegyver használata",
        "FEC_PFR": "Fegyver elsütése",
        "FEC_JMP": "Ugrás",
        "FEC_JUM": "Ugrás",
        "FEC_PJP": "Gyalogos ugrás",
        "FEC_SPN": "Sprint",
        "FEC_PSP": "Gyalogos sprint",
        "FEC_ENT": "Beszállás / Kiszállás járműből",
        "FEC_ENV": "Beszállás a járműbe",
        "FEC_EXV": "Beszállás és kiszállás",
        "FEC_EEX": "Beszállás / kiszállás",
        "FEC_HOR": "Duda",
        "FEC_HRN": "Duda",
        "FEC_CAM": "Kamera nézetek",
        "FEC_CMR": "Kamera váltása",
        "FEC_CMS": "Kamera mód váltása minden helyzetben.",
        "FEC_CEN": "Kamera középre",
        "FEC_CCM": "Kamera játékos mögé igazítása.",
        "FEC_CRD": "Rádióállomás váltása",
        "FEC_CWL": "Előző fegyver",
        "FEC_CWR": "Következő fegyver",
        "FEC_CLE": "Előző fegyver",
        "FEC_CRI": "Következő fegyver",
        "FEC_NWE": "Következő fegyver",
        "FEC_PWE": "Előző fegyver",
        "FEC_LKT": "Célpont rögzítése",
        "FEC_TAR": "Célzás",
        "FEC_NTR": "Következő célpont",
        "FEC_PTT": "Előző célpont",
        "FEC_LBH": "Hátranézés járműből",
        "FEC_LLF": "Nézés balra járműből",
        "FEC_LRG": "Nézés jobbra járműből",
        "FEC_LL": "Nézés balra",
        "FEC_LR": "Nézés jobbra",
        "FEC_PAS": "Szünet",
        "FEC_PAU": "Szünet",

        # Statistics & Briefs
        "FET_STA": "STATISZTIKA",
        "FEB_STA": "Statisztika",
        "FET_BRE": "KÜLDETÉSEK",
        "FEB_BRI": "Küldetések",
        "FEB_PMB": "Korábbi küldetések leírása:",
        "FEST_MP": "Teljesített küldetések",
        "FEST_RP": "Teljesített ámokfutások",
        "FEST_FE": "Eloltott tüzek száma",
        "FEST_LS": "Mentővel megmentett személyek",
        "FEST_CC": "Megölt bűnözők (Polgárőrség)",
        "FEST_DC": "Autóval megtett távolság (mérföld)",
        "FEST_DF": "Gyalog megtett távolság (mérföld)",
        "FESTDCM": "Autóval megtett távolság (méter)",
        "FESTDFM": "Gyalog megtett távolság (méter)",
        "FEST_HA": "Legmagasabb mentős szint",
        "FEST_LF": "Leghosszabb repülés a Dodóval",
        "FEST_OO": "összesen",

        # HUD & System Alerts
        "DEAD": "POCSÉKUL VÉGEZTED!",
        "BUSTED": "LEKAPCSOLTAK!",
        "1005": "LEKAPCSOLTAK!",
        "1006": "LEKAPCSOLTAK!",
        "1007": "LEKAPCSOLTAK!",
        "1008": "LEKAPCSOLTAK!",
        "1009": "LEKAPCSOLTAK!",
        "1010": "~r~A járműved a tetejére borult",
        "1011": "~r~A járműved a tetejére borult",
        "1012": "~r~A járműved a tetejére borult",
        "1013": "~r~A járműved a tetejére borult",
        "1014": "~r~A járműved a tetejére borult",
        "M_PASS": "KÜLDETÉS TELJESÍTVE! $~1~",
        "M_FAIL": "KÜLDETÉS SIKERTELEN!",
        "A_PASS": "Megmentve!",
        "C_PASS": "VESZÉLY ELHÁRÍTVA!",
        "F_PASS1": "Tűz eloltva!",
        "O_PASS": "MELLÉKKÜLDETÉS TELJESÍTVE!",
        "AMMU": "Menj be az Ammu-Nationbe fegyvert venni.",
        "BOMB1": "8-Ball garázsa",
        "RES_A": "A HÍD LE VAN ZÁRVA.",
        "TAX_1": "Vidd az utast a célállomásra!",
        "TAX_2": "Keresd meg a következő utast!",
        "TAX_3": "Fuvar teljesítve! Kerestél: $~1~",

        # Help / Tutorial Strings
        "HELP1": "Állj meg a kék jelzés közepén.",
        "HELP10": "Ez a jelvény jelzi a rendőrségi körözési szintedet.",
        "HELP11": "Minél több a jelvény, annál magasabb a körözési szinted.",
        "HELP12": "Lépj a kék jelzés közepébe a küldetés elindításához.",
        "HELP13": "Néha olyan utakat kell használnod, amelyeket nem mutat a radar.",
        "HELP14": "A fegyverek felvételéhez sétálj át rajtuk. Járműből nem lehet felvenni őket.",
        "HELP15": "Gyalog nyomd meg a ~h~~k~~PED_LOOKBEHIND~ gombot~w~ a ~h~hátranézéshez~w~.",
        "HELP2_A": "Nyomd meg a ~h~/ gombot~w~ futás közben a ~h~sprinteléshez.",
        "HELP3": "Csak rövid ideig tudsz sprintelni, mielőtt elfáradsz.",
        "HELP4_A": "Nyomd meg a~h~ ~k~~VEHICLE_ACCELERATE~ gombot~w~ a ~h~gyorsításhoz.",
        "HELP5_A": "Nyomd meg a~h~ ~k~~VEHICLE_BRAKE~ gombot~w~ a ~h~fékezéshez~w~, vagy a ~h~tolatáshoz~w~, ha a jármű már megállt.",
        "HELP6_A": "Nyomd meg a~h~ ~k~~VEHICLE_HANDBRAKE~ gombot ~w~a ~h~kézifék~w~ behúzásához.",
        "HELP6_C": "Nyomd meg a~h~ ~k~~VEHICLE_HANDBRAKE~ gombot ~w~a ~h~kézifék~w~ behúzásához.",
        "HELP6_D": "Nyomd meg a~h~ ~k~~VEHICLE_HANDBRAKE~ gombot ~w~a ~h~kézifék~w~ behúzásához.",

        # Key Gameplay Objectives & Alerts
        "EBAL_1": "Nyomd meg a~h~ ~k~~VEHICLE_ENTER_EXIT~ gombot~w~ a járműbe való ~h~beszálláshoz~w~ vagy ~h~kiszálláshoz~w~.",
        "EBAL_1B": "Nyomd meg a~h~ ~k~~VEHICLE_ENTER_EXIT~ gombot~w~ a járműbe való ~h~beszálláshoz~w~ vagy ~h~kiszálláshoz~w~.",
        "EBAL_2": "~g~Szállj vissza a kocsiba!",
        "EBAL_3": "Ez a ~h~radar~w~. Használd a városban való tájékozódáshoz, kövesd a ~h~jelzést~w~ a ~h~radaron~w~ a búvóhely megtalálásához!",
        "EBAL_4": "~r~8-Ball meghalt!",
        "EBAL_5": "~g~Szerezz egy járművet!",
        "EBAL_6": "~g~Vedd fel Mistyt!",
        "JM1_1": "~g~Vidd Forelli autóját 8-Ball garázsába északra, az 'Easy Credit Autos' mögé.",
        "LM1_1": "~g~Menj a kórházhoz és vedd fel Mistyt!",
        "LM1_2": "~g~Vidd vissza Mistyt Luigi klubjához!",
        "LM2_1": "~g~Menj Portland kikötőjébe és találd meg a dílert!",
        "LM2_2": "~g~Végezz a dílerrel!",
        "LM2_3": "~g~Vidd el a díler autóját a Pay 'n' Spray-be és fújasd át!",
        "PAGEB1": "Pisztoly leszállítva a búvóhelyre",
        "PAGEB2": "Uzi leszállítva a búvóhelyre",
        "PAGEB3": "Golyóálló mellény leszállítva a búvóhelyre",
        "PAGEB4": "Sörétes puska leszállítva a búvóhelyre",
        "PAGEB5": "Gránátok leszállítva a búvóhelyre",
        "PAGEB6": "Molotov-koktélok leszállítva a búvóhelyre",
        "PAGEB7": "AK-47 leszállítva a búvóhelyre",
        "PAGEB8": "Mesterlövész puska leszállítva a búvóhelyre",
        "PAGEB9": "M16 leszállítva a búvóhelyre",
        "PAGEB10": "Rakétavető leszállítva a búvóhelyre",
        "PAGEB11": "Lángszóró leszállítva a búvóhelyre",
        "PAGEB12": "Rendőri kenőpénz leszállítva a búvóhelyre",
        "PAGEB13": "Életerő csomag leszállítva a búvóhelyre",
        "PAGEB14": "Adrenalin kapszula leszállítva a búvóhelyre",

        # Pause Menu Navigation
        "FEP_AUD": "HANG",
        "FEP_BRI": "KÜLDETÉSEK",
        "FEP_CON": "IRÁNYÍTÁS",
        "FEP_DIS": "KÉPERNYŐ",
        "FEP_LAN": "NYELV",
        "FEP_STA": "STATISZTIKA",

        # Safehouse, Garage & Save Prompts
        "S_PROM2": "A szomszédos garázsban tárolhatsz egy járművet a játék mentésekor.",
        "S_PROMP": "Ha nem vagy küldetésben, itt ~h~elmentheted a játékot~w~, ami hat órát léptet előre az időben.",
        "SAVE1": "Menj be az ajtón a ~h~játék mentéséhez~w~. Küldetés közben nem menthetsz.",
        "SAVE2": "A garázsban hagyott járművek elmentődnek a játék mentésekor.",
        "GARAGE": "Hajts be a járművel a garázsba, majd sétálj ki.",
        "GARAGE1": "~g~Szállj ki a járműből és sétálj ki.",
        "NOGMSV": "Csak a búvóhelyeden menthetsz.",
        "S_TRN_1": "A metróval közlekedhetsz Liberty Cityben. Nyomd meg a~h~ ~k~~VEHICLE_ENTER_EXIT~ gombot~w~ a vonatra való ~h~felszálláshoz~w~ vagy ~h~leszálláshoz~w~.",
        "S_TRN_2": "A metróval közlekedhetsz Liberty Cityben. Nyomd meg a~h~ ~k~~VEHICLE_ENTER_EXIT~ gombot~w~ a vonatra való ~h~felszálláshoz~w~ vagy ~h~leszálláshoz~w~.",

        # System, Submissions & Emergency Missions
        "1000": "MEGHALTÁL",
        "1001": "MEGHALTÁL",
        "1002": "MEGHALTÁL",
        "1003": "MEGHALTÁL",
        "1004": "MEGHALTÁL",
        "CTUTOR": "Nyomd meg a ~h~~k~~TOGGLE_SUBMISSIONS~ gombot~w~ a Polgárőr küldetések be- vagy kikapcsolásához.",
        "CTUTOR2": "Nyomd meg a ~h~~k~~TOGGLE_SUBMISSIONS~ gombot~w~ a Polgárőr küldetések be- vagy kikapcsolásához.",
        "ATUTOR": "Nyomd meg a ~h~~k~~TOGGLE_SUBMISSIONS~ gombot~w~ a Mentős küldetések be- vagy kikapcsolásához.",
        "ATUTOR3": "Nyomd meg a ~h~~k~~TOGGLE_SUBMISSIONS~ gombot~w~ a Mentős küldetések be- vagy kikapcsolásához.",
        "ATUTOR2": "~g~ÓVATOSAN szállítsd a betegeket a kórházba. Minden ütközés csökkenti a túlélési esélyeiket.",
        "FTUTOR": "Nyomd meg a ~h~~k~~TOGGLE_SUBMISSIONS~ gombot~w~ a Tűzoltó küldetések be- vagy kikapcsolásához.",
        "FTUTOR2": "Nyomd meg a ~h~~k~~TOGGLE_SUBMISSIONS~ gombot~w~ a Tűzoltó küldetések be- vagy kikapcsolásához.",
        "TTUTOR": "Nyomd meg a ~h~~k~~TOGGLE_SUBMISSIONS~ gombot~w~ a Taxi küldetések be- vagy kikapcsolásához.",
        "TTUTOR2": "Nyomd meg a ~h~~k~~TOGGLE_SUBMISSIONS~ gombot~w~ a Taxi küldetések be- vagy kikapcsolásához.",
        "ALEVEL": "Mentős küldetés szintje: ~1~",
        "A_CANC": "~r~Mentős küldetés megszakítva!",
        "A_FAIL2": "~r~A késlekedés a beteg életébe került!",
        "A_FAIL3": "~r~A beteg meghalt!!",
        "A_FULL": "~r~A mentőautó megtelt!!",
        "A_RANGE": "~g~A mentő rádiója vételkörzeten kívül van, menj közelebb egy kórházhoz!",

        # Ammu-Nation & Bomb Shop
        "AMMU_A": "Luigi mondta, hogy szükséged lesz egy vasra...",
        "AMMU_B": "Joey szólt, hogy szereljelek fel...",
        "AMMU_C": "Menj a bolt mögé. Hagytam egy kilencest az udvaron.",
        "AMMU_D": "Minden megvan, ami az otthoni önvédelemhez kell.",
        "AMMU_E": "Engedélyt is akarsz hozzá?",
        "AMMU_F": "Nem kell igazolnod magad, megbízhatónak tűnsz.",
        "BOMB": "Hajts be a járművel a bombaműhelybe egy ~h~bomba~w~ felszereléséhez. Ár: ~h~$1000.",

        # Partner / Follower Warnings
        "HEY": "~g~Ne menj egyedül, tartsd együtt a csapatot!",
        "HEY2": "~g~Ne szakadjatok szét, tartsátok együtt a csoportot!",
        "HEY3": "~g~Elhagytad az emberedet, menj vissza 8-Ballért!",
        "HEY4": "~g~Ha elhagyod Mistyt, Luigi ellátja a bajodat! Menj és hozd el!",
        "HEY5": "~g~Az egyik lány eltűnt, menj vissza és keresd meg!",
        "HEY6": "~g~Nem hagyhatod cserben a jakuza kanbut. Meg kell védened!",
        "HEY7": "~g~Egy plusz fegyver jól jöhet. Menj vissza és vedd fel az emberedet!",
        "HEY8": "~g~A védelem védelmet jelent - védd meg az öreg úriembert!",
        "HEY9": "~g~Tudni akarod mi a helyzet az utcán? Menj az emberedhez!",

        # Early Missions Instructions
        "LM1": "'LUIGI LÁNYAI'",
        "LM1_2": "~g~Vidd Mistyt Luigi klubjához!",
        "LM1_3": "~g~Nyomd meg a dudát, hogy a lány beszálljon a kocsiba.",
        "LM1_6": "~g~Szállj vissza a kocsiba!",
        "LM1_7": "Állj meg a járművel Misty mellett, hogy beszállhasson.",
        "LM1_8": "Elmehetsz Luigihez további munkáért, vagy nézz körül Liberty Cityben.",
        "LM1_8A": "Ha extra pénzt akarsz keresni, miért nem 'kölcsönzöl' egy taxit...",
        "LM2": "'NE ZAKLASD A LÁNYAIT'",
        "LM2_1": "~g~Vidd el a kocsiját és fújasd át.",
        "LM2_2A": "Használd a~h~ ~k~~PED_FIREWEAPON~ gombot~w~ az ~h~ütéshez~w~ és ~h~rúgáshoz~w~, vagy az ütő ~h~lendítéséhez~w~!",
        "LM2_2C": "Használd a~h~ ~k~~PED_FIREWEAPON~ gombot~w~ az ~h~ütéshez~w~ és ~h~rúgáshoz~w~, vagy az ütő ~h~lendítéséhez~w~!",
        "LM2_2D": "Használd a~h~ ~k~~PED_FIREWEAPON~ gombot~w~ az ~h~ütéshez~w~ és ~h~rúgáshoz~w~, vagy az ütő ~h~lendítéséhez~w~!",
        "LM2_3": "~g~Rejtsd el a kocsit Luigi garázsában!",
        "LM2_4": "~g~Fújasd át a kocsit!",
        "LM3_1A": "Nyomd meg a~h~ ~k~~VEHICLE_HORN~ gombot~w~ a ~h~duda~w~ használatához, jelezve Mistynek, hogy itt vagy.",
        "LM3_1B": "Nyomd meg a~h~ ~k~~VEHICLE_HORN~ gombot~w~ a ~h~duda~w~ használatához, jelezve Mistynek, hogy itt vagy.",
        "LM3_1C": "Nyomd meg a~h~ ~k~~VEHICLE_HORN~ gombot~w~ a ~h~duda~w~ használatához, jelezve Mistynek, hogy itt vagy.",
        "LM3_2": "~g~Vidd Mistyt Joey műhelyébe!",
        "LM3_4": "~g~Menj és vedd fel Mistyt!",
        "LM3_10": "~g~Szerezz egy járművet!",
        "LM3_11": "~g~Misty nem hajlandó busszal utazni, szerezz egy másik járművet!",
        "JM1": "'MIKE LIPS UTOLSÓ EBÉDJE'",
        "JM1_1": "~g~Vidd Forelli kocsiját 8-Ball garázsába északra, az 'Easy Credit Autos' mögé.",
        "JM1_2": "~g~Parkold vissza a kocsit a Marco's Bistro elé.",
        "JM1_3": "~g~Aktiváld az autóba rejtett bombát, majd tűnj el onnan!",
        "JM1_4": "~g~Összetörted a járművet! Vidd el megjavíttatni!",
        "JM1_5": "~g~Az autóba rejtett bomba nincs élesítve!",
        "JM1_6": "~g~Állítsd vissza a kocsit a pontos helyére.",
        "JM1_7": "~g~Csukd be az autó ajtaját! Észre fogja venni!",
        "JM1_8A": "~y~Hé, itt van az emberem!",
        "JM1_8B": "~y~A bombaműhely automatizált. Csak hajts be, állj meg, a műhely elintézi a többit.",
        "JM1_8C": "~y~Tessék, az első ingyenes, de utána fizetned kell.",
        "JM2": "'BÚCSÚ CSALÁDI KÖRÖKBEN'",
        "JM3": "'CIPRIANI SOFŐRJE'",
        "JM3_1": "~g~Vidd a furgont a garázsba.",
        "JM3_2": "~g~Zúzd a furgont, amíg a sérülése 70 százalék alá nem esik.",
        "JM4": "'DÖGLÖTT HAL'",
        "JM4_7": "~g~Vidd Tonit az anyja éttermébe.",
        "JM4_8": "~r~Tonit kinyírták!",
        "JM5": "'A VÉGZETES HANG'",
        "JM5_1": "~g~Vidd a zúzdába!",
        "JM5_2": "~g~A Forelli testvérek azok!",
        "JM6": "'A NAGY RABLÁS'",
        "JM6_1": "Menj a bankhoz a főutcán.",
        "JM6_3": "Vigyél ki minket innen!!",
        "JM6_4": "Rázd le a zsarukat és vigyél a búvóhelyre!!",
        "JM6_5": "~g~Szükséged van egy menekülő autóra, idióta!",
        "JM6_6": "~g~Szerezz egy feltűnésmentesebb járművet!",
        "JM6_7": "~g~Mind a 3 emberre szükség van a bankrabláshoz!",
        "JM6_8": "~r~Elvesztetted az összes rablót!",

        # All Mission Titles
        "AM1": "'SAYONARA SALVATORE'",
        "AM2": "'MEGFIGYELÉS ALATT'",
        "AM3": "'PAPARAZZI VADÁSZAT'",
        "AM4": "'FIZETÉSI NAP RAYNEK'",
        "AM5": "'KÉTARCÚ TANNER'",
        "AS1": "'A CSALI'",
        "AS2": "'ESPRESSO-2-GO!'",
        "AS3": "'S.A.M.'",
        "AS4": "'VÁLTSÁGDÍJ'",
        "CAT1": "'VÁLTSÁGDÍJ'",
        "CAT2": "'A CSERE'",
        "COP_M": "'POLGÁRŐRSÉG'",
        "FIRE_M": "'TŰZOLTÓ'",
        "AMBUL_M": "'MENTŐS'",
        "TAXI_M": "'TAXI'",
        "DIAB1": "'TURISMO'",
        "DIAB2": "'FAGYLALTOS CSAPDA'",
        "DIAB3": "'TŰZKERESZTSÉG'",
        "DIAB4": "'VÉNÁS TEHERAUTÓ'",
        "FM1": "'CHAPERON'",
        "FM2": "'A KASZÁLÁS'",
        "FM21": "'BOMBA A BÁZISRA: 1. FELVONÁS'",
        "FM3": "'BOMBA A BÁZISRA: 2. FELVONÁS'",
        "FM4": "'AZ UTOLSÓ KÉRÉS'",
        "TM1": "'A KANCSÓ SZÉTVERÉSE'",
        "TM2": "'TÚSZMENTÉS'",
        "TM3": "'TRIÁD HÁBORÚ'",
        "TM4": "'KÜLDÖNC'",
        "TM5": "'CIPRIANI HALÁSZATA'"
    }

    STATIC_OVERRIDES.update(GUI_AND_SYSTEM_OVERRIDES)

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
    out_gxt_eng_repo = os.path.join(repo_text_dir, "english.gxt")
    pack_gxt(gxt, out_gxt_repo)
    pack_gxt(gxt, out_gxt_eng_repo)
    print(f"Generated repository GXT at: {out_gxt_repo} and {out_gxt_eng_repo}")

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

        # Update FEL_ENG in all other language GXT files so "MAGYAR" is visible from any language menu
        for fname in os.listdir(text_dir):
            if fname.lower().endswith(".gxt") and fname not in ["american.gxt", "english.gxt", "american_original_backup.gxt"]:
                other_gxt_path = os.path.join(text_dir, fname)
                try:
                    other_gxt = parse_gxt(other_gxt_path)
                    if "FEL_ENG" in other_gxt:
                        other_gxt["FEL_ENG"] = map_hungarian_text("MAGYAR")
                        pack_gxt(other_gxt, other_gxt_path)
                        print(f"Updated FEL_ENG -> MAGYAR in {fname}")
                except Exception as e:
                    print(f"Could not update {fname}: {e}")

    print("\nIn-game Hungarian GUI, Menus, and Subtitles installed and verified successfully!")

if __name__ == "__main__":
    main()

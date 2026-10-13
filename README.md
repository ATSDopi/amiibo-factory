# amiibo-factory

Flipper Zero Amiibo database regenerated to **factory-fresh state** — every file behaves like a brand-new, never-registered amiibo figure.

Based on [AmiiboDB/Amiibo](https://github.com/AmiiboDB/Amiibo) (964 dumps, all series).

## Why

Most public amiibo dumps are rips of **already-used figures**: the tag contains console registration data (owner nickname) and game appdata. On a real Switch/3DS this causes failures — the console detects the tag state, tries to write/validate it, and rejects the emulated tag. Two additional issues compound it:

1. **Missing NTAG215 auth data** — since Flipper firmware **0.94.1** the device enforces real NTAG215 authentication during emulation ([firmware issue #3188](https://github.com/flipperdevices/flipperzero-firmware/issues/3188)). Dumps converted from `.bin` have `Page 133`/`Page 134` zeroed → the console reports *"This is not an amiibo"* or times out.
2. **Used-state dumps** — verified empirically: dumps with registration/appdata filled are rejected by games (e.g. Zelda: Tears of the Kingdom), while factory-state dumps scan fine.

## What was fixed, for every dump

| Fix | Detail |
|---|---|
| Factory state | Registration/nickname/appdata areas blanked — tag presents as new-in-box |
| Valid signature | Re-signed with retail keys (`pyamiibo`), `verify()` passes |
| Unique UID | Fresh random UID per file → counts as a distinct figure for the 1-scan/day in-game limit |
| NTAG215 PWD | `Page 133` = password derived from UID (`UID[1]^UID[3]^0xAA`, `UID[2]^UID[4]^0x55`, `UID[3]^UID[5]^0xAA`, `UID[4]^UID[6]^0x55`) |
| NTAG215 PACK | `Page 134` = `80 80 00 00` |
| Broken dump repaired | `Pikmin_Amiibo/Pikmin.nfc` had an invalid UID → regenerated |

Amiibo IDs are unchanged — each file keeps its original figure identity (ID is read from the plaintext area at `0x54–0x5B`, so even broken dumps regenerate correctly).

## Contents

```
Amiibo NFC/   964 .nfc files — ready for Flipper (nfc/Amiibo on the SD card)
Amiibo Bin/   964 .bin files — raw NTAG215 images (emutag, pixl.js, other tools)
tools/        regen_factory.py — the regeneration tool + retail key + template
```

## Usage

**Flipper**: copy `Amiibo NFC/` to `nfc/Amiibo/` on the SD card. Emulate from `NFC → Saved → Amiibo → …`.

**Regenerate another collection**:

```bash
pip install pyamiibo
python tools/regen_factory.py /path/to/nfc/files          # in-place fix
python tools/regen_factory.py /path/to/nfc/files --dry-run  # report only
```

The tool scans every `.nfc`: files that are already factory-state are left untouched; used or broken dumps are rebuilt on a clean template with their own amiibo ID, a fresh UID and a valid signature.

## Notes

- File names/series tree identical to AmiiboDB — drop-in replacement.
- `Gerudo_King.nfc` / `Princess_Zelda.nfc` (Zelda TOTK folder) are unofficial datamined IDs — they scan, but they are not the real Zelda/Ganondorf figures. The real TOTK figures are `Link`, `Zelda (TotK)`, `Ganondorf (TotK)`.
- Some games write save data onto the amiibo on first use. That requires firmware with writable emulation (`.shd` shadow files on Momentum/RogueMaster) or a physical tag.

## Credits

- Original collection: [AmiiboDB/Amiibo](https://github.com/AmiiboDB/Amiibo)
- Crypto: [pyamiibo](https://github.com/tobywf/pyamiibo) / [amiitool](https://github.com/socram8888/amiitool) (retail keys — public)
- NTAG215 auth fix reference: [Flipper-NTAG215-password-converter](https://github.com/turbospok/Flipper-NTAG215-password-converter)

Amiibo and all related data © Nintendo. This repo is for personal archival/interoperability; the dumps remain Nintendo's copyrighted data.

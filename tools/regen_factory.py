#!/usr/bin/env python3
"""Regenerate Flipper Zero Amiibo .nfc files to factory-fresh state.

Fixes two issues that make amiibo fail on a real console:
  1. Dumps of *already used/registered* amiibo (nickname, console data and
     game appdata written to the tag). The Switch may try to update the tag
     on scan and rejects dumps it cannot write to / whose state is invalid.
     -> Regenerated as blank factory-state tags.
  2. Missing NTAG215 authentication data (Flipper firmware >= 0.94.1,
     issue flipperdevices/flipperzero-firmware#3188).
     -> Page 133 = PWD derived from UID, page 134 = PACK 80 80.

Every regenerated file keeps its original amiibo ID (read at 0x54-0x5B,
plaintext area), gets a fresh random UID (counts as a distinct figure for
the in-game daily limit) and is re-signed with the retail keys, so the
Nintendo signature stays valid.

Requires: pip install pyamiibo
Usage:    python regen_factory.py <dir-of-nfc-files> [--dry-run]
"""
import os, re, sys, random
from amiibo import AmiiboDump, AmiiboMasterKey
from amiibo.crypto import AmiiboHMACError

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = AmiiboMasterKey.from_combined_bin(open(os.path.join(HERE, 'key_retail.bin'), 'rb').read())

# Any valid *factory-state* dump works as template. We ship Gerudo_King.bin
# next to this script for that purpose.
TPL = open(os.path.join(HERE, 'template.bin'), 'rb').read()

PAGE_RE = re.compile(r'Page (\d+):\s*([0-9A-Fa-f ]+)')

def parse_nfc(path):
    pages = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = PAGE_RE.match(line.strip())
            if m:
                pages[int(m.group(1))] = bytes(int(x, 16) for x in m.group(2).split())
    return pages

def is_fresh(d):
    """Factory-state = no console registration / no appdata written."""
    return (d[0x14] == 0x10
        and not any(d[0x20:0x2C])
        and not any(d[0xBA:0xCE])
        and not any(d[0xE8:0xFC])
        and not any(d[0x10A:0x10E]))

def pwd_from_uid(uid):
    return [uid[1]^uid[3]^0xAA, uid[2]^uid[4]^0x55,
            uid[3]^uid[5]^0xAA, uid[4]^uid[6]^0x55]

def write_nfc(b, uid, path):
    pwd = pwd_from_uid(uid)
    out = ['Filetype: Flipper NFC device', 'Version: 2',
           '# Nfc device type can be UID, Mifare Ultralight, Bank card',
           'Device type: NTAG215',
           '# UID, ATQA and SAK are common for all formats',
           'UID: ' + ' '.join(f'{x:02X}' for x in uid),
           'ATQA: 44 00', 'SAK: 00', '# Mifare Ultralight specific data',
           'Signature: ' + ' '.join(['00'] * 32),
           'Mifare version: 00 04 04 02 01 00 11 03']
    for i in range(3):
        out += [f'Counter {i}: 0', f'Tearing {i}: 00']
    out.append('Pages total: 135')
    for p in range(135):
        pg = bytes(pwd) if p == 133 else (bytes([0x80, 0x80, 0, 0]) if p == 134 else b[p*4:p*4+4])
        out.append(f'Page {p}: ' + ' '.join(f'{x:02X}' for x in pg))
    with open(path, 'w', newline='\n') as f:
        f.write('\n'.join(out) + '\n')

def regenerate(amiibo_id):
    dump = AmiiboDump(KEYS, bytearray(TPL))
    dump.unlock()
    dump.data[0x54:0x5C] = amiibo_id
    uid = bytes([0x04]) + bytes(random.getrandbits(8) for _ in range(6))
    dump.uid_hex = uid.hex(' ')
    dump.lock()
    img = bytes(dump.data)
    chk = AmiiboDump(KEYS, bytearray(img))
    chk.unlock()  # raises if signature invalid
    assert bytes(chk.data[0x54:0x5C]) == amiibo_id
    return img, uid

def main():
    if len(sys.argv) < 2:
        sys.exit('usage: regen_factory.py <dir-of-nfc-files> [--dry-run]')
    root = sys.argv[1]
    dry = '--dry-run' in sys.argv
    stats = {'fresh': 0, 'regenerated': 0, 'skipped': [], 'errors': []}
    for dirpath, _, files in os.walk(root):
        for fn in sorted(files):
            if not fn.lower().endswith('.nfc'):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)
            try:
                pages = parse_nfc(path)
                if len(pages) < 135:
                    stats['skipped'].append(rel); continue
                raw = b''.join(pages.get(i, bytes(4)) for i in range(135))[:540]
                try:
                    d0 = AmiiboDump(KEYS, bytearray(raw)); d0.unlock()
                    if is_fresh(d0.data):
                        stats['fresh'] += 1; continue
                    amiibo_id = bytes(d0.data[0x54:0x5C])
                except Exception:
                    amiibo_id = raw[0x54:0x5C]
                if not any(amiibo_id) or amiibo_id == b'\xff' * 8:
                    stats['skipped'].append(rel); continue
                img, uid = regenerate(amiibo_id)
                if not dry:
                    write_nfc(img, uid, path)
                stats['regenerated'] += 1
            except Exception as e:
                stats['errors'].append((rel, repr(e)))
    print(stats)

if __name__ == '__main__':
    main()

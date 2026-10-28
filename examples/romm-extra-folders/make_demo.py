#!/usr/bin/env python3
"""Create a new text-only fixture. No game files or external downloads."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zlib

KINDS = 'dlc hack manual mod patch update demo translation prototype walkthrough soundtrack cheat screenshot'.split()

def create(root):
    root = root.absolute()
    root.mkdir(parents=True, exist_ok=False)
    (root/'dats').mkdir(); (root/'input').mkdir(); (root/'extras').mkdir()
    expected, rows = {}, []
    for platform, dat_name, games in [
        ('gb', 'Nintendo - Game Boy', [('Shared Title (USA)', 1), ('Two File Set (USA)', 2), ('Excluded (USA) (Demo)', 1)]),
        ('gba', 'Nintendo - Game Boy Advance', [('Shared Title (USA)', 1)]),
    ]:
        tree=ET.Element('datafile');header=ET.SubElement(tree,'header')
        ET.SubElement(header,'name').text=dat_name
        ET.SubElement(header,'description').text=dat_name+' - owned text fixture'
        ET.SubElement(header,'version').text='1'
        for game,count in games:
            g=ET.SubElement(tree,'game',name=game);ET.SubElement(g,'description').text=game
            entries={}
            for n in range(count):
                name=f'{platform} text {game} {n+1}.txt'
                payload=f'Original text fixture: {platform} / {game} / file {n+1}. Not a game.\n'.encode()
                (root/'input'/name).write_bytes(payload)
                ET.SubElement(g,'rom',name=name,size=str(len(payload)),crc=f'{zlib.crc32(payload):08x}',md5=hashlib.md5(payload).hexdigest(),sha1=hashlib.sha1(payload).hexdigest())
                entries[name]=payload.decode()
            if '(Demo)' not in game:
                expected[f'{platform}/{game}/{game}.zip']=entries
        ET.indent(tree)
        ET.ElementTree(tree).write(root/'dats'/f'{platform}.dat',encoding='utf-8',xml_declaration=True)
    for n,kind in enumerate(KINDS):
        name=f'Owned {kind} note.txt';(root/'extras'/name).write_text(f'Original {kind} placeholder text only.\n',encoding='utf-8')
        rows.append(dict(source='extras/'+name,platform='gb',game='Shared Title (USA)',kind=kind))
    (root/'extras'/'Second manual.txt').write_text('Second owned text note.\n')
    rows.append(dict(source='extras/Second manual.txt',platform='gb',game='Shared Title (USA)',kind='manual'))
    (root/'extras'/'Other platform.txt').write_text('Explicit other platform; same game title.\n')
    rows.append(dict(source='extras/Other platform.txt',platform='gba',game='Shared Title (USA)',kind='manual'))
    (root/'extras'/'Multi file note.txt').write_text('Extra for a two-file game folder.\n')
    rows.append(dict(source='extras/Multi file note.txt',platform='gb',game='Two File Set (USA)',kind='walkthrough'))
    (root/'extras.json').write_text(json.dumps(rows,indent=2)+'\n')
    (root/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
    return root

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    print(create(p.parse_args().directory))

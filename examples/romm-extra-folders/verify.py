#!/usr/bin/env python3
"""Run the text-only native Igir workflow and omission controls in a new directory."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from make_demo import create
from place_extras import prepare, KINDS

HERE = Path(__file__).resolve().parent

def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}

def native(base, label, omit=None, protections=True, anchors=(), expect_failure=False):
    node=shutil.which('node')
    entry=HERE/'node_modules/igir/dist/index.js'
    if not node or not entry.is_file():
        raise RuntimeError('Install the pinned npm dependency and put a supported Node.js on PATH first')
    commands=[x for x in ('zip','copy','test','clean') if x != omit]
    args=[node,str(entry),*commands,'--dat',str(base/'dats/*.dat'),
          '--input',str(base/'input'),'--output',str(base/'roms/{romm}'),
          '--dir-game-subdir','always','--overwrite-invalid',
          '--no-demo','--no-prototype','--no-bios','--no-bad','--no-sample','--no-beta','--no-debug',
          '--single','--prefer-language','EN','--prefer-revision','newer','--prefer-retail','--prefer-parent',
          '--prefer-region','USA,WORLD,EUR,JPN','--reader-threads','1','--writer-threads','1',
          '--disable-cache','--temp-dir',str(base/f'temporary {label}'),'-vvv']
    if 'clean' in commands:
        args+=['--clean-backup',str(base/'clean backup')]
        # Protect only manifest-declared kind directories, including unlisted files there.
        if protections:
            kinds=','.join(sorted(KINDS))
            args+=['--clean-exclude',(base/'roms').as_posix()+'/*/*/{'+kinds+'}/**']
        for anchor in anchors:
            args+=['--clean-exclude',str(anchor)]
    result=subprocess.run(args,cwd=base,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    log=base/f'{label}.log';log.write_text(result.stdout,encoding='utf-8')
    (base/f'{label}.command.json').write_text(json.dumps(args,indent=2)+'\n')
    if expect_failure:
        assert result.returncode != 0, 'omitted required command was accepted'
        return result.stdout
    if result.returncode:
        raise AssertionError(f'Igir exit {result.returncode}; see {log}')
    return result.stdout

def readonly_test(base, label):
    args=[shutil.which('node'),str(HERE/'node_modules/igir/dist/index.js'),'test',
          '--dat',str(base/'dats/*.dat'),'--input',str(base/'roms/**/*.zip'),
          '--no-demo','--disable-cache','--temp-dir',str(base/f'temporary {label}'),'-vvv']
    result=subprocess.run(args,cwd=base,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    (base/f'{label}.log').write_text(result.stdout)
    (base/f'{label}.command.json').write_text(json.dumps(args,indent=2)+'\n')
    assert result.returncode==0, f'read-only native test failed: {label}'
    return result.stdout

def archives(base, log, mode='zip'):
    expected=json.loads((base/'expected.json').read_text())
    actual={str(p.relative_to(base/'roms')) for p in (base/'roms').rglob('*.zip')}
    assert actual==set(expected), f'archive set differs: {actual}'
    for rel, entries in expected.items():
        path=base/'roms'/rel
        assert zipfile.is_zipfile(path), f'not a ZIP: {rel}'
        with zipfile.ZipFile(path) as archive:
            assert set(archive.namelist())==set(entries), f'ZIP entries differ: {rel}'
            for name,text in entries.items():
                assert archive.read(name)==text.encode(), f'ZIP bytes differ: {rel}/{name}'
        # These lines come from the real native verifier, checked separately from ZIP readback.
        phase='testing zip' if mode=='zip' else 'testing raw file'
        assert f'{path}: {phase}' in log, f'native test did not run: {rel}'
        assert f'{path}: test passed' in log, f'native test did not pass: {rel}'
    assert not any('Excluded' in str(p) for p in (base/'roms').rglob('*')), 'retained --no-demo filter did not apply'

def placement(base, apply=True):
    args=[sys.executable,str(HERE/'place_extras.py'),str(base/'extras.json'),str(base/'roms')]
    if apply: args.append('--apply')
    r=subprocess.run(args,text=True,capture_output=True,timeout=15)
    assert r.returncode==0, r.stderr
    return json.loads(r.stdout)

def extras(base):
    for item in prepare(base/'extras.json',base/'roms'):
        assert Path(item['target']).is_file(), f'missing extra: {item["target"]}'
        assert Path(item['source']).read_bytes()==Path(item['target']).read_bytes()

def stale(base, label):
    p=base/'roms/gb/Shared Title (USA)'/f'{label}.txt'
    p.write_text('Unlisted stale fixture file to be cleaned.\n')
    return p,p.read_bytes()

def cleaned(base, p, payload):
    assert not p.exists(), f'clean did not remove stale file: {p}'
    assert (base/'clean backup'/p.name).read_bytes()==payload, 'native clean backup bytes differ'

def baseline(base):
    create(base)
    before={key:snapshot(base/key) for key in ('input','dats','extras')}
    log=native(base,'initial')
    archives(base,log)
    return before

def main(directory):
    directory=directory.absolute()
    directory.mkdir(parents=True,exist_ok=False)
    cases={}
    base=directory/'complete workflow with spaces'
    before=baseline(base)
    tree_before=snapshot(base/'roms');dirs_before={str(p.relative_to(base/'roms')) for p in (base/'roms').rglob('*') if p.is_dir()}
    planned=placement(base,False)
    assert len(planned)==16 and snapshot(base/'roms')==tree_before and {str(p.relative_to(base/'roms')) for p in (base/'roms').rglob('*') if p.is_dir()}==dirs_before, 'default plan modified output'
    assert all(x['action']=='copy' for x in placement(base))
    extras(base)
    game_hashes={k:v for k,v in snapshot(base/'roms').items() if k.endswith('.zip')}
    # User-owned content not listed in the manifest also has to survive each clean.
    for parent in {Path(x['target']).parent for x in prepare(base/'extras.json',base/'roms')}:
        (parent/'Existing unlisted note.txt').write_text('Existing owned extra; keep these bytes.\n')
    protected=snapshot(base/'roms')
    for cycle in (1,2):
        p,payload=stale(base,f'stale cycle {cycle}')
        log=native(base,f'repeat {cycle}')
        cleaned(base,p,payload)
        # Igir can select its existing output as input and skip the writer's test.
        # Preserve that optimization; invoke its separate read-only test command.
        check_log=readonly_test(base,f'readonly {cycle}')
        archives(base,check_log,mode='raw');extras(base)
        assert snapshot(base/'roms')==protected, 'repeated clean changed protected content'
        assert all(x['action']=='unchanged' for x in placement(base))
        assert snapshot(base/'roms')==protected
    for key,value in before.items(): assert snapshot(base/key)==value, f'{key} source bytes changed'
    assert {k:v for k,v in snapshot(base/'roms').items() if k.endswith('.zip')}==game_hashes
    cases['complete']={'native_pipeline_runs':3,'native_readonly_tests':2,'archives':3,'zip_entries':4,'mapped_extras':16,'protected_kind_dirs':15,'unlisted_extras':15,'repeat_clean_cycles':2,'source_bytes_preserved':True}
    # Each omitted essential operation must fail its independent acceptance check.
    for omission in ('python','clean','exclusions','zip','copy','test'):
        b=directory/f'omit {omission}'
        if omission in ('zip','copy','test'):
            create(b)
            if omission=='copy':
                log=native(b,'omitted',omit='copy',expect_failure=True)
                assert 'requires the commands copy or move' in log
                assert not (b/'roms').exists()
                cases['omit_copy']={'detected':True,'reason':'native parser rejected zip without copy/move; no output created'}
                continue
            log=native(b,'omitted',omit=omission)
            try: archives(b,log)
            except AssertionError as error: reason=str(error)
            else: raise AssertionError(f'omit {omission} was not detected')
        else:
            baseline(b)
            if omission!='python': placement(b)
            if omission=='python':
                try: extras(b)
                except AssertionError as error: reason=str(error)
                else: raise AssertionError('omitted placement was not detected')
            elif omission=='clean':
                p,payload=stale(b,'stale without clean');native(b,'omitted',omit='clean')
                try: cleaned(b,p,payload)
                except AssertionError as error: reason=str(error)
                else: raise AssertionError('omitted clean was not detected')
            else:
                targets=[Path(x['target']) for x in prepare(b/'extras.json',b/'roms')]
                anchors=[]
                for parent in {p.parent for p in targets}:
                    anchor=parent/'Fixture keep.txt';anchor.write_text('Only a control anchor.\n');anchors.append(anchor)
                native(b,'omitted',protections=False,anchors=anchors)
                assert all(p.is_file() for p in anchors), 'control anchors were not retained'
                assert all(not p.exists() for p in targets), 'extras were not actually cleaned'
                assert all((b/'clean backup'/p.name).is_file() for p in targets)
                # No helper invocation occurs after this native clean.
                try: extras(b)
                except AssertionError as error: reason=str(error)
                else: raise AssertionError('omitted exclusions were not detected')
        cases[f'omit_{omission}']={'detected':True,'reason':reason}
    (directory/'results.json').write_text(json.dumps(cases,indent=2)+'\n')
    print(json.dumps(cases,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('new_directory',type=Path)
    main(p.parse_args().new_directory)

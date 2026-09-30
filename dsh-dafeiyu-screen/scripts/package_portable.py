import argparse,hashlib,json,pathlib,shutil,tarfile,zipfile

p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[1]
out=pathlib.Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
version=json.loads((root/'package.json').read_text(encoding='utf8'))['version']
name=f'DSH-DaFeiYu-Screen-{version}-Windows'
dest=out/name
if dest.exists():
    raise SystemExit(f'Output already exists, choose a new output directory: {dest}')
dest.mkdir()
tgz=out/f'dsh-dafeiyu-screen-{version}.tgz'
with tarfile.open(tgz,'r:gz') as t:
    for m in t.getmembers():
        rel=pathlib.PurePosixPath(m.name)
        if not m.isfile(): continue
        if rel.parts[0]!='package' or '..' in rel.parts: raise ValueError('Unexpected package path')
        target=dest.joinpath(*rel.parts[1:]);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(t.extractfile(m).read())
shutil.copytree(root/'runtime',dest/'runtime')
shutil.copytree(root/'node_modules'/'yaml',dest/'node_modules'/'yaml')
for n in ['启动大肥鱼.cmd','安装到DSH.cmd']: shutil.copy2(root/n,dest/n)
with zipfile.ZipFile(out/(name+'.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for f in dest.rglob('*'):
        if f.is_file():z.write(f,str(f.relative_to(out)))
checks={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [tgz,out/(name+'.zip')]}
(out/'SHA256.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
print(json.dumps({'folder':str(dest),'zip':str(out/(name+'.zip')),'sha256':checks}))

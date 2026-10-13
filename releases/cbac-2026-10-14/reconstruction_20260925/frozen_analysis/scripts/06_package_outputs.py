"""Create a local review archive; excludes expression matrices and never uploads."""
from pathlib import Path
import importlib.metadata
import json
import zipfile
from rebuild_common import sha256,write_json


def main():
    out=Path(__file__).resolve().parents[1]
    checks=json.loads((out/'release_checks.json').read_text(encoding='utf-8'))
    assert checks['status']=='TECHNICAL_CHECKS_PASSED_NOT_SUBMISSION_APPROVAL'
    hashes=json.loads((out/'code_sha256.json').read_text(encoding='utf-8'))
    assert all(sha256(out/'scripts'/name)==digest for name,digest in hashes.items()),'Scripts changed since final technical audit'
    packages=['anndata','scanpy','numpy','scipy','pandas','scikit-learn','threadpoolctl','matplotlib','statsmodels','openpyxl','h5py']
    versions={name:importlib.metadata.version(name) for name in packages}
    write_json(out/'complete_runtime_versions.json',versions)
    (out/'requirements_recorded.txt').write_text(''.join(f'{name}=={version}\n' for name,version in versions.items()),encoding='utf-8')
    files=[path for path in out.iterdir() if path.is_file() and path.suffix in ('.md','.json','.txt') and path.name!='archive_manifest.json']
    for folder in ('scripts','tables','figures','inputs'):
        files.extend(path for path in (out/folder).rglob('*') if path.is_file() and '__pycache__' not in path.parts)
    files=sorted(set(files))
    manifest=[dict(path=str(path.relative_to(out)).replace('\\','/'),bytes=path.stat().st_size,sha256=sha256(path)) for path in files]
    write_json(out/'archive_manifest.json',manifest)
    path=out/'review_outputs.zip'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for file in files+[out/'archive_manifest.json']:
            archive.write(file,str(file.relative_to(out)))
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
    print('LOCAL_ARCHIVE',path,'files',len(files)+1,'bytes',path.stat().st_size,flush=True)


if __name__=='__main__':
    main()

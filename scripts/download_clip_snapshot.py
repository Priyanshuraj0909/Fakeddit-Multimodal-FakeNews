"""Fetch a pinned official CLIP snapshot and convert verified tensor weights safely.

Offline inference still requires local safetensors and never downloads weights.
The large research snapshot remains ignored by Git and excluded from deployment.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

REPO='openai/clip-vit-base-patch32'
REVISION='3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268'
FILES=('config.json','preprocessor_config.json','merges.txt','special_tokens_map.json','tokenizer.json','tokenizer_config.json','vocab.json')


def download(output):
    output=Path(output)
    if output.exists():
        raise ValueError('Choose a new snapshot directory')
    output.mkdir(parents=True)
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true',timeout=30) as response:
        metadata=json.load(response)
    if metadata['sha'] != REVISION:
        raise ValueError('Unexpected repository revision')
    weights=next(item for item in metadata['siblings'] if item['rfilename']=='pytorch_model.bin')
    expected=weights['lfs']['sha256']
    for filename in FILES:
        with urllib.request.urlopen(f'https://huggingface.co/{REPO}/resolve/{REVISION}/{filename}',timeout=60) as response:
            (output/filename).write_bytes(response.read(10*1024*1024))
    source=output/'pytorch_model.bin.partial'
    digest=hashlib.sha256()
    with urllib.request.urlopen(f'https://huggingface.co/{REPO}/resolve/{REVISION}/pytorch_model.bin?download=true',timeout=60) as response, source.open('wb') as stream:
        count=0
        while chunk:=response.read(1024*1024):
            stream.write(chunk); digest.update(chunk); count+=len(chunk)
            if count % (50*1024*1024)==0:
                print(json.dumps({'downloaded_bytes':count}),flush=True)
    if digest.hexdigest()!=expected or source.stat().st_size!=weights['lfs']['size']:
        raise ValueError('Official weight size/hash mismatch')
    import torch
    from safetensors.torch import save_file
    tensors=torch.load(source,map_location='cpu',weights_only=True)
    if not isinstance(tensors,dict) or not all(isinstance(value,torch.Tensor) for value in tensors.values()):
        raise ValueError('Expected only tensor state dictionary')
    save_file({name:value.contiguous() for name,value in tensors.items()},str(output/'model.safetensors'),metadata={'format':'pt'})
    source.unlink()
    report={'downloaded_at':datetime.now(timezone.utc).isoformat(),'repository':REPO,'revision':REVISION,
            'official_pytorch_sha256':expected,'conversion':'Verified official LFS SHA256, torch.load(weights_only=True), safetensors save_file; no unrestricted pickle loading',
            'safetensors_sha256':hashlib.sha256((output/'model.safetensors').read_bytes()).hexdigest()}
    (output/'download-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    download(parser.parse_args().output)

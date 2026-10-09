"""Read-only wider dataset header/label/hash inventory; no training or copying."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from astrotrace.datasets.inventory import inventory_datasets

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(args.output)
    result=inventory_datasets(ROOT)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
    for source in result['sources']:
        print(json.dumps({k: source.get(k) for k in ('source','status','images','dimensions','modes')},allow_nan=False),flush=True)
    print('Cross-source/split duplicate groups:',len(result['cross_source_or_split_encoded_duplicates']))
    return 0
if __name__=='__main__':
    raise SystemExit(main())

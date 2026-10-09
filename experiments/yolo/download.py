"""Explicit bounded official artifact download; never fetch scientific datasets.

Range download supports the official large CUDA wheel when full requests stall.
Caller supplies expected SHA-256 from the publisher's simple index and byte size.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
import urllib.request

from .common import sha256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--bytes",type=int,required=True)
    parser.add_argument("--sha256",required=True)
    parser.add_argument("--timeout-s",type=int,default=420)
    parser.add_argument("--resume-partial",action="store_true",help="Reuse populated ranges from an interrupted download; final SHA-256 still required")
    args=parser.parse_args()
    if not args.url.startswith("https://download.pytorch.org/whl/") or not 0<args.bytes<4_000_000_000:
        raise ValueError("Only explicitly sized official PyTorch wheels supported")
    if args.output.exists():
        raise ValueError("Refusing to overwrite download")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    chunk=16*1024*1024
    start=time.monotonic()
    temporary=args.output.with_suffix(".partial")
    offsets=list(range(0,args.bytes,chunk))
    if args.resume_partial:
        if not temporary.is_file() or temporary.stat().st_size!=args.bytes:
            raise ValueError("Partial size differs from declared artifact size")
        missing=[]
        with temporary.open("rb") as stream:
            for offset in offsets:
                stream.seek(offset)
                payload=stream.read(min(chunk,args.bytes-offset))
                if not any(payload):missing.append(offset)
        offsets=missing
        print("Resume ranges remaining:",len(offsets),flush=True)
    else:
        with temporary.open("xb") as stream:
            stream.truncate(args.bytes)

    def fetch(offset):
        length=min(chunk,args.bytes-offset)
        if time.monotonic()-start>args.timeout_s:
            raise TimeoutError("Artifact download time budget exhausted")
        request=urllib.request.Request(args.url,headers={"Range":f"bytes={offset}-{offset+length-1}"})
        with urllib.request.urlopen(request,timeout=30) as response:
            if response.status!=206 or response.headers.get("Content-Range")!=f"bytes {offset}-{offset+length-1}/{args.bytes}":
                raise ValueError("Server did not honor the requested range")
            payload=response.read(length+1)
        if len(payload)!=length:
            raise ValueError("Truncated range response")
        with temporary.open("r+b") as stream:
            stream.seek(offset);stream.write(payload)
        return length

    done=0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for length in pool.map(fetch,offsets):
            done+=length
            if done%(10*chunk)==0 or done==args.bytes:
                print(f"Downloaded {done}/{args.bytes} bytes in {time.monotonic()-start:.1f}s",flush=True)
    if sha256(temporary)!=args.sha256:
        raise ValueError("Published SHA-256 mismatch; artifact will not be installed")
    temporary.rename(args.output)
    print("Verified",args.output,flush=True)


if __name__ == "__main__":
    main()

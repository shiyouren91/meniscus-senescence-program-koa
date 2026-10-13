"""Download version-1 public HRA processed files with size and MD5 checks."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import urllib.request

API = "https://api.figshare.com/v2/articles/26240492/versions/1"
EXPECTED = {
    "meniscal_chondrocyte.h5ad": (234779038, "e9319f4dcd333e53a1ace9b9b58046d8"),
    "meniscal_endo.h5ad": (44393051, "d6839d4f857625873032778ad57c7d87"),
    "meniscal_immune.h5ad": (33094415, "eaa357795a7eca228e5aeb0d98632274"),
}


def check(path, size, md5):
    if not path.is_file() or path.stat().st_size != size:
        return False
    h = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest() == md5


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--all-files", action="store_true",
                        help="Also download endothelial and immune files, not used in program discovery.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(API, timeout=60) as response:
        metadata = json.load(response)
    assert metadata["doi"] == "10.6084/m9.figshare.26240492.v1"
    for item in metadata["files"]:
        name = item["name"]
        if name not in EXPECTED or (not args.all_files and name != "meniscal_chondrocyte.h5ad"):
            continue
        size, md5 = EXPECTED[name]
        assert (item["size"], item["computed_md5"]) == (size, md5)
        destination = args.output / name
        if check(destination, size, md5):
            print("VERIFIED", name)
            continue
        if destination.exists():
            raise FileExistsError("Existing file failed checks; preserve and inspect it: " + str(destination))
        temporary = destination.with_suffix(destination.suffix + ".part")
        if temporary.exists():
            raise FileExistsError("Preserve or remove an earlier partial download first: " + str(temporary))
        with urllib.request.urlopen(item["download_url"], timeout=120) as response, temporary.open("xb") as stream:
            for block in iter(lambda: response.read(1024 * 1024), b""):
                stream.write(block)
        if not check(temporary, size, md5):
            raise ValueError("Downloaded content failed checks: " + str(temporary))
        os.replace(temporary, destination)
        print("DOWNLOADED AND VERIFIED", name)
    print("Source licence: CC BY 4.0. Cite Chen and Fu (2024) and the source eLife study.")


if __name__ == "__main__":
    main()

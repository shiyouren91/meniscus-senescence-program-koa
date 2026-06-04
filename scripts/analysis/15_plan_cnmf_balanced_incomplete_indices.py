#!/usr/bin/env python
"""Plan exact cNMF run-index chunks for incomplete balanced discovery runs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from cnmf import cNMF, load_df_from_npz


def chunks(values: list[int], chunk_size: int) -> list[list[int]]:
    return [values[start : start + chunk_size] for start in range(0, len(values), chunk_size)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--chunks-dir", required=True)
    parser.add_argument("--manifest-output", required=True)
    parser.add_argument("--chunk-size", type=int, default=5)
    parser.add_argument("--max-chunks", type=int, default=0)
    args = parser.parse_args()

    if args.chunk_size < 1:
        raise ValueError("chunk-size must be >= 1")

    cnmf_obj = cNMF(output_dir=args.output_dir, name=args.run_name)
    run_params = load_df_from_npz(cnmf_obj.paths["nmf_replicate_parameters"])

    incomplete: list[int] = []
    rows = []
    for idx, row in run_params.iterrows():
        k = int(row["n_components"])
        iteration = int(row["iter"])
        spectra_path = Path(cnmf_obj.paths["iter_spectra"] % (k, iteration))
        exists = spectra_path.exists()
        rows.append(
            {
                "run_index": int(idx),
                "k": k,
                "iter": iteration,
                "spectra_exists": bool(exists),
                "spectra_path": str(spectra_path),
            }
        )
        if not exists:
            incomplete.append(int(idx))

    planned_chunks = chunks(incomplete, args.chunk_size)
    if args.max_chunks > 0:
        planned_chunks = planned_chunks[: args.max_chunks]

    chunks_dir = Path(args.chunks_dir)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    for chunk_id, chunk_indices in enumerate(planned_chunks, start=1):
        chunk_path = chunks_dir / f"chunk_{chunk_id:05d}.txt"
        chunk_path.write_text("\n".join(map(str, chunk_indices)) + "\n", encoding="utf-8")
        chunk_meta = pd.DataFrame(rows).set_index("run_index").loc[chunk_indices].reset_index()
        manifest_rows.append(
            {
                "chunk_id": chunk_id,
                "chunk_path": str(chunk_path),
                "n_runs": len(chunk_indices),
                "first_run_index": min(chunk_indices),
                "last_run_index": max(chunk_indices),
                "k_values": ",".join(map(str, sorted(chunk_meta["k"].unique()))),
                "iter_values": ",".join(map(str, sorted(chunk_meta["iter"].unique()))),
            }
        )

    manifest = pd.DataFrame(manifest_rows)
    manifest_output = Path(args.manifest_output)
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(manifest_output, sep="\t", index=False)

    all_runs = pd.DataFrame(rows)
    all_runs.to_csv(manifest_output.with_suffix(".all_runs.tsv"), sep="\t", index=False)

    print(f"TOTAL_RUNS {run_params.shape[0]}")
    print(f"INCOMPLETE_RUNS {len(incomplete)}")
    print(f"PLANNED_CHUNKS {manifest.shape[0]}")
    print(f"CHUNK_SIZE {args.chunk_size}")
    print(f"WROTE {manifest_output}")
    print(f"WROTE {chunks_dir}")


if __name__ == "__main__":
    main()

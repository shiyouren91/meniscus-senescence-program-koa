#!/usr/bin/env python
"""Run a small sample-balanced cNMF pilot for GSE220243 fibrochondrocytes."""

from __future__ import annotations

import argparse
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
from cnmf import cNMF, load_df_from_npz


RUN_NAME = "gse220243_fibro_balanced_pilot"


def parse_components(value: str) -> list[int]:
    components = sorted({int(token.strip()) for token in value.split(",") if token.strip()})
    if not components:
        raise ValueError("At least one K value is required")
    if min(components) < 2:
        raise ValueError(f"All K values must be >= 2, got {components}")
    return components


def density_label(value: float) -> str:
    return str(value).replace(".", "_")


def load_selected_genes(path: Path, available_genes: pd.Index) -> list[str]:
    table = pd.read_csv(path, sep="\t")
    if "gene" not in table.columns:
        raise ValueError(f"Selected gene table is missing a gene column: {path}")
    available = set(available_genes.astype(str))
    genes = []
    for gene in table["gene"].astype(str):
        if gene in available and gene not in genes:
            genes.append(gene)
    if len(genes) < 500:
        raise ValueError(f"Too few selected genes overlap the h5ad matrix: {len(genes)}")
    return genes


def stratified_pilot_subset(adata: ad.AnnData, max_cells_per_sample: int, seed: int) -> tuple[ad.AnnData, pd.DataFrame]:
    if "sample_label" not in adata.obs:
        raise ValueError("Input h5ad is missing obs['sample_label']")
    rng = np.random.default_rng(seed)
    chosen_indices = []
    rows = []
    sample_values = adata.obs["sample_label"].astype(str)
    for sample in sorted(sample_values.unique()):
        indices = np.flatnonzero(sample_values.to_numpy() == sample)
        selected_n = len(indices) if max_cells_per_sample <= 0 else min(len(indices), max_cells_per_sample)
        selected = rng.choice(indices, size=selected_n, replace=False)
        selected.sort()
        chosen_indices.append(selected)
        disease = ""
        if "disease_status" in adata.obs:
            disease_counts = adata.obs.iloc[indices]["disease_status"].astype(str).value_counts()
            disease = str(disease_counts.index[0])
        rows.append(
            {
                "sample_label": sample,
                "disease_status": disease,
                "available_cells": int(len(indices)),
                "selected_cells": int(selected_n),
                "selection_fraction": float(selected_n / len(indices)),
            }
        )
    selected_indices = np.concatenate(chosen_indices)
    selected_indices.sort()
    subset = adata[selected_indices, :].copy()
    subset.obs["cnmf_pilot_selected"] = True
    return subset, pd.DataFrame(rows)


def filter_zero_count_genes(adata: ad.AnnData, genes: list[str]) -> tuple[ad.AnnData, list[str], list[str]]:
    column_sums = np.asarray(adata.X.sum(axis=0)).ravel()
    keep_mask = column_sums > 0
    kept_genes = list(adata.var_names[keep_mask].astype(str))
    dropped_genes = list(adata.var_names[~keep_mask].astype(str))
    ordered_kept = [gene for gene in genes if gene in set(kept_genes)]
    if len(ordered_kept) < 500:
        raise ValueError(f"Too few nonzero genes remain after pilot sampling: {len(ordered_kept)}")
    return adata[:, ordered_kept].copy(), ordered_kept, dropped_genes


def write_gene_file(path: Path, genes: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(genes) + "\n", encoding="utf-8")


def write_config(path: Path, rows: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [{"parameter": key, "value": value} for key, value in rows.items()]
    ).to_csv(path, sep="\t", index=False)


def stats_for_k(stats: pd.DataFrame, k: int) -> dict[str, float]:
    if stats.empty or "k" not in stats.columns:
        return {"silhouette": np.nan, "prediction_error": np.nan}
    match = stats.loc[stats["k"].astype(int) == int(k)]
    if match.empty:
        return {"silhouette": np.nan, "prediction_error": np.nan}
    row = match.iloc[0]
    return {
        "silhouette": float(row.get("silhouette", np.nan)),
        "prediction_error": float(row.get("prediction_error", np.nan)),
    }


def flatten_top_genes(top_genes: pd.DataFrame, k: int) -> pd.DataFrame:
    rows = []
    for program in top_genes.columns:
        for rank, gene in enumerate(top_genes[program].astype(str), start=1):
            rows.append({"k": int(k), "program": str(program), "rank": int(rank), "gene": gene})
    return pd.DataFrame(rows)


def summarize_usage(usage: pd.DataFrame, obs: pd.DataFrame, k: int) -> pd.DataFrame:
    aligned_obs = obs.loc[usage.index]
    rows = []
    for program in usage.columns:
        values = usage[program].astype(float)
        sample_totals = values.groupby(aligned_obs["sample_label"].astype(str)).sum()
        disease_totals = values.groupby(aligned_obs["disease_status"].astype(str)).sum()
        sample_means = values.groupby(aligned_obs["sample_label"].astype(str)).mean()
        total_usage = float(values.sum())
        dominant_sample = str(sample_totals.idxmax())
        dominant_disease = str(disease_totals.idxmax())
        rows.append(
            {
                "k": int(k),
                "program": str(program),
                "mean_usage": float(values.mean()),
                "median_usage": float(values.median()),
                "q95_usage": float(values.quantile(0.95)),
                "dominant_sample": dominant_sample,
                "dominant_sample_fraction": float(sample_totals.max() / total_usage) if total_usage > 0 else np.nan,
                "dominant_disease_status": dominant_disease,
                "dominant_disease_fraction": float(disease_totals.max() / total_usage) if total_usage > 0 else np.nan,
                "n_samples_detected": int((sample_means > 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def run_cnmf(
    pilot_h5ad: Path,
    output_dir: Path,
    genes_file: Path,
    components: list[int],
    n_iter: int,
    seed: int,
    max_nmf_iter: int,
    beta_loss: str,
) -> cNMF:
    cnmf_obj = cNMF(output_dir=str(output_dir), name=RUN_NAME)
    cnmf_obj.prepare(
        counts_fn=str(pilot_h5ad),
        components=components,
        n_iter=n_iter,
        seed=seed,
        beta_loss=beta_loss,
        num_highvar_genes=None,
        genes_file=str(genes_file),
        max_NMF_iter=max_nmf_iter,
    )
    cnmf_obj.factorize(worker_i=0, total_workers=1, skip_completed_runs=False)
    cnmf_obj.combine(components=components, skip_missing_files=False)
    cnmf_obj.k_selection_plot(close_fig=True)
    return cnmf_obj


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--balanced-h5ad", required=True)
    parser.add_argument("--selected-genes-input", required=True)
    parser.add_argument("--pilot-h5ad-output", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--config-output", required=True)
    parser.add_argument("--status-output", required=True)
    parser.add_argument("--top-genes-output", required=True)
    parser.add_argument("--usage-summary-output", required=True)
    parser.add_argument("--components", default="5,8")
    parser.add_argument("--n-iter", type=int, default=5)
    parser.add_argument("--max-cells-per-sample", type=int, default=350)
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument("--max-nmf-iter", type=int, default=450)
    parser.add_argument("--density-threshold", type=float, default=0.5)
    parser.add_argument("--beta-loss", default="frobenius")
    args = parser.parse_args()

    balanced_h5ad = Path(args.balanced_h5ad)
    selected_genes_input = Path(args.selected_genes_input)
    pilot_h5ad_output = Path(args.pilot_h5ad_output)
    output_dir = Path(args.output_dir)
    config_output = Path(args.config_output)
    status_output = Path(args.status_output)
    top_genes_output = Path(args.top_genes_output)
    usage_summary_output = Path(args.usage_summary_output)
    components = parse_components(args.components)

    if args.n_iter < 5:
        raise ValueError("Use n_iter >= 5 so cNMF consensus has at least one local-density neighbor")

    balanced = ad.read_h5ad(balanced_h5ad)
    required_obs = {"sample_label", "disease_status", "fibro_leiden", "draft_annotation"}
    missing_obs = required_obs.difference(balanced.obs.columns)
    if missing_obs:
        raise ValueError(f"Balanced h5ad is missing obs columns: {sorted(missing_obs)}")

    selected_genes = load_selected_genes(selected_genes_input, balanced.var_names)
    balanced = balanced[:, selected_genes].copy()
    pilot, sampling = stratified_pilot_subset(balanced, args.max_cells_per_sample, args.seed)
    pilot, selected_genes, dropped_zero_count_genes = filter_zero_count_genes(pilot, selected_genes)
    pilot_h5ad_output.parent.mkdir(parents=True, exist_ok=True)
    pilot.write_h5ad(pilot_h5ad_output, compression="gzip")

    output_dir.mkdir(parents=True, exist_ok=True)
    genes_file = output_dir / f"{RUN_NAME}_genes.txt"
    sampling_output = output_dir / f"{RUN_NAME}_sampling_summary.tsv"
    write_gene_file(genes_file, selected_genes)
    sampling.to_csv(sampling_output, sep="\t", index=False)

    config_rows = {
        "balanced_h5ad": str(balanced_h5ad),
        "selected_genes_input": str(selected_genes_input),
        "pilot_h5ad": str(pilot_h5ad_output),
        "output_dir": str(output_dir),
        "run_name": RUN_NAME,
        "components": ",".join(map(str, components)),
        "n_iter": int(args.n_iter),
        "max_cells_per_sample": int(args.max_cells_per_sample),
        "selected_cells": int(pilot.n_obs),
        "selected_genes": int(pilot.n_vars),
        "dropped_zero_count_genes": int(len(dropped_zero_count_genes)),
        "dropped_zero_count_gene_names": ",".join(dropped_zero_count_genes),
        "seed": int(args.seed),
        "max_nmf_iter": int(args.max_nmf_iter),
        "density_threshold": float(args.density_threshold),
        "beta_loss": args.beta_loss,
        "genes_file": str(genes_file),
        "sampling_summary": str(sampling_output),
    }
    write_config(config_output, config_rows)

    cnmf_obj = run_cnmf(
        pilot_h5ad=pilot_h5ad_output,
        output_dir=output_dir,
        genes_file=genes_file,
        components=components,
        n_iter=args.n_iter,
        seed=args.seed,
        max_nmf_iter=args.max_nmf_iter,
        beta_loss=args.beta_loss,
    )

    stats = load_df_from_npz(cnmf_obj.paths["k_selection_stats"])
    status_rows = []
    top_gene_tables = []
    usage_tables = []
    for k in components:
        k_stats = stats_for_k(stats, k)
        try:
            cnmf_obj.consensus(
                k,
                density_threshold=args.density_threshold,
                show_clustering=False,
                close_clustergram_fig=True,
            )
            usage, _spectra_scores, _spectra_tpm, top_genes = cnmf_obj.load_results(
                k,
                args.density_threshold,
                n_top_genes=100,
                norm_usage=True,
            )
            top_gene_tables.append(flatten_top_genes(top_genes, k))
            usage_tables.append(summarize_usage(usage, pilot.obs, k))
            status_rows.append(
                {
                    "k": int(k),
                    "status": "ok",
                    "message": "",
                    "n_programs": int(k),
                    "n_iter": int(args.n_iter),
                    "density_threshold": float(args.density_threshold),
                    "silhouette": k_stats["silhouette"],
                    "prediction_error": k_stats["prediction_error"],
                }
            )
        except Exception as exc:
            status_rows.append(
                {
                    "k": int(k),
                    "status": "failed",
                    "message": str(exc),
                    "n_programs": int(k),
                    "n_iter": int(args.n_iter),
                    "density_threshold": float(args.density_threshold),
                    "silhouette": k_stats["silhouette"],
                    "prediction_error": k_stats["prediction_error"],
                }
            )

    status_output.parent.mkdir(parents=True, exist_ok=True)
    top_genes_output.parent.mkdir(parents=True, exist_ok=True)
    usage_summary_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(status_rows).to_csv(status_output, sep="\t", index=False)
    if top_gene_tables:
        pd.concat(top_gene_tables, ignore_index=True).to_csv(top_genes_output, sep="\t", index=False)
    else:
        pd.DataFrame(columns=["k", "program", "rank", "gene"]).to_csv(top_genes_output, sep="\t", index=False)
    if usage_tables:
        pd.concat(usage_tables, ignore_index=True).to_csv(usage_summary_output, sep="\t", index=False)
    else:
        pd.DataFrame(
            columns=[
                "k",
                "program",
                "mean_usage",
                "median_usage",
                "q95_usage",
                "dominant_sample",
                "dominant_sample_fraction",
                "dominant_disease_status",
                "dominant_disease_fraction",
                "n_samples_detected",
            ]
        ).to_csv(usage_summary_output, sep="\t", index=False)

    failed = [row for row in status_rows if row["status"] != "ok"]
    print(f"PILOT_CELLS {pilot.n_obs}")
    print(f"PILOT_GENES {pilot.n_vars}")
    print(f"COMPONENTS {','.join(map(str, components))}")
    print(f"N_ITER {args.n_iter}")
    print(f"DENSITY_THRESHOLD {args.density_threshold}")
    print(f"FAILED_K {len(failed)}")
    print(f"WROTE {pilot_h5ad_output}")
    print(f"WROTE {config_output}")
    print(f"WROTE {status_output}")
    print(f"WROTE {top_genes_output}")
    print(f"WROTE {usage_summary_output}")
    print(f"WROTE {output_dir / RUN_NAME}")
    if failed:
        raise RuntimeError(f"cNMF consensus failed for K values: {[row['k'] for row in failed]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Run resumable balanced cNMF discovery for GSE220243 fibrochondrocytes."""

from __future__ import annotations

import argparse
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import scanpy as sc
import yaml
from cnmf import cNMF, load_df_from_npz, save_df_to_npz


DEFAULT_RUN_NAME = "gse220243_fibro_balanced_discovery"


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


def sample_balanced_subset(
    adata: ad.AnnData,
    max_cells_per_sample: int,
    seed: int,
) -> tuple[ad.AnnData, pd.DataFrame]:
    if "sample_label" not in adata.obs:
        raise ValueError("Input h5ad is missing obs['sample_label']")
    rng = np.random.default_rng(seed)
    chosen_indices = []
    rows = []
    sample_values = adata.obs["sample_label"].astype(str)
    for sample in sorted(sample_values.unique()):
        indices = np.flatnonzero(sample_values.to_numpy() == sample)
        selected_n = len(indices) if max_cells_per_sample <= 0 else min(len(indices), max_cells_per_sample)
        selected = indices if selected_n == len(indices) else rng.choice(indices, size=selected_n, replace=False)
        selected = np.asarray(selected)
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
    subset.obs["cnmf_balanced_discovery_selected"] = True
    return subset, pd.DataFrame(rows)


def filter_zero_count_genes(adata: ad.AnnData, genes: list[str]) -> tuple[ad.AnnData, list[str], list[str]]:
    column_sums = np.asarray(adata.X.sum(axis=0)).ravel()
    keep_mask = column_sums > 0
    kept_set = set(adata.var_names[keep_mask].astype(str))
    dropped_genes = list(adata.var_names[~keep_mask].astype(str))
    ordered_kept = [gene for gene in genes if gene in kept_set]
    if len(ordered_kept) < 500:
        raise ValueError(f"Too few nonzero genes remain after sampling: {len(ordered_kept)}")
    return adata[:, ordered_kept].copy(), ordered_kept, dropped_genes


def write_gene_file(path: Path, genes: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(genes) + "\n", encoding="utf-8")


def write_config(path: Path, rows: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"parameter": key, "value": value} for key, value in rows.items()]).to_csv(path, sep="\t", index=False)


def make_cnmf(output_dir: Path, run_name: str) -> cNMF:
    return cNMF(output_dir=str(output_dir), name=run_name)


def prepared_paths(output_dir: Path, run_name: str) -> dict[str, Path]:
    cnmf_obj = make_cnmf(output_dir, run_name)
    return {key: Path(value) if "%" not in value else Path(value.split("%")[0]).parent for key, value in cnmf_obj.paths.items()}


def prepare_discovery(args: argparse.Namespace, components: list[int]) -> cNMF:
    output_dir = Path(args.output_dir)
    run_name = args.run_name
    cnmf_obj = make_cnmf(output_dir, run_name)
    params_file = Path(cnmf_obj.paths["nmf_replicate_parameters"])
    if params_file.exists() and not args.force_prepare:
        raise FileExistsError(
            f"Existing cNMF prepared run found: {params_file}. "
            "Use --force-prepare only for deliberate smoke tests or reruns."
        )

    balanced = ad.read_h5ad(args.balanced_h5ad)
    required_obs = {"sample_label", "disease_status", "fibro_leiden", "draft_annotation"}
    missing_obs = required_obs.difference(balanced.obs.columns)
    if missing_obs:
        raise ValueError(f"Balanced h5ad is missing obs columns: {sorted(missing_obs)}")

    selected_genes = load_selected_genes(Path(args.selected_genes_input), balanced.var_names)
    balanced = balanced[:, selected_genes].copy()
    discovery, sampling = sample_balanced_subset(balanced, args.max_cells_per_sample, args.seed)
    discovery, selected_genes, dropped_zero_count_genes = filter_zero_count_genes(discovery, selected_genes)

    discovery_h5ad = Path(args.discovery_h5ad_output)
    discovery_h5ad.parent.mkdir(parents=True, exist_ok=True)
    discovery.write_h5ad(discovery_h5ad, compression="gzip")

    output_dir.mkdir(parents=True, exist_ok=True)
    genes_file = output_dir / f"{run_name}_genes.txt"
    sampling_output = output_dir / f"{run_name}_sampling_summary.tsv"
    write_gene_file(genes_file, selected_genes)
    sampling.to_csv(sampling_output, sep="\t", index=False)

    config_rows = {
        "balanced_h5ad": str(args.balanced_h5ad),
        "selected_genes_input": str(args.selected_genes_input),
        "discovery_h5ad": str(discovery_h5ad),
        "output_dir": str(output_dir),
        "run_name": run_name,
        "components": ",".join(map(str, components)),
        "n_iter": int(args.n_iter),
        "expected_nmf_runs": int(len(components) * args.n_iter),
        "max_cells_per_sample": int(args.max_cells_per_sample),
        "selected_cells": int(discovery.n_obs),
        "selected_genes": int(discovery.n_vars),
        "dropped_zero_count_genes": int(len(dropped_zero_count_genes)),
        "dropped_zero_count_gene_names": ",".join(dropped_zero_count_genes),
        "seed": int(args.seed),
        "max_nmf_iter": int(args.max_nmf_iter),
        "density_threshold": float(args.density_threshold),
        "beta_loss": args.beta_loss,
        "genes_file": str(genes_file),
        "sampling_summary": str(sampling_output),
    }
    write_config(Path(args.config_output), config_rows)

    cnmf_obj.prepare(
        counts_fn=str(discovery_h5ad),
        components=components,
        n_iter=args.n_iter,
        seed=args.seed,
        beta_loss=args.beta_loss,
        num_highvar_genes=None,
        genes_file=str(genes_file),
        max_NMF_iter=args.max_nmf_iter,
    )
    print(f"PREPARED_CELLS {discovery.n_obs}")
    print(f"PREPARED_GENES {discovery.n_vars}")
    print(f"EXPECTED_NMF_RUNS {len(components) * args.n_iter}")
    print(f"DROPPED_ZERO_COUNT_GENES {len(dropped_zero_count_genes)}")
    return cnmf_obj


def factorize_discovery(cnmf_obj: cNMF, args: argparse.Namespace) -> None:
    if args.run_index_file or args.run_indices:
        factorize_exact_indices(cnmf_obj, args)
        return
    if args.skip_completed_runs:
        cnmf_obj.update_nmf_iter_params()
    cnmf_obj.factorize(
        worker_i=args.worker_i,
        total_workers=args.total_workers,
        skip_completed_runs=args.skip_completed_runs,
    )


def parse_run_indices(args: argparse.Namespace) -> list[int]:
    indices: list[int] = []
    if args.run_indices:
        indices.extend(int(token.strip()) for token in args.run_indices.split(",") if token.strip())
    if args.run_index_file:
        path = Path(args.run_index_file)
        if not path.exists():
            raise FileNotFoundError(f"Run-index file not found: {path}")
        for line in path.read_text(encoding="utf-8").splitlines():
            token = line.strip()
            if token and not token.startswith("#"):
                indices.append(int(token))
    indices = sorted(set(indices))
    if not indices:
        raise ValueError("No run indices were provided for exact factorization")
    return indices


def factorize_exact_indices(cnmf_obj: cNMF, args: argparse.Namespace) -> None:
    run_indices = parse_run_indices(args)
    run_params = load_df_from_npz(cnmf_obj.paths["nmf_replicate_parameters"])
    missing_indices = [idx for idx in run_indices if idx not in run_params.index]
    if missing_indices:
        raise ValueError(f"Run indices are absent from cNMF params: {missing_indices[:10]}")

    norm_counts = sc.read(cnmf_obj.paths["normalized_counts"])
    nmf_kwargs_base = yaml.load(open(cnmf_obj.paths["nmf_run_parameters"]), Loader=yaml.FullLoader)

    completed = 0
    skipped = 0
    for idx in run_indices:
        p = run_params.loc[idx, :]
        k = int(p["n_components"])
        iteration = int(p["iter"])
        output = Path(cnmf_obj.paths["iter_spectra"] % (k, iteration))
        if args.skip_existing_index_files and output.exists():
            skipped += 1
            print(f"EXACT_SKIP idx={idx} k={k} iter={iteration}")
            continue

        nmf_kwargs = dict(nmf_kwargs_base)
        nmf_kwargs["random_state"] = int(p["nmf_seed"])
        nmf_kwargs["n_components"] = k
        print(f"EXACT_START idx={idx} k={k} iter={iteration}")
        spectra, _usages = cnmf_obj._nmf(norm_counts.X, nmf_kwargs)
        spectra = pd.DataFrame(spectra, index=np.arange(1, k + 1), columns=norm_counts.var.index)
        save_df_to_npz(spectra, str(output))
        completed += 1
        print(f"EXACT_DONE idx={idx} k={k} iter={iteration}")

    print(f"EXACT_FACTORIZE_COMPLETED {completed}")
    print(f"EXACT_FACTORIZE_SKIPPED {skipped}")


def combine_discovery(cnmf_obj: cNMF, components: list[int], args: argparse.Namespace) -> None:
    cnmf_obj.update_nmf_iter_params()
    cnmf_obj.combine(components=components, skip_missing_files=args.skip_missing)


def k_selection_discovery(cnmf_obj: cNMF) -> None:
    cnmf_obj.k_selection_plot(close_fig=True)


def consensus_discovery(cnmf_obj: cNMF, components: list[int], args: argparse.Namespace) -> None:
    failed = []
    for k in components:
        try:
            cnmf_obj.consensus(
                k,
                density_threshold=args.density_threshold,
                show_clustering=False,
                close_clustergram_fig=True,
            )
        except Exception as exc:
            failed.append((k, str(exc)))
    if failed:
        messages = "; ".join([f"K={k}: {message}" for k, message in failed])
        raise RuntimeError(f"Consensus failed for {len(failed)} K values: {messages}")


def load_k_selection_stats(cnmf_obj: cNMF) -> pd.DataFrame:
    path = Path(cnmf_obj.paths["k_selection_stats"])
    if not path.exists():
        return pd.DataFrame(columns=["k", "local_density_threshold", "silhouette", "prediction_error"])
    return load_df_from_npz(str(path))


def expected_completed_by_k(cnmf_obj: cNMF, components: list[int]) -> pd.DataFrame:
    params_path = Path(cnmf_obj.paths["nmf_replicate_parameters"])
    if not params_path.exists():
        return pd.DataFrame(
            [{"k": k, "expected_runs": 0, "completed_runs": 0} for k in components]
        )
    cnmf_obj.update_nmf_iter_params()
    params = load_df_from_npz(str(params_path))
    rows = []
    for k in components:
        subset = params.loc[params["n_components"].astype(int) == int(k)]
        rows.append(
            {
                "k": int(k),
                "expected_runs": int(subset.shape[0]),
                "completed_runs": int(subset["completed"].astype(bool).sum()) if "completed" in subset.columns else 0,
            }
        )
    return pd.DataFrame(rows)


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
        rows.append(
            {
                "k": int(k),
                "program": str(program),
                "mean_usage": float(values.mean()),
                "median_usage": float(values.median()),
                "q95_usage": float(values.quantile(0.95)),
                "dominant_sample": str(sample_totals.idxmax()),
                "dominant_sample_fraction": float(sample_totals.max() / total_usage) if total_usage > 0 else np.nan,
                "dominant_disease_status": str(disease_totals.idxmax()),
                "dominant_disease_fraction": float(disease_totals.max() / total_usage) if total_usage > 0 else np.nan,
                "n_samples_detected": int((sample_means > 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_discovery(cnmf_obj: cNMF, components: list[int], args: argparse.Namespace) -> pd.DataFrame:
    stats = load_k_selection_stats(cnmf_obj)
    if not stats.empty:
        Path(args.k_selection_stats_output).parent.mkdir(parents=True, exist_ok=True)
        stats.to_csv(args.k_selection_stats_output, sep="\t", index=False)
    else:
        pd.DataFrame(columns=["k", "local_density_threshold", "silhouette", "prediction_error"]).to_csv(
            args.k_selection_stats_output, sep="\t", index=False
        )

    try:
        obs = ad.read_h5ad(args.discovery_h5ad_output, backed="r").obs.copy()
    except Exception:
        obs = pd.DataFrame()

    expected_completed = expected_completed_by_k(cnmf_obj, components)
    top_gene_tables = []
    usage_tables = []
    status_rows = []
    dt = density_label(args.density_threshold)

    for k in components:
        row = expected_completed.loc[expected_completed["k"].astype(int) == int(k)].iloc[0].to_dict()
        merged_exists = Path(cnmf_obj.paths["merged_spectra"] % k).exists()
        consensus_usage_exists = Path(cnmf_obj.paths["consensus_usages__txt"] % (k, dt)).exists()
        gene_score_exists = Path(cnmf_obj.paths["gene_spectra_score__txt"] % (k, dt)).exists()
        gene_tpm_exists = Path(cnmf_obj.paths["gene_spectra_tpm__txt"] % (k, dt)).exists()
        stat_match = stats.loc[stats["k"].astype(int) == int(k)] if "k" in stats.columns else pd.DataFrame()
        if not stat_match.empty:
            stat_row = stat_match.iloc[0]
            silhouette = float(stat_row.get("silhouette", np.nan))
            prediction_error = float(stat_row.get("prediction_error", np.nan))
        else:
            silhouette = np.nan
            prediction_error = np.nan

        usage_has_nan = False
        if consensus_usage_exists and gene_score_exists and not obs.empty:
            usage, _spectra_scores, _spectra_tpm, top_genes = cnmf_obj.load_results(
                k,
                args.density_threshold,
                n_top_genes=args.top_n_genes,
                norm_usage=True,
            )
            usage_has_nan = bool(usage.isna().to_numpy().any())
            top_gene_tables.append(flatten_top_genes(top_genes, k))
            usage_tables.append(summarize_usage(usage, obs, k))

        status_rows.append(
            {
                "k": int(k),
                "expected_runs": int(row["expected_runs"]),
                "completed_runs": int(row["completed_runs"]),
                "merged_spectra_exists": bool(merged_exists),
                "k_selection_stats_exists": bool(not stat_match.empty),
                "consensus_usage_exists": bool(consensus_usage_exists),
                "gene_spectra_score_exists": bool(gene_score_exists),
                "gene_spectra_tpm_exists": bool(gene_tpm_exists),
                "usage_has_nan": bool(usage_has_nan),
                "silhouette": silhouette,
                "prediction_error": prediction_error,
            }
        )

    Path(args.status_output).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(status_rows).to_csv(args.status_output, sep="\t", index=False)

    Path(args.top_genes_output).parent.mkdir(parents=True, exist_ok=True)
    if top_gene_tables:
        pd.concat(top_gene_tables, ignore_index=True).to_csv(args.top_genes_output, sep="\t", index=False)
    else:
        pd.DataFrame(columns=["k", "program", "rank", "gene"]).to_csv(args.top_genes_output, sep="\t", index=False)

    Path(args.usage_summary_output).parent.mkdir(parents=True, exist_ok=True)
    if usage_tables:
        pd.concat(usage_tables, ignore_index=True).to_csv(args.usage_summary_output, sep="\t", index=False)
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
        ).to_csv(args.usage_summary_output, sep="\t", index=False)

    return pd.DataFrame(status_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["prepare", "factorize", "combine", "k-selection", "consensus", "summarize", "status", "all"], required=True)
    parser.add_argument("--balanced-h5ad", required=True)
    parser.add_argument("--selected-genes-input", required=True)
    parser.add_argument("--discovery-h5ad-output", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument("--config-output", required=True)
    parser.add_argument("--status-output", required=True)
    parser.add_argument("--top-genes-output", required=True)
    parser.add_argument("--usage-summary-output", required=True)
    parser.add_argument("--k-selection-stats-output", required=True)
    parser.add_argument("--components", default="5,6,7,8,9,10,12,14,16,18,20,22,24,26,28,30")
    parser.add_argument("--n-iter", type=int, default=100)
    parser.add_argument("--max-cells-per-sample", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument("--max-nmf-iter", type=int, default=1000)
    parser.add_argument("--density-threshold", type=float, default=0.5)
    parser.add_argument("--beta-loss", default="frobenius")
    parser.add_argument("--worker-i", type=int, default=0)
    parser.add_argument("--total-workers", type=int, default=1)
    parser.add_argument("--run-indices", default="")
    parser.add_argument("--run-index-file", default="")
    parser.add_argument("--skip-existing-index-files", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--top-n-genes", type=int, default=100)
    parser.add_argument("--force-prepare", action="store_true")
    parser.add_argument("--skip-completed-runs", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--skip-missing", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    components = parse_components(args.components)
    if args.n_iter < 5 and args.mode in {"prepare", "all"}:
        raise ValueError("Use n_iter >= 5 so cNMF consensus has at least one local-density neighbor")

    cnmf_obj = make_cnmf(Path(args.output_dir), args.run_name)
    modes = [args.mode] if args.mode != "all" else ["prepare", "factorize", "combine", "k-selection", "consensus", "summarize"]

    if "prepare" in modes:
        cnmf_obj = prepare_discovery(args, components)
    if "factorize" in modes:
        factorize_discovery(cnmf_obj, args)
    if "combine" in modes:
        combine_discovery(cnmf_obj, components, args)
    if "k-selection" in modes:
        k_selection_discovery(cnmf_obj)
    if "consensus" in modes:
        consensus_discovery(cnmf_obj, components, args)
    if "summarize" in modes or "status" in modes:
        status = summarize_discovery(cnmf_obj, components, args)
        completed = int(status["completed_runs"].sum()) if "completed_runs" in status.columns else 0
        expected = int(status["expected_runs"].sum()) if "expected_runs" in status.columns else 0
        print(f"NMF_COMPLETED {completed}/{expected}")
        print(f"STATUS_ROWS {status.shape[0]}")

    print(f"RUN_NAME {args.run_name}")
    print(f"OUTPUT_DIR {args.output_dir}")
    print(f"WROTE {args.status_output}")


if __name__ == "__main__":
    main()

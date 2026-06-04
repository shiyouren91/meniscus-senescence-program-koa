#!/usr/bin/env python
"""Prioritize MSP-associated paracrine ligand-receptor candidates."""

from __future__ import annotations

import argparse
import importlib.util
import math
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import sparse
from scipy.stats import mannwhitneyu


CURATED_LR_PAIRS = [
    ("MIF", "CD74", "MIF_CD74", "MSP/SASP macrophage-fibroblast signaling candidate", "curated_MSP_expert"),
    ("MIF", "CXCR4", "MIF_CXCR4", "chemokine-like inflammatory paracrine signaling", "curated_MSP_expert"),
    ("MIF", "CXCR2", "MIF_CXCR2", "chemokine-like inflammatory paracrine signaling", "curated_MSP_expert"),
    ("VEGFA", "KDR", "VEGF", "angiogenic and endothelial activation candidate", "curated_MSP_expert"),
    ("VEGFA", "FLT1", "VEGF", "angiogenic and vascular remodeling candidate", "curated_MSP_expert"),
    ("ANGPTL4", "ITGB1", "ANGPTL4_integrin", "interface angiogenic-matrix signaling candidate", "curated_MSP_expert"),
    ("ANGPTL4", "ITGAV", "ANGPTL4_integrin", "interface angiogenic-matrix signaling candidate", "curated_MSP_expert"),
    ("SPP1", "CD44", "SPP1_CD44", "matrix-immune and fibroblast activation candidate", "curated_MSP_expert"),
    ("SPP1", "ITGAV", "SPP1_integrin", "matrix-integrin communication candidate", "curated_MSP_expert"),
    ("SPP1", "ITGB1", "SPP1_integrin", "matrix-integrin communication candidate", "curated_MSP_expert"),
    ("CXCL12", "CXCR4", "CXCL12_CXCR4", "progenitor/interface chemokine axis", "curated_interface"),
    ("CXCL12", "ACKR3", "CXCL12_ACKR3", "progenitor/interface chemokine axis", "curated_interface"),
    ("BMP2", "BMPR1A", "BMP", "fibrocartilage differentiation and remodeling candidate", "curated_MSP_program"),
    ("BMP2", "BMPR2", "BMP", "fibrocartilage differentiation and remodeling candidate", "curated_MSP_program"),
    ("INHBA", "ACVR1B", "activin", "SASP/TGF-beta-family remodeling candidate", "curated_MSP_program"),
    ("INHBA", "ACVR2A", "activin", "SASP/TGF-beta-family remodeling candidate", "curated_MSP_program"),
    ("INHBA", "ACVR2B", "activin", "SASP/TGF-beta-family remodeling candidate", "curated_MSP_program"),
    ("IL11", "IL11RA", "IL11", "fibroblast activation and matrix remodeling candidate", "curated_MSP_program"),
    ("IL11", "IL6ST", "IL11", "fibroblast activation and matrix remodeling candidate", "curated_MSP_program"),
    ("FGF2", "FGFR1", "FGF", "repair/proliferation and stromal activation candidate", "curated_MSP_program"),
    ("FGF2", "FGFR2", "FGF", "repair/proliferation and stromal activation candidate", "curated_MSP_program"),
    ("FGF1", "FGFR1", "FGF", "repair/proliferation and stromal activation candidate", "curated_MSP_program"),
    ("LIF", "LIFR", "LIF", "IL6-family inflammatory remodeling candidate", "curated_SASP"),
    ("LIF", "IL6ST", "LIF", "IL6-family inflammatory remodeling candidate", "curated_SASP"),
    ("IL6", "IL6R", "IL6", "canonical SASP inflammatory signaling", "curated_SASP"),
    ("IL6", "IL6ST", "IL6", "canonical SASP inflammatory signaling", "curated_SASP"),
    ("CCL2", "CCR2", "CCL2_CCR2", "monocyte/macrophage recruitment candidate", "curated_SASP"),
    ("CXCL8", "CXCR1", "CXCL8", "neutrophil/angiogenic inflammatory candidate", "curated_SASP"),
    ("CXCL8", "CXCR2", "CXCL8", "neutrophil/angiogenic inflammatory candidate", "curated_SASP"),
    ("POSTN", "ITGAV", "POSTN_integrin", "fibrotic matrix-integrin communication candidate", "curated_matrix"),
    ("POSTN", "ITGB3", "POSTN_integrin", "fibrotic matrix-integrin communication candidate", "curated_matrix"),
    ("CCN2", "ITGAV", "CCN2_integrin", "matrix remodeling communication candidate", "curated_matrix"),
    ("CCN2", "ITGB1", "CCN2_integrin", "matrix remodeling communication candidate", "curated_matrix"),
    ("CCN1", "ITGAV", "CCN1_integrin", "matrix inflammatory communication candidate", "curated_matrix"),
    ("TNFSF12", "TNFRSF12A", "TWEAK_FN14", "FN14 receptor appears in MSP program; ligand availability needs validation", "curated_context"),
]

EXPERT_LIGANDS = {"MIF", "VEGFA", "SPP1", "ANGPTL4", "CXCL12", "IL6", "CCL2", "CXCL8"}


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    q = np.full(p.shape, np.nan)
    finite = np.isfinite(p)
    if not finite.any():
        return q.tolist()
    finite_indices = np.flatnonzero(finite)
    order = np.argsort(p[finite])
    ordered_indices = finite_indices[order]
    ranked = p[ordered_indices]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    q[ordered_indices] = np.clip(adjusted, 0, 1)
    return q.tolist()


def load_bulk_validation_module():
    module_path = Path(__file__).with_name("19_bulk_msp_validation.py")
    spec = importlib.util.spec_from_file_location("bulk_msp_validation", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import helper module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def curated_pairs_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ligand": ligand,
                "receptor": receptor,
                "pathway": pathway,
                "paracrine_rationale": rationale,
                "source": source,
            }
            for ligand, receptor, pathway, rationale, source in CURATED_LR_PAIRS
        ]
    )


def split_genes(value: object) -> list[str]:
    return [gene.strip().upper() for gene in str(value).split(",") if gene.strip()]


def ligand_program_evidence(programs: pd.DataFrame, ligands: set[str]) -> pd.DataFrame:
    rows = []
    parsed = []
    msp = programs.loc[programs["candidate_status"].astype(str).str.contains("msp_like", case=False, na=False)].copy()
    for _, row in msp.iterrows():
        genes = split_genes(row.get("top_genes_20", ""))
        parsed.append(
            {
                "program_id": f"K{int(row['k'])}_P{int(row['program'])}_{row['program_label']}",
                "candidate_status": str(row["candidate_status"]),
                "is_primary_msp": "primary" in str(row["candidate_status"]),
                "msp_rank_score": float(row.get("msp_rank_score", 0)),
                "genes": genes,
            }
        )
    for ligand in sorted(ligands):
        hits = []
        primary_hit = False
        ranks = []
        scores = []
        for item in parsed:
            if ligand in item["genes"]:
                hits.append(item["program_id"])
                scores.append(float(item["msp_rank_score"]))
                ranks.append(item["genes"].index(ligand) + 1)
                primary_hit = primary_hit or bool(item["is_primary_msp"])
        rows.append(
            {
                "ligand": ligand,
                "in_primary_msp_top_genes": bool(primary_hit),
                "n_msp_programs": int(len(hits)),
                "source_programs": ";".join(hits),
                "best_top_gene_rank": int(min(ranks)) if ranks else np.nan,
                "max_msp_rank_score": float(max(scores)) if scores else 0.0,
            }
        )
    return pd.DataFrame(rows)


def load_gene_expression(dataset_id: str, raw_dir: Path, extended_raw_dir: Path | None, helpers) -> tuple[pd.DataFrame, pd.DataFrame]:
    if dataset_id == "GSE89408":
        if extended_raw_dir is None:
            return pd.DataFrame(), pd.DataFrame()
        count_path = extended_raw_dir / "GSE89408" / "GSE89408_GEO_count_matrix_rename.txt.gz"
        if not count_path.exists():
            return pd.DataFrame(), pd.DataFrame()
        return helpers.read_count_matrix(count_path)
    dataset_dir = raw_dir / dataset_id
    if not dataset_dir.exists():
        return pd.DataFrame(), pd.DataFrame()
    supplement_readers = {
        "GSE114007": helpers.read_gse114007_supplement,
        "GSE143514": helpers.read_gse143514_supplement,
        "GSE185064": helpers.read_gse185064_supplement,
    }
    if dataset_id in supplement_readers:
        return supplement_readers[dataset_id](dataset_dir)
    matrix_paths = sorted(dataset_dir.glob("*_series_matrix.txt.gz"))
    soft_paths = sorted(dataset_dir.glob("*_family.soft.gz"))
    if not matrix_paths or not soft_paths:
        return pd.DataFrame(), pd.DataFrame()
    mapping = helpers.platform_mapping(soft_paths[0])
    expression, metadata, _series_meta = helpers.read_series_matrix(matrix_paths[0])
    gene_expression = helpers.collapse_expression_to_genes(expression, mapping)
    if "dataset_id" not in metadata.columns or metadata["dataset_id"].isna().all():
        metadata = helpers.add_sample_context(dataset_id, metadata)
    return gene_expression, metadata


def gene_z_scores(
    raw_dir: Path,
    extended_raw_dir: Path | None,
    manifest: pd.DataFrame,
    assignments: pd.DataFrame,
    genes: set[str],
) -> pd.DataFrame:
    helpers = load_bulk_validation_module()
    rows = []
    selected = manifest.loc[manifest["priority"].isin(["high", "medium"])].copy()
    for dataset_id in sorted(selected["dataset_id"].astype(str).unique()):
        expression, _metadata = load_gene_expression(dataset_id, raw_dir, extended_raw_dir, helpers)
        if expression.empty:
            continue
        expression = expression.copy()
        expression.index = expression.index.astype(str).str.upper()
        expression = expression.groupby(expression.index, observed=True).mean()
        assigned = assignments.loc[assignments["dataset_id"].astype(str) == dataset_id].copy()
        assigned_samples = [sample for sample in assigned["sample_id"].astype(str) if sample in expression.columns]
        if not assigned_samples:
            continue
        present = sorted(set(genes).intersection(expression.index))
        if not present:
            continue
        values = expression.loc[present, assigned_samples].astype(float)
        means = values.mean(axis=1)
        sds = values.std(axis=1).replace(0, np.nan)
        z = values.sub(means, axis=0).div(sds, axis=0)
        lookup = assigned.set_index("sample_id")
        for gene in present:
            for sample_id in assigned_samples:
                meta = lookup.loc[sample_id]
                rows.append(
                    {
                        "gene": gene,
                        "dataset_id": dataset_id,
                        "sample_id": sample_id,
                        "tissue": meta.get("tissue", ""),
                        "condition": meta.get("condition", ""),
                        "subtype_id": meta.get("subtype_id", ""),
                        "subtype_label": meta.get("subtype_label", ""),
                        "z_expression": float(z.loc[gene, sample_id]) if np.isfinite(z.loc[gene, sample_id]) else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def gene_subtype_tests(gene_scores: pd.DataFrame, roles: dict[str, str]) -> pd.DataFrame:
    scopes = [("overall", "all", gene_scores)]
    for tissue, frame in gene_scores.groupby("tissue", observed=True):
        scopes.append(("tissue", str(tissue), frame))
    for dataset_id, frame in gene_scores.groupby("dataset_id", observed=True):
        scopes.append(("dataset", str(dataset_id), frame))
    rows = []
    for scope, stratum, frame in scopes:
        for gene, gene_frame in frame.groupby("gene", observed=True):
            subtypes = sorted(gene_frame["subtype_id"].astype(str).unique())
            if len(subtypes) != 2:
                continue
            a_id, b_id = subtypes
            a = pd.to_numeric(gene_frame.loc[gene_frame["subtype_id"].astype(str) == a_id, "z_expression"], errors="coerce").dropna()
            b = pd.to_numeric(gene_frame.loc[gene_frame["subtype_id"].astype(str) == b_id, "z_expression"], errors="coerce").dropna()
            if len(a) < 2 or len(b) < 2:
                continue
            test = mannwhitneyu(a, b, alternative="two-sided")
            delta = float(a.mean() - b.mean())
            rows.append(
                {
                    "gene": gene,
                    "role": roles.get(gene, "unknown"),
                    "scope": scope,
                    "stratum": stratum,
                    "subtype_a": a_id,
                    "subtype_b": b_id,
                    "n_a": int(len(a)),
                    "n_b": int(len(b)),
                    "mean_a": float(a.mean()),
                    "mean_b": float(b.mean()),
                    "mean_delta_s1_minus_s2": delta,
                    "median_delta_s1_minus_s2": float(a.median() - b.median()),
                    "p_value": float(test.pvalue),
                    "effect_direction": f"{a_id}_higher" if delta > 0 else f"{b_id}_higher" if delta < 0 else "no_difference",
                }
            )
    result = pd.DataFrame(rows)
    if not result.empty:
        result["fdr_bh"] = benjamini_hochberg(result["p_value"].tolist())
        result = result.sort_values(["scope", "stratum", "fdr_bh", "gene"])
    return result


def state_means_for_genes(path: Path, group_col: str, genes: set[str], reference_name: str) -> pd.DataFrame:
    adata = ad.read_h5ad(path)
    var_lookup = {str(name).upper(): i for i, name in enumerate(adata.var_names)}
    present = [gene for gene in sorted(genes) if gene in var_lookup]
    if not present:
        return pd.DataFrame()
    indices = [var_lookup[gene] for gene in present]
    groups = adata.obs[group_col].astype(str)
    rows = []
    x = adata.X[:, indices]
    for state in sorted(groups.unique()):
        mask = groups == state
        if int(mask.sum()) < 10:
            continue
        block = x[mask.to_numpy(), :]
        if sparse.issparse(block):
            means = np.asarray(block.mean(axis=0)).ravel()
        else:
            means = np.asarray(block, dtype=float).mean(axis=0)
        for gene, value in zip(present, means):
            rows.append(
                {
                    "reference_name": reference_name,
                    "state": state,
                    "gene": gene,
                    "mean_expression": float(value),
                }
            )
    return pd.DataFrame(rows)


def receptor_reference_context(hra_h5ad: Path, gse_h5ad: Path, receptors: set[str]) -> pd.DataFrame:
    tables = [
        state_means_for_genes(hra_h5ad, "celltype", receptors, "HRA001986_chondrocyte"),
        state_means_for_genes(gse_h5ad, "draft_annotation", receptors, "GSE220243_broad"),
    ]
    data = pd.concat([table for table in tables if not table.empty], ignore_index=True)
    rows = []
    if data.empty:
        return pd.DataFrame()
    for (reference_name, receptor), frame in data.groupby(["reference_name", "gene"], observed=True):
        top = frame.sort_values("mean_expression", ascending=False).iloc[0]
        threshold = max(0.01, float(frame["mean_expression"].quantile(0.50)))
        detected = frame.loc[frame["mean_expression"] > threshold, "state"].astype(str).tolist()
        context_support = math.log1p(float(top["mean_expression"])) + min(len(detected), 5) * 0.15
        rows.append(
            {
                "receptor": receptor,
                "reference_name": reference_name,
                "top_state": top["state"],
                "top_state_mean_expression": float(top["mean_expression"]),
                "detected_states": ";".join(detected),
                "n_detected_states": int(len(detected)),
                "context_support": float(context_support),
            }
        )
    return pd.DataFrame(rows).sort_values(["receptor", "reference_name"])


def support_from_gene_tests(gene_tests: pd.DataFrame, gene: str) -> dict[str, float | str]:
    overall = gene_tests.loc[(gene_tests["scope"] == "overall") & (gene_tests["gene"].astype(str) == gene)]
    if overall.empty:
        return {"delta": 0.0, "fdr": 1.0, "direction": "not_tested", "support": 0.0}
    row = overall.iloc[0]
    delta = float(row["mean_delta_s1_minus_s2"])
    fdr = float(row["fdr_bh"])
    support = max(0.0, delta) * 1.5
    if delta > 0:
        support += min(2.0, -math.log10(max(fdr, 1e-6)) / 2)
    return {"delta": delta, "fdr": fdr, "direction": str(row["effect_direction"]), "support": support}


def priority_table(
    pairs: pd.DataFrame,
    ligand_evidence: pd.DataFrame,
    gene_tests: pd.DataFrame,
    receptor_context: pd.DataFrame,
) -> pd.DataFrame:
    ligand_lookup = ligand_evidence.set_index("ligand").to_dict(orient="index")
    receptor_context_score = receptor_context.groupby("receptor", observed=True)["context_support"].max().to_dict()
    receptor_top = (
        receptor_context.sort_values("context_support", ascending=False)
        .drop_duplicates("receptor")
        .set_index("receptor")
        .to_dict(orient="index")
        if not receptor_context.empty
        else {}
    )
    rows = []
    for _, pair in pairs.iterrows():
        ligand = str(pair["ligand"]).upper()
        receptor = str(pair["receptor"]).upper()
        ev = ligand_lookup.get(ligand, {})
        program_support = 0.0
        if ev.get("in_primary_msp_top_genes", False):
            program_support += 2.5
        program_support += min(2.0, float(ev.get("n_msp_programs", 0)) * 0.35)
        program_support += min(2.0, float(ev.get("max_msp_rank_score", 0)) / 12)
        ligand_bulk = support_from_gene_tests(gene_tests, ligand)
        receptor_bulk = support_from_gene_tests(gene_tests, receptor)
        receptor_support = min(2.5, float(receptor_context_score.get(receptor, 0)))
        expert_bonus = 1.0 if ligand in EXPERT_LIGANDS else 0.0
        score = program_support + float(ligand_bulk["support"]) + 0.6 * float(receptor_bulk["support"]) + receptor_support + expert_bonus
        if score >= 7:
            tier = "high"
        elif score >= 4.5:
            tier = "medium"
        else:
            tier = "exploratory"
        top_context = receptor_top.get(receptor, {})
        validation = "synovial fluid proteomics + CellChat/LIANA/NicheNet consensus"
        if ligand in {"VEGFA", "ANGPTL4"}:
            validation = "synovial fluid proteomics + endothelial/angiogenesis readout"
        elif ligand in {"MIF", "SPP1", "CCL2", "CXCL8", "IL6"}:
            validation = "synovial fluid proteomics + immune/synovial fibroblast response assay"
        rows.append(
            {
                "ligand": ligand,
                "receptor": receptor,
                "pathway": pair["pathway"],
                "priority_score": float(score),
                "priority_tier": tier,
                "ligand_program_support": float(program_support),
                "bulk_ligand_support": float(ligand_bulk["support"]),
                "bulk_ligand_delta_s1_minus_s2": float(ligand_bulk["delta"]),
                "bulk_ligand_fdr": float(ligand_bulk["fdr"]),
                "bulk_receptor_support": float(receptor_bulk["support"]),
                "bulk_receptor_delta_s1_minus_s2": float(receptor_bulk["delta"]),
                "bulk_receptor_fdr": float(receptor_bulk["fdr"]),
                "receptor_context_support": float(receptor_support),
                "receptor_top_context": f"{top_context.get('reference_name', '')}:{top_context.get('top_state', '')}",
                "source_programs": ev.get("source_programs", ""),
                "paracrine_rationale": pair["paracrine_rationale"],
                "recommended_validation": validation,
            }
        )
    return pd.DataFrame(rows).sort_values(["priority_score", "ligand", "receptor"], ascending=[False, True, True])


def save_heatmap(priority: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    top = priority.head(20).copy()
    top["pair"] = top["ligand"] + "->" + top["receptor"]
    matrix = top.set_index("pair")[
        ["ligand_program_support", "bulk_ligand_support", "bulk_receptor_support", "receptor_context_support"]
    ]
    plt.figure(figsize=(7, max(6, matrix.shape[0] * 0.35)))
    sns.heatmap(matrix, cmap="mako", annot=True, fmt=".2f", linewidths=0.2)
    plt.title("Top MSP paracrine LR evidence components")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def save_barplot(priority: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    top = priority.head(15).copy()
    top["pair"] = top["ligand"] + "->" + top["receptor"]
    plt.figure(figsize=(8, max(4, top.shape[0] * 0.35)))
    sns.barplot(data=top, y="pair", x="priority_score", hue="priority_tier", dodge=False)
    plt.title("Top MSP paracrine LR candidates")
    plt.tight_layout()
    plt.savefig(output, dpi=220)
    plt.close()


def write_notes(path: Path, priority: pd.DataFrame, ligand_evidence: pd.DataFrame, gene_tests: pd.DataFrame) -> None:
    lines = [
        "# MSP Paracrine Ligand-Receptor Prioritization",
        "",
        "## Scope",
        "",
        "This step prioritizes ligand-receptor candidates for meniscus-derived MSP paracrine signaling.",
        "It is a curated ligand-receptor prioritization screen, not a CellChat, LIANA, or NicheNet inference result.",
        "",
        "## Evidence Used",
        "",
        "- ligand membership in cNMF MSP-like programs",
        "- bulk S1 versus S2 ligand and receptor expression direction",
        "- receptor expression context in HRA001986 and GSE220243 single-cell references",
        "- expert-prioritized synovial fluid candidates such as MIF, SPP1, VEGFA, ANGPTL4, CXCL, and IL6-family axes",
        "",
        "## Top Candidates",
        "",
    ]
    for _, row in priority.head(15).iterrows():
        lines.append(
            "- {ligand}->{receptor} ({pathway}): score={score:.2f}, tier={tier}, validation={validation}".format(
                ligand=row["ligand"],
                receptor=row["receptor"],
                pathway=row["pathway"],
                score=float(row["priority_score"]),
                tier=row["priority_tier"],
                validation=row["recommended_validation"],
            )
        )
    primary_ligands = ligand_evidence.loc[ligand_evidence["in_primary_msp_top_genes"]]
    lines.extend(["", "## Primary MSP Ligands", ""])
    if primary_ligands.empty:
        lines.append("- No curated ligands were found in primary MSP top genes.")
    else:
        for _, row in primary_ligands.sort_values("max_msp_rank_score", ascending=False).iterrows():
            lines.append(
                f"- {row['ligand']}: programs={row['source_programs']}; max MSP rank score={float(row['max_msp_rank_score']):.2f}"
            )
    lines.extend(
        [
            "",
            "## Recommended Next Validation",
            "",
            "- Run CellChat and LIANA on tissue-matched single-cell objects as method-consensus communication support.",
            "- Run NicheNet-style target prediction for high-priority ligand axes against S1-high remodeling/MSP genes.",
            "- Check synovial fluid proteomics for MIF, SPP1, VEGFA, ANGPTL4, CXCL/CCL, IL6-family, and FGF/activin/BMP-family proteins.",
            "- If experiments are feasible, test senescent meniscus cell conditioned medium on synovial fibroblasts or chondrocytes with pathway-specific blockade.",
            "",
            "## Caution",
            "",
            "Cross-tissue meniscus-to-synovium/cartilage signaling is paracrine and joint-fluid mediated, not direct cell-cell contact.",
            "This table should be used to choose candidates for formal CellChat/LIANA/NicheNet and protein validation rather than as final communication proof.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True)
    parser.add_argument("--extended-raw-dir", required=True)
    parser.add_argument("--program-priority-input", required=True)
    parser.add_argument("--assignments-input", required=True)
    parser.add_argument("--deconvolution-manifest-input", required=True)
    parser.add_argument("--hra-reference-h5ad", required=True)
    parser.add_argument("--gse220243-reference-h5ad", required=True)
    parser.add_argument("--curated-pairs-output", required=True)
    parser.add_argument("--ligand-evidence-output", required=True)
    parser.add_argument("--gene-tests-output", required=True)
    parser.add_argument("--receptor-context-output", required=True)
    parser.add_argument("--priority-output", required=True)
    parser.add_argument("--notes-output", required=True)
    parser.add_argument("--heatmap-output", required=True)
    parser.add_argument("--barplot-output", required=True)
    args = parser.parse_args()

    pairs = curated_pairs_table()
    programs = pd.read_csv(args.program_priority_input, sep="\t")
    assignments = pd.read_csv(args.assignments_input, sep="\t")
    manifest = pd.read_csv(args.deconvolution_manifest_input, sep="\t")
    ligands = set(pairs["ligand"].astype(str).str.upper())
    receptors = set(pairs["receptor"].astype(str).str.upper())
    genes = ligands | receptors
    roles = {}
    for gene in genes:
        is_ligand = gene in ligands
        is_receptor = gene in receptors
        roles[gene] = "both" if is_ligand and is_receptor else "ligand" if is_ligand else "receptor"

    ligand_evidence = ligand_program_evidence(programs, ligands)
    gene_scores = gene_z_scores(Path(args.raw_dir), Path(args.extended_raw_dir), manifest, assignments, genes)
    gene_tests = gene_subtype_tests(gene_scores, roles)
    receptor_context = receptor_reference_context(Path(args.hra_reference_h5ad), Path(args.gse220243_reference_h5ad), receptors)
    priority = priority_table(pairs, ligand_evidence, gene_tests, receptor_context)

    for output in [
        args.curated_pairs_output,
        args.ligand_evidence_output,
        args.gene_tests_output,
        args.receptor_context_output,
        args.priority_output,
        args.notes_output,
        args.heatmap_output,
        args.barplot_output,
    ]:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    pairs.to_csv(args.curated_pairs_output, sep="\t", index=False)
    ligand_evidence.to_csv(args.ligand_evidence_output, sep="\t", index=False)
    gene_tests.to_csv(args.gene_tests_output, sep="\t", index=False)
    receptor_context.to_csv(args.receptor_context_output, sep="\t", index=False)
    priority.to_csv(args.priority_output, sep="\t", index=False)
    save_heatmap(priority, Path(args.heatmap_output))
    save_barplot(priority, Path(args.barplot_output))
    write_notes(Path(args.notes_output), priority, ligand_evidence, gene_tests)

    print(f"CURATED_PAIRS {pairs.shape[0]}")
    print(f"LIGAND_EVIDENCE_ROWS {ligand_evidence.shape[0]}")
    print(f"GENE_TEST_ROWS {gene_tests.shape[0]}")
    print(f"RECEPTOR_CONTEXT_ROWS {receptor_context.shape[0]}")
    print(f"PRIORITY_ROWS {priority.shape[0]}")


if __name__ == "__main__":
    main()

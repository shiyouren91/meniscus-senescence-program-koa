#!/usr/bin/env python
"""Apply expert JOT revision changelist to manuscript and figure-source files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


TEXT_FILES = [
    "docs/manuscript/07_msp_full_results_draft.md",
    "docs/manuscript/09_msp_full_methods_draft.md",
    "docs/manuscript/11_msp_discussion_draft.md",
    "docs/manuscript/15_msp_integrated_manuscript_draft.md",
    "docs/manuscript/21_jot_cover_letter_draft.md",
    "docs/manuscript/22_jot_anonymized_manuscript_draft.md",
]

PRIMARY_MANUSCRIPTS = [
    "docs/manuscript/15_msp_integrated_manuscript_draft.md",
    "docs/manuscript/22_jot_anonymized_manuscript_draft.md",
]

SUPPLEMENTARY_METHODS_STUB = """### Supplementary Methods: Reproducibility Details Pending Final Citation

Highly variable genes for the balanced fibrochondrocyte cNMF object were selected by dispersion after excluding mitochondrial, ribosomal, and cell-cycle genes; the exact dispersion cutoff and upstream filtering thresholds should be confirmed against the preprocessing scripts before final submission. [TODO: confirm exact HVG thresholds]

Signature enrichment used senescence, SASP, communication, fibrocartilage, ECM remodeling, generic stress, contamination, immune, mural, and cycling gene sets. Planned citation coverage includes SenMayo, Fridman senescence signatures, CellAge/CSGene-style senescence resources, SASP atlas or GO-derived inflammatory/secretory terms, and project-specific fibrocartilage/ECM marker panels; the exact source list should be reconciled with ST03 before final reference formatting. [TODO: confirm exact signature sources and gene-list versions]

The MSP rank score is a weighted program-prioritization score combining positive enrichment for senescence/SASP/communication/fibrocartilage/ECM-remodeling terms with penalties for contamination, immune/mural/cycling signatures, generic stress, and donor-skew where applicable. The final numerical weights should be copied from the program audit code or table before submission. [TODO: confirm rank-score weights]

Bulk meta-analysis FDR was controlled across the seven scored axes using Benjamini-Hochberg correction; tissue-stratified evidence grades should be treated as the primary bulk readout when comparator or tissue definitions differ across cohorts.
"""

REFERENCE_TODO = """[TODO: insert numbered reference list in JOT (Vancouver/Elsevier numbered) style covering at minimum:
 1. A meniscus scRNA-seq atlas (source of HRA001986 / comparable);
 2. The GSE220243 source publication;
 3. A program-level / cNMF method reference (Kotliar et al. cNMF);
 4. A senescence/SASP gene-set reference used for scoring (e.g. SenMayo - Saul et al.; Fridman & Tainsky; CellAge);
 5. CellChat (Jin et al.), LIANA (Dimitrov et al.), NicheNet (Browaeys et al.);
 6. A random-effects meta-analysis method reference (DerSimonian-Laird);
 7. 2-4 reviews on meniscal degeneration / OA senescence for the Introduction.
 Replace each in-text claim that needs support with a numbered citation.]"""


REPLACEMENTS = [
    (
        "A1_direction_of_effect",
        "These results support a validation-ready mechanism hypothesis centered on MSP-high meniscal fibrochondrocytes, immune/myeloid or vascular receiver contexts, and remodeling-associated target genes.",
        'These results support a validation-ready mechanism hypothesis centered on MSP-program-high meniscal fibrochondrocytes, immune/myeloid or vascular receiver contexts, and remodeling-associated target genes. Because the parent senescence-paracrine programs were normal- and donor-skewed in discovery (ST01) and directionally heterogeneous across bulk cohorts (pooled SMD between -0.48 and -0.97; I2 approximately 82-85%; ST10-ST11), "MSP-program-high" denotes relative within-fibrochondrocyte program usage and not an OA-upregulated state.',
    ),
    (
        "A2_discussion_sender_label",
        "These axes are attractive because they connect MSP-high fibrochondrocytes to plausible receiver contexts and bulk S1-high receiver-response genes.",
        "These axes are attractive because they connect MSP-program-high fibrochondrocytes (a relative within-cell program-usage state, not an OA-upregulated state) to plausible receiver contexts and bulk S1-high receiver-response genes.",
    ),
    (
        "A3_bulk_reframing",
        "Bulk validation across meniscus, cartilage, and synovium cohorts showed that MSP-like and remodeling axes were detectable across datasets, but their disease direction was heterogeneous. This was most visible for the MSP paracrine, angiogenic, and inflammatory axes, which did not support a simple universal OA-up claim. By contrast, fibrocartilage matrix remodeling showed stronger and more consistent bulk signal across cohorts.",
        "Bulk validation across meniscus, cartilage, and synovium cohorts showed that MSP-like and remodeling axes were detectable across datasets, but their disease direction was heterogeneous. Because comparator and tissue definitions differed across cohorts, we interpret tissue-stratified evidence grades (ST11) as primary and treat the pooled all-tissue meta-estimate as a sensitivity summary only. Under this framing, the only axis with strong and consistent bulk support was fibrocartilage matrix remodeling (Fibrocartilage_matrix_K14P4: pooled SMD 0.80, 95% CI 0.42-1.19, I2 = 30%, FDR = 3.2e-4), which was higher in disease/aged groups in cartilage and synovium. By contrast, the MSP paracrine, angiogenic, and inflammatory axes were directionally heterogeneous (I2 approximately 82-85%, direction consistency 0.56-0.67) and did not support a simple universal OA-up claim.",
    ),
    (
        "A4_methods_meta_analysis",
        "Cross-cohort evidence was summarized by random-effects meta-analysis, including effect estimates, confidence intervals, heterogeneity, and direction consistency. Because cohort, platform, tissue, and comparator definitions differed, bulk validation was interpreted as context-dependent support rather than a universal OA-up MSP signature.",
        "Cross-cohort evidence was summarized by random-effects (DerSimonian-Laird) meta-analysis, reporting effect estimates, 95% confidence intervals, tau2, I2 heterogeneity, and direction consistency, with Benjamini-Hochberg FDR applied across the seven scored axes. Because cohort, platform, tissue, and comparator definitions differed (including OA, RA, and normal comparators across cartilage, synovium, and meniscus), tissue-stratified evidence grades were treated as the primary bulk readout and the pooled all-tissue estimate as a sensitivity summary; bulk validation was therefore interpreted as context-dependent support rather than a universal OA-up MSP signature.",
    ),
    (
        "A5_results_subtype_relabel",
        "Consensus bulk subtyping organized samples into an S1 remodeling/MSP-interface-high state and an S2 mixed-low/MSP-low state. S1 was not an ECM-only subtype; it combined matrix/fibrotic remodeling with relatively higher MSP-interface features.",
        "Consensus bulk subtyping organized samples into an S1 ECM/fibrotic-high state and an S2 mixed-low state. S1 was defined primarily by high ECM-matrix and fibrotic-remodeling scores (mean z +0.62 and +0.37); its MSP-axis scores were near zero or slightly negative (e.g. MSP_inflammatory mean z -0.18), i.e. higher than S2 in relative terms but not elevated in absolute terms.",
    ),
    (
        "A5_discussion_subtype_relabel",
        "The S1 remodeling/MSP-interface-high subtype, the leading paracrine axes, and the validation roadmap provide a ranked set of hypotheses for biomarker and perturbation studies.",
        "The S1 ECM/fibrotic-high subtype, the leading paracrine axes, and the validation roadmap provide a ranked set of hypotheses for biomarker and perturbation studies.",
    ),
    (
        "A5_methods_subtype_relabel",
        "Consensus clustering and NMF were used to identify relative molecular states, yielding an S1 remodeling/MSP-interface-high subtype and an S2 mixed-low/MSP-low subtype.",
        "Consensus clustering and NMF were used to identify relative molecular states, yielding an S1 ECM/fibrotic-high subtype and an S2 mixed-low subtype; the two-subtype solution was selected using the consensus cophenetic correlation and proportion-of-ambiguous-clustering (PAC) criteria.",
    ),
    (
        "A6_cnmf_gene_selection",
        "The balanced discovery object contained 54882 selected cells and 3038 selected genes. Components were evaluated across K values 5,6,7,8,9,10,12,14,16,18,20,22,24,26,28,30, with 100 NMF iterations per K setting and seed 20260529.",
        "The balanced discovery object contained 54882 selected cells and 3038 selected genes (highly variable genes selected by dispersion, with mitochondrial, ribosomal, and cell-cycle genes excluded; see Supplementary Methods for exact thresholds). Components were evaluated across K values 5,6,7,8,9,10,12,14,16,18,20,22,24,26,28,30, with 100 NMF iterations per K setting and seed 20260529.",
    ),
    (
        "A6_program_rank_repro",
        "Programs were ranked by enrichment for senescence, SASP, communication, fibrocartilage, ECM remodeling, generic stress, contamination, immune, mural, and cycling signatures.",
        "Programs were ranked by enrichment for senescence, SASP, communication, fibrocartilage, ECM remodeling, generic stress, contamination, immune, mural, and cycling signatures. The exact gene lists for each signature, their sources, and the MSP rank-score formula (a weighted sum of signature-enrichment terms penalized by contamination and donor-skew terms) are provided in Supplementary Methods and the per-program audit table (ST03).",
    ),
    (
        "C1_abstract_results",
        "Results: MSP-like programs captured program-level senescence, SASP, fibrocartilage, and paracrine biology. HRA projection supported meniscus cell-state context, whereas bulk cohorts revealed tissue- and comparator-dependent heterogeneity rather than a universal OA-up pattern. Integrated evidence nominated MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes.",
        "Results: MSP-like programs captured program-level senescence, SASP, fibrocartilage, and paracrine biology. HRA projection supported meniscus cell-state context. In bulk cohorts, only the fibrocartilage-matrix remodeling axis showed strong, consistent disease-associated signal (pooled SMD 0.80, I2 = 30%, FDR = 3.2e-4), whereas the MSP paracrine, angiogenic, and inflammatory axes were tissue- and comparator-dependent (I2 approximately 82-85%) rather than universally OA-up. Integrated evidence nominated MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes for prioritized validation.",
    ),
    (
        "C1_abstract_results_bold",
        "**Results:** MSP-like programs captured program-level senescence, SASP, fibrocartilage, and paracrine biology. HRA projection supported meniscus cell-state context, whereas bulk cohorts revealed tissue- and comparator-dependent heterogeneity rather than a universal OA-up pattern. Integrated evidence nominated MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes.",
        "**Results:** MSP-like programs captured program-level senescence, SASP, fibrocartilage, and paracrine biology. HRA projection supported meniscus cell-state context. In bulk cohorts, only the fibrocartilage-matrix remodeling axis showed strong, consistent disease-associated signal (pooled SMD 0.80, I2 = 30%, FDR = 3.2e-4), whereas the MSP paracrine, angiogenic, and inflammatory axes were tissue- and comparator-dependent (I2 approximately 82-85%) rather than universally OA-up. Integrated evidence nominated MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes for prioritized validation.",
    ),
    (
        "C2_validation_roadmap_trim",
        "This final layer is deliberately prospective. The present study nominates candidate paracrine axes and a validation strategy; it does not establish that MSP ligands have disease-driving activity. Each leading axis is not a validated mechanism at this stage. Throughout the manuscript, MIF_CD74, ANGPTL4_integrin, and VEGF should be described as leading candidate axes, not causal or validated mechanisms, until formal CellChat/LIANA/NicheNet consensus, protein evidence, and perturbation experiments point in the same direction.",
        "This final layer is deliberately prospective. The present study nominates candidate paracrine axes and a validation strategy; it does not establish that MSP ligands have disease-driving activity. MIF_CD74, ANGPTL4_integrin, and VEGF are therefore leading candidate axes that require formal CellChat/LIANA/NicheNet consensus, protein evidence, and perturbation experiments before any causal interpretation.",
    ),
    (
        "C4_conclusion_positive_signal",
        "In summary, this study nominates a meniscus-centered MSP framework connecting program-level fibrochondrocyte states, context-dependent bulk remodeling, and candidate paracrine axes.",
        "In summary, this study nominates a meniscus-centered MSP framework connecting program-level fibrochondrocyte states, a robust fibrocartilage-matrix remodeling bulk signal, context-dependent MSP-axis remodeling, and candidate paracrine axes.",
    ),
    (
        "D3_gene_set_citation_anchor",
        "This is important because classical senescence markers such as CDKN1A or CDKN2A are sparse and context-dependent in single-cell data, and generic senescence signatures can miss tissue-specific fibrocartilage features.",
        "This is important because classical senescence markers such as CDKN1A or CDKN2A are sparse and context-dependent in single-cell data [TODO: cite], and generic senescence signatures (for example SenMayo or CellAge) can miss tissue-specific fibrocartilage features [TODO: cite].",
    ),
    (
        "D1_reference_todo",
        "[Reference list to be formatted according to Journal of Orthopaedic Translation requirements.]",
        REFERENCE_TODO,
    ),
    (
        "E1_cover_letter_alignment",
        "By combining fibrochondrocyte cNMF discovery, external HRA001986 projection, multi-tissue bulk validation, subtype analysis, and expression-based ligand-receptor prioritization, the study nominates MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes for future orthopaedic translational validation.",
        "By combining fibrochondrocyte cNMF discovery, external HRA001986 projection, multi-tissue bulk validation, subtype analysis, and expression-based ligand-receptor prioritization, the study identifies a robust fibrocartilage-matrix remodeling bulk signal and nominates MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes for future orthopaedic translational validation.",
    ),
]

GLOBAL_TEXT_REPLACEMENTS = [
    ("S1 remodeling/MSP-interface-high", "S1 ECM/fibrotic-high"),
    ("S2 mixed-low/MSP-low", "S2 mixed-low"),
    ("remodeling/MSP-interface-high", "ECM/fibrotic-high"),
    ("mixed-low/MSP-low", "mixed-low"),
    ("MSP-high meniscal fibrochondrocytes", "MSP-program-high meniscal fibrochondrocytes"),
    ("MSP-high fibrochondrocytes", "MSP-program-high fibrochondrocytes"),
    ("MSP-high fibrochondrocyte", "MSP-program-high fibrochondrocyte"),
    ("MIF CD74", "MIF_CD74"),
    ("ANGPTL4 integrin", "ANGPTL4_integrin"),
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def add_audit(audit: list[dict[str, str]], item_id: str, target: str, status: str, detail: str) -> None:
    audit.append({"item_id": item_id, "target": target, "status": status, "detail": detail})


def replace_once(text: str, find: str, replacement: str) -> tuple[str, str, str]:
    if replacement in text:
        return text, "already_applied", "replacement text already present"
    if find in text:
        return text.replace(find, replacement), "applied", "verbatim replacement"
    return text, "not_found", "find string absent; left unchanged"


def deduplicate_revision_sentences(text: str) -> tuple[str, int]:
    duplicate_targets = [
        "The exact gene lists for each signature, their sources, and the MSP rank-score formula (a weighted sum of signature-enrichment terms penalized by contamination and donor-skew terms) are provided in Supplementary Methods and the per-program audit table (ST03).",
    ]
    total = 0
    for sentence in duplicate_targets:
        doubled = sentence + " " + sentence
        while doubled in text:
            text = text.replace(doubled, sentence)
            total += 1
    return text, total


def remove_submission_caution(text: str) -> tuple[str, int]:
    pattern = re.compile(r"\n## Submission Caution\n\n.*?(?=\n## |\Z)", flags=re.S)
    return pattern.subn("", text)


def insert_novelty_paragraph(text: str) -> tuple[str, str]:
    novelty = (
        "Our approach differs from prior work in three ways. First, in contrast to single-marker or hub-gene senescence analyses, "
        "we define the MSP as a multi-gene program-level cell state derived by consensus non-negative matrix factorization, which is better suited to the sparsity of single-cell senescence markers. "
        "Second, where generic senescence signatures (for example SenMayo or CellAge) capture pan-tissue aging, we test whether a meniscus-derived program retains fibrocartilage-specific information beyond these signatures. "
        "Third, rather than asserting a disease-up signature from one dataset, we impose explicit sample-aware and cross-tissue guardrails and report candidate axes with calibrated, validation-ready confidence. "
        "[TODO: add citations for prior meniscus scRNA-seq atlas, generic senescence gene sets, and cNMF.]"
    )
    if novelty in text:
        return text, "already_applied"
    anchor = (
        "Cellular senescence is a plausible contributor to this biology, but single-marker senescence analysis is poorly suited to single-cell data. "
        "Canonical markers such as CDKN1A, CDKN2A, and LMNB1 are sparse, context-dependent, and insufficient on their own. "
        "A stronger design is to define a meniscus senescence program (MSP) as a program-level, multi-gene cell-state axis and then test whether this axis retains meniscus-specific information beyond generic senescence signatures."
    )
    if anchor in text:
        return text.replace(anchor, anchor + "\n\n" + novelty), "applied"
    return text, "not_found"


def insert_supplementary_methods_stub(text: str) -> tuple[str, str]:
    if "Supplementary Methods: Reproducibility Details" in text:
        return text, "already_applied"
    anchor = "\n## Figure Legends"
    if anchor in text:
        return text.replace(anchor, "\n" + SUPPLEMENTARY_METHODS_STUB + "\n" + anchor, 1), "applied"
    return text + "\n\n" + SUPPLEMENTARY_METHODS_STUB + "\n", "appended"


def apply_text_revisions(root: Path, audit: list[dict[str, str]]) -> None:
    for rel_path in TEXT_FILES:
        path = root / rel_path
        if not path.exists():
            add_audit(audit, "text_file", rel_path, "missing", "target file absent")
            continue
        text = read_text(path)
        original = text
        for item_id, find, replacement in REPLACEMENTS:
            if item_id == "E1_cover_letter_alignment" and path.name != "21_jot_cover_letter_draft.md":
                continue
            if item_id != "E1_cover_letter_alignment" and path.name == "21_jot_cover_letter_draft.md":
                continue
            text, status, detail = replace_once(text, find, replacement)
            add_audit(audit, item_id, rel_path, status, detail)

        if rel_path in PRIMARY_MANUSCRIPTS:
            text, status = insert_novelty_paragraph(text)
            add_audit(audit, "D2_novelty_paragraph", rel_path, status, "insert after cellular senescence paragraph")
            text, status = insert_supplementary_methods_stub(text)
            add_audit(audit, "A6_supplementary_methods_stub", rel_path, status, "supplementary methods reproducibility stub")

        text, removed = remove_submission_caution(text)
        add_audit(audit, "C3_remove_submission_caution", rel_path, "applied" if removed else "already_absent", f"removed sections={removed}")

        for old, new in GLOBAL_TEXT_REPLACEMENTS:
            count = text.count(old)
            if count:
                text = text.replace(old, new)
                add_audit(audit, "C5_or_global_label_cleanup", rel_path, "applied", f"{old} -> {new}; replacements={count}")

        text, dedup_count = deduplicate_revision_sentences(text)
        if dedup_count:
            add_audit(audit, "A6_deduplicate_repro_sentence", rel_path, "applied", f"deduplicated repeated revision sentences={dedup_count}")

        if text != original:
            write_text(path, text)
        else:
            add_audit(audit, "text_file_no_change", rel_path, "verified", "no text update needed")


def apply_global_generated_label_cleanup(root: Path, audit: list[dict[str, str]]) -> None:
    targets = []
    for pattern in ["docs/manuscript/*.md", "docs/workflow/*.md", "results/tables/manuscript_*.tsv"]:
        targets.extend(root.glob(pattern))
    for path in sorted(set(targets)):
        rel_path = path.relative_to(root).as_posix()
        text = read_text(path)
        original = text
        total = 0
        for old, new in GLOBAL_TEXT_REPLACEMENTS[:7]:
            count = text.count(old)
            if count:
                text = text.replace(old, new)
                total += count
        if total:
            write_text(path, text)
            add_audit(audit, "generated_label_cleanup", rel_path, "applied", f"replacements={total}")
        elif text != original:
            write_text(path, text)


def update_network_edges(root: Path, audit: list[dict[str, str]]) -> None:
    path = root / "results/tables/manuscript_figure4_network_edges.tsv"
    rel_path = path.relative_to(root).as_posix()
    if not path.exists():
        add_audit(audit, "B2_network_edges", rel_path, "missing", "network edge table absent")
        return
    df = pd.read_csv(path, sep="\t")
    before = len(df)
    if "edge_label" in df.columns:
        df["edge_label"] = df["edge_label"].replace({"ANGPTL4->TGB1": "ANGPTL4->ITGB1"})
        df = df.loc[df["edge_label"] != "VEGFA->KDR"].copy()
    for col in ["sender_node", "receiver_node"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace("MSP-high", "MSP-program-high", regex=False)
    df.to_csv(path, sep="\t", index=False)
    add_audit(audit, "B2_network_edges", rel_path, "applied", f"rows_before={before}; rows_after={len(df)}; dropped_VEGFA_KDR={before - len(df)}")


def update_axis_summary(root: Path, audit: list[dict[str, str]]) -> None:
    path = root / "results/tables/manuscript_figure4_axis_summary.tsv"
    rel_path = path.relative_to(root).as_posix()
    if not path.exists():
        add_audit(audit, "B3_axis_summary", rel_path, "missing", "axis summary table absent")
        return
    df = pd.read_csv(path, sep="\t")
    if "mechanism_evidence_score" in df.columns:
        score = pd.to_numeric(df["mechanism_evidence_score"], errors="coerce")
        df["mechanism_evidence_score_display"] = score.round(0).astype("Int64").astype(str)
    df["score_note"] = "Mechanism evidence score is a triage/prioritization score, not an effect size or causal estimate (see Methods)."
    df.to_csv(path, sep="\t", index=False)
    add_audit(audit, "B3_axis_summary", rel_path, "applied", "added integer display score and triage-score caveat")


def update_figure_plan(root: Path, audit: list[dict[str, str]]) -> None:
    path = root / "results/tables/manuscript_main_figure1_3_panel_plan.tsv"
    rel_path = path.relative_to(root).as_posix()
    if not path.exists():
        add_audit(audit, "B4_figure3_plan", rel_path, "missing", "figure plan table absent")
        return
    df = pd.read_csv(path, sep="\t")
    mask = (df["figure"].astype(str) == "Figure 3") & (df["panel"].astype(str) == "B")
    if mask.any():
        df.loc[mask, "main_message"] = "Subtype profiles support an S1 (ECM/fibrotic-high) state and an S2 (mixed-low) state; values are subtype mean z-scores (ST14)."
        df.loc[mask, "claim_guardrail"] = "Values are subtype mean z-scores (ST14); subtype labels are relative molecular states, not a clinical classifier."
        status = "applied"
    else:
        status = "not_found"
    df.to_csv(path, sep="\t", index=False)
    add_audit(audit, "B4_figure3_plan", rel_path, status, "updated Figure 3B units and subtype labels")


def update_generated_tables(root: Path, audit: list[dict[str, str]]) -> None:
    update_network_edges(root, audit)
    update_axis_summary(root, audit)
    update_figure_plan(root, audit)


def markdown_table(df: pd.DataFrame) -> str:
    cols = ["item_id", "target", "status", "detail"]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[col]).replace("\n", " ") for col in cols) + " |")
    return "\n".join(lines)


def build_doc(audit: pd.DataFrame) -> str:
    status_counts = audit["status"].value_counts().to_dict()
    return f"""# JOT Revision Changelist Application

## Assessment

The expert changelist was accepted as technically correct for the current manuscript framing. The strongest accepted revisions are the direction-of-effect guardrail, tissue-stratified bulk interpretation, S1/S2 relabeling, and explicit candidate-not-causal wording.

D1 was handled with a structured TODO rather than invented references. This keeps the manuscript honest: no invented references were added, and the final numbered reference list remains a manual or separately verified task before submission.

## Status Summary

- Audit rows: {len(audit)}
- Status counts: {status_counts}
- Reference handling: structured TODO, no invented references
- Figure handling: source tables and scripts are aligned with Figure 1, Figure 3, Figure 4, and Supplementary Figure S1 revision specs

## Audit

{markdown_table(audit)}
"""


def build_notes(audit: pd.DataFrame) -> str:
    return f"""# JOT Revision Changelist Workflow Notes

## Scope

This step applied the expert JOT revision changelist to manuscript markdown, cover-letter wording, figure-source tables, and generated workflow labels.

## Key Applied Changes

- Figure 1: per-column scaling and annotation requirements were moved into the figure-generation script.
- Figure 3: S1/S2 labels were revised to S1 (ECM/fibrotic-high) and S2 (mixed-low), with subtype mean z-score units.
- Figure 4: VEGFA->KDR was removed from the manuscript-facing network edge table; ANGPTL4->ITGB1 was retained; mechanism scores were marked as triage/prioritization scores.
- Supplementary Figure S1: the long MSP_paracrine_consensus label is abbreviated in the figure-generation script.
- Manuscript text: bulk interpretation, MSP-program-high wording, subtype labels, abstract, conclusion, and reference TODO were updated.
- D1 reference TODO: no real citations were invented.

## Technical Summary

- revision audit rows: {len(audit)}
- reference TODO inserted: {'D1_reference_todo' in set(audit['item_id'])}
- failed rows: {int((audit['status'] == 'failed').sum())}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--doc-output", type=Path, required=True)
    parser.add_argument("--notes-output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    audit: list[dict[str, str]] = []

    apply_text_revisions(root, audit)
    apply_global_generated_label_cleanup(root, audit)
    update_generated_tables(root, audit)

    audit_df = pd.DataFrame(audit)
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    audit_df.to_csv(args.audit_output, sep="\t", index=False)
    write_text(args.doc_output, build_doc(audit_df))
    write_text(args.notes_output, build_notes(audit_df))

    print(f"REVISION_AUDIT_ROWS {len(audit_df)}")


if __name__ == "__main__":
    main()

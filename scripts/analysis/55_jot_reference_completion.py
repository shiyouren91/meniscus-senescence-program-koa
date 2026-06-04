#!/usr/bin/env python
"""Complete JOT manuscript references and reproducibility placeholders."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


MANUSCRIPT_FILES = [
    "docs/manuscript/22_jot_anonymized_manuscript_draft.md",
    "docs/manuscript/15_msp_integrated_manuscript_draft.md",
]

METHOD_FILES = [
    "docs/manuscript/09_msp_full_methods_draft.md",
]

REFERENCES = [
    "Katz JN, Arant KR, Loeser RF. Diagnosis and Treatment of Hip and Knee Osteoarthritis: A Review. JAMA. 2021;325(6):568-578. doi:10.1001/jama.2020.22171.",
    "Ozeki N, Koga H, Sekiya I. Degenerative Meniscus in Knee Osteoarthritis: From Pathology to Treatment. Life (Basel). 2022;12(4):603. doi:10.3390/life12040603.",
    "Sun H, Wen X, Li H, Wu P, Gu M, Zhao X, et al. Single-cell RNA-seq analysis identifies meniscus progenitors and reveals the progression of meniscus degeneration. Ann Rheum Dis. 2020;79(3):408-417. doi:10.1136/annrheumdis-2019-215926.",
    "Fu W, Chen S, Yang R, Li C, Gao H, Li J, et al. Cellular features of localized microenvironments in human meniscal degeneration: a single-cell transcriptomic study. eLife. 2022;11:e79585. doi:10.7554/eLife.79585.",
    "Swahn H, Li K, Duffy T, Olmer M, D'Lima DD, Mondala TS, et al. Senescent cell population with ZEB1 transcription factor as its main regulator promotes osteoarthritis in cartilage and meniscus. Ann Rheum Dis. 2023;82(3):403-415. doi:10.1136/ard-2022-223227.",
    "Kotliar D, Veres A, Nagy MA, Tabrizi S, Hodis E, Melton DA, et al. Identifying gene expression programs of cell-type identity and cellular activity with single-cell RNA-Seq. eLife. 2019;8:e43803. doi:10.7554/eLife.43803.",
    "Saul D, Kosinsky RL, Atkinson EJ, Doolittle ML, Zhang X, LeBrasseur NK, et al. A new gene set identifies senescent cells and predicts senescence-associated pathways across tissues. Nat Commun. 2022;13(1):4827. doi:10.1038/s41467-022-32552-1.",
    "Fridman AL, Tainsky MA. Critical pathways in cellular senescence and immortalization revealed by gene expression profiling. Oncogene. 2008;27(46):5975-5987. doi:10.1038/onc.2008.213.",
    "Avelar RA, Ortega JG, Tacutu R, Tyler EJ, Bennett D, Binetti P, et al. A multidimensional systems biology analysis of cellular senescence in aging and disease. Genome Biol. 2020;21(1):91. doi:10.1186/s13059-020-01990-9.",
    "Basisty N, Kale A, Jeon OH, Kuehnemann C, Payne T, Rao C, et al. A proteomic atlas of senescence-associated secretomes for aging biomarker development. PLoS Biol. 2020;18(1):e3000599. doi:10.1371/journal.pbio.3000599.",
    "Jin S, Guerrero-Juarez CF, Zhang L, Chang I, Ramos R, Kuan CH, et al. Inference and analysis of cell-cell communication using CellChat. Nat Commun. 2021;12(1):1088. doi:10.1038/s41467-021-21246-9.",
    "Dimitrov D, Turei D, Garrido-Rodriguez M, Burmedi PL, Nagai JS, Boys C, et al. Comparison of methods and resources for cell-cell communication inference from single-cell RNA-Seq data. Nat Commun. 2022;13(1):3224. doi:10.1038/s41467-022-30755-0.",
    "Dimitrov D, Schafer PSL, Farr E, Rodriguez-Mier P, Lobentanzer S, Badia-I-Mompel P, et al. LIANA+ provides an all-in-one framework for cell-cell communication inference. Nat Cell Biol. 2024;26(9):1613-1622. doi:10.1038/s41556-024-01469-w.",
    "Browaeys R, Saelens W, Saeys Y. NicheNet: modeling intercellular communication by linking ligands to target genes. Nat Methods. 2020;17(2):159-162. doi:10.1038/s41592-019-0667-5.",
    "DerSimonian R, Laird N. Meta-analysis in clinical trials. Control Clin Trials. 1986;7(3):177-188. doi:10.1016/0197-2456(86)90046-2.",
]

REFERENCES_BLOCK = "## References\n\n" + "\n".join(
    f"{idx}. {ref}" for idx, ref in enumerate(REFERENCES, start=1)
) + "\n"

SUPPLEMENTARY_METHODS = """### Supplementary Methods: Reproducibility Details

Highly variable genes for the fibrochondrocyte cNMF input were selected with Scanpy's Seurat-flavor dispersion method using `n_top_genes=3000` and `batch_key=sample_label`. The cNMF gene universe then combined these 3000 HVGs with 128 recurrent or disease-skew program genes and 36 mandatory signature genes, yielding 3038 unique selected genes for the balanced discovery object.

Signature enrichment used curated panels for senescence arrest, SASP/ECM remodeling, angiogenesis or hypoxia, paracrine communication, fibrocartilage matrix, progenitor/interface states, generic stress, and immune, mural, endothelial, and cycling contamination controls. Senescence resources used to contextualize these panels included SenMayo, Fridman and Tainsky senescence signatures, CellAge, and a proteomic SASP atlas [7-10]. The exact program-level enrichment values are reported in ST03.

The MSP axis score was calculated as `1.15*senescence + 0.85*SASP + 0.75*ECM_remodeling + 1.05*communication + 0.25*fibrocartilage - 1.15*contamination - 0.20*generic_stress`. The final MSP rank score used for prioritization was `MSP_axis_score - 2.0*dominant_sample_fraction - 0.5*contamination_score + 1.0` for primary K settings. Candidate MSP-like programs additionally required `MSP_axis_score >= 6.0`, `communication_score >= 2.5`, senescence or SASP support, `contamination_score < 6.0`, and detection in at least eight samples.

Bulk meta-analysis FDR was controlled across the seven scored axes using Benjamini-Hochberg correction; tissue-stratified evidence grades should be treated as the primary bulk readout when comparator or tissue definitions differ across cohorts.
"""


TEXT_REPLACEMENTS = [
    (
        "Meniscal degeneration is increasingly recognized as an important contributor to the osteoarthritis joint environment, yet its transcriptional programs remain less systematically resolved than cartilage or synovium. The meniscus is also a fibrocartilaginous tissue with strong anatomical heterogeneity, making it difficult to separate inner-zone cartilage-like programs, outer-zone fibrous or vascular programs, and degeneration-associated responses.",
        "Knee osteoarthritis is a whole-joint disease involving cartilage, bone, synovium, and periarticular tissues [1]. Meniscal degeneration is increasingly recognized as an important contributor to the osteoarthritis joint environment [2], yet its transcriptional programs remain less systematically resolved than cartilage or synovium. The meniscus is also a fibrocartilaginous tissue with strong anatomical heterogeneity, making it difficult to separate inner-zone cartilage-like programs, outer-zone fibrous or vascular programs, and degeneration-associated responses. Prior human meniscus single-cell atlases have identified meniscal progenitor and degeneration-associated cell states [3,4].",
    ),
    (
        "Cellular senescence is a plausible contributor to this biology, but single-marker senescence analysis is poorly suited to single-cell data. Canonical markers such as CDKN1A, CDKN2A, and LMNB1 are sparse, context-dependent, and insufficient on their own. A stronger design is to define a meniscus senescence program (MSP) as a program-level, multi-gene cell-state axis and then test whether this axis retains meniscus-specific information beyond generic senescence signatures.",
        "Cellular senescence is a plausible contributor to this biology, including in osteoarthritis cartilage and meniscus [5], but single-marker senescence analysis is poorly suited to single-cell data. Canonical markers such as CDKN1A, CDKN2A, and LMNB1 are sparse, context-dependent, and insufficient on their own [7-10]. A stronger design is to define a meniscus senescence program (MSP) as a program-level, multi-gene cell-state axis and then test whether this axis retains meniscus-specific information beyond generic senescence signatures.",
    ),
    (
        "Our approach differs from prior work in three ways. First, in contrast to single-marker or hub-gene senescence analyses, we define the MSP as a multi-gene program-level cell state derived by consensus non-negative matrix factorization, which is better suited to the sparsity of single-cell senescence markers. Second, where generic senescence signatures (for example SenMayo or CellAge) capture pan-tissue aging, we test whether a meniscus-derived program retains fibrocartilage-specific information beyond these signatures. Third, rather than asserting a disease-up signature from one dataset, we impose explicit sample-aware and cross-tissue guardrails and report candidate axes with calibrated, validation-ready confidence. [TODO: add citations for prior meniscus scRNA-seq atlas, generic senescence gene sets, and cNMF.]",
        "Our approach differs from prior work in three ways. First, in contrast to single-marker or hub-gene senescence analyses, we define the MSP as a multi-gene program-level cell state derived by consensus non-negative matrix factorization [6], which is better suited to the sparsity of single-cell senescence markers. Second, where generic senescence signatures (for example SenMayo or CellAge) capture pan-tissue aging [7-10], we test whether a meniscus-derived program retains fibrocartilage-specific information beyond these signatures. Third, rather than asserting a disease-up signature from one dataset, we impose explicit sample-aware and cross-tissue guardrails and report candidate axes with calibrated, validation-ready confidence.",
    ),
    (
        "Here we developed an integrative transcriptomic workflow to nominate MSP-like fibrochondrocyte programs and evaluate their cross-context support. The analysis combines GSE220243 single-cell program discovery, author-processed HRA001986 meniscus projection, multi-tissue bulk validation, subtype analysis, and expression-based prioritization of candidate paracrine axes. The goal is not to claim causal mechanism from transcriptomic association, but to generate a traceable, validation-ready framework for meniscus-to-joint remodeling hypotheses in knee osteoarthritis.",
        "Here we developed an integrative transcriptomic workflow to nominate MSP-like fibrochondrocyte programs and evaluate their cross-context support. The analysis combines GSE220243 single-cell program discovery [5], author-processed HRA001986 meniscus projection [4], multi-tissue bulk validation, subtype analysis, and expression-based prioritization of candidate paracrine axes. The goal is not to claim causal mechanism from transcriptomic association, but to generate a traceable, validation-ready framework for meniscus-to-joint remodeling hypotheses in knee osteoarthritis.",
    ),
    (
        "This final layer is deliberately prospective. The present study nominates candidate paracrine axes and a validation strategy; it does not establish that MSP ligands have disease-driving activity. MIF_CD74, ANGPTL4_integrin, and VEGF are therefore leading candidate axes that require formal CellChat/LIANA/NicheNet consensus, protein evidence, and perturbation experiments before any causal interpretation.",
        "This final layer is deliberately prospective. The present study nominates candidate paracrine axes and a validation strategy; it does not establish that MSP ligands have disease-driving activity. MIF_CD74, ANGPTL4_integrin, and VEGF are therefore leading candidate axes that require formal CellChat/LIANA/NicheNet consensus [11-14], protein evidence, and perturbation experiments before any causal interpretation.",
    ),
    (
        "A central conceptual contribution is the definition of MSP as program-level biology. This is important because classical senescence markers such as CDKN1A or CDKN2A are sparse and context-dependent in single-cell data [TODO: cite], and generic senescence signatures (for example SenMayo or CellAge) can miss tissue-specific fibrocartilage features [TODO: cite]. The cNMF strategy allowed senescence-inflammatory, senescence-paracrine, angiogenic-paracrine, fibrocartilage matrix, and fibrotic remodeling programs to be interpreted together. The term MSP-like remains deliberate: several high-ranking programs were sample-aware and donor-skewed, so the evidence supports candidate meniscus senescence biology rather than a fixed disease state.",
        "A central conceptual contribution is the definition of MSP as program-level biology. This is important because classical senescence markers such as CDKN1A or CDKN2A are sparse and context-dependent in single-cell data, and generic senescence signatures (for example SenMayo or CellAge) can miss tissue-specific fibrocartilage features [7-10]. The cNMF strategy [6] allowed senescence-inflammatory, senescence-paracrine, angiogenic-paracrine, fibrocartilage matrix, and fibrotic remodeling programs to be interpreted together. The term MSP-like remains deliberate: several high-ranking programs were sample-aware and donor-skewed, so the evidence supports candidate meniscus senescence biology rather than a fixed disease state.",
    ),
    (
        "Each leading axis is not a validated mechanism until formal CellChat/LIANA/NicheNet consensus, protein-level evidence, and pathway-specific perturbation align.",
        "Each leading axis is not a validated mechanism until formal CellChat/LIANA/NicheNet consensus [11-14], protein-level evidence, and pathway-specific perturbation align.",
    ),
    (
        "First, formal CellChat/LIANA/NicheNet analyses should determine whether the expression-prioritized axes show method-consensus support.",
        "First, formal CellChat/LIANA/NicheNet analyses [11-14] should determine whether the expression-prioritized axes show method-consensus support.",
    ),
    (
        "Public single-cell and bulk transcriptomic resources were organized before analysis. GSE220243 was used as the primary runnable single-cell RNA-seq dataset for meniscus fibrochondrocyte discovery. The author-processed HRA001986 h5ad files were used as an independent meniscus single-cell reference for context projection.",
        "Public single-cell and bulk transcriptomic resources were organized before analysis. GSE220243 was used as the primary runnable single-cell RNA-seq dataset for meniscus fibrochondrocyte discovery [5]. The author-processed HRA001986 h5ad files were used as an independent meniscus single-cell reference for context projection [4].",
    ),
    (
        "Candidate MSP-like programs were discovered from the fibrochondrocyte subset using cNMF. The balanced discovery object contained 54882 selected cells and 3038 selected genes (highly variable genes selected by dispersion, with mitochondrial, ribosomal, and cell-cycle genes excluded; see Supplementary Methods for exact thresholds).",
        "Candidate MSP-like programs were discovered from the fibrochondrocyte subset using cNMF [6]. The balanced discovery object contained 54882 selected cells and 3038 selected genes (3000 Scanpy Seurat-flavor HVGs plus recurrent/disease-skew program genes and mandatory signature genes; see Supplementary Methods).",
    ),
    (
        "Cross-cohort evidence was summarized by random-effects (DerSimonian-Laird) meta-analysis, reporting effect estimates, 95% confidence intervals, tau2, I2 heterogeneity, and direction consistency, with Benjamini-Hochberg FDR applied across the seven scored axes.",
        "Cross-cohort evidence was summarized by random-effects (DerSimonian-Laird) meta-analysis [15], reporting effect estimates, 95% confidence intervals, tau2, I2 heterogeneity, and direction consistency, with Benjamini-Hochberg FDR applied across the seven scored axes.",
    ),
    (
        "The validation roadmap is prospective. It includes formal CellChat, LIANA, and NicheNet consensus analyses, synovial-fluid or tissue protein validation, and senescent meniscus conditioned-medium perturbation assays.",
        "The validation roadmap is prospective. It includes formal CellChat, LIANA, and NicheNet consensus analyses [11-14], synovial-fluid or tissue protein validation, and senescent meniscus conditioned-medium perturbation assays.",
    ),
    (
        "The current analysis did not perform Hotspot validation, RNA velocity, Mendelian randomization, or formal CellChat/LIANA/NicheNet consensus as completed causal evidence.",
        "The current analysis did not perform Hotspot validation, RNA velocity, Mendelian randomization, or formal CellChat/LIANA/NicheNet consensus [11-14] as completed causal evidence.",
    ),
    (
        "This study re-analyzed public and author-provided processed transcriptomic datasets. No new human or animal specimens were collected for this analysis. Source-study ethics statements should be cited as required by the journal.",
        "This study re-analyzed public and author-provided processed transcriptomic datasets [3-5]. No new human or animal specimens were collected for this analysis; ethics approval and consent were covered by the original source studies.",
    ),
    (
        "This study re-analyzes public and author-provided processed transcriptomic datasets. Ethics approvals for original sample collection should be cited from the source studies where required by the target journal. Author contributions, conflicts of interest, funding, acknowledgements, and any data-use restrictions require manual completion before submission.",
        "This study re-analyzes public and author-provided processed transcriptomic datasets [3-5]. Ethics approvals for original sample collection are reported in the source studies. Author contributions, conflicts of interest, funding, acknowledgements, and any data-use restrictions are tracked in the JOT title-page and author-confirmation files.",
    ),
]

COMMON_MAIN_REPLACEMENT_INDICES = list(range(0, 13))
JOT_ONLY_REPLACEMENT_INDICES = [13]
INTEGRATED_ONLY_REPLACEMENT_INDICES = [14]
METHOD_REPLACEMENT_INDICES = [8, 9, 10, 11, 12]


def has_extended_reference_list(text: str) -> bool:
    round3_extended = "23. Chen G, Tai K, Dai G." in text
    round4_extended = "23. DerSimonian R, Laird N." in text and "18. Chen G, Tai K, Dai G." in text
    return round3_extended or round4_extended


def has_round4_revision_state(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "23. DerSimonian R, Laird N.",
            "meniscal progenitor and degeneration-associated cell states [5,6]",
            "derived by consensus non-negative matrix factorization [13]",
            "using cNMF [13]",
            "random-effects (DerSimonian-Laird) meta-analysis [23]",
            "formal CellChat/LIANA/NicheNet consensus [14-17]",
        )
    )


def replace_once(text: str, old: str, new: str, rows: list[dict[str, str]], item: str) -> str:
    if old not in text:
        if new in text:
            rows.append({"item": item, "status": "already_updated", "detail": new[:160]})
        elif has_extended_reference_list(text) and any(
            token in item for token in ("_text_01", "_text_02", "_text_06")
        ):
            rows.append({"item": item, "status": "superseded_by_later_round", "detail": "later literature enrichment already revised this passage"})
        else:
            rows.append({"item": item, "status": "not_found", "detail": old[:120]})
        return text
    rows.append({"item": item, "status": "updated", "detail": new[:160]})
    return text.replace(old, new, 1)


def replace_references(text: str, rows: list[dict[str, str]], item_prefix: str) -> str:
    if has_extended_reference_list(text):
        rows.append({"item": f"{item_prefix}_references", "status": "already_updated", "detail": "extended reference list preserved"})
        return text
    marker = "## References"
    if marker in text:
        before = text.split(marker, 1)[0].rstrip()
        rows.append({"item": f"{item_prefix}_references", "status": "updated", "detail": f"{len(REFERENCES)} numbered references"})
        return before + "\n\n" + REFERENCES_BLOCK
    rows.append({"item": f"{item_prefix}_references", "status": "added", "detail": f"{len(REFERENCES)} numbered references"})
    return text.rstrip() + "\n\n" + REFERENCES_BLOCK


def replace_supplementary_methods(text: str, rows: list[dict[str, str]], item_prefix: str) -> str:
    start = "### Supplementary Methods: Reproducibility Details Pending Final Citation"
    if start not in text:
        if "### Supplementary Methods: Reproducibility Details" in text and "MSP axis score was calculated as" in text:
            rows.append({"item": f"{item_prefix}_supp_methods", "status": "already_updated", "detail": "supplementary methods block already completed"})
        else:
            rows.append({"item": f"{item_prefix}_supp_methods", "status": "not_found", "detail": "supplementary methods placeholder not present"})
        return text
    end_marker = "\n\nBulk meta-analysis FDR was controlled across the seven scored axes using Benjamini-Hochberg correction; tissue-stratified evidence grades should be treated as the primary bulk readout when comparator or tissue definitions differ across cohorts."
    start_index = text.index(start)
    end_index = text.index(end_marker, start_index) + len(end_marker)
    rows.append({"item": f"{item_prefix}_supp_methods", "status": "updated", "detail": "replaced HVG/signature/rank-score TODO block"})
    return text[:start_index] + SUPPLEMENTARY_METHODS.rstrip() + text[end_index:]


def complete_text(
    text: str,
    item_prefix: str,
    rows: list[dict[str, str]],
    include_refs: bool,
    replacement_indices: list[int],
    include_supplementary_methods: bool = True,
) -> str:
    if has_round4_revision_state(text):
        rows.append({"item": f"{item_prefix}_round4_guardrail", "status": "superseded_by_round4", "detail": "round4 citation order detected; reference-completion replacements skipped"})
        return text
    for index in replacement_indices:
        old, new = TEXT_REPLACEMENTS[index]
        text = replace_once(text, old, new, rows, f"{item_prefix}_text_{index + 1:02d}")
    if include_supplementary_methods:
        text = replace_supplementary_methods(text, rows, item_prefix)
    if include_refs:
        text = replace_references(text, rows, item_prefix)
    return text


def write_audit(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "status", "detail"], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_docs(doc_output: Path, notes_output: Path, rows: list[dict[str, str]]) -> None:
    updated = sum(row["status"] in {"updated", "added"} for row in rows)
    already_updated = sum(row["status"] == "already_updated" for row in rows)
    unresolved = [row for row in rows if row["status"] == "not_found"]
    lines = [
        "# JOT Reference Completion",
        "",
        f"- Numbered references inserted: {len(REFERENCES)}",
        f"- Audit items updated or added: {updated}",
        f"- Audit items already complete on rerun: {already_updated}",
        f"- Not-found items: {len(unresolved)}",
        "- Repository URL/DOI placeholder intentionally retained for the author to complete before submission.",
        "",
        "## Reference coverage",
        "",
        "- OA and degenerative meniscus background: references 1-2",
        "- Human meniscus single-cell sources: references 3-5",
        "- cNMF program discovery method: reference 6",
        "- Senescence/SASP resources: references 7-10",
        "- Cell-cell communication tools and method benchmarking: references 11-14",
        "- Random-effects meta-analysis: reference 15",
    ]
    if unresolved:
        lines.extend(["", "## Not Found During Scripted Replacement", ""])
        lines.extend(f"- {row['item']}: {row['detail']}" for row in unresolved)

    for output in (doc_output, notes_output):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--audit-output", required=True)
    parser.add_argument("--doc-output", required=True)
    parser.add_argument("--notes-output", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root)
    rows: list[dict[str, str]] = []

    for relative in MANUSCRIPT_FILES:
        path = project_root / relative
        text = path.read_text(encoding="utf-8")
        indices = COMMON_MAIN_REPLACEMENT_INDICES.copy()
        if relative.endswith("22_jot_anonymized_manuscript_draft.md"):
            indices.extend(JOT_ONLY_REPLACEMENT_INDICES)
        if relative.endswith("15_msp_integrated_manuscript_draft.md"):
            indices.extend(INTEGRATED_ONLY_REPLACEMENT_INDICES)
        updated = complete_text(text, relative, rows, include_refs=True, replacement_indices=indices)
        path.write_text(updated, encoding="utf-8", newline="\n")

    for relative in METHOD_FILES:
        path = project_root / relative
        text = path.read_text(encoding="utf-8")
        updated = complete_text(
            text,
            relative,
            rows,
            include_refs=False,
            replacement_indices=METHOD_REPLACEMENT_INDICES,
            include_supplementary_methods=False,
        )
        path.write_text(updated, encoding="utf-8", newline="\n")

    write_audit(Path(args.audit_output), rows)
    write_docs(Path(args.doc_output), Path(args.notes_output), rows)

    print(f"REFERENCE_ROWS {len(REFERENCES)}")
    print(f"AUDIT_ROWS {len(rows)}")
    print(f"WROTE {args.audit_output}")
    print(f"WROTE {args.doc_output}")
    print(f"WROTE {args.notes_output}")


if __name__ == "__main__":
    main()

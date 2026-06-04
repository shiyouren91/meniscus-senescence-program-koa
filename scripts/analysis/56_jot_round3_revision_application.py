#!/usr/bin/env python
"""Apply round-3 expert polish and literature enrichment to the JOT manuscript."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


PRIMARY_MANUSCRIPTS = [
    "docs/manuscript/22_jot_anonymized_manuscript_draft.md",
    "docs/manuscript/15_msp_integrated_manuscript_draft.md",
]

SUPPORTING_TEXT_FILES = [
    "docs/manuscript/09_msp_full_methods_draft.md",
    "docs/manuscript/11_msp_discussion_draft.md",
]

NEW_REFERENCES = [
    "16. Coryell PR, Diekman BO, Loeser RF. Mechanisms and therapeutic implications of cellular senescence in osteoarthritis. Nat Rev Rheumatol. 2021;17(1):47-57. doi:10.1038/s41584-020-00533-7.",
    "17. Whittaker JL, Losciale JM, Juhl CB, Thorlund JB, Lundberg M, Truong LK, et al. Risk factors for knee osteoarthritis after traumatic knee injury: a systematic review and meta-analysis of randomised controlled trials and cohort studies for the OPTIKNEE Consensus. Br J Sports Med. 2022;56(24):1406-1421. doi:10.1136/bjsports-2022-105496.",
    "18. Ma Z, Vyhlidal MJ, Li DX, Adesida AB. Mechano-bioengineering of the knee meniscus. Am J Physiol Cell Physiol. 2022;323(6):C1652-C1663. doi:10.1152/ajpcell.00336.2022.",
    "19. Deng M, Jiang Y, Chen Z, Chen K, Cao N, Huang Y, et al. Senescent synovial intimal fibroblasts aggravate osteoarthritis by regulating macrophage polarization and chondrocyte phenotype through the ANGPTL4-alpha5beta1 axis. Adv Sci (Weinh). 2026;13(13):e18056. doi:10.1002/advs.202518056.",
    "20. Peng R, Yu B, Zhang L, Xue Z, Yao L, Yang Q, et al. Targeted Inhibition of CD74+ Macrophages by Luteolin via CEBPB/P65 Signaling Ameliorates Osteoarthritis Progression. Adv Sci (Weinh). 2025;13(7):e08472. doi:10.1002/advs.202508472.",
    "21. Jia C, Li X, Pan J, Ma H, Wu D, Lu H, et al. Silencing of angiopoietin-like protein 4 (Angptl4) decreases inflammation, extracellular matrix degradation, and apoptosis in osteoarthritis via the sirtuin 1/NF-kappaB pathway. Oxid Med Cell Longev. 2022;2022:1135827. doi:10.1155/2022/1135827.",
    "22. Qian JJ, Xu Q, Xu WM, Cai R, Huang GC. Expression of VEGF-A signaling pathway in cartilage of ACLT-induced osteoarthritis mouse model. J Orthop Surg Res. 2021;16(1):379. doi:10.1186/s13018-021-02528-w.",
    "23. Chen G, Tai K, Dai G. Lineage plasticity and signal dysregulation define the cellular trajectory of osteoarthritis progression. Clin Exp Med. 2025;26(1):41. doi:10.1007/s10238-025-01947-x.",
]

REPLACEMENTS = [
    {
        "id": "A1_cross_context_echo",
        "old": "This heterogeneity is biologically informative: it argues against a simple universal OA-up MSP model and instead supports a context-dependent meniscus-interface remodeling hypothesis.",
        "new": "Consistent with the tissue-stratified Results, only the fibrocartilage-matrix remodeling axis showed strong, consistent disease-associated bulk signal (I2 = 30%), whereas the MSP paracrine, angiogenic, and inflammatory axes were directionally heterogeneous. This heterogeneity is biologically informative: it argues against a simple universal OA-up MSP model and instead supports a context-dependent meniscus-interface remodeling hypothesis.",
    },
    {
        "id": "A2_abstract_axis_basis",
        "old": "Integrated evidence nominated MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes for prioritized validation.",
        "new": "On the basis of ligand-receptor plausibility, single-cell sender-receiver context, and S1-high receiver-target concordance (rather than bulk direction), integrated evidence nominated MIF_CD74, ANGPTL4_integrin, and VEGF as leading candidate paracrine axes for prioritized validation.",
    },
    {
        "id": "A3_limitations_deduplicate",
        "old": " Planned validation items include formal CellChat/LIANA/NicheNet consensus; synovial-fluid or tissue protein validation; conditioned-medium perturbation assays. Not-performed current-analysis items include Hotspot independent co-expression validation; RNA velocity directionality analysis; Mendelian randomization causal inference.",
        "new": "",
    },
    {
        "id": "A4a_declarative_statistical_caution",
        "old": "The manuscript should maintain candidate/not causal language throughout the Results and figure legends.",
        "new": "Candidate and not-causal language is therefore used throughout the Results and figure legends.",
    },
    {
        "id": "A4b_declarative_supp_fig_s1",
        "old": "Supplementary Figure S1 should collect guardrail and sensitivity evidence, including secondary candidate axes, exploratory reserve axes, bulk heterogeneity, covariate and leave-one checks, and claim-language constraints. This supplementary material should make explicit why candidate and not causal language is used throughout the manuscript.",
        "new": "Supplementary Figure S1 collects guardrail and sensitivity evidence, including secondary candidate axes, exploratory reserve axes, bulk heterogeneity, covariate and leave-one checks, and claim-language constraints. These panels make explicit why candidate and not-causal language is used throughout the manuscript.",
    },
    {
        "id": "B1_intro_meniscus_biomechanics",
        "old": "The meniscus is also a fibrocartilaginous tissue with strong anatomical heterogeneity, making it difficult to separate inner-zone cartilage-like programs, outer-zone fibrous or vascular programs, and degeneration-associated responses.",
        "new": "The meniscus is a load-bearing fibrocartilaginous tissue, and meniscal injury or meniscectomy is an established risk factor for subsequent knee OA [17,18]. It also shows strong anatomical heterogeneity, making it difficult to separate inner-zone cartilage-like programs, outer-zone fibrous or vascular programs, and degeneration-associated responses.",
    },
    {
        "id": "B2_intro_senescence_review",
        "old": "Cellular senescence is a plausible contributor to this biology, including in osteoarthritis cartilage and meniscus [5], but single-marker senescence analysis is poorly suited to single-cell data.",
        "new": "Cellular senescence is a plausible contributor to this biology, including in osteoarthritis cartilage and meniscus [5,16], but single-marker senescence analysis is poorly suited to single-cell data.",
    },
    {
        "id": "B3_candidate_axis_corroboration",
        "old": "MIF_CD74 suggests a link to immune/myeloid activation; ANGPTL4_integrin suggests a matrix-adhesion and remodeling interface; VEGF suggests an angiogenic receiver context.",
        "new": "Each axis is consistent with independent OA literature: CD74+ pro-inflammatory synovial macrophages have been defined by single-cell profiling of human OA synovium and proposed as a therapeutic target [20]; senescent synovial fibroblasts have been reported to drive macrophage polarization and chondrocyte phenotype through an ANGPTL4-alpha5beta1 (ITGA5/ITGB1) axis, with EGR1 and ATF3 as senescence regulators [19] - notably, EGR1, ATF3, and NR4A family genes are among the top loadings of our senescence-inflammatory program (ST01); ANGPTL4 itself promotes chondrocyte inflammation and matrix degradation in OA models [21]; and VEGFA/VEGFR2 signaling tracks cartilage angiogenesis and OA severity [22]. MIF_CD74 thus suggests a link to immune/myeloid activation; ANGPTL4_integrin suggests a matrix-adhesion and remodeling interface; VEGF suggests an angiogenic receiver context.",
    },
    {
        "id": "B4_program_level_trajectory_comparator",
        "old": "The term MSP-like remains deliberate: several high-ranking programs were sample-aware and donor-skewed, so the evidence supports candidate meniscus senescence biology rather than a fixed disease state.",
        "new": "This program-level view complements single-cell OA studies that resolve chondrocyte lineage plasticity and signaling dysregulation (for example HIF1A-ANGPTL4 trajectories) during disease progression [23]. The term MSP-like remains deliberate: several high-ranking programs were sample-aware and donor-skewed, so the evidence supports candidate meniscus senescence biology rather than a fixed disease state.",
    },
    {
        "id": "B5_future_validation_senolytic_anchor",
        "old": "Third, senescent meniscus conditioned-medium experiments should test whether blockade of MIF_CD74, ANGPTL4_integrin, or VEGF alters inflammatory, angiogenic, or matrix-remodeling readouts in receiver cells.",
        "new": "Third, senescent meniscus conditioned-medium experiments should test whether blockade of MIF_CD74, ANGPTL4_integrin, or VEGF alters inflammatory, angiogenic, or matrix-remodeling readouts in receiver cells; senescence-directed perturbation (e.g. senolytic depletion) provides a complementary test of whether SASP-bearing meniscal cells are the relevant senders [16].",
    },
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def has_round4_reference_order(text: str) -> bool:
    return "23. DerSimonian R, Laird N." in text and "3. Whittaker JL" in text


def has_round4_program_sentence(text: str) -> bool:
    return "during disease progression [18]. The term MSP-like remains deliberate" in text


def replace_text(text: str, old: str, new: str, item: str, rows: list[dict[str, str]], required: bool) -> str:
    if old in text:
        rows.append({"item": item, "status": "updated", "detail": new[:180] if new else "deleted duplicated text"})
        return text.replace(old, new, 1)
    if not new:
        rows.append({"item": item, "status": "already_updated", "detail": "delete-only text is already absent"})
        return text
    if new and new in text:
        rows.append({"item": item, "status": "already_updated", "detail": new[:180]})
        return text
    if required:
        rows.append({"item": item, "status": "not_found", "detail": old[:180]})
    return text


def append_references(text: str, item: str, rows: list[dict[str, str]]) -> str:
    if "23. Chen G, Tai K, Dai G." in text or has_round4_reference_order(text):
        rows.append({"item": item, "status": "already_updated", "detail": "extended reference list already present"})
        return text
    anchor = "15. DerSimonian R, Laird N. Meta-analysis in clinical trials. Control Clin Trials. 1986;7(3):177-188. doi:10.1016/0197-2456(86)90046-2."
    replacement = anchor + "\n" + "\n".join(NEW_REFERENCES)
    return replace_text(text, anchor, replacement, item, rows, required=True)


def apply_to_primary(path: Path, rows: list[dict[str, str]]) -> None:
    text = read_text(path)
    if has_round4_reference_order(text):
        rows.append({"item": f"{path.name}_round4_guardrail", "status": "superseded_by_round4", "detail": "round4 reference order detected; round3 text replacements skipped"})
        write_text(path, text)
        return
    for replacement in REPLACEMENTS:
        text = replace_text(
            text,
            replacement["old"],
            replacement["new"],
            f"{path.name}_{replacement['id']}",
            rows,
            required=True,
        )
    text = append_references(text, f"{path.name}_B0_append_references", rows)
    write_text(path, text)


def apply_to_supporting(path: Path, rows: list[dict[str, str]]) -> None:
    text = read_text(path)
    if has_round4_program_sentence(text):
        rows.append({"item": f"{path.name}_round4_guardrail", "status": "superseded_by_round4", "detail": "round4 program-level comparator detected; round3 text replacements skipped"})
        write_text(path, text)
        return
    for replacement in REPLACEMENTS:
        text = replace_text(
            text,
            replacement["old"],
            replacement["new"],
            f"{path.name}_{replacement['id']}",
            rows,
            required=False,
        )
    write_text(path, text)


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "status", "detail"], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_docs(doc_output: Path, notes_output: Path, rows: list[dict[str, str]]) -> None:
    updated = sum(row["status"] == "updated" for row in rows)
    already = sum(row["status"] == "already_updated" for row in rows)
    not_found = sum(row["status"] == "not_found" for row in rows)
    lines = [
        "# JOT Round 3 Revision Application",
        "",
        "## Judgement",
        "",
        "- Part A polish items were accepted and applied.",
        "- Part B literature enrichment was accepted after DOI metadata review, with corrected OPTIKNEE title and Advanced Science article-number formatting.",
        "- Part C items were not auto-completed because they require author action: repository URL/DOI deposition and final confirmation/deletion of bracketed declaration notes.",
        "",
        "## Applied Items",
        "",
        f"- Updated rows: {updated}",
        f"- Already complete rows on rerun: {already}",
        f"- Not-found rows: {not_found}",
        "- New references appended as #16-#23.",
        "",
        "## Manual Items Left For Author",
        "",
        "- Insert the final repository URL or DOI in Data and Code Availability.",
        "- Confirm COI, ethics wording, and GenAI-use declaration in the title page/declarations, then remove the bracketed confirmation notes.",
    ]
    doc_output.parent.mkdir(parents=True, exist_ok=True)
    notes_output.parent.mkdir(parents=True, exist_ok=True)
    write_text(doc_output, "\n".join(lines) + "\n")
    write_text(notes_output, "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--audit-output", required=True)
    parser.add_argument("--doc-output", required=True)
    parser.add_argument("--notes-output", required=True)
    args = parser.parse_args()

    root = Path(args.project_root)
    rows: list[dict[str, str]] = []

    for relative in PRIMARY_MANUSCRIPTS:
        apply_to_primary(root / relative, rows)
    for relative in SUPPORTING_TEXT_FILES:
        apply_to_supporting(root / relative, rows)

    rows.append({"item": "C1_repository_url_or_doi", "status": "manual_author_action", "detail": "Repository URL/DOI placeholder intentionally retained."})
    rows.append({"item": "C2_declaration_brackets", "status": "manual_author_action", "detail": "Bracketed title-page/declaration confirmation notes intentionally retained."})

    write_tsv(Path(args.audit_output), rows)
    write_docs(Path(args.doc_output), Path(args.notes_output), rows)

    print(f"ROUND3_AUDIT_ROWS {len(rows)}")
    print(f"WROTE {args.audit_output}")
    print(f"WROTE {args.doc_output}")
    print(f"WROTE {args.notes_output}")


if __name__ == "__main__":
    main()

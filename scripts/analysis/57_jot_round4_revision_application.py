#!/usr/bin/env python
"""Apply round-4 defect fixes and Vancouver reference renumbering."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


PRIMARY_MANUSCRIPTS = [
    "docs/manuscript/22_jot_anonymized_manuscript_draft.md",
    "docs/manuscript/15_msp_integrated_manuscript_draft.md",
]

SUPPORTING_TEXT_FILES = [
    "docs/manuscript/09_msp_full_methods_draft.md",
    "docs/manuscript/11_msp_discussion_draft.md",
]

OLD_TO_NEW = {
    1: 1,
    2: 2,
    3: 5,
    4: 6,
    5: 7,
    6: 13,
    7: 9,
    8: 10,
    9: 11,
    10: 12,
    11: 14,
    12: 15,
    13: 16,
    14: 17,
    15: 23,
    16: 8,
    17: 3,
    18: 4,
    19: 20,
    20: 19,
    21: 21,
    22: 22,
    23: 18,
}

CROSS_SENTENCE = "Consistent with the tissue-stratified Results, only the fibrocartilage-matrix remodeling axis showed strong, consistent disease-associated bulk signal (I2 = 30%), whereas the MSP paracrine, angiogenic, and inflammatory axes were directionally heterogeneous."

PROGRAM_SENTENCE_OLD = "This program-level view complements single-cell OA studies that resolve chondrocyte lineage plasticity and signaling dysregulation (for example HIF1A-ANGPTL4 trajectories) during disease progression [23]."
PROGRAM_SENTENCE_NEW = "This program-level view complements single-cell OA studies that resolve chondrocyte lineage plasticity and signaling dysregulation (for example HIF1A-ANGPTL4 trajectories) during disease progression [18]."
PROGRAM_SENTENCE_BASE = "This program-level view complements single-cell OA studies that resolve chondrocyte lineage plasticity and signaling dysregulation (for example HIF1A-ANGPTL4 trajectories) during disease progression"
PROGRAM_SENTENCE_ANY_CITE = re.compile(rf"(?:{re.escape(PROGRAM_SENTENCE_BASE)} \[\d+\]\.\s*)+")

ROUND3_CONTEXT_PATTERNS = (
    "meniscectomy is an established risk factor for subsequent knee OA [17,18]",
    "including in osteoarthritis cartilage and meniscus [5,16]",
    "generic senescence signatures (for example SenMayo or CellAge) can miss tissue-specific fibrocartilage features [7-10]",
    "The cNMF strategy [6]",
    "using cNMF [6]",
    "CellChat/LIANA/NicheNet consensus [11-14]",
    "CellChat, LIANA, and NicheNet consensus analyses [11-14]",
    "formal CellChat/LIANA/NicheNet analyses [11-14]",
    "meta-analysis [15]",
    "source studies [3-5]",
    "primary runnable single-cell RNA-seq dataset for meniscus fibrochondrocyte discovery [5]",
    "independent meniscus single-cell reference for context projection [4]",
    "proposed as a therapeutic target [20]; senescent synovial fibroblasts",
    "through an ANGPTL4-alpha5beta1 (ITGA5/ITGB1) axis, with EGR1 and ATF3 as senescence regulators [19]",
    "senolytic depletion) provides a complementary test of whether SASP-bearing meniscal cells are the relevant senders [16]",
    PROGRAM_SENTENCE_OLD,
)

REFERENCE_BLOCK = """1. Katz JN, Arant KR, Loeser RF. Diagnosis and Treatment of Hip and Knee Osteoarthritis: A Review. JAMA. 2021;325(6):568-578. doi:10.1001/jama.2020.22171.
2. Ozeki N, Koga H, Sekiya I. Degenerative Meniscus in Knee Osteoarthritis: From Pathology to Treatment. Life (Basel). 2022;12(4):603. doi:10.3390/life12040603.
3. Whittaker JL, Losciale JM, Juhl CB, Thorlund JB, Lundberg M, Truong LK, et al. Risk factors for knee osteoarthritis after traumatic knee injury: a systematic review and meta-analysis of randomised controlled trials and cohort studies for the OPTIKNEE Consensus. Br J Sports Med. 2022;56(24):1406-1421. doi:10.1136/bjsports-2022-105496.
4. Ma Z, Vyhlidal MJ, Li DX, Adesida AB. Mechano-bioengineering of the knee meniscus. Am J Physiol Cell Physiol. 2022;323(6):C1652-C1663. doi:10.1152/ajpcell.00336.2022.
5. Sun H, Wen X, Li H, Wu P, Gu M, Zhao X, et al. Single-cell RNA-seq analysis identifies meniscus progenitors and reveals the progression of meniscus degeneration. Ann Rheum Dis. 2020;79(3):408-417. doi:10.1136/annrheumdis-2019-215926.
6. Fu W, Chen S, Yang R, Li C, Gao H, Li J, et al. Cellular features of localized microenvironments in human meniscal degeneration: a single-cell transcriptomic study. eLife. 2022;11:e79585. doi:10.7554/eLife.79585.
7. Swahn H, Li K, Duffy T, Olmer M, D'Lima DD, Mondala TS, et al. Senescent cell population with ZEB1 transcription factor as its main regulator promotes osteoarthritis in cartilage and meniscus. Ann Rheum Dis. 2023;82(3):403-415. doi:10.1136/ard-2022-223227.
8. Coryell PR, Diekman BO, Loeser RF. Mechanisms and therapeutic implications of cellular senescence in osteoarthritis. Nat Rev Rheumatol. 2021;17(1):47-57. doi:10.1038/s41584-020-00533-7.
9. Saul D, Kosinsky RL, Atkinson EJ, Doolittle ML, Zhang X, LeBrasseur NK, et al. A new gene set identifies senescent cells and predicts senescence-associated pathways across tissues. Nat Commun. 2022;13(1):4827. doi:10.1038/s41467-022-32552-1.
10. Fridman AL, Tainsky MA. Critical pathways in cellular senescence and immortalization revealed by gene expression profiling. Oncogene. 2008;27(46):5975-5987. doi:10.1038/onc.2008.213.
11. Avelar RA, Ortega JG, Tacutu R, Tyler EJ, Bennett D, Binetti P, et al. A multidimensional systems biology analysis of cellular senescence in aging and disease. Genome Biol. 2020;21(1):91. doi:10.1186/s13059-020-01990-9.
12. Basisty N, Kale A, Jeon OH, Kuehnemann C, Payne T, Rao C, et al. A proteomic atlas of senescence-associated secretomes for aging biomarker development. PLoS Biol. 2020;18(1):e3000599. doi:10.1371/journal.pbio.3000599.
13. Kotliar D, Veres A, Nagy MA, Tabrizi S, Hodis E, Melton DA, et al. Identifying gene expression programs of cell-type identity and cellular activity with single-cell RNA-Seq. eLife. 2019;8:e43803. doi:10.7554/eLife.43803.
14. Jin S, Guerrero-Juarez CF, Zhang L, Chang I, Ramos R, Kuan CH, et al. Inference and analysis of cell-cell communication using CellChat. Nat Commun. 2021;12(1):1088. doi:10.1038/s41467-021-21246-9.
15. Dimitrov D, Turei D, Garrido-Rodriguez M, Burmedi PL, Nagai JS, Boys C, et al. Comparison of methods and resources for cell-cell communication inference from single-cell RNA-Seq data. Nat Commun. 2022;13(1):3224. doi:10.1038/s41467-022-30755-0.
16. Dimitrov D, Schafer PSL, Farr E, Rodriguez-Mier P, Lobentanzer S, Badia-I-Mompel P, et al. LIANA+ provides an all-in-one framework for cell-cell communication inference. Nat Cell Biol. 2024;26(9):1613-1622. doi:10.1038/s41556-024-01469-w.
17. Browaeys R, Saelens W, Saeys Y. NicheNet: modeling intercellular communication by linking ligands to target genes. Nat Methods. 2020;17(2):159-162. doi:10.1038/s41592-019-0667-5.
18. Chen G, Tai K, Dai G. Lineage plasticity and signal dysregulation define the cellular trajectory of osteoarthritis progression. Clin Exp Med. 2025;26(1):41. doi:10.1007/s10238-025-01947-x.
19. Peng R, Yu B, Zhang L, Xue Z, Yao L, Yang Q, et al. Targeted Inhibition of CD74+ Macrophages by Luteolin via CEBPB/P65 Signaling Ameliorates Osteoarthritis Progression. Adv Sci (Weinh). 2025;13(7):e08472. doi:10.1002/advs.202508472.
20. Deng M, Jiang Y, Chen Z, Chen K, Cao N, Huang Y, et al. Senescent synovial intimal fibroblasts aggravate osteoarthritis by regulating macrophage polarization and chondrocyte phenotype through the ANGPTL4-alpha5beta1 axis. Adv Sci (Weinh). 2026;13(13):e18056. doi:10.1002/advs.202518056.
21. Jia C, Li X, Pan J, Ma H, Wu D, Lu H, et al. Silencing of angiopoietin-like protein 4 (Angptl4) decreases inflammation, extracellular matrix degradation, and apoptosis in osteoarthritis via the sirtuin 1/NF-kappaB pathway. Oxid Med Cell Longev. 2022;2022:1135827. doi:10.1155/2022/1135827.
22. Qian JJ, Xu Q, Xu WM, Cai R, Huang GC. Expression of VEGF-A signaling pathway in cartilage of ACLT-induced osteoarthritis mouse model. J Orthop Surg Res. 2021;16(1):379. doi:10.1186/s13018-021-02528-w.
23. DerSimonian R, Laird N. Meta-analysis in clinical trials. Control Clin Trials. 1986;7(3):177-188. doi:10.1016/0197-2456(86)90046-2."""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def add_row(rows: list[dict[str, str]], item: str, status: str, detail: str) -> None:
    rows.append({"item": item, "status": status, "detail": detail})


def collapse_repeated_sentence(
    text: str,
    sentence: str,
    rows: list[dict[str, str]],
    item: str,
    required: bool,
) -> str:
    pattern = re.compile(rf"(?:{re.escape(sentence)}\s*){{2,}}")
    matches = pattern.findall(text)
    if matches:
        text = pattern.sub(sentence + " ", text)
        add_row(rows, item, "updated", f"collapsed {len(matches)} repeated sentence run(s)")
    elif sentence in text:
        add_row(rows, item, "already_updated", "sentence appears without consecutive duplication")
    else:
        add_row(rows, item, "not_found" if required else "not_applicable", sentence[:160])
    return text


def normalize_program_sentence(
    text: str,
    rows: list[dict[str, str]],
    item: str,
    required: bool,
) -> str:
    matches = [match.group(0).strip() for match in PROGRAM_SENTENCE_ANY_CITE.finditer(text)]
    if not matches:
        add_row(rows, item, "not_found" if required else "not_applicable", PROGRAM_SENTENCE_BASE)
        return text

    text = PROGRAM_SENTENCE_ANY_CITE.sub(PROGRAM_SENTENCE_NEW + " ", text)
    if len(matches) == 1 and matches[0] == PROGRAM_SENTENCE_NEW:
        add_row(rows, item, "already_updated", "program-level comparator already normalized")
    else:
        add_row(rows, item, "updated", f"normalized {len(matches)} program-level comparator occurrence(s) to [18]")
    return text


def title_case_headings(text: str, rows: list[dict[str, str]], prefix: str, required: bool) -> str:
    replacements = {
        "### sample-aware cNMF MSP discovery": "### Sample-aware cNMF MSP discovery",
        "### bulk validation and meta-analysis": "### Bulk validation and meta-analysis",
        "### bulk subtype analysis and robustness checks": "### Bulk subtype analysis and robustness checks",
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
            add_row(rows, f"{prefix}_{old}", "updated", new)
        elif new in text:
            add_row(rows, f"{prefix}_{old}", "already_updated", new)
        else:
            add_row(rows, f"{prefix}_{old}", "not_found" if required else "not_applicable", old)
    return text


def polish_limitations(text: str, rows: list[dict[str, str]], prefix: str, required: bool) -> str:
    old = "Several limitations should be explicit. First, the analysis relies on public datasets"
    new = "Several limitations apply. First, the analysis relies on public datasets"
    if old in text:
        text = text.replace(old, new)
        add_row(rows, f"{prefix}_limitations_opening", "updated", new)
    elif new in text:
        add_row(rows, f"{prefix}_limitations_opening", "already_updated", new)
    else:
        add_row(rows, f"{prefix}_limitations_opening", "not_found" if required else "not_applicable", old)
    return text


def expand_anchor(content: str) -> list[int]:
    values: list[int] = []
    for part in content.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(piece.strip()) for piece in part.split("-", 1)]
            values.extend(range(start, end + 1))
        else:
            values.append(int(part))
    return values


def compress_numbers(numbers: list[int]) -> str:
    if not numbers:
        return ""
    parts: list[str] = []
    start = prev = numbers[0]
    for number in numbers[1:]:
        if number == prev + 1:
            prev = number
            continue
        parts.append(format_run(start, prev))
        start = prev = number
    parts.append(format_run(start, prev))
    return ",".join(parts)


def format_run(start: int, end: int) -> str:
    run_length = end - start + 1
    if run_length >= 3:
        return f"{start}-{end}"
    if run_length == 2:
        return f"{start},{end}"
    return str(start)


def has_round4_reference_block(text: str) -> bool:
    marker = "## References"
    if marker not in text:
        return False
    after = text.split(marker, 1)[1]
    return all(
        marker_text in after
        for marker_text in ("3. Whittaker JL", "18. Chen G", "23. DerSimonian R, Laird N.")
    )


def has_round3_anchor_context(text: str) -> bool:
    return any(pattern in text for pattern in ROUND3_CONTEXT_PATTERNS)


def normalize_round4_anchor_style(text: str, rows: list[dict[str, str]], prefix: str) -> str:
    replacements = {
        "[3-4]": "[3,4]",
        "[5-6]": "[5,6]",
        "[7-8]": "[7,8]",
    }
    changed = 0
    for old, new in replacements.items():
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            changed += count
    add_row(
        rows,
        f"{prefix}_F2c_round4_anchor_style",
        "updated" if changed else "already_updated",
        f"normalized {changed} two-reference range anchor(s)",
    )
    return text


def renumber_body_anchors(text: str, rows: list[dict[str, str]], prefix: str) -> str:
    if "## References" in text:
        body, refs = text.split("## References", 1)
        suffix = "## References" + refs
    else:
        body, suffix = text, ""

    changed = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        content = match.group(1)
        numbers = expand_anchor(content)
        if any(number not in OLD_TO_NEW for number in numbers):
            return match.group(0)
        mapped = sorted({OLD_TO_NEW[number] for number in numbers})
        new_anchor = "[" + compress_numbers(mapped) + "]"
        if new_anchor != match.group(0):
            changed += 1
        return new_anchor

    body = re.sub(r"\[([\d,\-\s]+)\]", repl, body)
    add_row(rows, f"{prefix}_F2a_renumber_body_anchors", "updated" if changed else "already_updated", f"changed {changed} citation anchor(s)")
    return body + suffix


def replace_reference_block(text: str, rows: list[dict[str, str]], prefix: str) -> str:
    marker = "## References"
    if marker not in text:
        add_row(rows, f"{prefix}_F2b_reference_block", "not_found", "References marker missing")
        return text
    before, after = text.split(marker, 1)
    if "23. DerSimonian R, Laird N." in after and "3. Whittaker JL" in after:
        add_row(rows, f"{prefix}_F2b_reference_block", "already_updated", "reference block already in round4 order")
        return before.rstrip() + "\n\n" + marker + "\n\n" + REFERENCE_BLOCK + "\n"
    add_row(rows, f"{prefix}_F2b_reference_block", "updated", "reordered references to first-appearance order")
    return before.rstrip() + "\n\n" + marker + "\n\n" + REFERENCE_BLOCK + "\n"


def apply_round4(path: Path, rows: list[dict[str, str]], primary: bool) -> None:
    text = read_text(path)
    prefix = path.name
    required = primary
    text = collapse_repeated_sentence(text, CROSS_SENTENCE, rows, f"{prefix}_F1_cross_context_dedupe", required=required)
    text = title_case_headings(text, rows, prefix, required=required)
    text = polish_limitations(text, rows, prefix, required=required)
    if primary:
        if has_round4_reference_block(text):
            add_row(rows, f"{prefix}_F2a_renumber_body_anchors", "already_updated", "round4 reference block detected; body anchors not remapped")
        else:
            text = renumber_body_anchors(text, rows, prefix)
        text = normalize_round4_anchor_style(text, rows, prefix)
        text = normalize_program_sentence(text, rows, f"{prefix}_extra_program_sentence_normalized", required=True)
        text = replace_reference_block(text, rows, prefix)
    elif has_round3_anchor_context(text):
        text = renumber_body_anchors(text, rows, prefix)
        text = normalize_round4_anchor_style(text, rows, prefix)
        text = normalize_program_sentence(text, rows, f"{prefix}_extra_program_sentence_normalized", required=False)
    else:
        add_row(rows, f"{prefix}_F2a_renumber_body_anchors", "already_updated", "no round3 citation-anchor context detected")
        text = normalize_round4_anchor_style(text, rows, prefix)
        text = normalize_program_sentence(text, rows, f"{prefix}_extra_program_sentence_normalized", required=False)
    write_text(path, text)


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "status", "detail"], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_docs(doc_output: Path, notes_output: Path, rows: list[dict[str, str]]) -> None:
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    lines = [
        "# JOT Round 4 Revision Application",
        "",
        "## Judgement",
        "",
        "- F1 is correct and was applied: duplicated robust-result sentence was collapsed.",
        "- An additional duplicated program-level comparator sentence introduced during reruns was also collapsed.",
        "- F3 is correct and was applied: Methods headings and Limitations wording were polished.",
        "- F2 is correct and was applied last: in-text citations and the reference list were renumbered to Vancouver first-appearance order.",
        "- Author-owned repository URL/DOI and declaration confirmations remain unchanged.",
        "",
        "## Audit Status Counts",
        "",
    ]
    lines.extend(f"- {status}: {count}" for status, count in sorted(status_counts.items()))
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
        apply_round4(root / relative, rows, primary=True)
    for relative in SUPPORTING_TEXT_FILES:
        apply_round4(root / relative, rows, primary=False)

    rows.append({"item": "manual_repository_url_or_doi", "status": "manual_author_action", "detail": "Repository URL/DOI placeholder intentionally retained."})
    rows.append({"item": "manual_declaration_brackets", "status": "manual_author_action", "detail": "Title-page/declaration bracketed confirmations intentionally retained."})

    write_tsv(Path(args.audit_output), rows)
    write_docs(Path(args.doc_output), Path(args.notes_output), rows)
    print(f"ROUND4_AUDIT_ROWS {len(rows)}")
    print(f"WROTE {args.audit_output}")
    print(f"WROTE {args.doc_output}")
    print(f"WROTE {args.notes_output}")


if __name__ == "__main__":
    main()

# Reviewer-driven reanalysis summary

## Why the manuscript was rebuilt

The previous manuscript treated an investigator-defined meniscus senescence score as the central object. The revised analysis tests a narrower question: which transcriptional programs are discovered without forced signature genes, recur after independent decomposition of a second meniscus dataset, and retain support at the sample level and in tissue-specific bulk cohorts?

## New analyses

1. GSE220243 program discovery was repeated using only 3,000 batch-aware highly variable genes. NMF was run across four ranks, five random starts, and two sample-balanced cell selections.
2. Disease association was tested at the sample level rather than treating cells as independent replicates.
3. HRA001986 was decomposed independently before any GSE220243 reference genes were introduced. Program matching was performed only after discovery.
4. Locked top-30 program genes were evaluated in six designated OA-vs-normal bulk cohorts. Meta-analysis was stratified by tissue, with modified Hartung-Knapp uncertainty for the small number of cohorts.
5. The former weighted senescence score, pooled diagnostic model, subtype classifier, mechanism evidence score, and ligand-receptor mechanism claims were removed from the central inference.

## Revised scientific conclusion

The most reproducible positive finding is structural remodeling. Collagen/fibrotic-remodeling and fibrocartilage-identity programs recur in both single-cell datasets and are higher in abnormal HRA001986 samples. A senescence/stress state is identifiable at the gene-module level, but it is not consistently increased in OA. Bulk effects vary by tissue and cohort and do not support a universal cross-tissue diagnostic signature.

## Submission files

- `Revised_Manuscript_Structural_Remodeling_Primary.docx`
- `Revised_Supplementary_Tables.xlsx`
- `Figures/Fig1.tif`
- `Figures/Fig2.tif`
- `Figures/Fig3.tif`

## Quality-control status

- Abstract: 301 words.
- All three figures, both main tables, and S1 File are cited in the main text.
- All 20 references are cited.
- Key numerical statements match the source TSV files.
- The final DOCX was rendered to a 14-page PDF and visually checked page by page.
- No placeholders or obsolete mechanistic/diagnostic claims remain.

## Remaining journal-specific work

The manuscript is scientifically reframed but deliberately journal neutral. The title page, reference style, declarations, cover letter, and upload-file naming should be adapted after the next target journal is selected.

"""Fail closed on rebuild inconsistencies and export one program-level evidence ledger."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import anndata as ad
from scipy import stats
from rebuild_common import RANKS,SEEDS,SAMPLING_SEEDS,bh,sha256,write_json,exact_permutation


def main():
    out=Path(__file__).resolve().parents[1]; tables=out/'tables'
    checks=[]
    def passed(name,detail):
        checks.append(dict(check=name,status='PASS',detail=detail))
    primary={}
    fit_count=0
    for dataset,filename in [('GSE220243','GSE220243_repaired_hvg.h5ad'),('HRA001986','HRA001986_mapped_hvg.h5ad')]:
        data=ad.read_h5ad(out/'data'/filename,backed='r')
        assert data.var_names.is_unique and data.var_names.str.match(r'^ENSG\d+$').all()
        summary=json.loads((out/f'{dataset}_discovery_summary.json').read_text(encoding='utf-8'))
        assert sha256(out/'data'/filename)==summary['input_sha256']
        assert data.obs.groupby('donor_id',observed=True).status.nunique().eq(1).all()
        assert data.obs.donor_id.nunique()==(13 if dataset=='GSE220243' else 8)
        passed(dataset+'_input_integrity',f'{data.n_obs} cells, {data.n_vars} unique Ensembl genes, donor mapping and H5AD hash checked')
        data.file.close()
        for scheme in SAMPLING_SEEDS:
            matrix=out/'fits'/dataset/f'{scheme}_weighted_input.npz'
            matrix_hash=sha256(matrix)
            for rank in RANKS:
                for seed in SEEDS:
                    prefix=out/'fits'/dataset/f'{scheme}_K{rank}_seed{seed}'
                    meta=json.loads(prefix.with_suffix('.json').read_text(encoding='utf-8'))
                    assert meta['matrix_sha256']==matrix_hash
                    assert meta['loadings_sha256']==sha256(prefix.with_suffix('.npz'))
                    assert meta['checkpoint_version']==2 and meta['converged'] and meta['n_iter']<meta['max_iter']
                    assert (meta['rank'],meta['seed'])==(rank,seed)
                    values=np.load(prefix.with_suffix('.npz'))['loadings']
                    assert values.shape==(rank,summary['n_genes']) and np.isfinite(values).all() and (values>=0).all()
                    fit_count+=1
        tests=pd.read_csv(tables/f'{dataset}_donor_tests.tsv',sep='\t')
        assert not tests.program_id.duplicated().any()
        assert (tests.program_id.str.contains('primary300')==tests.scheme.eq('primary300')).all()
        tests=tests.loc[tests.scheme.eq('primary300')&tests['rank'].eq(summary['primary_rank'])]
        donor=pd.read_csv(tables/f'{dataset}_donor_scores.tsv',sep='\t')
        donor=donor.loc[donor.scheme.eq('primary300')&donor['rank'].eq(summary['primary_rank'])]
        for row in tests.itertuples():
            sample=donor.loc[donor.program_id.eq(row.program_id)]
            delta,p,extreme,count=exact_permutation(sample.mean_score,sample.status.eq('case'))
            np.testing.assert_allclose([row.delta,row.exact_p],[delta,p])
            assert row.total_allocations==count and row.extreme_allocations==extreme
        np.testing.assert_allclose(tests.bh_fdr,bh(tests.exact_p))
        primary[dataset]=tests
        passed(dataset+'_inference','Exhaustive donor P and full selected-rank BH family independently recalculated')
    assert fit_count==80
    passed('all_checkpoints','80/80 converged fits; payload and weighted-input SHA256, shape, seed, rank verified')
    pairs=pd.read_csv(tables/'independent_all_module_matches.tsv',sep='\t')
    assert len(pairs)==len(primary['GSE220243'])*len(primary['HRA001986'])
    for row in pairs.itertuples():
        np.testing.assert_allclose(row.full_top50_jaccard,row.full_top50_overlap_n/(row.gse_top50_n+row.hra_top50_n-row.full_top50_overlap_n))
        p=stats.hypergeom.sf(row.overlap_shared_universe-1,row.shared_nmf_input_test_universe_n,
                            row.gse_genes_in_shared_universe,row.hra_genes_in_shared_universe)
        np.testing.assert_allclose(row.hypergeom_p,p)
    np.testing.assert_allclose(pairs.hypergeom_fdr_all_pairs,bh(pairs.hypergeom_p))
    passed('independent_overlap','100 module pairs; full top-50 Jaccard and conditional shared-input enrichment verified')
    fixed=pd.read_csv(tables/'HRA_fixed_GSE_projection_donor_tests.tsv',sep='\t')
    np.testing.assert_allclose(fixed.bh_fdr,bh(fixed.exact_p))
    assert set(fixed.program_id)==set(primary['GSE220243'].program_id)
    passed('fixed_projection','All ten locked GSE programs scored in full-gene HRA, with one BH family')
    effects=pd.read_csv(tables/'bulk_program_effects.tsv',sep='\t')
    main=effects.loc[effects.role.eq('primary')&effects.normalization_primary]
    assert set(main.accession)=={'GSE114007','GSE55235','GSE55457'}
    assert effects.loc[effects.accession.eq('GSE143514'),'tissue'].eq('synovium').all()
    assert effects.loc[effects.accession.eq('GSE143514'),'role'].eq('uncertain_units_context').all()
    np.testing.assert_allclose(main.bh_fdr_all_primary_tests,bh(main.welch_p),equal_nan=True)
    pools=effects.loc[effects.role.isin(['pooled_context','cultured_pooled_context'])]
    assert pools.welch_p.isna().all() and pools.variance_g.isna().all()
    scores=pd.read_csv(tables/'bulk_sample_scores.tsv',sep='\t')
    primary_scores=scores.loc[scores.accession.isin(main.accession)]
    assert set(primary_scores.condition)=={'OA','normal'}
    passed('bulk_roles_and_families',f'{len(main)} eligible primary cohort-program tests; RNA pools excluded; no RA in primary scoring')
    assert not scores.duplicated(['accession','normalization','program_id','expression_column']).any()
    assert np.isfinite(scores.score).all()
    coverage=pd.read_csv(tables/'bulk_gene_coverage.tsv',sep='\t')
    assert coverage.eligible.eq(coverage.n_scored.ge(21)).all()
    passed('bulk_scores','Unique sample-score keys, finite values, >=21/30 coverage gate')
    meta=pd.read_csv(tables/'bulk_tissue_meta_analysis.tsv',sep='\t')
    for row in meta.itertuples():
        cohorts=row.cohorts.split(',')
        families={'PMID24690414' if x in ['GSE55235','GSE55457'] else x for x in cohorts}
        assert len(cohorts)==row.n_cohorts and len(families)==row.n_publication_families
        assert row.tissue=='synovium' and 'GSE114007' not in cohorts
    passed('meta_units','Per-module cohort/publication-family counts verified; no cartilage or cross-tissue pooling')
    top=pd.read_csv(tables/'locked_GSE_program_genes_for_bulk.tsv',sep='\t')
    descriptions=top.groupby('program_id').apply(lambda frame:','.join(frame.sort_values('gene_rank').head(10).gene_symbol),include_groups=False).rename('top10_genes')
    ledger=primary['GSE220243'][['program_id','delta','exact_p','bh_fdr']].rename(columns={'delta':'gse_delta','exact_p':'gse_exact_p','bh_fdr':'gse_fdr'}).merge(descriptions,on='program_id')
    ledger=ledger.merge(fixed[['program_id','delta','exact_p','bh_fdr','n_scored_genes']].rename(columns={'delta':'hra_fixed_delta','exact_p':'hra_fixed_exact_p','bh_fdr':'hra_fixed_fdr','n_scored_genes':'hra_projected_genes'}),on='program_id',validate='one_to_one')
    best=pd.read_csv(tables/'independent_best_matches_with_donor_effects.tsv',sep='\t')
    ledger=ledger.merge(best[['gse_program','hra_program','full_top50_jaccard','full_top50_overlap_n','hra_donor_delta','hra_donor_fdr']].rename(columns={'gse_program':'program_id'}),on='program_id',validate='one_to_one')
    for accession,frame in main.groupby('accession'):
        ledger=ledger.merge(frame[['program_id','hedges_g','bh_fdr_all_primary_tests','n_scored']].rename(columns={
            'hedges_g':accession+'_g','bh_fdr_all_primary_tests':accession+'_global_fdr','n_scored':accession+'_genes'}),on='program_id',how='left',validate='one_to_one')
    ledger=ledger.merge(meta.loc[meta.omitted_center.eq('none')&meta.analysis_scope.eq('strict_primary'),['program_id','pooled_g','ci_low','ci_high','bh_fdr_within_meta_family','i_squared_percent','n_cohorts']].rename(columns={
        'pooled_g':'synovium_g','ci_low':'synovium_ci_low','ci_high':'synovium_ci_high','bh_fdr_within_meta_family':'synovium_fdr'}),on='program_id',how='left',validate='one_to_one')
    ledger.to_csv(tables/'program_evidence_ledger.tsv',sep='\t',index=False)
    sources=pd.read_csv(tables/'GSE220243_source_provenance.tsv',sep='\t')
    source_hashes=[dict(path=row.input_h5ad,sha256=sha256(row.input_h5ad)) for row in sources.itertuples()]
    write_json(out/'single_cell_input_hashes.json',source_hashes)
    code_hashes={path.name:sha256(path) for path in sorted((out/'scripts').glob('*.py'))}
    write_json(out/'code_sha256.json',code_hashes)
    write_json(out/'release_checks.json',dict(status='TECHNICAL_CHECKS_PASSED_NOT_SUBMISSION_APPROVAL',checks=checks,
                limitations=['No independent cell-compartment reannotation','Age/BMI and cell-mixture confounding remain',
                             'HRA projected and independently decomposed tests are not two independent cohorts',
                             'Previously explored data; no confirmatory registration','Input unit warnings and study-family dependence retained',
                             'Manuscript numbers and references must be reconciled before a new submission']))
    print('PASS',len(checks),'release checks; 80 fits; all locked programs preserved',flush=True)
    print(ledger.to_string(index=False),flush=True)


if __name__=='__main__':
    main()

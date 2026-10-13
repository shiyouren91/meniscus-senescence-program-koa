"""Rebuild inputs by stable Ensembl IDs and full-library normalization."""
from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse
import scanpy as sc

from rebuild_common import normalize_from_full_totals, select_cells, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.project_root.resolve(), Path(__file__).resolve().parents[1]
    data, tables = out/'data', out/'tables'
    data.mkdir(exist_ok=True)
    tables.mkdir(exist_ok=True)
    os.environ.setdefault('NUMBA_CACHE_DIR', str(out/'cache'))
    sc.settings.n_jobs = 2
    schema=json.loads((out/'inputs/legacy_selected_GSE_metadata_schema.json').read_text(encoding='utf-8'))
    old_obs = pd.read_csv(out/'inputs/legacy_selected_GSE_cell_metadata.tsv.gz', sep='\t', index_col=0, dtype=schema)
    manifest_path = out/'inputs/gse220243_single_cell_manifest.tsv'
    manifest = pd.read_csv(manifest_path, sep='\t')
    manifest = manifest.loc[manifest.sample_label.isin(old_obs.sample_label.unique())].copy()
    feature_frames, reference_sets, sample_features = [], [], {}
    for row in manifest.itertuples():
        frame = pd.read_csv(row.features_path, sep='\t', header=None, names=['gene_id', 'source_symbol', 'feature_type'])
        assert frame.gene_id.is_unique and frame.feature_type.eq('Gene Expression').all()
        frame['sample_id'] = row.sample_label
        frame['source_symbol'] = frame.source_symbol.str.upper()
        feature_frames.append(frame)
        reference_sets.append(set(frame.gene_id))
        sample_features[row.sample_label] = frame
    all_features = pd.concat(feature_frames, ignore_index=True)
    common = sorted(set.intersection(*reference_sets))
    reference_sample = sorted(sample_features, key=lambda key: (-len(sample_features[key]), key))[0]
    symbols = sample_features[reference_sample].set_index('gene_id').source_symbol
    assert set(common).issubset(symbols.index)
    var = pd.DataFrame({'gene_symbol': symbols.loc[common].to_numpy()}, index=pd.Index(common, name='gene_id'))
    symbol_to_ids = all_features.groupby('source_symbol').gene_id.agg(lambda x: sorted(set(x)))
    alias_rows = all_features.groupby('gene_id').agg(
        all_source_symbols=('source_symbol', lambda x: '|'.join(sorted(set(x)))),
        n_reference_samples=('sample_id', 'nunique')).reset_index()
    alias_rows['reference_symbol'] = alias_rows.gene_id.map(symbols).fillna('')
    alias_rows['present_all_samples'] = alias_rows.gene_id.isin(common)
    alias_rows.to_csv(tables/'gene_id_alias_map.tsv', sep='\t', index=False)
    matrices, metadata, audits, marker_rows, source_rows = [], [], [], [], []
    markers = {'fibrocartilage': ['COMP', 'CILP', 'SCRG1', 'PRELP', 'COL1A1', 'COL1A2'],
               'immune': ['PTPRC', 'CD3D', 'LST1', 'TYROBP'],
               'endothelial': ['PECAM1', 'VWF', 'KDR'], 'mural': ['RGS5', 'CSPG4', 'MYH11']}
    alias_examples = ['ENSG00000118523', 'ENSG00000142871', 'ENSG00000119147']
    for row in manifest.sort_values('sample_label').itertuples():
        sample = row.sample_label
        path = root/f'data/processed/single_cell/GSE220243/meniscus_by_sample/{sample}.h5ad'
        source = ad.read_h5ad(path, backed='r')
        ids = source.var.gene_id.astype(str)
        features = sample_features[sample]
        assert ids.is_unique and ids.tolist() == features.gene_id.tolist()
        assert source.var.gene_symbol.str.upper().tolist() == features.source_symbol.tolist()
        selected_obs = old_obs.loc[old_obs.sample_label.eq(sample)].copy()
        indices = source.obs_names.get_indexer(selected_obs.index)
        assert (indices >= 0).all()
        raw = source.X[indices].tocsr()
        assert np.isfinite(raw.data).all() and (raw.data >= 0).all() and np.all(raw.data == np.rint(raw.data))
        totals = np.asarray(raw.sum(1)).ravel().astype(float)
        detected = np.asarray((raw > 0).sum(1)).ravel()
        mito = source.var.gene_symbol.str.upper().str.startswith('MT-').to_numpy()
        percent_mito = np.asarray(raw[:, mito].sum(1)).ravel() / totals * 100
        old_totals = selected_obs.n_counts.to_numpy(float)
        keep = ((totals >= 500) & (totals <= 75000) & (detected >= 500)
                & (detected <= 7500) & (percent_mito <= 20))
        positions = pd.Index(ids).get_indexer(common)
        assert (positions >= 0).all()
        counts = raw[:, positions]
        normalized = normalize_from_full_totals(counts, totals)
        selected_obs['sample_id'] = sample
        selected_obs['donor_id'] = 'MenNorm1' if sample in ('MenNorm1VAS', 'MenNorm1AVAS') else sample
        selected_obs['status'] = np.where(selected_obs.disease_status.str.lower().eq('oa'), 'case', 'control')
        selected_obs['full_library_counts'] = totals
        selected_obs['corrected_n_genes'] = detected
        selected_obs['corrected_percent_mito'] = percent_mito
        selected_obs['rebuild_qc_pass'] = keep
        for marker_type, panel in markers.items():
            marker_idx = np.flatnonzero(var.gene_symbol.isin(panel).to_numpy())
            marker_rows.append(dict(sample_id=sample, marker_panel=marker_type, n_genes=len(marker_idx),
                                    mean_log_expression=float(normalized[keep][:, marker_idx].mean())))
        summary = dict(sample_id=sample, n_original_selected=len(totals), n_corrected_qc_pass=int(keep.sum()),
                       source_features=len(ids), common_features=len(common),
                       full_total_max_difference_from_old=float(np.max(np.abs(totals-old_totals))),
                       median_full_library=float(np.median(totals)), median_mito=float(np.median(percent_mito)),
                       max_mito_difference_from_old=float(np.max(np.abs(percent_mito-selected_obs.pct_counts_mt.to_numpy(float)))),
                       median_common_fraction=float(np.median(np.asarray(counts.sum(1)).ravel()/totals)))
        for gene_id in alias_examples:
            summary['raw_mean_'+gene_id] = float(raw[:, int(pd.Index(ids).get_loc(gene_id))].mean())
        audits.append(summary)
        matrices.append(normalized[keep].tocsr())
        metadata.append(selected_obs.loc[keep])
        source_rows.append(dict(sample_id=sample, input_h5ad=str(path), input_size=path.stat().st_size,
                                features_path=row.features_path, features_sha256=sha256(row.features_path)))
        source.file.close()
        del raw, normalized, counts, source
        gc.collect()
        print('REBUILT',sample,summary['n_corrected_qc_pass'],flush=True)
    obs = pd.concat(metadata)
    assert obs.index.is_unique and obs.donor_id.nunique() == 13
    full = ad.AnnData(sparse.vstack(matrices, format='csr'), obs=obs, var=var)
    del matrices
    gene_detected = np.asarray((full.X > 0).sum(0)).ravel()
    full.var['detected_cells'] = gene_detected
    full.var.to_csv(tables/'GSE220243_gene_universe.tsv', sep='\t')
    eligible = gene_detected >= 3
    chosen = select_cells(full.obs, 1000, 20260926)
    hvg = full[chosen, eligible].copy()
    sc.pp.highly_variable_genes(hvg, n_top_genes=3000, flavor='seurat', batch_key='donor_id')
    hvg.var.to_csv(tables/'GSE220243_recomputed_hvg.tsv', sep='\t')
    selected_ids = hvg.var_names[hvg.var.highly_variable]
    assert len(selected_ids) == 3000
    hvg_mask = full.var_names.isin(selected_ids)
    retained = full[:, hvg_mask].copy()
    retained.uns['normalization'] = 'log1p(1e4 * counts / full per-sample gene-expression library total), before feature restriction'
    retained.uns['gene_id_reference_sample_for_symbols'] = reference_sample
    retained.uns['cell_universe'] = 'legacy balanced selected compartment; QC rechecked; no independent reannotation'
    retained.write_h5ad(data/'GSE220243_repaired_hvg.h5ad', compression='gzip')
    obs.to_csv(tables/'GSE220243_cell_metadata.tsv.gz', sep='\t')
    pd.DataFrame(audits).to_csv(tables/'GSE220243_input_qc_audit.tsv', sep='\t', index=False)
    pd.DataFrame(marker_rows).to_csv(tables/'GSE220243_compartment_marker_audit.tsv', sep='\t', index=False)
    pd.DataFrame(source_rows).to_csv(tables/'GSE220243_source_provenance.tsv', sep='\t', index=False)
    gse_n = full.n_obs
    del full, hvg, retained
    gc.collect()

    hra_path = root/'data/raw/HRA001986/meniscal_chondrocyte.h5ad'
    hra = ad.read_h5ad(hra_path)
    original_symbols = hra.var_names.str.upper()
    mappings = [symbol_to_ids.get(symbol, []) for symbol in original_symbols]
    ids = [value[0] if len(value) == 1 else '' for value in mappings]
    unique_ids = pd.Series(ids)
    unambiguous = np.array([bool(value) for value in ids]) & ~unique_ids.duplicated(keep=False).to_numpy()
    hvg_mask = hra.var['vst.variable'].astype(bool).to_numpy() & unambiguous
    mapping_table = pd.DataFrame(dict(original_symbol=original_symbols, gene_id=ids,
                                      n_reference_mappings=[len(v) for v in mappings],
                                      unique_mapping=unambiguous, author_hvg=hra.var['vst.variable'].to_numpy(),
                                      retained_hvg=hvg_mask))
    mapping_table.to_csv(tables/'HRA001986_symbol_mapping.tsv', sep='\t', index=False)
    exp_totals = []
    for start in range(0, hra.n_obs, 2048):
        block = hra.X[start:start+2048].copy()
        assert sparse.issparse(block) and np.isfinite(block.data).all() and (block.data >= 0).all()
        block.data = np.expm1(block.data)
        exp_totals.extend(np.asarray(block.sum(1)).ravel().tolist())
    assert np.allclose(exp_totals, 1e4, rtol=1e-4, atol=1e-2), 'HRA normalization differs from expected author log-library scale'
    detected = np.asarray((hra.X > 0).sum(0)).ravel()
    hra_universe = mapping_table.loc[unambiguous, ['gene_id', 'original_symbol']].copy()
    hra_universe['detected_cells'] = detected[unambiguous]
    hra_universe.to_csv(tables/'HRA001986_gene_universe.tsv', sep='\t', index=False)
    info_path = out/'inputs/HRA_public_donor_metadata.xlsx'
    info = pd.read_excel(info_path).set_index('sample name')
    hobs = hra.obs.copy()
    hobs['sample_id'] = hobs['orig.ident'].astype(str)
    hobs['donor_id'] = hobs.sample_id.str[0]
    hobs['source_status'] = hobs.status.astype(str)
    hobs['status'] = np.where(hobs.source_status.eq('abnormal'), 'case', 'control')
    hobs['region'] = hobs.anatomy.astype(str)
    for target, column in [('age', 'Age'), ('bmi', 'BMI'), ('sex', 'donor sex')]:
        hobs[target] = hobs.sample_id.map(info[column])
        assert hobs[target].notna().all()
    assert hobs.donor_id.nunique() == 8 and hobs.groupby('donor_id').status.nunique().max() == 1
    hvar = pd.DataFrame(dict(gene_symbol=[symbols.get(gene_id, original_symbols[i]) for i,gene_id in enumerate(ids) if hvg_mask[i]]),
                        index=pd.Index(np.asarray(ids)[hvg_mask], name='gene_id'))
    rebuilt_hra = ad.AnnData(hra.X[:, hvg_mask].astype(np.float32).tocsr(), obs=hobs, var=hvar)
    rebuilt_hra.uns['normalization'] = 'author log-normalized data retained; expm1 full-gene row totals verified near 10000; no raw counts reconstructed'
    rebuilt_hra.write_h5ad(data/'HRA001986_mapped_hvg.h5ad', compression='gzip')
    hobs.to_csv(tables/'HRA001986_cell_metadata.tsv.gz', sep='\t')
    hobs[['donor_id', 'status', 'age', 'bmi', 'sex']].drop_duplicates().to_csv(tables/'HRA001986_donor_covariates.tsv', sep='\t', index=False)
    for dataset, frame in [('GSE220243',obs), ('HRA001986',hobs)]:
        frame.groupby(['sample_id','donor_id','status','region'],observed=True).size().rename('n_cells').reset_index().to_csv(
            tables/f'{dataset}_donor_region_manifest.tsv',sep='\t',index=False)
    write_json(out/'input_preparation_summary.json', dict(
        gse_cells=gse_n, gse_genes=3000, gse_common_reference_genes=len(common), gse_donors=13,
        hra_cells=hra.n_obs, hra_author_hvg=2000, hra_retained_hvg=int(hvg_mask.sum()), hra_donors=8,
        hra_expm1_totals_min=float(min(exp_totals)), hra_expm1_totals_max=float(max(exp_totals)),
        source_metadata_sha256=sha256(info_path), feature_symbol_reference=reference_sample,
        cell_compartment_caveat='Legacy cell universe retained with QC and marker audit, not independent reannotation.'))
    print('INPUTS_READY',gse_n,int(hvg_mask.sum()),flush=True)


if __name__ == '__main__':
    main()

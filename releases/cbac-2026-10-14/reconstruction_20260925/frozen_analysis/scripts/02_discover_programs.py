"""Converged donor-balanced NMF, label-blind rank selection, donor-level inference."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import time
import warnings

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import NMF
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

from rebuild_common import (RANKS, SEEDS, SAMPLING_SEEDS, align_consensus, bh, donor_region_weights,
                            score_modules, select_cells, sha256, write_json)


def run_fit(task):
    path, prefix, matrix_hash, rank, seed = task
    path, prefix = Path(path), Path(prefix)
    metadata_file = prefix.with_suffix('.json')
    loading_file = prefix.with_suffix('.npz')
    if metadata_file.is_file() and loading_file.is_file():
        saved = json.loads(metadata_file.read_text(encoding='utf-8'))
        if (saved.get('matrix_sha256') == matrix_hash and saved.get('converged')
                and saved.get('tol') == 1e-4 and saved.get('rank') == rank
                and saved.get('seed') == seed and saved.get('checkpoint_version') == 2
                and saved.get('loadings_sha256') == sha256(loading_file)):
            with np.load(loading_file) as checkpoint:
                values = checkpoint['loadings']
                if (values.shape == (rank, saved['n_genes']) and np.isfinite(values).all()
                        and (values >= 0).all() and (values.sum(axis=1) > 0).all()):
                    return saved
    matrix = sparse.load_npz(path).astype(np.float64)
    attempts = []
    started = time.perf_counter()
    for max_iter in (5000, 15000):
        model = NMF(n_components=rank, init='random', solver='cd', beta_loss='frobenius',
                    random_state=seed, max_iter=max_iter, tol=1e-4)
        with threadpool_limits(limits=2), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            model.fit_transform(matrix)
        convergence_warning = any(issubclass(w.category, ConvergenceWarning) for w in caught)
        attempts.append(dict(max_iter=max_iter, actual_iter=int(model.n_iter_),
                             warnings=[str(w.message) for w in caught]))
        converged = not convergence_warning and model.n_iter_ < max_iter
        if converged:
            break
    result = dict(matrix_sha256=matrix_hash, rank=rank, seed=seed, n_cells=matrix.shape[0],
                  n_genes=matrix.shape[1], n_iter=int(model.n_iter_), max_iter=max_iter,
                  tol=1e-4, converged=converged, reconstruction_error=float(model.reconstruction_err_),
                  relative_reconstruction_error=float(model.reconstruction_err_ / np.linalg.norm(matrix.data)),
                  seconds=time.perf_counter()-started, attempts=attempts)
    if not converged:
        write_json(prefix.with_suffix('.failed.json'), result)
        raise RuntimeError(f'Unconverged NMF: {prefix}; consensus is not released')
    temporary_loading = prefix.with_suffix('.pending.npz')
    np.savez_compressed(temporary_loading, loadings=model.components_)
    result['loadings_sha256'] = sha256(temporary_loading)
    result['checkpoint_version'] = 2
    os.replace(temporary_loading, loading_file)
    # Publish metadata last; interrupted writes cannot authenticate a stale payload.
    temporary_metadata = prefix.with_suffix('.pending.json')
    write_json(temporary_metadata, result)
    os.replace(temporary_metadata, metadata_file)
    return result


def execute_dataset(out, dataset, input_path, jobs):
    data = ad.read_h5ad(input_path)
    tables, fits = out/'tables', out/'fits'/dataset
    fits.mkdir(parents=True, exist_ok=True)
    tasks, selections, selection_rows, manifest = [], {}, [], []
    for scheme, cap in [('primary300', 300), ('sensitivity1000', 1000)]:
        selected = select_cells(data.obs, cap, SAMPLING_SEEDS[scheme])
        obs = data.obs.iloc[selected].copy()
        weights = donor_region_weights(obs) * len(selected)
        matrix = sparse.diags(np.sqrt(weights)).dot(data.X[selected]).tocsr().astype(np.float64)
        matrix_path = fits/f'{scheme}_weighted_input.npz'
        sparse.save_npz(matrix_path, matrix)
        matrix_hash = sha256(matrix_path)
        selections[scheme] = obs
        selected_table = obs[['sample_id','donor_id','status','region']].copy()
        selected_table['squared_loss_weight'] = weights
        selected_table.to_csv(tables/f'{dataset}_{scheme}_selected_cells.tsv.gz',sep='\t')
        for donor, group in selected_table.groupby('donor_id', observed=True):
            selection_rows.append(dict(dataset=dataset, scheme=scheme, donor_id=donor, n_cells=len(group),
                                       total_loss_weight=float(group.squared_loss_weight.sum()),
                                       n_regions=group.sample_id.nunique()))
        for rank in RANKS:
            for seed in SEEDS:
                tasks.append((str(matrix_path), str(fits/f'{scheme}_K{rank}_seed{seed}'), matrix_hash, rank, seed))
                manifest.append(dict(dataset=dataset,scheme=scheme,rank=rank,seed=seed,matrix_sha256=matrix_hash))
    pd.DataFrame(selection_rows).to_csv(tables/f'{dataset}_sampling_audit.tsv',sep='\t',index=False)
    pd.DataFrame(manifest).to_csv(tables/f'{dataset}_fit_manifest.tsv',sep='\t',index=False)
    if jobs == 1:
        for task in tasks:
            result = run_fit(task)
            print('FIT',dataset,Path(task[1]).name,result['n_iter'],f"{result['seconds']:.1f}s",flush=True)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            futures = {executor.submit(run_fit, task):task for task in tasks}
            for future in as_completed(futures):
                result = future.result()
                task = futures[future]
                print('FIT',dataset,Path(task[1]).name,result['n_iter'],f"{result['seconds']:.1f}s",flush=True)
    metrics, stability_frames, mapping_frames, top_frames, rank_rows = [], [], [], [], []
    all_regions, all_donors, all_tests, all_influence = [], [], [], []
    for scheme in SAMPLING_SEEDS:
        for rank in RANKS:
            matrices = []
            rank_metrics = []
            for seed in SEEDS:
                prefix = fits/f'{scheme}_K{rank}_seed{seed}'
                run = json.loads(prefix.with_suffix('.json').read_text(encoding='utf-8'))
                assert run['converged']
                matrices.append(np.load(prefix.with_suffix('.npz'))['loadings'])
                rank_metrics.append(run)
                metrics.append({k:v for k,v in run.items() if k!='attempts'} | dict(dataset=dataset,scheme=scheme))
            loadings, stability, mapping = align_consensus(matrices, SEEDS)
            np.savez_compressed(fits/f'{scheme}_K{rank}_consensus.npz',loadings=loadings,gene_ids=data.var_names.to_numpy(str))
            for frame in (stability,mapping):
                frame['dataset'],frame['scheme'],frame['rank']=dataset,scheme,rank
            stability_frames.append(stability)
            mapping_frames.append(mapping)
            rank_rows.append(dict(dataset=dataset,scheme=scheme,rank=rank,
                                  rank_stability=float(stability.median_pairwise_cosine.median()),
                                  min_component_stability=float(stability.median_pairwise_cosine.min()),
                                  median_relative_error=float(np.median([run['relative_reconstruction_error'] for run in rank_metrics]))))
            top = []
            for component, profile in enumerate(loadings,1):
                program_id=f'{dataset}_{scheme}_K{rank}_C{component}'
                for order,j in enumerate(np.argsort(-profile,kind='stable')[:100],1):
                    top.append(dict(dataset=dataset,scheme=scheme,rank=rank,component=component,program_id=program_id,
                                    gene_rank=order,gene_id=str(data.var_names[j]),gene_symbol=str(data.var.iloc[j].gene_symbol),
                                    loading=float(profile[j])))
            top = pd.DataFrame(top)
            top_frames.append(top)
            region,donor,tests,influence=score_modules(data.X,data.obs,data.var,top,dataset)
            for frame in (region,donor,tests,influence):
                frame['scheme'],frame['rank']=scheme,rank
            all_regions.append(region)
            all_donors.append(donor)
            all_tests.append(tests)
            all_influence.append(influence)
    ranks=pd.DataFrame(rank_rows)
    primary_rank=int(ranks.loc[ranks.scheme.eq('primary300')].sort_values(['rank_stability','rank'],ascending=[False,True]).iloc[0]['rank'])
    ranks['selected_primary_rank']=ranks['rank'].eq(primary_rank)
    tests=pd.concat(all_tests,ignore_index=True)
    tests['bh_fdr_all_ranks_in_scheme']=tests.groupby('scheme',group_keys=False).exact_p.transform(lambda x:bh(x.to_numpy()))
    tests['selected_primary_rank']=tests['rank'].eq(primary_rank)
    outputs={'fit_metrics':pd.DataFrame(metrics),'consensus_stability':pd.concat(stability_frames,ignore_index=True),
             'seed_component_alignment':pd.concat(mapping_frames,ignore_index=True),'consensus_top_genes':pd.concat(top_frames,ignore_index=True),
             'rank_selection':ranks,'regional_scores':pd.concat(all_regions,ignore_index=True),
             'donor_scores':pd.concat(all_donors,ignore_index=True),'donor_tests':tests,
             'leave_one_donor_out':pd.concat(all_influence,ignore_index=True)}
    for name,frame in outputs.items():
        frame.to_csv(tables/f'{dataset}_{name}.tsv',sep='\t',index=False)
    write_json(out/f'{dataset}_discovery_summary.json',dict(dataset=dataset,primary_rank=primary_rank,
                n_cells=data.n_obs,n_genes=data.n_vars,n_donors=data.obs.donor_id.nunique(),
                input_sha256=sha256(input_path),all_fits_converged=True,n_fits=len(metrics),
                rank_selection='Maximum median cross-seed one-to-one matched cosine in primary300; no disease labels',
                score='Donor/region-weighted standardized top-30 gene expression, not NMF usage'))
    print('DISCOVERY_COMPLETE',dataset,'primary rank',primary_rank,flush=True)
    print(tests.loc[tests.scheme.eq('primary300')&tests['rank'].eq(primary_rank)].sort_values('bh_fdr').to_string(index=False),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs',type=int,default=2)
    parser.add_argument('--dataset',choices=['all','GSE220243','HRA001986'],default='all')
    args=parser.parse_args()
    out=Path(__file__).resolve().parents[1]
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
        os.environ[name]='2'
    packages={name:importlib.metadata.version(name) for name in ['anndata','numpy','pandas','scipy','scikit-learn','scanpy','threadpoolctl']}
    write_json(out/'runtime_versions.json',dict(python=platform.python_version(),platform=platform.platform(),packages=packages))
    for dataset,filename in [('GSE220243','GSE220243_repaired_hvg.h5ad'),('HRA001986','HRA001986_mapped_hvg.h5ad')]:
        if args.dataset in ('all',dataset):
            execute_dataset(out,dataset,out/'data'/filename,args.jobs)


if __name__=='__main__':
    main()

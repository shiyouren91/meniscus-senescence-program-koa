"""Matched-budget NMF sensitivity with donor-level inference in both arms."""
from __future__ import annotations

import os
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '2'
import argparse
import hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
import importlib.metadata
import json
from pathlib import Path
import platform
import time
import uuid

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linear_sum_assignment
from sklearn.metrics.pairwise import cosine_similarity

from original_discovery import run_fit
from rebuild_common import (SEEDS, align_consensus, bh, donor_region_weights,
                            score_modules, select_cells, sha256, write_json)

SAMPLING = (20260925, 20261013, 20261014)
ARMS = ('balanced', 'pooled')
RANK = 10


def sample_arm(obs, arm, seed, cap=300):
    if arm not in ARMS or cap <= 0 or obs.empty:
        raise ValueError('Invalid sampling configuration')
    balanced = select_cells(obs, cap, seed)
    selected = balanced if arm == 'balanced' else np.sort(
        np.random.default_rng(seed).choice(len(obs), size=len(balanced), replace=False))
    chosen = obs.iloc[selected]
    weights = donor_region_weights(chosen) * len(chosen) if arm == 'balanced' else np.ones(len(chosen))
    assert len(np.unique(selected)) == len(selected) and np.isclose(weights.sum(), len(selected))
    return selected, weights


def match_reference(reference, candidate):
    similarities = cosine_similarity(reference, candidate)
    rows, cols = linear_sum_assignment(-similarities)
    assert np.array_equal(rows, np.arange(len(reference))) and len(set(cols)) == len(cols)
    return cols, similarities[rows, cols]


def top_indices(profile, number=50):
    return set(np.argsort(-profile, kind='stable')[:number].tolist())


def jaccard(first, second):
    return len(first & second) / len(first | second)


def configurations(data, include_omissions):
    for seed in SAMPLING:
        for arm in ARMS:
            yield dict(kind='full', omitted_donor='', sampling_seed=seed, arm=arm)
    if include_omissions:
        for donor in sorted(data.obs.donor_id.unique()):
            for arm in ARMS:
                yield dict(kind='omit', omitted_donor=str(donor), sampling_seed=SAMPLING[0], arm=arm)


def config_id(config):
    omitted = config['omitted_donor'] or 'none'
    assert not any(x in omitted for x in ('/', '\\', ':'))
    return f"{config['kind']}_{config['arm']}_s{config['sampling_seed']}_omit-{omitted}"


def fixed_omission_sample(full_obs, arm, seed, omitted_donor):
    """Keep exactly the full-arm selected cells belonging to retained donors."""
    selected, _ = sample_arm(full_obs, arm, seed)
    chosen = full_obs.iloc[selected]
    selected = selected[chosen.donor_id.astype(str).ne(str(omitted_donor)).to_numpy()]
    chosen = full_obs.iloc[selected]
    weights = donor_region_weights(chosen) * len(chosen) if arm == 'balanced' else np.ones(len(chosen))
    return selected, weights


def begin_run(out):
    run_id = uuid.uuid4().hex
    if (out / 'completion.json').exists():
        os.replace(out / 'completion.json', out / f'completion.previous.{run_id}.json')
    if (out / 'provenance.json').exists():
        os.replace(out / 'provenance.json', out / f'provenance.previous.{run_id}.json')
    write_json(out / 'run_state.json', dict(run_id=run_id, status='running'))
    return run_id


def execute(rebuild, out, jobs=2, include_omissions=True):
    started = time.time()
    out.mkdir(parents=True, exist_ok=True)
    run_id = begin_run(out)
    for name in ('fits', 'tables', 'figures'):
        (out / name).mkdir(parents=True, exist_ok=True)
    paths = {'GSE220243': rebuild / 'data/GSE220243_repaired_hvg.h5ad',
             'HRA001986': rebuild / 'data/HRA001986_mapped_hvg.h5ad'}
    provenance = dict(inputs={ds: dict(path=str(p), sha256=sha256(p)) for ds, p in paths.items()},
                      rank=RANK, cap=300, sampling_seeds=SAMPLING, nmf_seeds=SEEDS,
                      include_omissions=include_omissions, jobs=jobs,
                      python=platform.python_version(), platform=platform.platform(),
                      packages={n: importlib.metadata.version(n) for n in
                                ('anndata', 'numpy', 'scipy', 'pandas', 'scikit-learn', 'threadpoolctl')},
                      plan_sha256=sha256(out / 'ANALYSIS_PLAN.md'),
                      reference_hashes={ds: {
                          'consensus': sha256(rebuild / 'fits' / ds / 'primary300_K10_consensus.npz'),
                          'donor_tests': sha256(rebuild / 'tables' / f'{ds}_donor_tests.tsv')} for ds in paths},
                      omission='Fixed full-arm cell selections with omitted donor removed; arm budgets may differ',
                      code_sha256={p.name: sha256(p) for p in Path(__file__).parent.glob('*.py')})
    runtime_fingerprint = hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()
    provenance['runtime_fingerprint'], provenance['run_id'] = runtime_fingerprint, run_id
    write_json(out / 'provenance.json', provenance)
    all_tasks, config_rows, sampling_rows = [], [], []
    for dataset, path in paths.items():
        data = ad.read_h5ad(path)
        assert data.obs_names.is_unique and data.var_names.is_unique
        for conf in configurations(data, include_omissions):
            retained = data.obs.donor_id.astype(str).ne(conf['omitted_donor']).to_numpy()
            obs = data.obs.loc[retained].copy()
            if conf['kind'] == 'full':
                selected, weights = sample_arm(data.obs, conf['arm'], conf['sampling_seed'])
            else:
                selected, weights = fixed_omission_sample(data.obs, conf['arm'], conf['sampling_seed'], conf['omitted_donor'])
            cid = config_id(conf)
            folder = out / 'fits' / dataset / cid
            folder.mkdir(parents=True, exist_ok=True)
            chosen = data.obs.iloc[selected].copy()
            assert conf['omitted_donor'] not in chosen.donor_id.astype(str).to_list()
            chosen['squared_loss_weight'] = weights
            chosen[['sample_id', 'donor_id', 'status', 'region', 'squared_loss_weight']].to_csv(
                folder / 'selected_cells.tsv.gz', sep='\t')
            matrix = sparse.diags(np.sqrt(weights)).dot(data.X[selected]).tocsr().astype(np.float64)
            matrix_path = folder / 'input.npz'
            sparse.save_npz(matrix_path, matrix)
            matrix_hash = sha256(matrix_path)
            by_donor = chosen.groupby('donor_id', observed=True).squared_loss_weight.sum()
            shares = (by_donor / by_donor.sum()).reindex(obs.donor_id.unique(), fill_value=0)
            config_rows.append(dict(dataset=dataset, config=cid, **conf, n_cells=len(selected),
                                    n_retained_donors=obs.donor_id.nunique(),
                                    n_sampled_donors=chosen.donor_id.nunique(),
                                    max_donor_loss_share=float(shares.max()),
                                    effective_donor_count=float(1 / (shares ** 2).sum()),
                                    matrix_sha256=matrix_hash))
            for sample, group in obs.groupby('sample_id', observed=True):
                selected_group = chosen.loc[chosen.sample_id.eq(sample)]
                sampling_rows.append(dict(dataset=dataset, config=cid, **conf,
                    donor_id=str(group.donor_id.iloc[0]), sample_id=str(sample),
                    available_cells=len(group), sampled_cells=len(selected_group),
                    loss_weight=float(selected_group.squared_loss_weight.sum()),
                    total_cells=len(selected)))
            for seed in SEEDS:
                all_tasks.append((str(matrix_path), str(folder / f'seed{seed}'), matrix_hash, RANK, seed, runtime_fingerprint))
        del data
    configs = pd.DataFrame(config_rows)
    configs.to_csv(out / 'tables/configurations.tsv', sep='\t', index=False)
    pd.DataFrame(sampling_rows).to_csv(out / 'tables/sampling_representation.tsv', sep='\t', index=False)
    metrics = []
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = {executor.submit(run_fit, task): task for task in all_tasks}
        for n, future in enumerate(as_completed(futures), 1):
            result = future.result()
            task = futures[future]
            path = Path(task[1])
            metrics.append({k: v for k, v in result.items() if k != 'attempts'} |
                           dict(dataset=path.parent.parent.name, config=path.parent.name))
            if n % 10 == 0 or n == len(all_tasks):
                print(f'FITS {n}/{len(all_tasks)} elapsed={time.time()-started:.1f}s', flush=True)
    pd.DataFrame(metrics).sort_values(['dataset', 'config', 'seed']).to_csv(
        out / 'tables/fit_metrics.tsv', sep='\t', index=False)
    all_genes, matches, stability_all, donors_all, tests_all = [], [], [], [], []
    reproduction = []
    for dataset, path in paths.items():
        data = ad.read_h5ad(path)
        ref_file = rebuild / 'fits' / dataset / 'primary300_K10_consensus.npz'
        with np.load(ref_file) as ref:
            reference = ref['loadings']
            assert np.array_equal(ref['gene_ids'], data.var_names.to_numpy(str))
        old_tests = pd.read_csv(rebuild / 'tables' / f'{dataset}_donor_tests.tsv', sep='\t')
        old_tests = old_tests.loc[old_tests.scheme.eq('primary300') & old_tests['rank'].eq(10)]
        for _, conf in configs.loc[configs.dataset.eq(dataset)].fillna('').iterrows():
            cid = conf.config
            folder = out / 'fits' / dataset / cid
            matrices = [np.load(folder / f'seed{seed}.npz')['loadings'] for seed in SEEDS]
            consensus, stability, alignment = align_consensus(matrices, SEEDS)
            cols, cos = match_reference(reference, consensus)
            matched = consensus[cols]
            stability['reference_component'] = [int(np.flatnonzero(cols == i)[0] + 1) for i in range(RANK)]
            stability['dataset'], stability['config'] = dataset, cid
            stability_all.append(stability)
            alignment.to_csv(folder / 'seed_alignment.tsv', sep='\t', index=False)
            np.savez_compressed(folder / 'consensus.npz', loadings=matched,
                                gene_ids=data.var_names.to_numpy(str), original_components=cols + 1)
            top = []
            for i, profile in enumerate(matched):
                ref_set, test_set = top_indices(reference[i]), top_indices(profile)
                matches.append(dict(dataset=dataset, config=cid, kind=conf.kind, arm=conf.arm,
                    sampling_seed=conf.sampling_seed, omitted_donor=conf.omitted_donor,
                    reference_component=i+1, candidate_component=int(cols[i]+1),
                    cosine=float(cos[i]), top50_jaccard=jaccard(ref_set, test_set),
                    shared_top50=len(ref_set & test_set),
                    max_loading_difference=float(np.abs(reference[i] - profile).max())))
                for order, j in enumerate(np.argsort(-profile, kind='stable')[:100], 1):
                    top.append(dict(dataset=dataset, config=cid, component=i+1,
                        program_id=f'{dataset}_{cid}_refC{i+1}', gene_rank=order,
                        gene_id=str(data.var_names[j]), gene_symbol=str(data.var.iloc[j].gene_symbol),
                        loading=float(profile[j])))
            top = pd.DataFrame(top)
            all_genes.append(top)
            retained = data.obs.donor_id.astype(str).ne(str(conf.omitted_donor)).to_numpy()
            obs = data.obs.loc[retained].copy()
            _, donors, tests, _ = score_modules(data.X[retained], obs, data.var, top, dataset)
            for frame in (donors, tests):
                frame['config'], frame['kind'], frame['arm'] = cid, conf.kind, conf.arm
                frame['sampling_seed'], frame['omitted_donor'] = conf.sampling_seed, conf.omitted_donor
                frame['reference_component'] = frame.program_id.str.extract(r'_refC(\d+)$').astype(int)
            donors_all.append(donors)
            tests_all.append(tests)
            if conf.kind == 'full' and conf.arm == 'balanced' and conf.sampling_seed == SAMPLING[0]:
                for _, test in tests.iterrows():
                    old = old_tests.loc[old_tests.program_id.eq(f'{dataset}_primary300_K10_C{test.reference_component}')].iloc[0]
                    reproduction.append(dict(dataset=dataset, component=test.reference_component,
                        delta_error=float(test.delta-old.delta), q_error=float(test.bh_fdr-old.bh_fdr),
                        max_loading_error=float(np.abs(matched[test.reference_component-1]-reference[test.reference_component-1]).max())))
            print('SCORED', dataset, cid, flush=True)
        del data
    tests = pd.concat(tests_all, ignore_index=True)
    tests['bh_full_60_per_dataset'] = np.nan
    for dataset in paths:
        keep = tests.dataset.eq(dataset) & tests.kind.eq('full')
        tests.loc[keep, 'bh_full_60_per_dataset'] = bh(tests.loc[keep, 'exact_p'])
    outputs = {'program_matches': pd.DataFrame(matches), 'program_genes': pd.concat(all_genes, ignore_index=True),
               'consensus_stability': pd.concat(stability_all, ignore_index=True),
               'donor_scores': pd.concat(donors_all, ignore_index=True), 'donor_tests': tests,
               'reference_reproduction': pd.DataFrame(reproduction)}
    for name, frame in outputs.items():
        frame.to_csv(out / 'tables' / f'{name}.tsv', sep='\t', index=False)
    check = outputs['reference_reproduction']
    assert check[['delta_error', 'q_error', 'max_loading_error']].abs().to_numpy().max() < 1e-7
    match_tests = outputs['program_matches'].merge(tests[['dataset', 'config', 'reference_component', 'delta', 'bh_fdr']],
                      on=['dataset', 'config', 'reference_component'], validate='one_to_one')
    match_tests.to_csv(out / 'tables/matches_and_tests.tsv', sep='\t', index=False)
    summarize(out, configs, match_tests)
    completion = dict(n_fits=len(metrics), n_configurations=len(configs), run_id=run_id,
        all_converged=all(m['converged'] for m in metrics), reference_reproduced=True,
        elapsed_seconds=time.time()-started, finished_local=time.strftime('%Y-%m-%d %H:%M:%S'),
        output_sha256={str(p.relative_to(out)): sha256(p) for folder in ('tables', 'figures')
                       for p in sorted((out / folder).glob('*')) if p.is_file()})
    write_json(out / 'completion.pending.json', completion)
    os.replace(out / 'completion.pending.json', out / 'completion.json')
    write_json(out / 'run_state.json', dict(run_id=run_id, status='complete'))
    print('COMPLETE', str(out), flush=True)


def summarize(out, configs, results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'pdf.fonttype': 42})
    selected = results.loc[(results.dataset.eq('GSE220243') & results.reference_component.eq(9)) |
                           (results.dataset.eq('HRA001986') & results.reference_component.eq(4))].copy()
    summaries = []
    for key, g in selected.groupby(['dataset', 'kind', 'arm']):
        summaries.append(dict(dataset=key[0], kind=key[1], arm=key[2], n_configurations=len(g),
            jaccard_min=g.top50_jaccard.min(), jaccard_max=g.top50_jaccard.max(),
            jaccard_median=g.top50_jaccard.median(), cosine_min=g.cosine.min(),
            delta_min=g.delta.min(), delta_max=g.delta.max(), n_positive=int(g.delta.gt(0).sum()),
            n_q_below_05=int(g.bh_fdr.lt(.05).sum())))
    pd.DataFrame(summaries).to_csv(out / 'tables/collagen_program_summary.tsv', sep='\t', index=False)
    fig, axes = plt.subplots(2, 2, figsize=(8, 6.4), constrained_layout=True)
    colors = {'balanced': '#247B91', 'pooled': '#C46B31'}
    for col, (dataset, label) in enumerate([('GSE220243', 'GSE220243 C9'), ('HRA001986', 'HRA001986 C4')]):
        c = configs.loc[configs.dataset.eq(dataset) & configs.kind.eq('full')]
        a = axes[0, col]
        for x, arm in enumerate(ARMS):
            v = c.loc[c.arm.eq(arm), 'max_donor_loss_share'].to_numpy()
            a.scatter(x + np.linspace(-.08,.08,len(v)), v, color=colors[arm], s=35)
        a.axhline(1/(13 if col == 0 else 8), ls=':', color='gray')
        a.set(xticks=[0,1], xticklabels=['Balanced','Pooled'], ylabel='Largest donor loss-weight share',
              title=f'{"ab"[col]}  {dataset}: equal total cell budget')
        a.set_ylim(0, max(.25, c.max_donor_loss_share.max()*1.2))
        a = axes[1, col]
        g = selected.loc[selected.dataset.eq(dataset) & selected.kind.eq('omit')]
        donors = sorted(g.omitted_donor.unique())
        for arm in ARMS:
            y = g.loc[g.arm.eq(arm)].set_index('omitted_donor').loc[donors, 'top50_jaccard']
            a.plot(range(len(donors)), y, marker='o', ms=4, lw=1, color=colors[arm], label=arm.capitalize())
        a.set(xticks=list(range(len(donors))), xticklabels=donors, ylim=(0,1.03),
              ylabel='Top-50 Jaccard to original balanced program', xlabel='Omitted donor',
              title=f'{"cd"[col]}  {label}: conditional omission refits')
        a.tick_params(axis='x', labelrotation=65, labelsize=7)
        a.legend(frameon=False, fontsize=8)
    fig.savefig(out / 'figures/Supplementary_Figure_S3.png', dpi=300)
    fig.savefig(out / 'figures/Supplementary_Figure_S3.pdf')
    plt.close(fig)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rebuild', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--full-only', action='store_true')
    args = p.parse_args()
    try:
        execute(args.rebuild, args.out, args.jobs, not args.full_only)
    except Exception as exc:
        state = json.loads((args.out / 'run_state.json').read_text(encoding='utf-8'))
        state.update(status='failed', error=repr(exc))
        write_json(args.out / 'run_state.json', state)
        raise

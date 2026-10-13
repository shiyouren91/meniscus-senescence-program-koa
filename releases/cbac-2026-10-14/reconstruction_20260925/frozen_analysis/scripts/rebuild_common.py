"""Shared, independently testable helpers for the donor-aware technical rebuild."""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linear_sum_assignment
from sklearn.metrics.pairwise import cosine_similarity

RANKS = (10, 12, 14, 16)
SEEDS = (11, 23, 37, 53, 71)
SAMPLING_SEEDS = {'primary300': 20260925, 'sensitivity1000': 20260926}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def bh(values):
    values = np.asarray(values, dtype=float)
    result = np.full(values.shape, np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    order = valid[np.argsort(values[valid])]
    adjusted = values[order] * len(order) / np.arange(1, len(order) + 1)
    result[order] = np.minimum(np.minimum.accumulate(adjusted[::-1])[::-1], 1)
    return result


def exact_permutation(values, cases):
    values, cases = np.asarray(values, float), np.asarray(cases, bool)
    assert len(values) == len(cases) and np.isfinite(values).all()
    n, n_case = len(values), int(cases.sum())
    assert 0 < n_case < n
    delta = values[cases].mean() - values[~cases].mean()
    extreme, total = 0, values.sum()
    tolerance = 1e-12 * max(1, abs(delta))
    for indices in itertools.combinations(range(n), n_case):
        selected = values[list(indices)].sum()
        permuted = selected / n_case - (total - selected) / (n - n_case)
        extreme += abs(permuted) >= abs(delta) - tolerance
    count = math.comb(n, n_case)
    return float(delta), extreme / count, int(extreme), count


def donor_region_weights(obs):
    """Weights sum to one: equal donor, equal region within donor, equal cell within region."""
    obs = obs[['donor_id', 'sample_id']].astype(str)
    assert obs.groupby('sample_id').donor_id.nunique().max() == 1
    region_sizes = obs.groupby('sample_id').size()
    regions_per_donor = obs.drop_duplicates().groupby('donor_id').size()
    result = 1 / (obs.donor_id.nunique() * obs.donor_id.map(regions_per_donor).to_numpy()
                  * obs.sample_id.map(region_sizes).to_numpy())
    assert np.isclose(result.sum(), 1)
    return result


def select_cells(obs, cap, seed):
    """Balanced regional quotas, redistributing unfilled quotas within the same donor."""
    rng, selected = np.random.default_rng(seed), []
    for donor in sorted(obs.donor_id.unique()):
        group = obs.loc[obs.donor_id.eq(donor)]
        samples = sorted(group.sample_id.unique())
        budget = min(cap, len(group))
        available = {sample: list(rng.permutation(np.flatnonzero(obs.sample_id.eq(sample).to_numpy())))
                     for sample in samples}
        while budget:
            progress = False
            for sample in samples:
                if budget and available[sample]:
                    selected.append(available[sample].pop())
                    budget -= 1
                    progress = True
            assert progress, 'Sampling budget cannot be fulfilled'
    return np.asarray(sorted(selected), dtype=int)


def normalize_from_full_totals(matrix, totals):
    totals = np.asarray(totals, float)
    assert len(totals) == matrix.shape[0] and (totals > 0).all()
    normalized = sparse.diags(1e4 / totals).dot(matrix.astype(np.float64)).tocsr()
    normalized.data = np.log1p(normalized.data)
    return normalized.astype(np.float32)


def align_consensus(matrices, seeds):
    """Medoid-run, one-to-one alignment; no seed contributes multiple components."""
    normalized = [np.asarray(x, float) / np.maximum(np.asarray(x, float).sum(1, keepdims=True), 1e-12)
                  for x in matrices]
    n_seeds, rank = len(normalized), len(normalized[0])
    pair = np.zeros((n_seeds, n_seeds))
    for i in range(n_seeds):
        for j in range(i + 1, n_seeds):
            sim = cosine_similarity(normalized[i], normalized[j])
            rows, cols = linear_sum_assignment(-sim)
            pair[i, j] = pair[j, i] = sim[rows, cols].mean()
    medoid_index = int(np.argmax(pair.sum(1)))
    reference, aligned, mappings = normalized[medoid_index], [], []
    for seed, matrix in zip(seeds, normalized):
        sim = cosine_similarity(reference, matrix)
        rows, cols = linear_sum_assignment(-sim)
        assert np.array_equal(rows, np.arange(rank)) and len(set(cols)) == rank
        aligned.append(matrix[cols])
        mappings.extend(dict(seed=int(seed), reference_component=int(i + 1),
                             original_component=int(j + 1), reference_cosine=float(sim[i, j]))
                        for i, j in zip(rows, cols))
    stack = np.stack(aligned)
    consensus = np.median(stack, axis=0)
    consensus /= np.maximum(consensus.sum(1, keepdims=True), 1e-12)
    stability = []
    for component in range(rank):
        pairwise = cosine_similarity(stack[:, component, :])
        values = pairwise[np.triu_indices(n_seeds, 1)]
        stability.append(dict(component=component + 1, medoid_seed=int(seeds[medoid_index]),
                              n_seeds=n_seeds, median_pairwise_cosine=float(np.median(values)),
                              min_pairwise_cosine=float(values.min())))
    return consensus, pd.DataFrame(stability), pd.DataFrame(mappings)


def score_modules(matrix, obs, var, top_genes, dataset):
    """Program expression scores, not NMF usage fractions. Inference uses donors."""
    lookup = {str(g): i for i, g in enumerate(var.index)}
    weights = donor_region_weights(obs)
    region_frames, donor_frames, tests, influence = [], [], [], []
    region_meta = obs[['sample_id', 'donor_id', 'status', 'region']].drop_duplicates().set_index('sample_id')
    assert region_meta.index.is_unique
    for program_id, genes in top_genes.groupby('program_id', sort=True):
        selected = genes.sort_values('gene_rank').head(30)
        positions = [lookup[g] for g in selected.gene_id]
        block = matrix[:, positions].astype(np.float64).tocsr()
        means = np.asarray(block.T.dot(weights)).ravel()
        squared = block.copy()
        squared.data **= 2
        variance = np.maximum(np.asarray(squared.T.dot(weights)).ravel() - means ** 2, 0)
        std = np.sqrt(variance)
        keep = std > 1e-8
        assert keep.sum() > 0
        values = np.asarray(block[:, keep].dot(1 / std[keep])).ravel() / keep.sum()
        values -= np.mean(means[keep] / std[keep])
        cells = pd.DataFrame({'sample_id': obs.sample_id.to_numpy(), 'score': values})
        regions = cells.groupby('sample_id').score.agg(['mean', 'median', 'size']).rename(
            columns={'mean': 'mean_score', 'median': 'median_score', 'size': 'n_cells'}).join(region_meta).reset_index()
        regions['program_id'], regions['dataset'] = program_id, dataset
        donors = regions.groupby(['donor_id', 'status'], as_index=False, observed=True).agg(
            mean_score=('mean_score', 'mean'), n_regions=('sample_id', 'size'), n_cells=('n_cells', 'sum'))
        donors['program_id'], donors['dataset'] = program_id, dataset
        cases = donors.status.eq('case').to_numpy()
        values = donors.mean_score.to_numpy()
        delta, p, extreme, allocations = exact_permutation(values, cases)
        positive, negative = values[cases], values[~cases]
        pairwise = positive[:, None] - negative[None, :]
        tests.append(dict(dataset=dataset, program_id=program_id, n_case=len(positive), n_control=len(negative),
                          mean_case=positive.mean(), mean_control=negative.mean(), delta=delta,
                          cliffs_delta=float(np.sign(pairwise).mean()), exact_p=p,
                          extreme_allocations=extreme, total_allocations=allocations,
                          n_scored_genes=int(keep.sum())))
        for i, row in donors.iterrows():
            subset = donors.drop(index=i)
            shift = subset.loc[subset.status.eq('case'), 'mean_score'].mean() - subset.loc[subset.status.eq('control'), 'mean_score'].mean()
            influence.append(dict(dataset=dataset, program_id=program_id, omitted_donor=row.donor_id,
                                  delta_without_donor=shift, sign_preserved=bool(np.sign(shift) == np.sign(delta))))
        region_frames.append(regions)
        donor_frames.append(donors)
    tests = pd.DataFrame(tests)
    tests['bh_fdr'] = bh(tests.exact_p)
    return pd.concat(region_frames, ignore_index=True), pd.concat(donor_frames, ignore_index=True), tests, pd.DataFrame(influence)

"""Small deterministic regression checks for the rebuilt inference helpers."""
import unittest
import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy import sparse
from scipy import stats

from rebuild_common import align_consensus, bh, donor_region_weights, exact_permutation, normalize_from_full_totals, select_cells, score_modules
from bulk_statistics import normalize_counts, resolve_gene, compare_scores, pm_modified_hk
from bulk_inputs import _platform_annotations


class RebuildTests(unittest.TestCase):
    def test_exhaustive_permutation_has_no_plus_one(self):
        delta, p, extreme, n = exact_permutation([1, 1, 0, 0], [1, 1, 0, 0])
        self.assertEqual((delta, extreme, n), (1, 2, 6))
        self.assertAlmostEqual(p, 1/3)

    def test_bh(self):
        np.testing.assert_allclose(bh([.01, .04, .03]), [.03, .04, .04])

    def test_full_library_denominator(self):
        result = normalize_from_full_totals(sparse.csr_matrix([[2, 3], [4, 6]]), [10, 20])
        np.testing.assert_allclose(result.toarray(), np.log1p([[2000, 3000], [2000, 3000]]), rtol=1e-6)

    def test_donor_weight_not_library_weight(self):
        obs = pd.DataFrame({'donor_id':['A']*6+['B']*2, 'sample_id':['A1']*4+['A2']*2+['B1']*2})
        weights = donor_region_weights(obs)
        self.assertAlmostEqual(weights[:6].sum(), .5)
        self.assertAlmostEqual(weights[:4].sum(), .25)
        selected = select_cells(obs, 2, 11)
        self.assertEqual(obs.iloc[selected].groupby('donor_id').size().tolist(), [2, 2])

    def test_one_component_per_seed(self):
        base = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1.]])
        consensus, stability, mapping = align_consensus([base, base[[2, 0, 1]], base[[1, 2, 0]]], [1, 2, 3])
        self.assertEqual(len(mapping), 9)
        self.assertTrue(mapping.groupby('seed').original_component.nunique().eq(3).all())
        np.testing.assert_allclose(stability.median_pairwise_cosine, 1)
        np.testing.assert_allclose(consensus, base)

    def test_categorical_metadata_does_not_create_phantom_donors(self):
        obs = pd.DataFrame({'sample_id':['A1','A1','A2','B1','C1','D1'],
                            'donor_id':['A','A','A','B','C','D'],
                            'status':['case']*4+['control']*2,
                            'region':['inner','inner','outer','inner','inner','inner']}).astype('category')
        var = pd.DataFrame(index=['g1','g2'])
        top = pd.DataFrame({'program_id':['p1','p1'],'gene_id':['g1','g2'],'gene_rank':[1,2]})
        matrix = sparse.csr_matrix([[1.,1.],[1.,2.],[2.,2.],[2.,3.],[4.,4.],[5.,5.]])
        regions, donors, tests, influence = score_modules(matrix,obs,var,top,'test')
        self.assertEqual(len(donors),4)
        self.assertEqual(int(tests.iloc[0].n_case),2)
        self.assertTrue(np.isfinite(donors.mean_score).all())

    def test_count_depth_invariance(self):
        baseline=np.arange(1,21,dtype=float)
        values=np.column_stack([baseline,baseline*10])
        normalized,factors,totals=normalize_counts(values)
        np.testing.assert_allclose(normalized[:,0],normalized[:,1])
        self.assertAlmostEqual(factors[1]/factors[0],10)
        self.assertAlmostEqual(totals[1]/totals[0],10)
        cpm,_,_=normalize_counts(values,'cpm')
        np.testing.assert_allclose(cpm[:,0],cpm[:,1])

    def test_multigene_probes_excluded_aliases_retained(self):
        aliases={'OLD':{'g1'},'NEW':{'g1'},'B':{'g2'}}
        ids={'g1','g2'}
        self.assertEqual(resolve_gene({'gene_symbol':'OLD /// NEW'},aliases,ids)[0],'g1')
        self.assertIsNone(resolve_gene({'gene_symbol':'OLD /// B'},aliases,ids)[0])
        self.assertIsNone(resolve_gene({'gene_symbol':'OLD /// UNKNOWN'},aliases,ids)[0])

    def test_transcript_ids_are_not_mistaken_for_gene_ids(self):
        index=pd.Index(['p1','p2'])
        platform=pd.DataFrame({'ENSEMBL_ID':['ENST000000001','ENSG000000002'],
                               'GENE_SYMBOL':['FN1','OTHER']},index=index)
        result=_platform_annotations(index,platform)
        self.assertEqual(result.loc['p1','gene_id'],'')
        self.assertEqual(result.loc['p1','transcript_id'],'ENST000000001')
        self.assertEqual(result.loc['p1','gene_symbol'],'FN1')
        self.assertEqual(result.loc['p2','gene_id'],'ENSG000000002')

    def test_hedges_g_sign_and_pooled_no_pvalue(self):
        values=[1,2,3,0,1,2]; cases=[1,1,1,0,0,0]
        result=compare_scores(values,cases)
        self.assertGreater(result['hedges_g'],0)
        self.assertAlmostEqual(result['welch_p'],stats.ttest_ind(values[:3],values[3:],equal_var=False).pvalue)
        pooled=compare_scores(values,cases,inferential=False)
        self.assertTrue(np.isnan(pooled['welch_p']))
        self.assertTrue(np.isnan(pooled['variance_g']))

    def test_modified_hk_keeps_small_k_uncertainty(self):
        result=pm_modified_hk([1,1,1],[.1,.1,.1])
        self.assertEqual(result['tau_squared'],0)
        self.assertEqual(result['hk_scale'],1)
        self.assertAlmostEqual(result['se_modified_hk'],np.sqrt(.1/3))
        self.assertAlmostEqual(result['ci_high'],1+stats.t.ppf(.975,2)*np.sqrt(.1/3))
        with self.assertRaises(ValueError):
            pm_modified_hk([1],[.1])

    def test_checkpoint_tampering_forces_refit(self):
        path=Path(__file__).with_name('02_discover_programs.py')
        spec=importlib.util.spec_from_file_location('discovery_for_test',path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        class FakeNMF:
            fits=0
            def __init__(self,**kwargs):
                self.rank=kwargs['n_components']
            def fit_transform(self,matrix):
                FakeNMF.fits+=1
                self.components_=np.ones((self.rank,matrix.shape[1]))
                self.n_iter_=2; self.reconstruction_err_=1.
        cache=Path(__file__).resolve().parents[1]/'cache'
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as directory,patch.object(module,'NMF',FakeNMF):
            directory=Path(directory); matrix=directory/'matrix.npz'; prefix=directory/'fit'
            sparse.save_npz(matrix,sparse.csr_matrix(np.ones((4,3))))
            task=(matrix,prefix,module.sha256(matrix),2,11)
            module.run_fit(task);module.run_fit(task)
            self.assertEqual(FakeNMF.fits,1)
            np.savez_compressed(prefix.with_suffix('.npz'),loadings=np.zeros((2,3)))
            module.run_fit(task)
            self.assertEqual(FakeNMF.fits,2)


if __name__ == '__main__':
    unittest.main()

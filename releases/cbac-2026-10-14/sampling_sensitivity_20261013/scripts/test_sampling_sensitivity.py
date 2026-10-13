import itertools
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from types import SimpleNamespace
import numpy as np
import pandas as pd
from sampling_sensitivity import sample_arm, match_reference, jaccard, fixed_omission_sample, configurations, begin_run
from rebuild_common import donor_region_weights, exact_permutation, bh


class SamplingTests(unittest.TestCase):
    def setUp(self):
        self.obs = pd.DataFrame({'donor_id': ['A']*1000+['B']*100+['C']*500,
                                 'sample_id': ['A1']*700+['A2']*300+['B1']*100+['C1']*500,
                                 'status': ['case']*1100+['control']*500})

    def test_matched_budget_unique_and_reproducible(self):
        for arm in ('balanced', 'pooled'):
            s, w = sample_arm(self.obs, arm, 11)
            self.assertEqual(len(s), 700)
            self.assertEqual(len(set(s)), 700)
            np.testing.assert_array_equal(s, sample_arm(self.obs, arm, 11)[0])
            self.assertAlmostEqual(w.sum(), 700)

    def test_balanced_loss_and_regions(self):
        s, w = sample_arm(self.obs, 'balanced', 11)
        selected = self.obs.iloc[s].assign(weight=w)
        np.testing.assert_allclose(selected.groupby('donor_id').weight.sum(), 700/3)
        self.assertEqual(selected.sample_id.eq('A1').sum(), 150)
        self.assertEqual(selected.sample_id.eq('A2').sum(), 150)

    def test_labels_ignored(self):
        relabeled = self.obs.assign(status='unavailable')
        for arm in ('balanced', 'pooled'):
            np.testing.assert_array_equal(sample_arm(self.obs, arm, 12)[0], sample_arm(relabeled, arm, 12)[0])

    def test_pooled_weights_and_yield(self):
        s, w = sample_arm(self.obs, 'pooled', 11)
        self.assertTrue((w == 1).all())
        self.assertGreater(self.obs.iloc[s].donor_id.eq('A').mean(), .5)

    def test_hungarian_permutation(self):
        x = np.eye(4)
        col, similarity = match_reference(x, x[[2,0,3,1]])
        np.testing.assert_array_equal(col, [1,3,0,2])
        np.testing.assert_allclose(similarity, 1)

    def test_full_set_jaccard(self):
        self.assertAlmostEqual(jaccard(set(range(50)), set(range(19,69))), 31/69)

    def test_exact_permutation_and_bh(self):
        delta, p, extreme, total = exact_permutation([0,1,2,3], [False,False,True,True])
        self.assertEqual((delta, extreme, total), (2,2,6))
        self.assertAlmostEqual(p, 1/3)
        np.testing.assert_allclose(bh([.01,.04,.9]), [.03,.06,.9])

    def test_invalid(self):
        with self.assertRaises(ValueError): sample_arm(self.obs, 'unknown', 11)
        with self.assertRaises(ValueError): sample_arm(self.obs.iloc[:0], 'pooled', 11)

    def test_omission_retains_exact_cells(self):
        for arm in ('balanced', 'pooled'):
            full, _ = sample_arm(self.obs, arm, 11)
            for donor in ('A','B','C'):
                selected, weights = fixed_omission_sample(self.obs, arm, 11, donor)
                expected = full[self.obs.iloc[full].donor_id.ne(donor).to_numpy()]
                np.testing.assert_array_equal(selected, expected)
                self.assertFalse(self.obs.iloc[selected].donor_id.eq(donor).any())
                self.assertAlmostEqual(weights.sum(), len(selected))

    def test_configuration_counts(self):
        total = 0
        for n in (13,8):
            fake = SimpleNamespace(obs=pd.DataFrame({'donor_id': [str(i) for i in range(n)]}))
            total += len(list(configurations(fake, True)))
        self.assertEqual(total,54)
        self.assertEqual(total*5,270)

    def test_begin_run_invalidates_previous_completion(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'completion.json').write_text('{}')
            (root/'provenance.json').write_text('{}')
            run_id=begin_run(root)
            self.assertFalse((root/'completion.json').exists())
            self.assertTrue((root/f'completion.previous.{run_id}.json').exists())
            self.assertEqual(json.loads((root/'run_state.json').read_text())['status'],'running')


if __name__ == '__main__': unittest.main()

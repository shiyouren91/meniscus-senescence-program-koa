"""Fixed GSE programs projected onto full-gene HRA expression, without refitting."""
from pathlib import Path
import argparse
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import anndata as ad
import numpy as np
import pandas as pd
from rebuild_common import score_modules, sha256, write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,required=True)
    root=parser.parse_args().project_root
    out=Path(__file__).resolve().parents[1]
    tables=out/'tables'
    path=tables/'locked_GSE_program_genes_for_bulk.tsv'
    lock=json.loads((out/'bulk_program_lock.json').read_text(encoding='utf-8'))
    assert sha256(path)==lock['programs_sha256']
    genes=pd.read_csv(path,sep='\t')
    mapping=pd.read_csv(tables/'HRA001986_symbol_mapping.tsv',sep='\t').fillna('')
    raw=ad.read_h5ad(root/'data/raw/HRA001986/meniscal_chondrocyte.h5ad')
    assert np.array_equal(raw.var_names.str.upper().to_numpy(),mapping.original_symbol.to_numpy())
    eligible=mapping.unique_mapping.astype(bool)&mapping.gene_id.isin(genes.gene_id)
    positions=np.flatnonzero(eligible)
    block=raw.X[:,positions].tocsr().astype(np.float64)
    means=np.asarray(block.mean(0)).ravel()
    squared=block.copy(); squared.data**=2
    variable=np.asarray(squared.mean(0)).ravel()-means**2>1e-16
    var=mapping.loc[eligible,['gene_id','original_symbol']].set_index('gene_id').rename(columns={'original_symbol':'gene_symbol'})
    var=var.iloc[np.flatnonzero(variable)]
    block=block[:,variable]
    obs=pd.read_csv(tables/'HRA001986_cell_metadata.tsv.gz',sep='\t',index_col=0)
    assert obs.index.equals(raw.obs_names)
    coverage=[]; selected=[]
    for program,frame in genes.groupby('program_id'):
        kept=frame.loc[frame.gene_id.isin(var.index)].copy()
        coverage.append(dict(program_id=program,n_expected=len(frame),n_mapped_variable=len(kept),
                             coverage=len(kept)/len(frame),eligible=len(kept)>=21,
                             missing_symbols=','.join(frame.loc[~frame.gene_id.isin(var.index),'gene_symbol'])))
        if len(kept)>=21:
            selected.append(kept)
    pd.DataFrame(coverage).to_csv(tables/'HRA_fixed_GSE_projection_coverage.tsv',sep='\t',index=False)
    if not selected:
        raise RuntimeError('No locked program meets the prespecified coverage gate')
    region,donor,tests,influence=score_modules(block,obs,var,pd.concat(selected), 'HRA001986_fixed_GSE_projection')
    for name,table in [('regional_scores',region),('donor_scores',donor),('donor_tests',tests),('leave_one_donor_out',influence)]:
        table.to_csv(tables/f'HRA_fixed_GSE_projection_{name}.tsv',sep='\t',index=False)
    write_json(out/'fixed_projection_summary.json',dict(program_list_sha256=sha256(path),n_programs=len(tests),
               n_fdr_below_005=int(tests.bh_fdr.lt(.05).sum()),
               limitation='Previously explored cohort; age/BMI confounding; expression-score projection is not independent causal or clinical validation'))
    gse=pd.read_csv(tables/'GSE220243_donor_scores.tsv',sep='\t')
    gse=gse.loc[gse.program_id.isin(genes.program_id)]
    order=genes.sort_values('component').program_id.drop_duplicates().tolist()
    labels={name:name.split('_')[-1]+' '+','.join(frame.sort_values('gene_rank').head(3).gene_symbol)
            for name,frame in genes.groupby('program_id')}
    fig,axes=plt.subplots(1,2,figsize=(13,7),sharey=True,layout='constrained')
    rng=np.random.default_rng(20260925)
    for ax,frame,title in [(axes[0],gse,'GSE220243: 6 OA / 7 normal donors'),
                           (axes[1],donor,'HRA001986: 4 degenerated / 4 normal donors')]:
        for y,name in enumerate(order):
            for status,color,offset in [('control','#356989',-.13),('case','#b05235',.13)]:
                values=frame.loc[frame.program_id.eq(name)&frame.status.eq(status),'mean_score']
                jitter=rng.uniform(-.055,.055,len(values))
                ax.scatter(values,y+offset+jitter,color=color,s=20,alpha=.8,label=status if y==0 else None)
                ax.plot(values.mean(),y+offset,marker='|',markersize=13,color='black',markeredgewidth=2)
        ax.axvline(0,color='#aaaaaa',linewidth=.7);ax.set_title(title)
        ax.set_xlabel('Program expression score (within-cohort standardization)')
        ax.legend(loc='lower right',fontsize=8)
    axes[0].set_yticks(range(len(order)),[labels[name] for name in order]);axes[0].invert_yaxis()
    fig.savefig(out/'figures/fixed_program_donor_scores.png',dpi=300)
    fig.savefig(out/'figures/fixed_program_donor_scores.pdf');plt.close(fig)
    print(tests.sort_values('bh_fdr').to_string(index=False),flush=True)


if __name__=='__main__':
    main()

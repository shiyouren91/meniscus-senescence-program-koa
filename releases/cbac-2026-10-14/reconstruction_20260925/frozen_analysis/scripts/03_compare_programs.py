"""Compare independently discovered programs without selecting on disease effects."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import anndata as ad

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import hypergeom

from rebuild_common import bh, sha256, write_json

LEGACY={'collagen_rich_ecm':12,'fibrocartilage_identity':6,'stress_senescence_associated':5,'hypoxia_angiogenic_reference':7}


def module_sets(top, n=50):
    return {name:set(frame.sort_values('gene_rank').head(n).gene_id)
            for name,frame in top.groupby('program_id',sort=True)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,required=True)
    root=parser.parse_args().project_root.resolve()
    out=Path(__file__).resolve().parents[1]
    tables,figures=out/'tables',out/'figures'
    figures.mkdir(exist_ok=True)
    tops,tests,ranks={}, {}, {}
    for dataset in ['GSE220243','HRA001986']:
        ranks[dataset]=json.loads((out/f'{dataset}_discovery_summary.json').read_text(encoding='utf-8'))['primary_rank']
        all_top=pd.read_csv(tables/f'{dataset}_consensus_top_genes.tsv',sep='\t')
        tops[dataset]=all_top.loc[all_top.scheme.eq('primary300')&all_top['rank'].eq(ranks[dataset])].copy()
        all_tests=pd.read_csv(tables/f'{dataset}_donor_tests.tsv',sep='\t')
        tests[dataset]=all_tests.loc[all_tests.scheme.eq('primary300')&all_tests['rank'].eq(ranks[dataset])].copy()
    gse_sets,hra_sets=module_sets(tops['GSE220243']),module_sets(tops['HRA001986'])
    g_universe=pd.read_csv(tables/'GSE220243_gene_universe.tsv',sep='\t')
    h_universe=pd.read_csv(tables/'HRA001986_gene_universe.tsv',sep='\t')
    detected_universe=set(g_universe.loc[g_universe.detected_cells.ge(3),'gene_id'])&set(h_universe.loc[h_universe.detected_cells.ge(3),'gene_id'])
    input_genes={}
    for dataset,filename in [('GSE220243','GSE220243_repaired_hvg.h5ad'),('HRA001986','HRA001986_mapped_hvg.h5ad')]:
        obj=ad.read_h5ad(out/'data'/filename,backed='r')
        input_genes[dataset]=set(obj.var_names)
        obj.file.close()
    # Conditional overlap null: a gene must have been eligible for both decompositions.
    universe=detected_universe&input_genes['GSE220243']&input_genes['HRA001986']
    symbols=g_universe.set_index('gene_id').gene_symbol.to_dict()
    pairs=[]
    for gname,genes in gse_sets.items():
        for hname,hgenes in hra_sets.items():
            ga,ha=genes&universe,hgenes&universe
            overlap=genes&hgenes
            pairs.append(dict(gse_program=gname,hra_program=hname,full_top50_overlap_n=len(overlap),
                              full_top50_jaccard=len(overlap)/len(genes|hgenes),shared_detected_universe_n=len(detected_universe),
                              shared_nmf_input_test_universe_n=len(universe),
                              hypergeom_background='shared detected NMF-input genes; conditional descriptive overlap test',
                              gse_top50_n=len(genes),hra_top50_n=len(hgenes),gse_genes_in_shared_universe=len(ga),
                              hra_genes_in_shared_universe=len(ha),overlap_shared_universe=len(ga&ha),
                              hypergeom_p=float(hypergeom.sf(len(ga&ha)-1,len(universe),len(ga),len(ha))) if ga&ha else 1.,
                              overlap_gene_ids=','.join(sorted(overlap)),
                              overlap_gene_symbols=','.join(sorted(symbols.get(g,g) for g in overlap))))
    pairs=pd.DataFrame(pairs)
    pairs['hypergeom_fdr_all_pairs']=bh(pairs.hypergeom_p)
    pairs.to_csv(tables/'independent_all_module_matches.tsv',sep='\t',index=False)
    best=pairs.sort_values(['gse_program','full_top50_jaccard','hra_program'],ascending=[True,False,True]).drop_duplicates('gse_program')
    best=best.merge(tests['GSE220243'][['program_id','delta','bh_fdr']].rename(columns={'program_id':'gse_program','delta':'gse_donor_delta','bh_fdr':'gse_donor_fdr'}),on='gse_program',validate='one_to_one')
    best=best.merge(tests['HRA001986'][['program_id','delta','bh_fdr']].rename(columns={'program_id':'hra_program','delta':'hra_donor_delta','bh_fdr':'hra_donor_fdr'}),on='hra_program',validate='many_to_one')
    best.to_csv(tables/'independent_best_matches_with_donor_effects.tsv',sep='\t',index=False)

    aliases=pd.read_csv(tables/'gene_id_alias_map.tsv',sep='\t').fillna('')
    alias_to_ids={}
    for row in aliases.itertuples():
        for symbol in row.all_source_symbols.split('|'):
            alias_to_ids.setdefault(symbol,set()).add(row.gene_id)
    old=pd.read_csv(out/'inputs/legacy_GSE_top_genes.tsv',sep='\t')
    old_sets={}
    for name,component in LEGACY.items():
        genes=old.loc[old.nmf_rank.eq(14)&old.consensus_component.eq(component)].sort_values('gene_rank').head(50).gene.str.upper()
        old_sets[name]=set(next(iter(alias_to_ids[gene])) for gene in genes if len(alias_to_ids.get(gene,[]))==1)
    tracking=[]
    for name,query in old_sets.items():
        for program,genes in gse_sets.items():
            tracking.append(dict(legacy_label=name,repaired_program=program,legacy_mapped_unique_genes=len(query),
                                 overlap_n=len(query&genes),full_jaccard=len(query&genes)/len(query|genes)))
    tracking=pd.DataFrame(tracking)
    tracking.to_csv(tables/'legacy_to_repaired_all_matches.tsv',sep='\t',index=False)
    pivot=tracking.pivot(index='legacy_label',columns='repaired_program',values='full_jaccard')
    rows,cols=linear_sum_assignment(-pivot.to_numpy())
    chosen=[]
    for i,j in zip(rows,cols):
        record=tracking.loc[tracking.legacy_label.eq(pivot.index[i])&tracking.repaired_program.eq(pivot.columns[j])].iloc[0].to_dict()
        record['purpose']='post_hoc_lineage_only; not a biological validation or selection by disease direction'
        chosen.append(record)
    lineage=pd.DataFrame(chosen)
    lineage=lineage.merge(best,left_on='repaired_program',right_on='gse_program',validate='one_to_one')
    lineage.to_csv(tables/'legacy_lineage_evidence_summary.tsv',sep='\t',index=False)

    # Freeze every selected-rank program, rather than selecting significant ones for bulk.
    genes=tops['GSE220243'].loc[tops['GSE220243'].gene_rank.le(30)].copy()
    genes.to_csv(tables/'locked_GSE_program_genes_for_bulk.tsv',sep='\t',index=False)
    write_json(out/'bulk_program_lock.json',dict(programs_sha256=sha256(tables/'locked_GSE_program_genes_for_bulk.tsv'),
                program_count=len(gse_sets),selection_rule='All modules from label-blind selected primary GSE rank',
                exploratory_lineage_labels=lineage[['legacy_label','repaired_program','full_jaccard']].to_dict('records')))

    # Legacy panels annotate programs only; they never enter feature selection or model fits.
    panels=json.loads((out/'inputs/annotation_panels.json').read_text(encoding='utf-8'))
    write_json(out/'annotation_panels.json',{name:sorted(value) for name,value in panels.items()})
    annotation=[]
    for dataset in tops:
        # Full NMF gene universe, not merely the union of selected top genes.
        background=input_genes[dataset]
        for program,query in module_sets(tops[dataset]).items():
            for name,panel in panels.items():
                panel_ids=set(next(iter(alias_to_ids[gene])) for gene in panel if len(alias_to_ids.get(gene,[]))==1)&background
                overlap=query&panel_ids
                annotation.append(dict(dataset=dataset,program_id=program,panel=name,overlap_n=len(overlap),
                                       overlap_symbols=','.join(sorted(symbols.get(g,g) for g in overlap)),
                                       hypergeom_p=float(hypergeom.sf(len(overlap)-1,len(background),len(query),len(panel_ids))) if overlap else 1.))
    annotation=pd.DataFrame(annotation)
    annotation['bh_fdr_all_annotations']=bh(annotation.hypergeom_p)
    annotation.to_csv(tables/'post_discovery_annotation.tsv',sep='\t',index=False)

    cross=[]
    for dataset in tops:
        all_top=pd.read_csv(tables/f'{dataset}_consensus_top_genes.tsv',sep='\t')
        primary=module_sets(tops[dataset])
        for (scheme,rank),frame in all_top.groupby(['scheme','rank']):
            comparison=module_sets(frame)
            for program,query in primary.items():
                candidates=[(len(query&genes)/len(query|genes),name,len(query&genes)) for name,genes in comparison.items()]
                similarity,matched,overlap=max(candidates,key=lambda x:(x[0],x[1]))
                cross.append(dict(dataset=dataset,primary_program=program,comparison_scheme=scheme,comparison_rank=rank,
                                  best_program=matched,full_top50_jaccard=similarity,overlap_n=overlap))
    pd.DataFrame(cross).to_csv(tables/'cross_rank_and_sampling_stability.tsv',sep='\t',index=False)

    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for ax,dataset in zip(axes,['GSE220243','HRA001986']):
        frame=tests[dataset].sort_values('delta')
        labels=frame.program_id.str.replace(dataset+'_primary300_','',regex=False)
        ax.barh(labels,frame.delta,color=np.where(frame.bh_fdr.lt(.05),'#376b99','#b9bfc5'))
        ax.axvline(0,color='black',linewidth=.8)
        ax.set_xlabel('Donor-mean score difference (case - control)')
        ax.set_title(f'{dataset}: {int(frame.n_case.iloc[0])} cases / {int(frame.n_control.iloc[0])} controls')
    fig.savefig(figures/'donor_program_effects.png',dpi=300)
    fig.savefig(figures/'donor_program_effects.pdf')
    plt.close(fig)
    table=pairs.pivot(index='gse_program',columns='hra_program',values='full_top50_jaccard')
    fig,ax=plt.subplots(figsize=(9,7),layout='constrained')
    im=ax.imshow(table.to_numpy(),vmin=0,vmax=1,cmap='Blues')
    ax.set_xticks(range(len(table.columns)),[x.replace('HRA001986_primary300_','') for x in table.columns],rotation=90)
    ax.set_yticks(range(len(table)),[x.replace('GSE220243_primary300_','') for x in table.index])
    ax.set_xlabel('Independent HRA001986 programs')
    ax.set_ylabel('Repaired GSE220243 programs')
    ax.set_title('Full top-50 gene-ID overlap; not disease validation')
    fig.colorbar(im,ax=ax,label='Jaccard index')
    fig.savefig(figures/'independent_module_overlap.png',dpi=300)
    plt.close(fig)
    print(lineage[['legacy_label','repaired_program','full_jaccard','hra_program','full_top50_jaccard',
                   'gse_donor_delta','gse_donor_fdr','hra_donor_delta','hra_donor_fdr']].to_string(index=False))


if __name__=='__main__':
    main()

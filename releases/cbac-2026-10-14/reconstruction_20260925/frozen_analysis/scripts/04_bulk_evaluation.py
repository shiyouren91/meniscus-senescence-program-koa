"""Source-audited, tissue-stratified contextual bulk evaluation of every locked GSE program."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from bulk_inputs import load_cohort
from bulk_statistics import normalize_counts,resolve_gene,compare_scores,pm_modified_hk
from rebuild_common import bh,sha256,write_json

COHORTS=['GSE114007','GSE143514','GSE55235','GSE55457','GSE169077','GSE185064','GSE98918','GSE191157','GSE89408']
PUBLICATION_FAMILY={'GSE55235':'PMID24690414','GSE55457':'PMID24690414'}


def adjusted_association(scores,metadata,accession):
    result=dict(adjustment_status='not_planned_or_metadata_unavailable')
    if accession not in ('GSE114007','GSE55457'):
        return result
    frame=metadata.copy()
    frame['age_numeric']=pd.to_numeric(frame.age,errors='coerce')
    frame['male']=frame.sex.astype(str).str.strip().str.lower().map({'male':1.,'m':1.,'female':0.,'f':0.})
    if frame[['age_numeric','male']].isna().any().any():
        return dict(adjustment_status='incomplete_covariates_no_imputation')
    design=pd.DataFrame({'intercept':1.,'case':frame.is_case.astype(float),
                         'age_per_10years':frame.age_numeric/10.,'male':frame.male},index=frame.index)
    if accession=='GSE114007':
        platforms=pd.get_dummies(frame.platform_id,prefix='platform',drop_first=True,dtype=float)
        design=pd.concat([design,platforms],axis=1)
    if len(frame)<=design.shape[1]+2 or np.linalg.matrix_rank(design.to_numpy())<design.shape[1]:
        return dict(adjustment_status='nonestimable_design')
    model=sm.OLS(np.asarray(scores,float),design.astype(float)).fit(cov_type='HC3',use_t=True)
    interval=model.conf_int().loc['case']
    age_case=frame.loc[frame.is_case,'age_numeric']; age_control=frame.loc[~frame.is_case,'age_numeric']
    overlap=max(age_case.min(),age_control.min())<=min(age_case.max(),age_control.max())
    return dict(adjustment_status='HC3_OLS_exploratory',adjusted_delta=float(model.params['case']),
                adjusted_ci_low=float(interval.iloc[0]),adjusted_ci_high=float(interval.iloc[1]),
                adjusted_p=float(model.pvalues['case']),adjustment_covariates=','.join(design.columns),
                age_range_overlap=bool(overlap),design_condition_number=float(np.linalg.cond(design.to_numpy())),
                n_covariate_complete=len(frame),residual_df=float(model.df_resid))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,required=True)
    root=parser.parse_args().project_root
    out=Path(__file__).resolve().parents[1]; tables=out/'tables'
    lock_path=tables/'locked_GSE_program_genes_for_bulk.tsv'
    assert sha256(lock_path)==json.loads((out/'bulk_program_lock.json').read_text(encoding='utf-8'))['programs_sha256']
    locked=pd.read_csv(lock_path,sep='\t')
    aliases={}; alias_table=pd.read_csv(tables/'gene_id_alias_map.tsv',sep='\t').fillna('')
    for row in alias_table.itertuples():
        for symbol in row.all_source_symbols.split('|'):
            aliases.setdefault(symbol.upper(),set()).add(row.gene_id)
    known_ids=set(alias_table.gene_id)
    effects=[]; coverage=[]; score_rows=[]; metadata_rows=[]; inputs=[]; mappings=[]; factors=[]; roles=[]; adjusted=[]
    for accession in COHORTS:
        raw,metadata,annotations,info=load_cohort(root,accession)
        assert raw.columns.equals(metadata.index) and raw.index.equals(annotations.index)
        assert raw.columns.is_unique and raw.index.is_unique
        metadata=metadata.loc[metadata.condition.isin([info['case'],info['control']])].copy()
        metadata['is_case']=metadata.condition.eq(info['case'])
        assert metadata.is_case.any() and (~metadata.is_case).any()
        raw=raw.loc[:,metadata.index].apply(pd.to_numeric,errors='raise')
        assert np.isfinite(raw.to_numpy()).all()
        metadata['accession']=accession; metadata['tissue']=info['tissue']; metadata['role']=info['role']
        metadata_rows.append(metadata.reset_index(names='expression_column'))
        for file in info['source_files']:
            path=Path(file)
            inputs.append(dict(accession=accession,path=str(path),bytes=path.stat().st_size,sha256=sha256(path)))
        roles.append(dict(accession=accession,tissue=info['tissue'],role=info['role'],scale=info['scale'],
                          contrast=info['case']+'_vs_'+info['control'],n_case=int(metadata.is_case.sum()),
                          n_control=int((~metadata.is_case).sum()),source_notes=json.dumps(info,ensure_ascii=False,default=str)))
        resolved=[resolve_gene(row,aliases,known_ids) for row in annotations.to_dict('records')]
        gene_ids=pd.Series([x[0] for x in resolved],index=raw.index,dtype=object)
        if info['scale']=='counts' and gene_ids.dropna().duplicated().any():
            duplicated=gene_ids.notna()&gene_ids.duplicated(keep=False)
            gene_ids.loc[duplicated].to_csv(tables/f'{accession}_duplicate_mapped_count_features_excluded.tsv',sep='\t')
            gene_ids.loc[duplicated]=None
            resolved=[(None,'duplicate_count_gene_mapping_excluded') if duplicated.iloc[i] else value
                      for i,value in enumerate(resolved)]
        for identifier,(gene_id,status) in zip(raw.index,resolved):
            mappings.append(dict(accession=accession,source_feature=identifier,gene_id=gene_id,mapping_status=status))
        modes=['median_ratio','cpm'] if info['scale']=='counts' else ['deposited']
        if info.get('scale_requires_review'):
            modes.append('log2_deposited_values')
        for mode in modes:
            if mode=='log2_deposited_values':
                values=np.log2(raw.to_numpy(dtype=float)+1)
            elif info['scale']=='counts':
                values,sf,totals=normalize_counts(raw.to_numpy(),mode)
                for column,factor,total in zip(raw.columns,sf,totals):
                    factors.append(dict(accession=accession,normalization=mode,expression_column=column,
                                        size_factor=factor,full_feature_library_total=total))
            elif info['scale']=='linear_intensity':
                assert (raw.to_numpy()>=0).all()
                values=np.log2(raw.to_numpy()+1)
            elif info['scale']=='log_expression':
                values=raw.to_numpy(dtype=float)
            else:
                raise ValueError(info['scale'])
            matrix=pd.DataFrame(values,index=raw.index,columns=raw.columns).rename_axis('source_feature')
            matrix['gene_id']=gene_ids
            # Averaging probe/feature log values never treats one ambiguous probe as a gene.
            expression=matrix.dropna(subset=['gene_id']).groupby('gene_id',sort=True).mean()
            std=expression.std(axis=1,ddof=0)
            expression=expression.loc[std>1e-8]
            z=expression.sub(expression.mean(axis=1),axis=0).div(std.loc[expression.index],axis=0)
            for program,genes in locked.groupby('program_id',sort=True):
                present=genes.loc[genes.gene_id.isin(z.index)]
                cov=dict(accession=accession,program_id=program,normalization=mode,tissue=info['tissue'],role=info['role'],
                         n_expected=len(genes),n_scored=len(present),fraction_scored=len(present)/len(genes),
                         eligible=len(present)>=21,missing_symbols=','.join(genes.loc[~genes.gene_id.isin(z.index),'gene_symbol']))
                coverage.append(cov)
                if not cov['eligible']:
                    continue
                scores=z.loc[present.gene_id].mean(axis=0)
                pooled=info['role'] in ('pooled_context','cultured_pooled_context')
                result=compare_scores(scores.to_numpy(),metadata.is_case.to_numpy(),inferential=not pooled)
                result.update(cov); result['contrast']=info['case']+'_vs_'+info['control']
                result['scale_requires_review']=bool(info.get('scale_requires_review',False))
                result['normalization_primary']=mode in ('median_ratio','deposited')
                effects.append(result)
                for column,score in scores.items():
                    score_rows.append(dict(accession=accession,program_id=program,normalization=mode,
                                           expression_column=column,sample_id=metadata.loc[column,'sample_id'],
                                           condition=metadata.loc[column,'condition'],score=score,n_scored=len(present)))
                if mode in ('median_ratio','deposited') and accession in ('GSE114007','GSE55457'):
                    adjusted.append(dict(accession=accession,program_id=program,**adjusted_association(scores,metadata,accession)))
        print('BULK_READY',accession,info['tissue'],info['role'],len(metadata),flush=True)
    effects=pd.DataFrame(effects)
    effects['bh_fdr_within_cohort_method']=effects.groupby(['accession','normalization']).welch_p.transform(lambda x:bh(x.to_numpy()))
    main=effects.role.eq('primary')&effects.normalization_primary
    effects['bh_fdr_all_primary_tests']=np.nan
    effects.loc[main,'bh_fdr_all_primary_tests']=bh(effects.loc[main,'welch_p'])
    effects.to_csv(tables/'bulk_program_effects.tsv',sep='\t',index=False)
    for name,rows in [('bulk_gene_coverage',coverage),('bulk_sample_scores',score_rows),('bulk_source_provenance',inputs),
                      ('bulk_feature_mapping',mappings),('bulk_normalization_factors',factors),('bulk_cohort_roles',roles)]:
        pd.DataFrame(rows).to_csv(tables/f'{name}.tsv',sep='\t',index=False)
    pd.concat(metadata_rows,ignore_index=True).to_csv(tables/'bulk_sample_metadata.tsv',sep='\t',index=False)
    adj=pd.DataFrame(adjusted)
    if 'adjusted_p' in adj:
        adj['bh_fdr_all_adjusted_tests']=bh(adj.adjusted_p)
    adj.to_csv(tables/'bulk_covariate_sensitivity.tsv',sep='\t',index=False)
    meta=[]; meta_status=[]
    meta_inputs=[]
    for scope,mask in [('strict_primary',main),('includes_uncertain_units',
                       effects.role.isin(['primary','uncertain_units_context'])&effects.normalization_primary)]:
        for key,frame in effects.loc[mask].groupby(['tissue','program_id']):
            meta_inputs.append((scope,key,frame))
    for scope,(tissue,program),frame in meta_inputs:
        for omit in ['', 'GSE55235','GSE55457','GSE143514']:
            sub=frame.loc[frame.accession.ne(omit)]
            finite=np.isfinite(sub.hedges_g)&np.isfinite(sub.variance_g)&sub.variance_g.gt(0)
            removed=','.join(sub.loc[~finite,'accession'])
            sub=sub.loc[finite]
            meta_status.append(dict(tissue=tissue,program_id=program,omitted_center=omit or 'none',
                                    analysis_scope=scope,
                                    n_eligible_cohorts=len(sub),nonestimable_cohorts=removed,
                                    status='computed' if len(sub)>=2 else 'fewer_than_two_estimable_cohorts'))
            if len(sub)<2:
                continue
            result=pm_modified_hk(sub.hedges_g,sub.variance_g)
            result.update(tissue=tissue,program_id=program,omitted_center=omit or 'none',
                          analysis_scope=scope,
                          cohorts=','.join(sub.accession),
                          n_publication_families=len({PUBLICATION_FAMILY.get(x,x) for x in sub.accession}))
            meta.append(result)
    meta=pd.DataFrame(meta)
    if not meta.empty:
        meta['bh_fdr_within_meta_family']=meta.groupby(['analysis_scope','tissue','omitted_center']).p_value.transform(lambda x:bh(x.to_numpy()))
    meta.to_csv(tables/'bulk_tissue_meta_analysis.tsv',sep='\t',index=False)
    pd.DataFrame(meta_status).to_csv(tables/'bulk_meta_eligibility.tsv',sep='\t',index=False)
    # Show every primary program. Display symbols are annotations, not renamed biological claims.
    labels={program:program.split('_')[-1]+' '+','.join(frame.sort_values('gene_rank').head(3).gene_symbol)
            for program,frame in locked.groupby('program_id')}
    plot=effects.loc[main].pivot(index='program_id',columns='accession',values='hedges_g')
    plot=plot.reindex(locked.sort_values('component').program_id.drop_duplicates())
    fig,ax=plt.subplots(figsize=(9,7),layout='constrained')
    extent=max(float(np.nanmax(np.abs(plot.to_numpy()))),.1)
    cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#eeeeee')
    image=ax.imshow(np.ma.masked_invalid(plot.to_numpy()),cmap=cmap,vmin=-extent,vmax=extent,aspect='auto')
    ax.set_yticks(range(len(plot)),[labels[x] for x in plot.index])
    ax.set_xticks(range(len(plot.columns)),plot.columns,rotation=30,ha='right')
    for i in range(len(plot)):
        for j in range(len(plot.columns)):
            value=plot.iloc[i,j]
            ax.text(j,i,f'{value:.2f}' if np.isfinite(value) else 'coverage <70%',ha='center',va='center',fontsize=9,
                    color='white' if abs(value)>extent*.55 else 'black')
    ax.set_title('Native-tissue OA vs normal: all locked programs\nHedges g; cohorts analyzed separately')
    fig.colorbar(image,ax=ax,label='OA - normal (Hedges g)')
    fig.savefig(out/'figures/bulk_all_program_effects.png',dpi=300); fig.savefig(out/'figures/bulk_all_program_effects.pdf')
    plt.close(fig)
    if not meta.empty:
        plot=meta.loc[meta.omitted_center.eq('none')&meta.analysis_scope.eq('strict_primary')].sort_values('pooled_g')
        fig,ax=plt.subplots(figsize=(10,7),layout='constrained')
        y=np.arange(len(plot))
        ax.errorbar(plot.pooled_g,y,xerr=np.vstack([plot.pooled_g-plot.ci_low,plot.ci_high-plot.pooled_g]),fmt='o',color='#356989',capsize=3)
        ax.set_yticks(y,[labels[row.program_id]+f' (k={row.n_cohorts}, families={row.n_publication_families})'
                        for row in plot.itertuples()]); ax.axvline(0,color='gray',linewidth=.8)
        ax.set_xlabel('Hedges g with modified Hartung-Knapp 95% CI')
        ax.set_title('Synovium: modified Hartung-Knapp estimates\nk = cohorts; families = source publications')
        fig.savefig(out/'figures/synovium_meta_all_programs.png',dpi=300);fig.savefig(out/'figures/synovium_meta_all_programs.pdf')
        plt.close(fig)
    write_json(out/'bulk_evaluation_summary.json',dict(locked_genes_sha256=sha256(lock_path),cohorts=len(COHORTS),
               primary_native_tissue_cohorts=3,extended_cohorts_including_uncertain_units=4,n_primary_eligible_tests=int(main.sum()),
               n_primary_tests_global_fdr_below_005=int(effects.loc[main,'bh_fdr_all_primary_tests'].lt(.05).sum()),
               normalization='Within-comparison full-feature count factors or deposited log-expression; cohort-internal gene-wise z scores',
               limitations=['Previously explored cohorts; not untouched external validation','Only one primary cartilage cohort',
                            'The two strict-primary synovial cohorts share one publication family; donor re-identification cannot be excluded',
                            'GSE143514 unit ambiguity: count-based evaluation conditional; excluded from strict primary',
                            'No native meniscus OA-versus-normal individual-tissue cohort in primary bulk set',
                            'Unknown-member pools excluded from primary inference','No pooled cross-tissue diagnostic AUC']))
    if not meta.empty:
        print(meta.loc[meta.omitted_center.eq('none')].to_string(index=False),flush=True)


if __name__=='__main__':
    main()

"""Small, testable helpers for exploratory bulk program evaluation."""
from __future__ import annotations
import re
import numpy as np
from scipy.optimize import brentq
from scipy import stats


def normalize_counts(values, method='median_ratio'):
    values=np.asarray(values,dtype=float)
    if not np.isfinite(values).all() or (values<0).any():
        raise ValueError('Counts must be finite and nonnegative')
    totals=values.sum(axis=0)
    if (totals<=0).any():
        raise ValueError('Empty count library')
    if method=='median_ratio':
        positive=(values>0).all(axis=1)
        if positive.sum()<10:
            raise ValueError('Fewer than ten all-positive genes for median-of-ratios normalization')
        log_values=np.log(values[positive])
        ratios=np.exp(log_values-log_values.mean(axis=1,keepdims=True))
        factors=np.median(ratios,axis=0)
        factors/=np.exp(np.log(factors).mean())
    elif method=='cpm':
        factors=totals/1e6
    else:
        raise ValueError(method)
    return np.log2(values/factors+1),factors,totals


def annotation_tokens(text):
    if text is None or str(text).lower() in ('nan','none',''):
        return []
    return [x.strip().upper() for x in re.split(r'\s*///\s*|\s*//\s*|[;,|]',str(text))
            if x.strip().upper() not in ('','---','NA','NAN','NULL','NONE')]


def resolve_gene(annotation, aliases, known_ids):
    ids=annotation_tokens(annotation.get('gene_id',''))
    resolved_ids=set()
    for token in ids:
        token=re.sub(r'\.\d+$','',token)
        if token in known_ids:
            resolved_ids.add(token)
        else:
            return None,'unresolved_explicit_id'
    symbols=annotation_tokens(annotation.get('gene_symbol',''))
    if len(symbols)>1:
        if any(len(aliases.get(symbol,set()))!=1 for symbol in symbols):
            return None,'ambiguous_multigene_symbol'
        resolved_ids.update(next(iter(aliases[symbol])) for symbol in symbols)
    elif not resolved_ids and symbols:
        resolved_ids.update(aliases.get(symbols[0],set()))
    if len(resolved_ids)==1:
        return next(iter(resolved_ids)),'unique'
    return None,'ambiguous' if len(resolved_ids)>1 else 'unmapped'


def compare_scores(values, cases, inferential=True):
    values=np.asarray(values,float); cases=np.asarray(cases,bool)
    case,control=values[cases],values[~cases]
    result=dict(n_case=len(case),n_control=len(control),mean_case=float(case.mean()),
                mean_control=float(control.mean()),delta=float(case.mean()-control.mean()),
                inference_allowed=inferential)
    for key in ('hedges_g','variance_g','g_ci_low','g_ci_high','welch_p','delta_ci_low','delta_ci_high'):
        result[key]=np.nan
    if min(len(case),len(control))<2 or not np.isfinite(values).all():
        result['test_status']='insufficient_finite_independent_units'
        return result
    n1,n0=len(case),len(control); df=n1+n0-2
    s1,s0=case.var(ddof=1),control.var(ddof=1)
    pooled=((n1-1)*s1+(n0-1)*s0)/df
    if pooled<=1e-16:
        result['test_status']='zero_within_group_variance'
        return result
    correction=1-3/(4*df-1)
    g=correction*result['delta']/np.sqrt(pooled)
    result['hedges_g']=g
    if not inferential:
        result['test_status']='descriptive_only_unknown_pool_membership'
        return result
    variance=correction**2*(n1+n0)/(n1*n0)+g*g/(2*df)
    se=np.sqrt(s1/n1+s0/n0)
    welch_df=(s1/n1+s0/n0)**2/((s1/n1)**2/(n1-1)+(s0/n0)**2/(n0-1))
    critical=stats.t.ppf(.975,welch_df)
    result.update(variance_g=variance,g_ci_low=g-1.959963984540054*np.sqrt(variance),
                  g_ci_high=g+1.959963984540054*np.sqrt(variance),
                  welch_p=float(stats.ttest_ind(case,control,equal_var=False).pvalue),
                  delta_ci_low=result['delta']-critical*se,delta_ci_high=result['delta']+critical*se,
                  test_status='welch_exploratory')
    return result


def pm_modified_hk(effects,variances):
    y,v=np.asarray(effects,float),np.asarray(variances,float)
    if len(y)<2 or len(y)!=len(v) or not np.isfinite(y).all() or not np.isfinite(v).all() or (v<=0).any():
        raise ValueError('At least two finite independent effects and positive variances required')
    k=len(y); df=k-1
    def residual_q(tau):
        w=1/(v+tau); mean=np.sum(w*y)/w.sum()
        return float(np.sum(w*(y-mean)**2))
    q0=residual_q(0)
    tau=0.
    if q0>df:
        high=max(float(np.var(y)),float(np.max(v)),1.)
        while residual_q(high)>df:
            high*=2
        tau=float(brentq(lambda x:residual_q(x)-df,0,high))
    w=1/(v+tau); mean=float(np.sum(w*y)/w.sum())
    h=max(1.,residual_q(tau)/df)
    se=np.sqrt(h/w.sum()); critical=stats.t.ppf(.975,df)
    return dict(n_cohorts=k,pooled_g=mean,se_modified_hk=float(se),ci_low=mean-critical*se,
                ci_high=mean+critical*se,p_value=float(2*stats.t.sf(abs(mean/se),df)),
                tau_squared=tau,q_fixed=q0,i_squared_percent=max(0.,(q0-df)/q0)*100 if q0>0 else 0.,
                hk_scale=h,df=df,method='Paule-Mandel tau2; modified Hartung-Knapp; t interval')

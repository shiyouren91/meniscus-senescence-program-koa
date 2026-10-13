"""Freeze legacy selection/annotation inputs locally, with provenance; no public upload."""
from pathlib import Path
import argparse
import ast
import shutil
import anndata as ad
import pandas as pd
from rebuild_common import sha256,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,required=True)
    root=parser.parse_args().project_root
    out=Path(__file__).resolve().parents[1]; inputs=out/'inputs'; inputs.mkdir(exist_ok=True)
    provenance=[]
    source=root/'data/processed/single_cell/GSE220243/cnmf/gse220243_fibrochondrocyte_cnmf_balanced_discovery_counts.h5ad'
    obj=ad.read_h5ad(source,backed='r')
    target=inputs/'legacy_selected_GSE_cell_metadata.tsv.gz'
    obj.obs.to_csv(target,sep='\t')
    schema={column:str(dtype) if pd.api.types.is_numeric_dtype(dtype) else 'str'
            for column,dtype in obj.obs.dtypes.items()}
    write_json(inputs/'legacy_selected_GSE_metadata_schema.json',schema)
    obj.file.close()
    provenance.append(dict(source=str(source),source_sha256=sha256(source),target=target.name,target_sha256=sha256(target),
                           purpose='Freeze only prior compartment/cell selection; the inherited normalized counts are not used'))
    for relative,name in [
        ('results/tables/reviewer_reanalysis/gse220243_hvg_only_consensus_top_genes.tsv','legacy_GSE_top_genes.tsv'),
        ('metadata/datasets/gse220243_single_cell_manifest.tsv','gse220243_single_cell_manifest.tsv'),
        ('docs/literature/elife_79585/elife-79585-supp1-donor_sample_information.xlsx','HRA_public_donor_metadata.xlsx')]:
        source=root/relative;target=inputs/name
        shutil.copy2(source,target)
        provenance.append(dict(source=str(source),source_sha256=sha256(source),target=target.name,target_sha256=sha256(target)))
    source=root/'scripts/analysis/70_gse220243_hvg_only_program_discovery.py'
    tree=ast.parse(source.read_text(encoding='utf-8'))
    node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SIGNATURES' for t in n.targets))
    panels=ast.literal_eval(node.value)
    target=inputs/'annotation_panels.json';write_json(target,{k:sorted(v) for k,v in panels.items()})
    provenance.append(dict(source=str(source),source_sha256=sha256(source),target=target.name,target_sha256=sha256(target),
                           purpose='Legacy panels for descriptive annotation only, not discovery inputs'))
    write_json(inputs/'support_input_provenance.json',provenance)
    print('FROZEN',len(provenance),'supporting inputs',flush=True)


if __name__=='__main__':
    main()

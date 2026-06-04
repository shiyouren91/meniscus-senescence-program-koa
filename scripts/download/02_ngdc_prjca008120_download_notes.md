# PRJCA008120 Download Notes

Primary URL: https://ngdc.cncb.ac.cn/bioproject/browse/PRJCA008120

## Why This Is Separate

PRJCA008120 is hosted by NGDC/CNCB rather than GEO. Download behavior can differ by mirror, login/session state, and whether the processed matrix or raw FASTQ files are selected. For this project, prefer processed matrices first. Raw FASTQ files should go to the G drive extension directory.

## Target Locations

- Processed matrices, metadata, and small files:
  `F:\半月板特异性衰老程序连接纤维软骨细胞命运障碍与膝骨关节炎滑膜-软骨炎症重塑\data\raw\single_cell\PRJCA008120`

- Large raw files:
  `G:\半月板特异性衰老程序连接纤维软骨细胞命运障碍与膝骨关节炎滑膜-软骨炎症重塑扩展资料\raw_large\single_cell\PRJCA008120`

## Download Priority

1. Sample metadata.
2. Processed gene-by-cell matrix or h5/h5ad/rds objects if provided.
3. Cell annotation files if provided.
4. Raw FASTQ files only if processed matrices are unavailable or quality reprocessing is required.

## Tracking

After download, record each file in:

`metadata\datasets\download_inventory.tsv`

Recommended columns:

`dataset_id	file_name	source_url	local_path	size_bytes	md5_or_sha256	date_downloaded	notes`


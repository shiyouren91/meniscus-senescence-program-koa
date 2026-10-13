"""Read local GEO bulk inputs without normalization, scoring, or row collapsing.

load_cohort(project_root, accession) returns (raw, metadata, annotations, info).
The rebuild directory may also be supplied as root. Expression labels are kept
verbatim; metadata.index equals raw.columns, annotations.index equals raw.index.
Only verified one-to-one matches receive GSM sample_id values. Display strings
join repeated metadata fields, while metadata.soft_fields retains every original
SOFT sample field as a list, including repeats. Missing annotation is ''.
Microarray gene_symbol/gene_id cells retain complete multi-gene annotations.
gene_id denotes Ensembl annotation where supplied, not an inferred Entrez ID.
Repeated feature labels get unique opaque row keys; source_feature_id preserves
the original label. No repeated expression row is dropped, summed, or averaged.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import pandas as pd


COHORTS = {
    'GSE114007': ('counts', 'cartilage', 'primary', 'OA', 'normal'),
    'GSE143514': ('counts', 'synovium', 'uncertain_units_context', 'OA', 'normal'),
    'GSE185064': ('counts', 'meniscus', 'cultured_pooled_context', 'OA', 'normal'),
    'GSE169077': ('linear_intensity', 'cartilage', 'pooled_context', 'OA', 'normal'),
    'GSE55235': ('linear_intensity', 'synovium', 'primary', 'OA', 'normal'),
    'GSE55457': ('linear_intensity', 'synovium', 'primary', 'OA', 'normal'),
    'GSE98918': ('log_expression', 'meniscus', 'non_normal_context', 'OA', 'APM'),
    'GSE191157': ('log_expression', 'meniscus', 'non_normal_context', 'aged', 'young'),
    'GSE89408': ('counts', 'synovium', 'ra_rich_sensitivity', 'OA', 'normal'),
}
_ARRAYS = {'GSE169077', 'GSE55235', 'GSE55457', 'GSE98918', 'GSE191157'}
_META_COLUMNS = [
    'sample_id', 'title', 'condition', 'age', 'sex', 'platform_id',
    'source_name', 'raw_characteristics', 'description',
    'identity_status', 'identity_basis', 'soft_fields',
]


def _open_text(path):
    opener = gzip.open if Path(path).suffix == '.gz' else open
    return opener(path, 'rt', encoding='utf-8-sig', newline='')


def _project_root(root):
    root = Path(root).resolve()
    for candidate in (root, *root.parents):
        if (candidate / 'data' / 'raw').is_dir():
            return candidate
    raise FileNotFoundError(f'No project data/raw directory at or above {root}')


def _find_file(root, accession, filename):
    for directory in (root / 'data' / 'raw', root / 'raw_large'):
        path = directory / accession / filename
        if path.is_file():
            return path.resolve(), []
    inventory = root / 'metadata' / 'datasets' / 'download_inventory.tsv'
    if inventory.is_file():
        with inventory.open(encoding='utf-8-sig', newline='') as stream:
            # This archive's header uses literal PowerShell `t, unlike its rows.
            header = next(stream).rstrip('\r\n').replace('`t', '\t')
            fields = next(csv.reader([header], delimiter='\t'))
            matches = []
            for row in csv.DictReader(stream, fieldnames=fields, delimiter='\t'):
                if row.get('dataset_id') == accession and row.get('file_name') == filename:
                    path = Path(row['local_path'])
                    if not path.is_absolute():
                        path = root / path
                    if path.is_file():
                        matches.append(path.resolve())
            matches = list(dict.fromkeys(matches))
            if len(matches) == 1:
                return matches[0], [inventory.resolve()]
            if len(matches) > 1:
                raise ValueError(f'Ambiguous inventory paths for {filename}: {matches}')
    raise FileNotFoundError(f'Cannot locate archived {accession}/{filename}')


def read_soft(path):
    """Return series fields, GSM sample fields, and GPL tables; keep repeated fields."""
    series, samples, platforms = {}, {}, {}
    entity = None
    table_lines = None
    skipping_sample_table = False
    with _open_text(path) as stream:
        for line in stream:
            stripped = line.rstrip('\r\n')
            if stripped == '!sample_table_begin':
                skipping_sample_table = True
                continue
            if stripped == '!sample_table_end':
                skipping_sample_table = False
                continue
            if skipping_sample_table:
                continue
            if stripped == '!platform_table_begin':
                if entity is None or entity[0] != 'PLATFORM':
                    raise ValueError('Platform table outside a PLATFORM entity')
                table_lines = []
                continue
            if stripped == '!platform_table_end':
                table = pd.read_csv(io.StringIO(''.join(table_lines)), sep='\t',
                                    dtype=str, keep_default_na=False)
                if 'ID' not in table or table['ID'].duplicated().any():
                    raise ValueError(f'Missing/nonunique platform probe IDs: {entity}')
                platforms[entity[1]] = table.set_index('ID')
                table_lines = None
                continue
            if table_lines is not None:
                table_lines.append(line)
                continue
            if stripped.startswith('^'):
                kind, separator, identifier = stripped[1:].partition(' = ')
                if not separator:
                    raise ValueError(f'Malformed SOFT entity: {stripped}')
                entity = (kind, identifier)
                if kind == 'SAMPLE':
                    if identifier in samples:
                        raise ValueError(f'Duplicate SOFT sample: {identifier}')
                    samples[identifier] = {}
                continue
            key, separator, value = stripped.partition(' = ')
            if not separator:
                continue
            if key.startswith('!Series_'):
                series.setdefault(key, []).append(value)
            elif entity and entity[0] == 'SAMPLE' and key.startswith('!Sample_'):
                samples[entity[1]].setdefault(key, []).append(value)
    if table_lines is not None or skipping_sample_table:
        raise ValueError(f'Unterminated SOFT table in {path}')
    if not samples:
        raise ValueError(f'No SOFT samples in {path}')
    return series, samples, platforms


def _values(sample, field):
    return sample.get('!Sample_' + field, [])


def _one(sample, field):
    values = list(dict.fromkeys(_values(sample, field)))
    if len(values) > 1:
        raise ValueError(f'Conflicting single-valued SOFT field {field}: {values}')
    return values[0] if values else ''


def _characteristics(sample):
    result = {}
    for text in _values(sample, 'characteristics_ch1'):
        key, separator, value = text.partition(':')
        if separator:
            result.setdefault(key.strip().lower(), []).append(value.strip())
    return result


def _characteristic(chars, *keys):
    values = list(dict.fromkeys(v for key in keys for v in chars.get(key, [])))
    if len(values) > 1:
        raise ValueError(f'Conflicting characteristics {keys}: {values}')
    return values[0] if values else ''


def _condition(accession, sample):
    chars = _characteristics(sample)
    title = _one(sample, 'title').lower()
    if accession == 'GSE114007':
        if title.startswith('normal_'):
            return 'normal'
        if title.startswith('oa_'):
            return 'OA'
    if accession == 'GSE98918':
        if 'arthroscopic partial meniscectomy' in title:
            return 'APM'
        if 'osteoarthritis' in title:
            return 'OA'
    if accession == 'GSE191157':
        age = _characteristic(chars, 'age').lower()
        if age in {'aged', 'young'}:
            return age
    state = _characteristic(chars, 'disease state', 'clinical status',
                            'subject status', 'disease').lower()
    if state.startswith('rheumatoid arthritis'):
        return 'RA'
    if state == 'arthralgia':
        return 'AG'
    if state == 'undifferentiated arthritis':
        return 'undiff'
    if state in {'oa', 'osteoarthritis', 'late stage oa cartilage'} or 'osteoarthritic' in state:
        return 'OA'
    if state in {'normal', 'normal cartilage', 'normal control', 'healthy control',
                 'healthy', 'control'}:
        return 'normal'
    raise ValueError(f'Unrecognized condition in {accession}: title={title!r}, state={state!r}')


def _column_condition_89408(column, strict=True):
    match = re.fullmatch(r'(normal|OA|RA|AG|undiff)_tissue_([1-9][0-9]*)', column)
    if not match:
        if not strict:
            return None
        raise ValueError(f'No explicit public condition in GSE89408 column {column!r}')
    return match.group(1)


def _match_samples(columns, samples, key_by_column, fields, allow_unresolved=False):
    lookup = {}
    for gsm, sample in samples.items():
        keys = [gsm] if 'gsm' in fields else []
        for field in fields:
            if field != 'gsm':
                keys.extend(_values(sample, field))
        for key in keys:
            lookup.setdefault(key, set()).add(gsm)
    matches, used = {}, set()
    for column in columns:
        key = key_by_column(column)
        candidates = lookup.get(key, set())
        if len(candidates) > 1:
            raise ValueError(f'Ambiguous identity for {column}: {sorted(candidates)}')
        if not candidates:
            if not allow_unresolved:
                raise ValueError(f'No exact SOFT match for {column!r} via {key!r}')
            matches[column] = None
            continue
        gsm = next(iter(candidates))
        if gsm in used:
            raise ValueError(f'Multiple expression columns map to one GSM: {gsm}')
        matches[column] = gsm
        used.add(gsm)
    if not allow_unresolved and used != set(samples):
        raise ValueError(f'SOFT samples absent from expression: {sorted(set(samples) - used)}')
    return matches


def _metadata(columns, samples, matches, accession, basis):
    rows = []
    for column in columns:
        gsm = matches[column]
        sample = samples[gsm] if gsm is not None else {}
        chars = _characteristics(sample)
        sex = _characteristic(chars, 'sex', 'gender')
        sex = {'male': 'M', 'female': 'F', 'm': 'M', 'f': 'F'}.get(sex.lower(), sex)
        condition = (_condition(accession, sample) if gsm is not None
                     else _column_condition_89408(column))
        if accession == 'GSE89408':
            named_condition = _column_condition_89408(column, strict=False)
            if named_condition is not None and condition != named_condition:
                raise ValueError(f'Column/SOFT condition conflict for {column}')
        rows.append({
            'sample_id': gsm if gsm is not None else column,
            'title': _one(sample, 'title') if gsm is not None else column,
            'condition': condition,
            'age': pd.to_numeric(_characteristic(chars, 'age', 'age (years)'), errors='coerce'),
            'sex': sex,
            'platform_id': _one(sample, 'platform_id'),
            'source_name': _one(sample, 'source_name_ch1'),
            'raw_characteristics': '; '.join(_values(sample, 'characteristics_ch1')),
            'description': ' | '.join(_values(sample, 'description')),
            'identity_status': 'verified_gsm' if gsm is not None else 'unresolved',
            'identity_basis': basis if gsm is not None else 'public_column_condition_only',
            'soft_fields': {key: list(values) for key, values in sample.items()},
        })
    return pd.DataFrame(rows, index=columns.copy(), columns=_META_COLUMNS)


def _read_tsv(path):
    with _open_text(path) as stream:
        header = next(csv.reader([next(stream)], delimiter='\t'))
    if len(set(header)) != len(header):
        raise ValueError(f'Duplicate expression column labels in {path}')
    return pd.read_csv(path, sep='\t', dtype={header[0]: str}, keep_default_na=False)


def _series_matrix(path):
    lines, in_table, ended = [], False, False
    with _open_text(path) as stream:
        for line in stream:
            if line.startswith('!series_matrix_table_begin'):
                in_table = True
            elif line.startswith('!series_matrix_table_end'):
                ended = True
                break
            elif in_table:
                lines.append(line)
    if not lines or not ended:
        raise ValueError(f'Missing/incomplete expression table in {path}')
    header = next(csv.reader([lines[0]], delimiter='\t'))
    if header[0] != 'ID_REF' or len(set(header)) != len(header):
        raise ValueError(f'Invalid series-matrix columns in {path}')
    return pd.read_csv(io.StringIO(''.join(lines)), sep='\t', dtype={'ID_REF': str},
                       keep_default_na=False).set_index('ID_REF')


def _symbol_annotations(index):
    annotations = pd.DataFrame({'gene_id': '', 'gene_symbol': index.astype(str)}, index=index.copy())
    is_id = index.astype(str).str.fullmatch(r'ENSG[0-9]+(?:\.[0-9]+)?')
    annotations.loc[is_id, 'gene_id'] = index[is_id].astype(str)
    annotations.loc[is_id, 'gene_symbol'] = ''
    return annotations


def _annotations_89408(index):
    annotations = _symbol_annotations(index)
    annotations['original_annotation'] = index.astype(str)
    decoded = 0
    unresolved = []
    for label in index:
        match = re.fullmatch(r'([^:\s]+):(ENSG[0-9]{11}(?:\.[0-9]+)?)', label)
        if match:
            annotations.loc[label, 'gene_symbol'] = match.group(1)
            annotations.loc[label, 'gene_id'] = match.group(2)
            decoded += 1
        elif ':' in label:
            # Other colon forms may be accessions or genuine labels, not gene symbols.
            annotations.loc[label, ['gene_symbol', 'gene_id']] = ''
            unresolved.append(label)
    return annotations, decoded, unresolved


def _platform_annotations(index, platform):
    mapped = platform.reindex(index).fillna('')
    annotations = mapped.add_prefix('platform_')
    for output, candidates in {
        'gene_id': ('ENSEMBL_ID', 'Ensembl Gene ID', 'ENSEMBL', 'gene_id'),
        'gene_symbol': ('GENE_SYMBOL', 'Gene Symbol', 'gene_symbol', 'Symbol', 'ORF'),
    }.items():
        source = next((name for name in candidates if name in mapped), None)
        annotations[output] = mapped[source].to_numpy() if source else ''
    # Several GEO platforms name an ENST transcript column ENSEMBL_ID.
    # Preserve that annotation but do not confuse transcript IDs with gene IDs.
    original_ensembl=annotations['gene_id'].astype(str)
    annotations['original_ensembl_annotation']=original_ensembl
    annotations['transcript_id']=original_ensembl.map(lambda x:' /// '.join(dict.fromkeys(re.findall(r'ENST\d+(?:\.\d+)?',x))))
    annotations['gene_id']=original_ensembl.map(lambda x:' /// '.join(dict.fromkeys(re.findall(r'ENSG\d+(?:\.\d+)?',x))))
    annotations.index = index.copy()
    return annotations


def _mrna_description(column):
    match = re.fullmatch(r'(Normal|Osteoarthritis)_([0-9]+[AB])_count', column)
    if not match:
        raise ValueError(f'Unexpected GSE143514 mRNA column: {column}')
    prefix = {'Normal': 'Nor', 'Osteoarthritis': 'OA'}[match.group(1)]
    return prefix + '-' + match.group(2)


def _unique_feature_keys(raw, annotations):
    original = raw.index.astype(str)
    labels = original.tolist()
    occupied = set(labels)
    annotations = annotations.copy()
    annotations.insert(0, 'source_feature_id', original.to_numpy(copy=True))
    duplicated = original.duplicated(keep=False)
    for position in np.flatnonzero(duplicated):
        key = f'{labels[position]}::row={position + 1}'
        while key in occupied:
            key += ':'
        occupied.add(key)
        labels[position] = key
    raw = raw.copy(deep=False)
    raw.index = pd.Index(labels, name=raw.index.name)
    annotations.index = raw.index.copy()
    return raw, annotations, int(duplicated.sum()), int(original.duplicated().sum())


def _raw_114007(path):
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    frames = []
    try:
        for name in ('Normal', 'OA'):
            rows = workbook[name].iter_rows(values_only=True)
            header = next(rows)
            if header[0] != 'symbol' or len(set(header)) != len(header):
                raise ValueError(f'Invalid raw-count workbook header: {name}')
            frame = pd.DataFrame(rows, columns=header).set_index('symbol')
            if frame.index.isna().any() or frame.index.duplicated().any():
                raise ValueError(f'Missing/duplicate workbook symbols: {name}')
            frames.append(frame)
    finally:
        workbook.close()
    if set(frames[0].index) != set(frames[1].index):
        raise ValueError('GSE114007 sheets have different gene universes; no zero filling allowed')
    return pd.concat([frames[0], frames[1].reindex(frames[0].index)], axis=1)


def load_cohort(root, accession):
    """Load one of nine local cohorts; no downloads, writes, or transformations.

    info.scale is explicit, not selected by a percentile heuristic. GSE143514
    retains the deposited raw-count declaration, with conflicting FPKM text
    flagged in scale_status/warnings for downstream gating. GSE89408 never
    expands abbreviations or matches by position to guess GSM identities.
    """
    if accession not in COHORTS:
        raise ValueError(f'Unsupported cohort {accession!r}; choose from {tuple(COHORTS)}')
    root = _project_root(root)
    source_files = []

    def source(filename):
        path, provenance = _find_file(root, accession, filename)
        source_files.extend([path, *provenance])
        return path

    series, all_samples, platforms = read_soft(source(accession + '_family.soft.gz'))
    samples = all_samples
    scale, tissue, role, case, control = COHORTS[accession]
    warnings, extra = [], {}
    identity_key, fields = lambda column: column, ('title',)
    basis = 'exact_sample_title'
    if accession == 'GSE114007':
        workbook_path = source(accession + '_raw_counts.xlsx')
        declared_files = series.get('!Series_supplementary_file', [])
        declared = any(Path(urlsplit(url).path).name == workbook_path.name for url in declared_files)
        if not declared:
            raise ValueError('GSE114007 raw-count workbook is not declared by the local SOFT')
        raw = _raw_114007(workbook_path)
        annotations = _symbol_annotations(raw.index)
        extra['scale_evidence'] = ('SOFT-declared raw-count workbook Normal/OA sheets, sample descriptions '
                                   'name raw_counts.xlsx, SOFT reports HTSeq-count; all values checked '
                                   'as finite nonnegative integers; normalized supplements unused')
        extra['raw_workbook_declared_in_soft'] = declared
        extra['normalized_supplements_used'] = False
    elif accession == 'GSE143514':
        frame = _read_tsv(source(accession + '_mRNA_raw_count.txt.gz'))
        raw = frame.set_index('gene')
        annotations = _symbol_annotations(raw.index)
        samples = {gsm: s for gsm, s in all_samples.items()
                   if _one(s, 'title').endswith('(mRNA)')}
        if len(samples) != 8 or raw.shape[1] != 8:
            raise ValueError('GSE143514 must contain exactly eight mRNA samples')
        identity_key, fields = _mrna_description, ('description',)
        basis = 'explicit_column_label_to_exact_mRNA_description'
        extra['scale_status'] = 'deposited_counts_processing_text_conflicts_with_FPKM'
        extra['scale_requires_review'] = True
        extra['ignored_gsm_ids'] = sorted(set(all_samples) - set(samples))
        warnings.append('Supplement says raw counts; SOFT also describes Cuffquant/Cuffdiff FPKM. '
                        'Values unchanged; confirm units before count-specific normalization.')
    elif accession == 'GSE185064':
        frame = _read_tsv(source(accession + '_4_genes_fpkm_expression.txt.gz')).set_index('gene_id')
        count_columns = [c for c in frame if c.startswith('count.')]
        if not count_columns:
            raise ValueError('GSE185064 has no count columns')
        raw = frame[count_columns].copy()
        annotations = pd.DataFrame({'gene_id': frame.index.astype(str),
                                    'gene_symbol': frame['gene_name'].to_numpy()}, index=raw.index.copy())
        identity_key = lambda column: column.removeprefix('count.')
        basis = 'count_prefix_removed_then_exact_sample_title'
        extra.update(observation_unit='library_with_unresolved_donor_or_pool',
                     culture_hours=48, fpkm_columns_used=False)
        warnings.append('Cultured primary meniscus cells; pooled RNA mentioned; donor/pool membership unknown.')
    elif accession in _ARRAYS:
        raw = _series_matrix(source(accession + '_series_matrix.txt.gz'))
        fields, basis = ('gsm',), 'exact_GSM_accession'
        platform_ids = {_one(s, 'platform_id') for s in samples.values()}
        if len(platform_ids) != 1 or '' in platform_ids:
            raise ValueError(f'Cannot use one probe annotation for platforms {platform_ids}')
        platform_id = next(iter(platform_ids))
        if platform_id not in platforms:
            raise ValueError(f'No local platform table for {platform_id}')
        annotations = _platform_annotations(raw.index, platforms[platform_id])
        extra['scale_evidence'] = ('Archived log-scale array export; not transformed by this reader'
                                   if scale == 'log_expression'
                                   else 'Archived dChip/GCOS/MAS5 linear-intensity export')
        if accession == 'GSE169077':
            extra.update(observation_unit='RNA_pool', rna_samples_per_pool=5)
            warnings.append('Six OA/five normal pools; donor identities and overlap between pools unknown.')
        if accession in {'GSE55235', 'GSE55457'}:
            extra['study_family'] = 'PMID24690414'
            warnings.append('Same multicenter study family; distinct accession does not prove donor independence.')
    else:
        frame = _read_tsv(source(accession + '_GEO_count_matrix_rename.txt.gz'))
        raw = frame.set_index(frame.columns[0])
        annotations, decoded, unparsed = _annotations_89408(raw.index)
        extra['composite_id_rows_decoded'] = decoded
        extra['unparsed_composite_ids'] = unparsed
        if unparsed:
            warnings.append('Unrecognized colon annotations remain unmapped; original labels are preserved.')
        fields, basis = ('description', 'title', 'gsm'), 'exact_full_description_title_or_GSM'
        extra['scale_evidence'] = 'Deposited RSEM feature counts; fractional estimated counts permitted'
        extra['observation_unit'] = 'biopsy; one per subject per SOFT; column identity may be unresolved'

    if raw.empty or not raw.columns.is_unique:
        raise ValueError(f'Empty expression or duplicate sample columns in {accession}')
    raw = raw.apply(pd.to_numeric, errors='raise')
    values = raw.to_numpy(dtype=float)
    if np.isinf(values).any() or (scale != 'log_expression' and (values < 0).any()):
        raise ValueError(f'Infinite or invalid negative {scale} values in {accession}')
    if scale == 'counts':
        finite = np.isfinite(values)
        fractional = int((values[finite] != np.floor(values[finite])).sum())
        extra['count_value_checks'] = {
            'n_values': int(values.size), 'all_finite': bool(finite.all()),
            'negative_entries': int((values < 0).sum()), 'fractional_entries': fractional,
        }
        if accession == 'GSE114007' and (not finite.all() or fractional):
            raise ValueError('GSE114007 raw-count workbook must contain finite nonnegative integer counts')
    raw, annotations, renamed_rows, duplicate_labels = _unique_feature_keys(raw, annotations)
    matches = _match_samples(raw.columns, samples, identity_key, fields,
                             allow_unresolved=accession == 'GSE89408')
    metadata = _metadata(raw.columns, samples, matches, accession, basis)
    if (not metadata.index.equals(raw.columns) or not annotations.index.equals(raw.index)
            or not raw.index.is_unique or not annotations.index.is_unique):
        raise AssertionError('Expression/metadata/annotation index alignment failed')
    unresolved = metadata.index[metadata['identity_status'].eq('unresolved')].tolist()
    if unresolved:
        warnings.append('Unmatched GSE89408 columns keep original sample_id, no donor-specific SOFT '
                        'attributes, and only explicit column-name condition. GSM is not guessed.')
    group_counts = {str(k): int(v) for k, v in metadata['condition'].value_counts().items()}
    if not group_counts.get(case) or not group_counts.get(control):
        raise ValueError(f'Missing case/control group in {accession}: {group_counts}')
    info = {
        'accession': accession, 'scale': scale, 'tissue': tissue, 'role': role,
        'case': case, 'control': control,
        'source_files': list(dict.fromkeys(str(p) for p in source_files)),
        'series_fields': series,
        'n_features': raw.shape[0], 'n_samples': raw.shape[1],
        'group_counts': group_counts,
        'identity_status': ('unresolved' if len(unresolved) == len(metadata) else
                            'partially_unresolved' if unresolved else 'verified_gsm'),
        'unresolved_columns': unresolved,
        'identity_matches': {column: gsm for column, gsm in matches.items() if gsm is not None},
        'soft_sample_count': len(all_samples),
        'soft_platform_ids': sorted({_one(s, 'platform_id') for s in all_samples.values()}),
        'duplicate_feature_rows': int(raw.index.duplicated().sum()),
        'duplicate_source_feature_labels': duplicate_labels,
        'feature_keys_rewritten': renamed_rows,
        'missing_expression_values': int(raw.isna().sum().sum()),
        'warnings': warnings,
        **extra,
    }
    if accession == 'GSE89408':
        matched_gsm = {gsm for gsm in matches.values() if gsm is not None}
        # Keep unlinked records for audit without attributing them to matrix columns.
        info['unmatched_soft_samples'] = {gsm: s for gsm, s in samples.items() if gsm not in matched_gsm}
        info['soft_group_counts'] = dict(Counter(_condition(accession, s) for s in samples.values()))
        info['group_counts_agree_with_soft'] = info['soft_group_counts'] == group_counts
        if not info['group_counts_agree_with_soft']:
            raise ValueError('GSE89408 public column-condition totals disagree with SOFT')
    return raw, metadata, annotations, info


def main():
    parser = argparse.ArgumentParser(description='Read-only GEO input validation; writes no files.')
    parser.add_argument('--project-root', required=True, type=Path)
    parser.add_argument('--accessions', nargs='+', choices=tuple(COHORTS), default=list(COHORTS))
    args = parser.parse_args()
    for accession in args.accessions:
        raw, metadata, annotations, info = load_cohort(args.project_root, accession)
        summary = {key: info[key] for key in ('accession', 'scale', 'tissue', 'role', 'group_counts',
                                             'identity_status', 'duplicate_feature_rows',
                                             'missing_expression_values')}
        summary.update(shape=list(raw.shape), metadata_aligned=metadata.index.equals(raw.columns),
                       annotations_aligned=annotations.index.equals(raw.index),
                       verified_GSM=int(metadata['identity_status'].eq('verified_gsm').sum()),
                       unresolved=len(info['unresolved_columns']),
                       age_available=int(metadata['age'].notna().sum()),
                       sex_available=int(metadata['sex'].ne('').sum()))
        print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

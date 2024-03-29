"""
Steps used to process a GWAS file for future use
"""
import hashlib
import json
import logging

from zorp import (
    exceptions as z_exc,
    parsers,
    readers,
    sniffers
)
# from .exceptions import ManhattanExeption, QQPlotException, UnexpectedIngestException
from . exceptions import TopHitException
from . import (
    helpers,
    manhattan,
    qq
)

logger = logging.getLogger(__name__)


@helpers.capture_errors
def get_file_sha256(src_path, block_size=2 ** 20) -> bytes:
    # https://stackoverflow.com/a/1131255/1422268
    with open(src_path, 'rb') as f:
        shasum_256 = hashlib.sha256()

        while True:
            data = f.read(block_size)
            if not data:
                break
            shasum_256.update(data)
        return shasum_256.digest()


@helpers.capture_errors
def normalize_contents(src_path: str, parser_options: dict, dest_path: str, log_path: str) -> bool:
    """
    Initial content ingestion: load the file and write variants in a standardized format

    This routine will deliberately exclude lines that could not be handled in a reliable fashion, such as pval=NA
    """
    parser = parsers.GenericGwasLineParser(**parser_options)
    reader = sniffers.guess_gwas(src_path, parser=parser)

    success = False
    try:
        dest_fn = reader.write(dest_path, make_tabix=True)
    except z_exc.TooManyBadLinesException as e:
        raise e
    else:
        success = True
        logger.info('Conversion succeeded! Results written to: {}'.format(dest_fn))
    finally:
        # Always write a log entry, no matter what
        with open(log_path, 'a+') as f:
            for n, reason, _ in reader.errors:
                f.write('Excluded row {} from output due to parse error: {}\n'.format(n, reason))
            if success:
                f.write('[success] GWAS file has been converted.\n')
                return True
            else:
                f.write('[failure] Could not create normalized GWAS file.\n')
    # In reality a failing task will usually raise an exception rather than returning False
    return False


@helpers.capture_errors
def generate_manhattan(in_filename: str, out_filename: str) -> bool:
    """Generate manhattan plot data for the processed file"""
    # FIXME: Pheweb loader code does not handle infinity values, so we exclude these from manhattan plots
    #   This is almost assuredly not the final desired behavior
    reader = readers.standard_gwas_reader(in_filename)\
        .add_filter('neg_log_pvalue', lambda v, row: v is not None)

    binner = manhattan.Binner()
    for variant in reader:
        binner.process_variant(variant)

    manhattan_data = binner.get_result()

    with open(out_filename, 'w') as f:
        json.dump(manhattan_data, f)
    return True


@helpers.capture_errors
def generate_qq(in_filename: str, out_filename) -> bool:
    """Largely borrowed from PheWeb code (load.qq.make_json_file)"""
    # TODO: Currently the ingest pipeline never stores "af"/"maf" at all, which could affect this calculation
    # TODO: This step appears to load ALL data into memory (list on generator). This could be a memory hog; not sure if
    #   there is a way around it as it seems to rely on sorting values

    # FIXME: See note above: we will exclude "infinity" values for now, but this is not the desired behavior because it
    #   hides the hits of greatest interest
    reader = readers.standard_gwas_reader(in_filename)\
        .add_filter("neg_log_pvalue", lambda v, row: v is not None)

    # TODO: Pheweb QQ code benefits from being passed { num_samples: n }, from metadata stored outside the
    #   gwas file. This is used when AF/MAF are present (which at the moment ingest pipeline does not support)

    variants = list(qq.augment_variants(reader))

    rv = {}
    if variants:
        if variants[0].maf is not None:
            rv['overall'] = qq.make_qq_unstratified(variants, include_qq=False)
            rv['by_maf'] = qq.make_qq_stratified(variants)
            rv['ci'] = list(qq.get_confidence_intervals(len(variants) / len(rv['by_maf'])))
        else:
            rv['overall'] = qq.make_qq_unstratified(variants, include_qq=True)
            rv['ci'] = list(qq.get_confidence_intervals(len(variants)))

    with open(out_filename, 'w') as f:
        json.dump(rv, f)

    return True


@helpers.capture_errors
def get_top_hit(in_filename: str):
    """
    Find the very top hit in the study

    Although most of the tasks in our pipeline are written to be ORM-agnostic, this one modifies the database.
    """
    reader = readers.standard_gwas_reader(in_filename).add_filter("neg_log_pvalue", lambda v, row: v is not None)
    best_pval = 1
    best_row = None
    for row in reader:
        if row.pval < best_pval:
            best_pval = row.pval
            best_row = row

    if best_row is None:
        raise TopHitException('No usable top hit could be identified. Check that the file has valid p-values.')

    return best_row

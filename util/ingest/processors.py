"""
Steps used to process a GWAS file for future use
"""
import json
import logging
import math
import typing as ty

from pheweb.load import (
    manhattan,
    qq,
)

from zorp import (
    exceptions as z_exc,
    parsers,
    readers,
    sniffers
)
# from .exceptions import ManhattanExeption, QQPlotException, UnexpectedIngestException
from . import helpers

from locuszoom_plotting_service.gwas import models

logger = logging.getLogger(__name__)


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
        with open(log_path, 'w') as f:
            for n, reason, _ in reader.errors:
                f.write('Excluded row {} from output due to parse error: {}\n'.format(n, reason))

            if success:
                f.write('[success] GWAS file has been converted.\n')
                return True
            else:
                f.write('[failure] Could not create normalized GWAS file for: {}'.format(src_path))


@helpers.capture_errors
def _pheweb_adapter(reader) -> ty.Iterator[dict]:
    """Formats zorp parsed data into the format expected by pheweb"""
    for row in reader:
        yield {'chrom': row.chrom, 'pos': row.pos, 'pval': row.pvalue}


@helpers.capture_errors
def generate_manhattan(in_filename: str, out_filename: str) -> bool:
    """Generate manhattan plot data for the processed file"""
    # FIXME: Pheweb loader code does not handle infinity values; exclude these from manhattan plots
    #   This is almost assuredly not the final desired behavior
    reader = readers.standard_gwas_reader(in_filename)\
        .add_filter('neg_log_pvalue', lambda v, row: v is not None)\
        .add_filter('neg_log_pvalue', lambda v, row: not math.isinf(v))

    reader_adapter = _pheweb_adapter(reader)

    binner = manhattan.Binner()
    for variant in reader_adapter:
        binner.process_variant(variant)

    manhattan_data = binner.get_result()

    # TODO: consider using boltons.atomicsaver in future
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
        .add_filter("neg_log_pvalue", lambda v, row: v is not None)\
        .add_filter('neg_log_pvalue', lambda v, row: not math.isinf(v))
    reader_adapter = _pheweb_adapter(reader)

    # TODO: Pheweb QQ code benefits from being passed { num_samples: n }, from metadata stored outside the
    #   gwas file. This is used when AF/MAF are present (which at the moment ingest pipeline does not support)
    stub = {}

    variants = list(qq.augment_variants(reader_adapter, stub))

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
def get_top_hit(in_filename: str, gwas_id: ty.Union[str, int]) -> bool:
    """
    Find the very top hit in the study

    Although most of the tasks in our pipeline are written to be ORM-agnostic, this one modifies the database.
    """
    gwas = models.Gwas.objects.get(pk=gwas_id)
    reader = readers.standard_gwas_reader(in_filename).add_filter("neg_log_pvalue", lambda v, row: v is not None)
    best_pval = 1
    best_row = None
    for row in reader:
        if row.pval < best_pval:
            best_pval = row.pval
            best_row = row

    if best_row is None:
        raise Exception('No usable top hit could be identified. Check that the file has valid p-values.')

    top_hit = models.RegionView.objects.create(
        label='Top hit',
        chrom=best_row.chrom,
        start=best_row.pos - 250_000,
        end=best_row.pos + 250_000
    )
    gwas.top_hit_view = top_hit

    gwas.save()
    print('----', top_hit)
    print(gwas.top_hit_view)
    return True

"""
Steps used to process a GWAS file for future use
"""
import json

from pheweb.load import manhattan

from . loaders import make_reader


def generate_manhattan(in_filename: str, out_filename: str) -> str:
    """Generate manhattan plot data for the processed file"""
    # Convert the reader to use the data structure expected by pheweb
    reader_adapter = (
        {'chrom': row.chrom, 'pos': row.pos, 'pval': row.pvalue}
        for row in make_reader(in_filename)
    )

    binner = manhattan.Binner()
    for variant in reader_adapter:
        binner.process_variant(variant)

    manhattan_data = binner.get_result()

    # TODO: consider using boltons.atomicsaver in future
    with open(out_filename, 'w') as f:
        json.dump(manhattan_data, f)

    return out_filename

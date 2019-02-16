"""
Coordinate file format detection and loading. Format detection, reader instance creation, etc..

# TODO: Generalize and move to ZORP iff useful
"""
import magic

from util.zorp.parsers import standard_gwas_parser
from util.zorp.readers import (
    BaseReader, TabixReader, TextFileReader
)


def make_reader(filename, mimetype: str = None) -> BaseReader:
    mimetype = mimetype or magic.from_file(filename, mime=True)
    if mimetype in ('application/gzip', 'application/x-gzip'):
        parser = TabixReader
    elif mimetype.startswith('text/'):
        parser = TextFileReader
    else:
        raise Exception(f'Unsupported file encoding: {mimetype}')
    return parser(filename, parser=standard_gwas_parser, skip_rows=1)

"""Perform simple sanity checks to make sure the uploaded file is valid and readable"""

import itertools
import logging

import magic

from pheweb.utils import chrom_order

from .loaders import make_reader
from util.zorp.readers import BaseReader

from . import helpers


logger = logging.getLogger(__name__)


class _GwasValidator:
    """Validate a raw GWAS file as initially uploaded"""
    def __init__(self, headers=None, delimiter='\t'):
        self._delimiter = delimiter
        self._headers = headers

    @helpers.false_on_fail
    def validate(self, filename: str) -> bool:
        """Perform all checks for a stored file"""
        encoding = self._get_encoding(filename)
        reader = make_reader(filename, mimetype=encoding)
        return all([
            self._validate_mimetype(encoding),
            self._validate_contents(reader),
        ])

    def _get_encoding(self, filename: str) -> str:
        return magic.from_file(filename, mime=True)

    @helpers.false_on_fail
    def _validate_mimetype(self, mimetype: str) -> bool:
        """Uploaded either a gzipped file or plain text"""
        return (mimetype in ['application/gzip', 'application/gzip']) or mimetype.startswith('text/')

    @helpers.false_on_fail
    def _validate_headers(self, reader) -> bool:
        n_head, content = reader.get_headers()
        # First version: match headers to an expected string + row count
        # TODO: replace with a sniffer class that simply says "has all columns required"
        return all([
            n_head == 1,
            tuple(content.lower().split(self._delimiter)) == self._headers
        ])

    @helpers.false_on_fail
    def _validate_data_rows(self, reader) -> bool:
        """Data must be sorted, all values must be readable, and all chroms must be known"""
        # Horked from PheWeb's `load.read_input_file.PhenoReader` class
        cp_groups = itertools.groupby(reader, key=lambda v: (v.chrom, v.pos))

        def _get_chrom_index(chrom):
            try:
                return chrom_order[chrom]
            except KeyError:
                raise Exception('PheWeb pipeline does not support the specified chromosome')

        prev_chrom_index = -1
        prev_pos = -1
        for cp, tied_variants in cp_groups:
            chrom_index = _get_chrom_index(cp[0])
            if chrom_index < prev_chrom_index:
                # Chroms in wrong order for PheWeb- TODO is this relevant to the parts we use?
                return False

            if chrom_index == prev_chrom_index and cp[1] < prev_pos:
                # Positions not in correct order for Pheweb to use
                return False

            prev_chrom_index = chrom_index
            prev_pos = cp[1]

        # Must make it through the entire file without parsing errors, with all chroms in order, and find at least
        #   one row of data
        return prev_pos != -1

    @helpers.false_on_fail
    def _validate_contents(self, reader: BaseReader) -> bool:
        """Validate file contents; useful for unit testing"""
        return all([
            self._validate_headers(reader),
            self._validate_data_rows(reader),
        ])


# TODO: Better header detection/ sniffers?
standard_gwas_validator = _GwasValidator(delimiter='\t', headers=("#chrom", "pos", "ref", "alt", "pvalue"))

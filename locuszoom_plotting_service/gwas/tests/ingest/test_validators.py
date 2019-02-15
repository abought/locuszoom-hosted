from locuszoom_plotting_service.gwas.ingest import validators

from util.zorp import (
    parsers, readers
)


class TestStandardGwasValidator:
    def test_valid_input(self):
        reader = readers.IterableReader([
            "#chrom\tpos\tref\talt\tlogpvalue",
            "1\t1\tA\tC\t7.3"
            "X\t1\tA\tC\t7.3"
        ], parser=parsers.standard_gwas_parser)

        is_valid = validators.standard_gwas_validator._validate_contents(reader)
        assert is_valid

    def test_wrong_headers(self):
        reader = readers.IterableReader([
            "#NOPE\tpos\tref\talt\tlogpvalue",
            "1\t1\tA\tC\t7.3"
            "X\t1\tA\tC\t7.3"
        ], parser=parsers.standard_gwas_parser)

        is_valid = validators.standard_gwas_validator._validate_contents(reader)
        assert not is_valid

    def test_wrong_datatype(self):
        reader = readers.IterableReader([
            "#chrom\tpos\tref\talt\tlogpvalue",
            "1\t1\tA\tC\t7.3"
            "X\t1\tA\tC\tNOPE"
        ], parser=parsers.standard_gwas_parser)

        is_valid = validators.standard_gwas_validator._validate_contents(reader)
        assert not is_valid

    def test_wrong_chrom_order(self):
        reader = readers.IterableReader([
            "#chrom\tpos\tref\talt\tlogpvalue",
            "X\t1\tA\tC\t7.3"
            "1\t1\tA\tC\t7.3"
        ], parser=parsers.standard_gwas_parser)

        is_valid = validators.standard_gwas_validator._validate_contents(reader)
        assert not is_valid

    def test_chroms_not_sorted(self):
        reader = readers.IterableReader([
            "#chrom\tpos\tref\talt\tlogpvalue",
            "1\t1\tA\tC\t7.3",
            "X\t1\tA\tC\t7.3",
            "1\t2\tA\tC\t7.3",
        ], parser=parsers.standard_gwas_parser)

        is_valid = validators.standard_gwas_validator._validate_contents(reader)
        assert not is_valid

    def test_positions_not_sorted(self):
        reader = readers.IterableReader([
            "#chrom\tpos\tref\talt\tlogpvalue",
            "1\t2\tA\tC\t7.3",
            "1\t1\tA\tC\t7.3",
            "X\t1\tA\tC\t7.3",
        ], parser=parsers.standard_gwas_parser)

        is_valid = validators.standard_gwas_validator._validate_contents(reader)
        assert not is_valid

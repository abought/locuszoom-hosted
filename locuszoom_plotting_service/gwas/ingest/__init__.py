"""
GWAS Data ingestion pipeline

0. Confirm that the file can be read (text or bgzipped format)
1. Validate that a GWAS file is valid and acceptable: has all columns; known chromosomes; pvals not missing or 0;
    data is sorted
2. Convert the GWAS file to tabixed, gzipped format
3. Generate data needed for binned manhattan plot + QQ plot.
4. Find a list of top hits in each region, based on some algorithm/ criteria
"""

GENOME_BUILDS = (
    ('GRCh37', 'GRCh37'),
    ('GRCh38', 'GRCh38'),
)
INGEST_STATES = (
    (0, 'PENDING'),
    (1, 'FAILED'),
    (2, 'SUCCESS')
)

PHENO_CLASSIFICATIONS = (
    (1, 'SNOMED CT (Core)'),
)
# -Other systems (not supported in our current database, but useful to keep a list)
#     (2, 'ICD-9'),
#     (3, 'ICD-10'),
#     (4, 'Experimental Factor Ontology'),
#     (5, 'Vanderbilt PheCode (ICD-9)'),
#     (6, 'Vanderbilt PheCode (ICD-10)'),
# )

####
# Below are some enumerations that might be useful in the future (but aren't now)

# List based on all options available in Michigan Imputation Server. Too restrictive to be universal list.
# IMPUTATION_PANELS = (
#     ('CAAPA', 'CAAPA - African American Panel'),
#     ('1000G', '1000 Genomes'),
#     ('hapmap2', 'HapMap 2'),
#     ('hrc1', 'HRC r1 2015'),
#     ('hrc.r1.1.2016', 'HRC r1.1 2016'),
#     ('1000G-phase1', '1000G Phase 1 v3 Shapeit2 (no singletons)'),
#     ('1000G-phase3', '1000G Phase 3 v5'),
#     ('other', 'Other (unspecified)')
# )

#


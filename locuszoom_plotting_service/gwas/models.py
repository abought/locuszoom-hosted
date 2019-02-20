import hashlib
import logging
import os
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django.utils import timezone
from django.utils.http import urlencode
from django.urls import reverse
from model_utils.models import TimeStampedModel

from . import constants
from . import util

from util.ingest import pipeline


logger = logging.getLogger(__name__)


User = get_user_model()

# class Phenotypes(models.Model):
#     """Pre-defined lists of phenotypes: ICD9, ICD10, EFO, or Vanderbilt phecodes"""
#     short_desc = models.CharField()
#     long_desc = models.CharField()
#     classification = None  # TODO: Create enum or other system


def _pipeline_folder():
    # Get pipeline folder name; must be a standalone function for migrations to work
    return uuid.uuid1().hex


class Gwas(TimeStampedModel):
    """A single analysis (GWAS results) that may be part of a larger group"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    analysis = models.CharField(max_length=100,
                                help_text="A human-readable description, eg DIAGRAM Height GWAS")

    # Metadata that the user must fill in when uploading
    build = models.CharField(max_length=10, choices=constants.GENOME_BUILDS)
    imputed = models.CharField(max_length=25, blank=True,
                               # TODO: This may be too restrictive?
                               choices=constants.IMPUTATION_PANELS,
                               help_text="If your data was imputed, please specify the reference panel used")
    is_log_pvalue = models.BooleanField(default=True)

    # Data to be filled in by upload/ post processing steps
    top_hit_view = models.OneToOneField('gwas.RegionView', on_delete=models.SET_NULL, null=True, related_name='+')
    pipeline_complete = models.DateTimeField(null=True)

    ########
    # Below this line: first iteration will be to serve files from local filesystem, rather than database
    pipeline_path = models.CharField(max_length=32,
                                     default=_pipeline_folder,
                                     help_text="Internal use only: path to folder of ingested data")
    raw_gwas_file = models.FileField(upload_to=util.get_gwas_raw_fn)  # The original / raw file
    file_sha256 = models.CharField(max_length=64)

    def get_absolute_url(self):
        return reverse('gwas:overview', kwargs={'pk': self.id})

    def __str__(self):
        return self.analysis

    #######
    # Tell the upload pipeline where to find/ store each asset
    @property
    def normalized_gwas_path(self):
        """Path to the normalized, tabix-indexed GWAS file"""
        return os.path.join(util.get_study_folder(self, absolute_path=True), 'normalized.txt.gz')

    @property
    def normalized_gwas_log_path(self):
        """Path to the normalized, tabix-indexed GWAS file"""
        return os.path.join(util.get_study_folder(self, absolute_path=True), 'normalized.log')

    @property
    def manhattan_path(self):
        # PheWeb pipeline writes a JSON file that is used in entirety by frontend
        return os.path.join(util.get_study_folder(self, absolute_path=True), 'manhattan.json')

    @property
    def qq_path(self):
        return os.path.join(util.get_study_folder(self, absolute_path=True), 'qq.json')

    @property
    def tophits_path(self):
        # PheWeb pipeline writes a tabixed file that supports region queries # TODO: Implement
        return os.path.join(util.get_study_folder(self, absolute_path=True), 'tophits.gz')


class RegionView(TimeStampedModel):
    """
    Represents an interesting locus region, with optional config parameters

    The upload pipeline will define a few suggested views (eg top hits), and users can save their own views on any
        public dataset
    """
    # What is this view associated with? Allows users to save views for someone else's (public) datasets
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True)  # Null for views created by system
    gwas = models.ForeignKey(Gwas, on_delete=models.DO_NOTHING)

    label = models.CharField(max_length=100)

    # What region to view?
    chrom = models.CharField(max_length=5, blank=False)  # Standardize with PheWeb chroms list?
    start = models.PositiveIntegerField()
    end = models.PositiveIntegerField()

    # Additional arbitrary params associated with the page- URL query params
    options = JSONField(null=True, blank=True)  # TODO: Decouple front and backend as requirements emerge

    def get_absolute_url(self):
        """A region view is just a LocusZoom plot with some specific options"""
        base_url = reverse('gwas:region', kwargs={'pk': self.gwas.id})
        params = urlencode(self.get_url_params())
        return f'{base_url}?{params}'

    # Helper methods
    def get_url_params(self):
        # The standalone fields are source of truth and override any values stored in the "extra" params blob
        basic = {'chrom': self.chrom, 'start': self.start, 'end': self.end}
        extended = self.options or {}
        return {**extended, **basic}


@receiver(signals.post_save, sender=Gwas)
def analysis_upload_pipeline(sender, instance: Gwas = None, created=None, **kwargs):
    """
    Specify a series of operations to be run on a newly uploaded file, such as integrity verification and
        "interesting region" detection

    - Compute SHA for the initially uploaded GWAS
    - Write data for a pheweb-style manhattan plot
    :return:
    """
    # Only run once when model first created.
    # This is a safeguard to prevent infinite recursion from re-saves (a downside of using signals)
    if not created:
        return

    # Track the SHA of what was uploaded, so user can validate later.
    with instance.raw_gwas_file.open('rb') as f:  # type: ignore
        shasum_256 = hashlib.sha256()
        if f.multiple_chunks():
            for chunk in f.chunks():
                shasum_256.update(chunk)
        else:
            shasum_256.update(f.read())

    instance.file_sha256 = shasum_256.hexdigest()  # type: ignore
    instance.save()

    try:
        pipeline.standard_gwas_pipeline(
            os.path.join(settings.MEDIA_ROOT, instance.raw_gwas_file.name),
            instance.normalized_gwas_path,
            instance.normalized_gwas_log_path,
            instance.manhattan_path,
            instance.qq_path,
        )
    except Exception as e:
        # TODO: Mark pipeline completed (failed), and send notification email to the user
        # TODO: Add a field to indicate failures, and consider how/when to clean up files that could not be processed
        logger.exception('Ingestion pipeline failed')
        raise e
    else:
        # Mark analysis pipeline as having completed successfully
        # TODO: Send a notification email to the user
        instance.pipeline_complete = timezone.now()  # type: ignore
        instance.save()  # type: ignore

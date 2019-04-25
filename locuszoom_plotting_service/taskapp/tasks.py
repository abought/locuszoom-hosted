import hashlib
import os

from celery.utils.log import get_task_logger
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import signals
from django.dispatch import receiver
from django.utils import timezone

from locuszoom_plotting_service.gwas import models
from util.ingest import pipeline


logger = get_task_logger(__name__)


@shared_task(bind=True)
def analysis_upload_pipeline(self, gwas_id: int):
    """All steps of the analysis upload process"""
    # TODO: In the future this might be refactored into parallel for improved performance/speed

    # Track the SHA of what was uploaded, so user can validate later.
    instance = models.Gwas.objects.get(pk=gwas_id)

    with instance.raw_gwas_file.open('rb') as f:
        shasum_256 = hashlib.sha256()
        if f.multiple_chunks():
            for chunk in f.chunks():
                shasum_256.update(chunk)
        else:
            shasum_256.update(f.read())

    instance.file_sha256 = shasum_256.hexdigest()
    instance.save()

    try:
        pipeline.standard_gwas_pipeline(
            gwas_id,
            os.path.join(settings.MEDIA_ROOT, instance.raw_gwas_file.name),
            instance.parser_options,
            instance.normalized_gwas_path,
            instance.normalized_gwas_log_path,
            instance.manhattan_path,
            instance.qq_path,
        )
    except Exception as e:
        logger.exception('Ingestion pipeline failed for gwas id: {}'.format(instance.pk))
        instance.ingest_status = 1
        raise e
    else:
        # Mark analysis pipeline as having completed successfully
        instance.ingest_status = 2  # TODO: Use enum
    finally:
        instance.ingest_complete = timezone.now()
        instance.save()


@shared_task(bind=True)
def email_admins(self):
    """Email site admins to warn of a failed task. Eventually, this should only warn for totally unknown error cases."""
    pass


@shared_task(bind=True)
def analysis_upload_notify(self, gwas_id):
    """Notify the owner of a gwas that ingestion has successfully completed"""
    instance = models.Gwas.objects.get(pk=gwas_id)

    send_mail('Results done processing',
              f'Your results are done processing. Please visit {instance.get_absolute_url()} to see the Manhattan plot.',
              'noreply@umich.edu',
              [instance.owner.email])


@receiver(signals.post_save, sender=models.Gwas)
def gwas_upload_signal(sender, instance: models.Gwas = None, created=None, **kwargs):
    """
    Specify a series of operations to be run on a newly uploaded file, such as integrity verification and
        "interesting region" detection

    - Compute SHA for the initially uploaded GWAS
    - Write data for a pheweb-style manhattan plot
    :return:
    """
    # Only run once when model first created.
    # This is a safeguard to prevent infinite recursion from re-saves
    if not created or not instance:
        return

    # TODO: provide a way to disable pipeline for unit tests (besides not running celery)

    #  Submit a celery task immediately
    analysis_upload_pipeline.apply_async(
        (instance.pk, ),
        link=analysis_upload_notify.si(instance.pk)
    )

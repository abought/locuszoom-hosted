import os

from django.conf import settings
from rest_framework import exceptions as drf_exceptions
from rest_framework import generics
from rest_framework import renderers as drf_renderers

from locuszoom_plotting_service.gwas import models as lz_models

from util.zorp.readers import TabixReader
from util.zorp.parsers import standard_gwas_parser

from . import serializers


class GwasListView(generics.ListAPIView):
    """List all known uploaded GWAS analyses"""
    # TODO: No current support for file upload via API endpoint
    queryset = lz_models.Gwas.objects.all()
    serializer_class = serializers.GwasSerializer
    ordering = ('id',)


class GwasDetailView(generics.RetrieveAPIView):
    """Metadata describing one particular uploaded GWAS"""
    queryset = lz_models.Gwas.objects.filter(pipeline_complete__isnull=False).all()
    serializer_class = serializers.GwasSerializer


class GwasRegionView(generics.RetrieveAPIView):
    """
    Fetch the GWAS data (such as from a file) for a specific region
    # TODO: Improve serialization, error handling, etc. (in errors section, not detail)
    """
    renderer_classes = [drf_renderers.JSONRenderer]
    filter_backends: list = []
    queryset = lz_models.Gwas.objects.all()
    serializer_class = serializers.GwasFileSerializer

    def get_serializer(self, *args, **kwargs):
        """Unique scenario: a single model that returns a list of records"""
        return super(GwasRegionView, self).get_serializer(*args, many=True, **kwargs)

    def get_object(self):
        gwas = super(GwasRegionView, self).get_object()
        chrom, start, end = self._query_params()

        if not os.path.isfile(gwas.normalized_gwas_path):
            raise drf_exceptions.NotFound

        reader = TabixReader(gwas.normalized_gwas_path, parser=standard_gwas_parser)
        return list(reader.fetch(chrom, start, end))

    def _query_params(self)-> (str, int, int):
        """
        Specific rules for GWAS retrieval
        # TODO: Write tests!
        - Must specify chrom, start, and end as query params
        - start and end must be integers
        - end > start
        - 0 <= (end - start) <= 500000
        """
        params = self.request.query_params

        chrom = params.get('chrom', None)
        start = params.get('start', None)
        end = params.get('end', None)

        if not (chrom and start and end):
            raise drf_exceptions.ParseError('Must specify "chrom", "start", and "end" as query parameters')

        try:
            start = int(start)
            end = int(end)
        except ValueError:
            raise drf_exceptions.ParseError('"start" and "end" must be integers')

        if end <= start:
            raise drf_exceptions.ParseError('"end" position must be greater than "start"')

        if not (0 <= (end - start) <= settings.LZ_MAX_REGION_SIZE):
            raise drf_exceptions.ParseError(f'Cannot handle requested region size. Max allowed is {500_000}')

        return chrom, start, end

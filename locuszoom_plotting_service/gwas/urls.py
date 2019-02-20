from django.urls import path
from django.contrib.auth.decorators import login_required

from django.views.generic import RedirectView

from . import views

app_name = 'gwas'
urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', login_required(views.GwasCreate.as_view()), name='upload'),

    # Dataset-specific views
    path('gwas/', RedirectView.as_view(pattern_name='home')),
    path('gwas/<pk>/', views.GwasSummary.as_view(), name='overview'),

    # Some views that serve up raw data from server
    path('gwas/<pk>/data/', views.gwas_summarystats, name='gwas-download'),
    path('gwas/<pk>/data/ingest_log/', views.gwas_ingest_log, name='gwas-ingest-log'),
    path('gwas/<pk>/data/manhattan/', views.gwas_manhattan_json, name='manhattan-json'),
    path('gwas/<pk>/data/qq/', views.gwas_qq_json, name='qq-json'),


    path('gwas/<pk>/region/', views.GwasLocus.as_view(), name='region'),
]

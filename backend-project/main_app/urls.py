from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import *
from .views2 import *
from .app_api.parent_views import ParentPedagogiqueAPIView
from .app_api.dashboard_views import EnseignantDashboardStats, DirectionDashboardFilters, DirectionDashboardStats,PerformanceEleveAPIView,EnseignantDashboardFilters
from django.conf import settings
from django.conf.urls.static import static
from .gemini import PreviewExcelAPIView as preview


urlpatterns = [

    # Antso
    path('rapport-finance/paiement/<int:pk>/', PaiementRetrieveUpdateDestroyAPIView.as_view(), name='paiement-rud'),
    path('api/certificat/generer/', CertificatTexteAPIView.as_view(), name='certificat-texte'),
    path('api/certificat/export/', ExportCertificatDocxAPIView.as_view(), name='certificat-export'),
    path('api/statut_paiements/', PaiementViewSet.as_view({'get': 'statut_paiements'}), name='paiement-statut'),
    path('paiement/paiements_enfant/', PaiementViewSet.as_view({'get': 'paiements_enfant'}), name='paiement-enfant'),

    #T siory
    path('api/parent/pedagogique/', ParentPedagogiqueAPIView.as_view()),
    path("preview-excel/", preview.as_view(), name="preview-excel"),
    path("upload-excel/", SaveExcelAPIView.as_view(), name="upload-excel"),
    path("api/presence/verifier/<int:cours_id>", verifier_presence_par_cours, name="verifier_pres"),
    path("api/dashboard/enseignant/stats/",EnseignantDashboardStats.as_view(), name="dashboard-enseignant"),
    path("api/dashboard/enseignant/filters/",EnseignantDashboardFilters.as_view(), name="dashboardFilters"),
    path("api/dashboard/direction/stats/",DirectionDashboardStats.as_view(), name="dashboard-dir"),
    path("api/dashboard/direction/filters/",DirectionDashboardFilters.as_view(), name="directionFilters"),
    path('stats/classe/<int:classe_id>/', StatistiquesClasseAPIView.as_view()),
    path('stats/classe/<int:classe_id>/periode/<int:periode_id>/', StatistiquesClasseAPIView.as_view()),
    path('stats/eleve/<int:eleve_id>/', EvolutionEleveAPIView.as_view()),
    path('stats/alertes/', AlertesDifficulteAPIView.as_view()),
    path('api/stats/presence/eleve/<int:eleve_id>/', PresenceStatsEleveAPIView.as_view()),
    path('api/eleves/<int:eleve_id>/stats/', PerformanceEleveAPIView.as_view(), name='performance-eleve'),

    # url site
    path("dir/events/",EventListCreateView.as_view(), name="events"),
    path("dir/events/list/",EventListCreateView.as_view(), name="events"),
    path("events/list/",EventListView.as_view(), name="events"),
    path("events/list/<int:pk>/",EventRetrieveView.as_view(), name="events"),
    # path("class/list/",GetClass.as_view(), name="class"),
] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
urlpatterns = format_suffix_patterns(urlpatterns)

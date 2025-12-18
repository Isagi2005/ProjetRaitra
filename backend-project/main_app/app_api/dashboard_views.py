from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .dashboard_serializers import DashboardStatsSerializer,PerformanceEleveSerializer, DashboardFilterSerializer
from main_app.models import Classe, AnneeScolaire, Periode, Bulletin, EvaluationEtudiant, PresenceEtudiant, Etudiant
from django.db.models import Q

class EnseignantDashboardStats(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # 1. Récupérer toutes les classes où l'utilisateur est titulaire
        classes = Classe.objects.filter(titulaire=user)
        if not classes.exists():
            return Response({"error": "Aucune classe assignée"}, status=404)

        # 2. Récupérer toutes les années scolaires de ces classes
        annees = AnneeScolaire.objects.filter(classe__in=classes).distinct().order_by('-id')
        # 3. Récupérer tous les trimestres de ces années
        periodes = Periode.objects.filter(typePeriode='TRIM', dateDebut__isnull=False, dateFin__isnull=False).order_by('ordre')

        # 4. Paramètres de filtre (GET)
        annee_id = request.GET.get('annee_id')
        trimestre_id = request.GET.get('trimestre_id')
        classe_id = request.GET.get('classe_id')

        # 5. Classe par défaut (plus récente)
        classe = None
        if classe_id:
            classe = Classe.objects.filter(id=classe_id, titulaire=user).first()
        if not classe:
            classe = classes.order_by('-anneeScolaire__id').first()

        # 6. Année scolaire par défaut (plus récente de la classe)
        annee = None
        if annee_id:
            annee = AnneeScolaire.objects.filter(id=annee_id).first()
        if not annee and classe:
            annee = classe.anneeScolaire

        # 7. Période (trimestre) sélectionnée
        trimestre = None
        if trimestre_id:
            trimestre = Periode.objects.filter(id=trimestre_id).first()

        # 8. Filtrer les bulletins
        bulletins = Bulletin.objects.filter(eleve__classe=classe)
        if annee:
            bulletins = bulletins.filter(eleve__classe__anneeScolaire=annee)
        if trimestre:
            bulletins = bulletins.filter(periode=trimestre)
        else:
            # Si pas de trimestre, on prend tous les trimestres de l'année sélectionnée
            if annee:
                periodes_annee = Periode.objects.filter(typePeriode='TRIM', dateDebut__year__gte=int(str(annee.anneeScolaire)[:4]))
                bulletins = bulletins.filter(periode__in=periodes_annee)

        # 9. Calculer les stats
        data = DashboardStatsSerializer.get_stats(classe, bulletins)
        return Response(data)


class DirectionDashboardStats(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        classes = Classe.objects.all()
        # 2. Récupérer toutes les années scolaires de ces classes
        annees = AnneeScolaire.objects.filter(classe__in=classes).distinct().order_by('-id')
        # 3. Récupérer tous les trimestres de ces années
        periodes = Periode.objects.filter(typePeriode='TRIM', dateDebut__isnull=False, dateFin__isnull=False).order_by('ordre')

        # 4. Paramètres de filtre (GET)
        annee_id = request.GET.get('annee_id')
        trimestre_id = request.GET.get('trimestre_id')
        classe_id = request.GET.get('classe_id')

        # 5. Classe par défaut (plus récente)
        classe = None
        if classe_id:
            classe = Classe.objects.filter(id=classe_id).first()
        if not classe:
            classe = classes.order_by('-anneeScolaire__id').first()

        # 6. Année scolaire par défaut (plus récente de la classe)
        annee = None
        if annee_id:
            annee = AnneeScolaire.objects.filter(id=annee_id).first()
        if not annee and classe:
            annee = classe.anneeScolaire

        # 7. Période (trimestre) sélectionnée
        trimestre = None
        if trimestre_id:
            trimestre = Periode.objects.filter(id=trimestre_id).first()

        # 8. Filtrer les bulletins
        bulletins = Bulletin.objects.filter(eleve__classe=classe)
        if annee:
            bulletins = bulletins.filter(eleve__classe__anneeScolaire=annee)
        if trimestre:
            bulletins = bulletins.filter(periode=trimestre)
        else:
            # Si pas de trimestre, on prend tous les trimestres de l'année sélectionnée
            if annee:
                periodes_annee = Periode.objects.filter(typePeriode='TRIM', dateDebut__year__gte=int(str(annee.anneeScolaire)[:4]))
                bulletins = bulletins.filter(periode__in=periodes_annee)

        # 9. Calculer les stats
        data = DashboardStatsSerializer.get_stats(classe, bulletins)
        return Response(data)

class DirectionDashboardFilters(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        classes = Classe.objects.all()
        annees = AnneeScolaire.objects.filter(classe__in=classes).distinct().order_by('-id')
        
        periodes = Periode.objects.filter(
            typePeriode='TRIM',
            dateDebut__isnull=False,
            dateFin__isnull=False,
            anneeScolaire__in=annees
        ).order_by('ordre')
        data = DashboardFilterSerializer.get_filters(classes, annees, periodes)
        return Response(data)

class EnseignantDashboardFilters(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        classes = Classe.objects.filter(titulaire=user)
        annees = AnneeScolaire.objects.filter(classe__in=classes).distinct().order_by('-id')
       
        periodes = Periode.objects.filter(
            typePeriode='TRIM',
            dateDebut__isnull=False,
            dateFin__isnull=False,
            anneeScolaire__in=annees
        ).order_by('ordre')
        data = DashboardFilterSerializer.get_filters(classes, annees, periodes)
        return Response(data)

class PerformanceEleveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, eleve_id):
        trimestre_id = request.GET.get("trimestre_id")
        try:
            eleve = Etudiant.objects.get(id=eleve_id)
        except Etudiant.DoesNotExist:
            return Response({"error": "Élève non trouvé"}, status=404)

        classe = eleve.classe
        bulletins = Bulletin.objects.filter(eleve=eleve).order_by('periode__ordre')
        total_eleves = Etudiant.objects.filter(classe=classe).count() if classe else 0

        # Liste des trimestres où il y a un bulletin
        trimestres_disponibles = [
            {"id": b.periode.id, "nom": str(b.periode)}
            for b in bulletins if b.periode
        ]

        # Evolution = toutes les moyennes disponibles
        evolution = []
        for b in bulletins:
            if b.moyenneGenerale is not None and b.periode:
                evolution.append({
                    "trimestre": str(b.periode.nom),
                    "moyenne": b.moyenneGenerale
                })

        # Bulletin à utiliser pour les matières et la moyenne générale
        bulletin = None
        if trimestre_id:
            bulletin = bulletins.filter(periode__id=trimestre_id).first()
        else:
            # Dernier bulletin où il y a une moyenne
            bulletins_with_moy = [b for b in bulletins if b.moyenneGenerale is not None]
            if bulletins_with_moy:
                bulletin = bulletins_with_moy[-1]

        moyenne_generale = bulletin.moyenneGenerale if bulletin else None

        # Rang dans la classe pour ce trimestre
        rang_classe = None
        if bulletin and classe:
            bulletins_classe = Bulletin.objects.filter(periode=bulletin.periode, eleve__classe=classe).order_by('-moyenneGenerale')
            moyennes = [b.moyenneGenerale for b in bulletins_classe if b.moyenneGenerale is not None]
            try:
                rang_classe = sorted(moyennes, reverse=True).index(moyenne_generale) + 1
            except ValueError:
                rang_classe = None

        # Matières du bulletin sélectionné
        matieres = []
        if bulletin:
            evaluations = EvaluationEtudiant.objects.filter(bulletin=bulletin)
            for eval in evaluations:
                matieres.append({
                    "nom": str(eval.domaine),
                    "moyenne": eval.valeurNote,
                    "appreciation": eval.appreciation or "",
                })

        data = {
            "moyenne_generale": moyenne_generale,
            "rang_classe": rang_classe,
            "total_eleves": total_eleves,
            "matieres": matieres,
            "evolution": evolution,
            "trimestres_disponibles": trimestres_disponibles,
            "trimestre_selectionne": bulletin.periode.id if bulletin and bulletin.periode else None,
        }

        serializer = PerformanceEleveSerializer(data)
        return Response(serializer.data)
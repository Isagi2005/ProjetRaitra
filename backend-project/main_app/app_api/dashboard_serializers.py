from rest_framework import serializers
from main_app.models import Etudiant, PresenceEtudiant, EvaluationEtudiant
from collections import defaultdict
import datetime

class MatierePerformanceSerializer(serializers.Serializer):
    nom = serializers.CharField()
    moyenne = serializers.FloatField()
    appreciation = serializers.CharField()

class EvolutionTrimestreSerializer(serializers.Serializer):
    trimestre = serializers.CharField()
    moyenne = serializers.FloatField()

class TrimestreDisponibleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nom = serializers.CharField()

class PerformanceEleveSerializer(serializers.Serializer):
    moyenne_generale = serializers.FloatField(allow_null=True)
    rang_classe = serializers.IntegerField(allow_null=True)
    total_eleves = serializers.IntegerField()
    matieres = MatierePerformanceSerializer(many=True)
    evolution = EvolutionTrimestreSerializer(many=True)
    trimestres_disponibles = TrimestreDisponibleSerializer(many=True)
    trimestre_selectionne = serializers.IntegerField(allow_null=True)

# --- Dashboard Enseignant Serializers (NOUVELLE VERSION) ---
class RepartitionNoteSerializer(serializers.Serializer):
    range = serializers.CharField()
    count = serializers.IntegerField()
    color = serializers.CharField()

class MatierePerfSerializer(serializers.Serializer):
    nom = serializers.CharField()
    moyenne = serializers.FloatField()
    meilleure = serializers.FloatField()
    min = serializers.FloatField()

class EvolutionMoyenneSerializer(serializers.Serializer):
    mois = serializers.CharField()
    moyenne = serializers.FloatField()

class DashboardStatsSerializer(serializers.Serializer):
    classe_nom = serializers.CharField()
    annee_nom = serializers.CharField()
    annee_id = serializers.IntegerField()
    classe_id = serializers.IntegerField()
    total_etudiants = serializers.IntegerField()
    retards_30plus = serializers.IntegerField()
    absences_demi_journee = serializers.IntegerField()
    nombre_eleve_classe = serializers.IntegerField()
    moyenne_generale = serializers.FloatField(required=False, allow_null=True)
    meilleure_moyenne = serializers.FloatField(required=False, allow_null=True)
    moyenne_min = serializers.FloatField(required=False, allow_null=True)
    taux_reussite = serializers.FloatField(required=False, allow_null=True)
    repartition_notes = RepartitionNoteSerializer(many=True, required=False)
    eleves_en_difficulte = serializers.IntegerField(required=False, read_only=True)
    evolution_moyenne = EvolutionMoyenneSerializer(many=True, required=False, read_only=True)
    matieres = MatierePerfSerializer(many=True, required=False, read_only=True)
    eleves_excellents = serializers.IntegerField(required=False, read_only=True)

    @staticmethod
    def get_stats(classe, bulletins):
        
        total_etudiants = Etudiant.objects.filter(classe=classe).count()
        retards_30plus = PresenceEtudiant.objects.filter(
            cours__classe=classe,
            statut=PresenceEtudiant.RETARD,
            heureA__gt=serializers.models.F('cours__heureDebut') + datetime.timedelta(minutes=30)
        ).count()
        demi_journee = datetime.timedelta(hours=4)
        absences_demi_journee = PresenceEtudiant.objects.filter(
            cours__classe=classe,
            statut=PresenceEtudiant.ABSENT,
            cours__heureFin__lt=serializers.models.F('cours__heureDebut') + demi_journee
        ).count()
        effectif_officiel = total_etudiants
        moyennes = list(bulletins.values_list('moyenneGenerale', flat=True))
        moyenne_generale = round(sum(moyennes) / len(moyennes), 2) if moyennes else None
        meilleure_moyenne = max(moyennes) if moyennes else None
        moyenne_min = min(moyennes) if moyennes else None
        nb_reussite = len([m for m in moyennes if m is not None and m >= 10])
        taux_reussite = round((nb_reussite / len(moyennes)) * 100, 2) if moyennes else None
        repartition = [
            {"range": "< 8", "count": 0, "color": "#e53935"},
            {"range": "8-10", "count": 0, "color": "#ff9800"},
            {"range": "10-12", "count": 0, "color": "#ffeb3b"},
            {"range": "12-14", "count": 0, "color": "#8bc34a"},
            {"range": "14-16", "count": 0, "color": "#4caf50"},
            {"range": "16-18", "count": 0, "color": "#2196f3"},
            {"range": "> 18", "count": 0, "color": "#3f51b5"}
        ]
        for m in moyennes:
            if m is None:
                continue
            if m < 8:
                repartition[0]["count"] += 1
            elif m < 10:
                repartition[1]["count"] += 1
            elif m < 12:
                repartition[2]["count"] += 1
            elif m < 14:
                repartition[3]["count"] += 1
            elif m < 16:
                repartition[4]["count"] += 1
            elif m < 18:
                repartition[5]["count"] += 1
            else:
                repartition[6]["count"] += 1
        eleves_en_difficulte = len([m for m in moyennes if m is not None and m < 10])
        eleves_excellents = len([m for m in moyennes if m is not None and m >= 16])
        evolution_moyenne = []
        if bulletins and hasattr(bulletins.first(), 'dateEdition'):
            mois_dict = defaultdict(list)
            for b in bulletins:
                if b.dateEdition and b.moyenneGenerale is not None:
                    mois = b.dateEdition.strftime('%b')
                    mois_dict[mois].append(b.moyenneGenerale)
            mois_tries = sorted(mois_dict.keys(), key=lambda m: datetime.datetime.strptime(m, '%b'))[-6:]
            for mois in mois_tries:
                moy = sum(mois_dict[mois]) / len(mois_dict[mois])
                evolution_moyenne.append({"mois": mois, "moyenne": round(moy, 2)})
        matieres = []
        evals = EvaluationEtudiant.objects.filter(bulletin__in=bulletins)
        if evals.exists():
            domaines = evals.values_list('domaine__nom', flat=True).distinct()
            for nom in domaines:
                notes = evals.filter(domaine__nom=nom).values_list('valeurNote', flat=True)
                notes = [n for n in notes if n is not None]
                if notes:
                    matieres.append({
                        "nom": nom,
                        "moyenne": round(sum(notes) / len(notes), 2),
                        "meilleure": max(notes),
                        "min": min(notes)
                    })
        return {
            "classe_nom": f"{classe.nom}-{classe.anneeScolaire.anneeScolaire}" if classe and classe.anneeScolaire else classe.nom,
            "annee_nom": classe.anneeScolaire.anneeScolaire if classe and classe.anneeScolaire else "",
            "annee_id": classe.anneeScolaire.id if classe and classe.anneeScolaire else None,
            "classe_id": classe.id if classe else None,
            "total_etudiants": total_etudiants,
            "retards_30plus": retards_30plus,
            "absences_demi_journee": absences_demi_journee,
            "nombre_eleve_classe": effectif_officiel,
            "moyenne_generale": moyenne_generale,
            "meilleure_moyenne": meilleure_moyenne,
            "moyenne_min": moyenne_min,
            "taux_reussite": taux_reussite,
            "repartition_notes": repartition,
            "eleves_en_difficulte": eleves_en_difficulte,
            "eleves_excellents": eleves_excellents,
            "evolution_moyenne": evolution_moyenne,
            "matieres": matieres
        }

class DashboardFilterSerializer(serializers.Serializer):
    classes = serializers.ListField()
    annees = serializers.ListField()
    periodes = serializers.ListField()

    @staticmethod
    def get_filters(classes, annees, periodes):
        return {
            "classes": [
                {"id": c.id, "nom": c.nom, "annee_id": c.anneeScolaire.id if c.anneeScolaire else None, "annee_nom": c.anneeScolaire.anneeScolaire if c.anneeScolaire else ""}
                for c in classes
            ],
            "annees": [
                {"id": a.id, "nom": a.anneeScolaire}
                for a in annees
            ],
            "periodes": [
                {"id": p.id, "nom": p.nom, "ordre": p.ordre, "annee_id": None}
                for p in periodes
            ]
        }

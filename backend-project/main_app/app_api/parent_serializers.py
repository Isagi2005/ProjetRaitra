from rest_framework import serializers
from main_app.models import Etudiant, Periode, Bulletin, PresenceEtudiant
from .serializers import BulletinSerializer

class PeriodePedagogiqueSerializer(serializers.ModelSerializer):
    bulletin = serializers.SerializerMethodField()
    absences = serializers.SerializerMethodField()
    retards = serializers.SerializerMethodField()
    class Meta:
        model = Periode
        fields = ["id", "nom", "typePeriode", "dateDebut", "dateFin", "bulletin", "absences", "retards"]

    def get_bulletin(self, obj):
        enfant = self.context.get("enfant")
        try:
            bulletin = Bulletin.objects.get(eleve=enfant, periode=obj)
            # Ajoute explicitement les évaluations dans la réponse (pour clarté côté front)
            data = BulletinSerializer(bulletin).data
            data['evaluations'] = [
                {
                    'matiere': eval.domaine.nom if hasattr(eval.domaine, 'nom') else '',
                    'valeur': eval.valeurNote,
                    'appreciation': eval.appreciation or ''
                }
                for eval in bulletin.evaluations.all()
            ]
            return data
        except Bulletin.DoesNotExist:
            return None

    def get_absences(self, obj):
        enfant = self.context.get("enfant")
        return PresenceEtudiant.objects.filter(etudiant=enfant, cours__date__range=[obj.dateDebut, obj.dateFin], statut=PresenceEtudiant.ABSENT).count()

    def get_retards(self, obj):
        enfant = self.context.get("enfant")
        return PresenceEtudiant.objects.filter(etudiant=enfant, cours__date__range=[obj.dateDebut, obj.dateFin], statut=PresenceEtudiant.RETARD).count()

class EnfantPedagogiqueSerializer(serializers.ModelSerializer):
    classe = serializers.CharField(source="classe.nom")
    trimestres = serializers.SerializerMethodField()
    class Meta:
        model = Etudiant
        fields = ["id", "nom", "prenom", "classe", "trimestres"]

    def get_trimestres(self, obj):
        periodes = Periode.objects.filter(typePeriode="TRIM", anneeScolaire=obj.classe.anneeScolaire)
        return PeriodePedagogiqueSerializer(periodes, many=True, context={"enfant": obj}).data
from ..models import Paiement

def is_mois_paye(etudiant, mois: str, annee_scolaire_id: int) -> bool:
    return Paiement.objects.filter(
        etudiant=etudiant,
        mois=mois,
        categorie='Ecolage',
        etudiant__classe__anneeScolaire_id=annee_scolaire_id
    ).exists()

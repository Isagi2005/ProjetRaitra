from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from main_app.models import Cycle
from main_app.bulletin_models import Domaine, SousDomaine, Competence

class Command(BaseCommand):
    help = 'Seed initial bulletin domains, subdomains, and competencies'

    def handle(self, *args, **kwargs):
        # Get or create cycles
        cycle2, _ = Cycle.objects.get_or_create(
            nom='Cycle 2', 
            description='Apprentissages fondamentaux (CP, CE1, CE2)'
        )

        # Define domains with their subdomains and competencies
        domains_data = [
            {
                'nom': 'Français',
                'categorie': 'LINGUISTIQUE',
                'cycle': cycle2,
                'sous_domaines': [
                    {
                        'nom': 'Langage Oral',
                        'competences': [
                            'Écouter et comprendre',
                            'S\'exprimer clairement',
                            'Participer à des échanges'
                        ]
                    },
                    {
                        'nom': 'Lecture',
                        'competences': [
                            'Comprendre un texte lu',
                            'Identifier des mots',
                            'Lire à voix haute'
                        ]
                    },
                    {
                        'nom': 'Écriture',
                        'competences': [
                            'Écrire des mots',
                            'Produire un écrit',
                            'Copier correctement'
                        ]
                    }
                ]
            },
            {
                'nom': 'Mathématiques',
                'categorie': 'MATHEMATIQUE',
                'cycle': cycle2,
                'sous_domaines': [
                    {
                        'nom': 'Nombres et Calcul',
                        'competences': [
                            'Comprendre les nombres',
                            'Calculer mentalement',
                            'Résoudre des problèmes'
                        ]
                    },
                    {
                        'nom': 'Géométrie',
                        'competences': [
                            'Reconnaître des formes',
                            'Reproduire des figures',
                            'Situer des objets'
                        ]
                    }
                ]
            }
        ]

        # Create domains, subdomains, and competencies
        for domain_data in domains_data:
            domain, _ = Domaine.objects.get_or_create(
                nom=domain_data['nom'], 
                categorie=domain_data['categorie'],
                cycle=domain_data['cycle']
            )

            for sous_domaine_data in domain_data['sous_domaines']:
                sous_domaine, _ = SousDomaine.objects.get_or_create(
                    nom=sous_domaine_data['nom'], 
                    domaine=domain
                )

                for competence_nom in sous_domaine_data['competences']:
                    Competence.objects.get_or_create(
                        nom=competence_nom, 
                        sous_domaine=sous_domaine
                    )

        self.stdout.write(self.style.SUCCESS('Successfully seeded bulletin data'))

    def create_complete_bulletin_example(self, etudiant):
        """
        Example method to create a complete bulletin for a student
        """
        from main_app.bulletin_models import Bulletin, EvaluationCompetence, EvaluationGlobale, VieScolaire

        # Create Bulletin
        bulletin = Bulletin.objects.create(
            etudiant=etudiant,
            annee_scolaire='2024-2025',
            trimestre='1',
            appreciation_generale="Bon début d'année, continue comme ça!"
        )

        # Get all competencies
        competencies = Competence.objects.all()

        # Create Competence Evaluations
        for competence in competencies:
            EvaluationCompetence.objects.create(
                bulletin=bulletin,
                competence=competence,
                niveau='EN_COURS',  # Example level
                commentaire=f"Progression satisfaisante en {competence.nom}"
            )

        # Create Global Domain Evaluations
        domains = Domaine.objects.all()
        for domain in domains:
            EvaluationGlobale.objects.create(
                bulletin=bulletin,
                domaine=domain,
                niveau='EN_COURS',
                appreciation=f"Bon développement dans le domaine {domain.nom}"
            )

        # Create Vie Scolaire
        VieScolaire.objects.create(
            bulletin=bulletin,
            participation="Participe activement en classe",
            comportement="Respectueux et attentif",
            points_forts="Motivation et curiosité",
            axes_amelioration="Prendre plus de confiance à l'oral"
        )

        return bulletin

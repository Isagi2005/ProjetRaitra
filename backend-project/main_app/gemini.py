from django.conf import settings
from django.core.cache import cache
import google.generativeai as genai
import hashlib
import json
import pandas as pd
import io
import datetime
import unidecode
from fuzzywuzzy import process
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Classe, Cycle, Etudiant

class PreviewExcelAPIView(APIView):
    # Temps de cache en secondes (1 heure)
    CACHE_TIMEOUT = 3600
    # Limite du nombre de lignes à envoyer à Gemini pour éviter les dépassements
    GEMINI_ROW_LIMIT = 50

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "Aucun fichier fourni"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Générer une clé de cache unique pour le fichier
            file_content = file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            cache_key = f"excel_preview_{file_hash}"
            
            # Vérifier le cache d'abord
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data, status=status.HTTP_200_OK)

            sheets = pd.read_excel(io.BytesIO(file_content), sheet_name=None, engine="openpyxl")
            
            # Essayer d'abord avec Gemini AI si configuré
            preview_data = None
            method_used = "traditional"
            
            if settings.GEMINI_API_KEY:
                preview_data = self.try_with_gemini(file_content, sheets, request)
                if preview_data:
                    method_used = "gemini"
            
            # Si Gemini échoue ou n'est pas configuré, utiliser la méthode traditionnelle
            if not preview_data:
                preview_data = self.traditional_method(sheets, request)
                print("traditionnel")
            
            # Préparer la réponse finale
            response_data = {
                "preview": preview_data,
                "method": method_used,
                "cache_key": file_hash
            }
            
            # Mettre en cache le résultat
            cache.set(cache_key, response_data, self.CACHE_TIMEOUT)
            
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def try_with_gemini(self, file_content, sheets, request):
        """Tente de normaliser les données avec Gemini AI avec gestion des erreurs améliorée"""
        try:
            # Configurer l'API Gemini
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Construire le prompt avec des instructions claires
            prompt = self.build_gemini_prompt(sheets)
            
            # Appeler l'API avec gestion du timeout
            try:
                response = model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.2}  # Moins de créativité pour plus de cohérence
                )
            except Exception as api_error:
                print(f"Erreur API Gemini: {str(api_error)}")
                return None
            
            # Valider et parser la réponse
            return self.parse_and_validate_gemini_response(response, sheets, request)
            
        except Exception as e:
            print(f"Erreur Gemini globale: {str(e)}")
            return None

    def build_gemini_prompt(self, sheets):
        """Construit un prompt détaillé pour Gemini"""
        prompt = """
        Vous êtes un assistant spécialisé dans la normalisation de données éducatives. 
        Voici les règles à suivre :

        ### Colonnes attendues :
        Obligatoires:
        - nom (string): Nom de famille
        - prenoms (string): Prénoms
        - sexe (string: 'H' ou 'F'): Masculin/Féminin

        Optionnelles:
        - dateDeNaissance (date: YYYY-MM-DD)
        - classe (string): Nom de la classe
        - religion (string)
        - adresse (string)
        - image (string: URL ou chemin)
        - pere (string): Nom du père
        - mere (string): Nom de la mère

        ### Instructions :
        1. Identifiez les colonnes correspondantes dans les données sources
        2. Normalisez les noms de colonnes selon la nomenclature ci-dessus
        3. Transformez les données :
           - Dates : standardiser au format YYYY-MM-DD
           - Sexe : 'H' ou 'F' (majuscule)
           - Champs vides : null
        4. Ne conservez que les colonnes demandées
        5. Pour chaque feuille, retournez un objet JSON avec :
           - sheet: nom de la feuille
           - data: tableau des données normalisées

        ### Données sources :
        """

        # Ajouter les métadonnées des feuilles
        for sheet_name, df in sheets.items():
            prompt += f"\n\nFeuille '{sheet_name}' - Colonnes: {list(df.columns)}"
            
            # Ajouter un échantillon des données (limité pour éviter des prompts trop longs)
            sample_data = df.head(min(3, len(df))).fillna('').to_dict('records')
            def serialize_dates(obj):
                if isinstance(obj, (datetime.datetime, datetime.date)):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            prompt += f"\nExemple de lignes:\n{json.dumps(sample_data, indent=2, ensure_ascii=False, default=serialize_dates)}"
        
        prompt += "\n\nRetournez UNIQUEMENT un JSON valide conforme au format demandé, sans commentaires."
        return prompt

    def parse_and_validate_gemini_response(self, response, sheets, request):
        """Valide et transforme la réponse de Gemini"""
        try:
            # Extraire le texte de la réponse
            if not response or not response.text:
                return None
                
            json_str = response.text
            
            # Nettoyer la réponse pour extraire le JSON
            json_start = json_str.find('[')
            json_end = json_str.rfind(']')
            
            if json_start == -1 or json_end == -1:
                return None
                
            json_str = json_str[json_start:json_end+1]
            
            # Parser le JSON
            gemini_data = json.loads(json_str)
            
            # Validation de la structure
            if not isinstance(gemini_data, list):
                return None
                
            required_fields = {'nom', 'prenoms', 'sexe'}
            valid_sheets = []
            
            for sheet_data in gemini_data:
                if not isinstance(sheet_data, dict) or 'sheet' not in sheet_data or 'data' not in sheet_data:
                    continue
                    
                # Valider chaque enregistrement
                valid_records = []
                for record in sheet_data['data']:
                    if not all(field in record for field in required_fields):
                        continue
                        
                    # Normalisation supplémentaire
                    record['sexe'] = record['sexe'].upper()[0] if record.get('sexe') else 'H'
                    if record['sexe'] not in ['H', 'F']:
                        record['sexe'] = 'H'
                        
                    # Gestion de la classe
                    if 'classe' in record and record['classe']:
                        try:
                            classe, created = Classe.objects.get_or_create(
                                nom=record['classe'],
                                defaults={
                                    'titulaire': request.user,
                                    'niveau': Cycle.objects.first(),
                                    'categorie': Classe.PRESCOLAIRE
                                }
                            )
                            record['classe_id'] = classe.id
                            record['classe_created'] = created
                        except Exception as e:
                            record['classe_error'] = str(e)
                    else:
                        record['classe_id'] = None
                        
                    valid_records.append(record)
                
                if valid_records:
                    valid_sheets.append({
                        "sheet": sheet_data['sheet'],
                        "data": valid_records
                    })
            
            return valid_sheets if valid_sheets else None
            
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(f"Erreur parsing Gemini: {str(e)}")
            return None

    def traditional_method(self, sheets, request):
        """Méthode traditionnelle avec optimisations"""
        required_columns = {"nom", "prenoms", "sexe"}
        optional_columns = {"dateDeNaissance", "classe", "religion", "adresse", "image", "pere", "mere"}
        preview_data = []

        for sheet_name, df in sheets.items():
            try:
                # Normalisation des noms de colonnes
                df.columns = [self.normalize_column_name(col) for col in df.columns]
                
                # Mapping des colonnes
                column_mapping = self.build_column_mapping(df.columns, required_columns, optional_columns)
                
                # Vérification des colonnes obligatoires
                missing_columns = required_columns - set(column_mapping.values())
                if missing_columns:
                    raise ValueError(f"Colonnes manquantes: {missing_columns}")
                
                # Renommage et sélection des colonnes
                df = df.rename(columns=column_mapping)
                available_columns = required_columns.union(optional_columns).intersection(df.columns)
                df = df[list(available_columns)]
                
                # Nettoyage des données
                df = self.clean_data(df)
                
                # Conversion en JSON
                json_data = df.to_dict(orient="records")
                
                # Post-traitement
                json_data = self.post_process_records(json_data, request)
                
                preview_data.append({
                    "sheet": sheet_name,
                    "data": json_data
                })
                
            except Exception as e:
                print(f"Erreur traitement feuille {sheet_name}: {str(e)}")
                continue
                
        return preview_data

    def normalize_column_name(self, col_name):
        """Normalise un nom de colonne"""
        if not isinstance(col_name, str):
            col_name = str(col_name)
        return unidecode.unidecode(col_name).lower().replace(" ", "").strip()

    def build_column_mapping(self, columns, required_cols, optional_cols):
        """Construit le mapping des colonnes avec fuzzy matching"""
        column_mapping = {}
        used_columns = set()
        normalized_columns = {self.normalize_column_name(col): col for col in columns}
        
        # Chercher d'abord les correspondances exactes
        for col in required_cols.union(optional_cols):
            normalized = self.normalize_column_name(col)
            if normalized in normalized_columns:
                column_mapping[normalized_columns[normalized]] = col
                used_columns.add(normalized)
        
        # Fuzzy matching pour les colonnes manquantes
        remaining_required = required_cols - set(column_mapping.values())
        for col in remaining_required:
            matches = process.extractOne(col, normalized_columns.keys(), score_cutoff=80)
            if matches and matches[0] not in used_columns:
                column_mapping[normalized_columns[matches[0]]] = col
                used_columns.add(matches[0])
        
        return column_mapping

    def clean_data(self, df):
        """Nettoie les données du dataframe"""
        # Gestion des valeurs manquantes
        df = df.fillna('')
        
        # Normalisation des dates
        if 'dateDeNaissance' in df.columns:
            df['dateDeNaissance'] = pd.to_datetime(
                df['dateDeNaissance'], 
                errors='coerce', 
                dayfirst=True  # Important pour les formats européens
            ).dt.strftime('%Y-%m-%d')
        
        # Normalisation du sexe
        if 'sexe' in df.columns:
            df['sexe'] = df['sexe'].str.upper().str[0].replace({'M': 'H', 'F': 'F'})
            df['sexe'] = df['sexe'].apply(lambda x: 'H' if x not in ['H', 'F'] else x)
        
        return df

    def post_process_records(self, records, request):
        """Post-traitement des enregistrements"""
        for record in records:
            # Gestion de la classe
            if 'classe' in record and record['classe']:
                try:
                    classe, created = Classe.objects.get_or_create(
                        nom=record['classe'],
                        defaults={
                            'titulaire': request.user,
                            'niveau': Cycle.objects.first(),
                            'categorie': Classe.PRESCOLAIRE
                        }
                    )
                    record['classe_id'] = classe.id
                    record['classe_created'] = created
                except Exception as e:
                    record['classe_error'] = str(e)
            else:
                record['classe_id'] = None
            
            # Nettoyage des valeurs None/null
            for key in list(record.keys()):
                if record[key] is None or record[key] == '':
                    record[key] = None
        
        return records
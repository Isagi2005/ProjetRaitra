def generer_prompt_certificat(etudiant, annee_scolaire):
    sexe = "né" if etudiant.sexe == "H" else "née"
    naissance = etudiant.dateDeNaissance.strftime('%d/%m/%Y') if etudiant.dateDeNaissance else "inconnue"
    classe_nom = etudiant.classe.classeName if etudiant.classe else "non précisée"

    return (
        f"Je soussignée, Madame la Directrice de l'école RAITRA KIDZ, certifie que :<br/><br/>"
        f"L'élève <strong>{etudiant.prenom} {etudiant.nom}</strong>, {sexe} le <strong>{naissance}</strong>,<br/>"
        f"Enfant de <strong>{etudiant.pere}</strong> et de <strong>{etudiant.mere}</strong>,<br/>"
        f"Est inscrit(e) dans notre établissement pour l'année scolaire <strong>{annee_scolaire}</strong><br/>"
        f"En classe de <strong>{classe_nom}</strong>.<br/><br/>"
        f"Le présent certificat est délivré à l'intéressé(e) pour servir et valoir ce que de droit."
    )
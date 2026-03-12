import unicodedata
import re
from datetime import datetime
from .models import Patient

def normalize_string(s):
    if not s:
        return ""
    # Normalize unicode (accents) and lowercase
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8')
    s = s.lower()
    # Remove non-alphanumeric characters and whitespace
    s = re.sub(r'[^a-zA-Z0-9]', '', s)
    return s.strip()

def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def similarity_score(s1, s2):
    s1 = normalize_string(s1)
    s2 = normalize_string(s2)
    if not s1 or not s2:
        return 0
    if s1 == s2:
        return 100
    
    distance = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    return round((1 - distance / max_len) * 100)

class DuplicateDetectionService:
    @staticmethod
    def detect_duplicates(target_data):
        """
        Detects potential duplicate patients for given input data.
        Returns a list of dicts with patient data and similarity score.
        """
        nom = target_data.get('nom', '')
        prenom = target_data.get('prenom', '')
        date_naissance = target_data.get('date_naissance')
        if isinstance(date_naissance, str):
            try:
                date_naissance = datetime.strptime(date_naissance, '%Y-%m-%d').date()
            except ValueError:
                date_naissance = None
        
        # 1. Blocking Strategy: Patients with same birth year
        if not date_naissance:
            # If no date, broaden search but this is rare in cancer registries
            candidates = Patient.objects.all()
            print(f"[DuplicateDetection] No birth date provided, searching all {candidates.count()} patients.")
        else:
            # On récupère les candidats (même année de naissance)
            candidates = Patient.objects.filter(date_naissance__year=date_naissance.year)
            print(f"[DuplicateDetection] Found {candidates.count()} candidates for year {date_naissance.year}")
        
        potential_matches = []

        for candidate in candidates:
            print(f"[DuplicateDetection] Comparing with {candidate.nom} {candidate.prenom}")
            score = 0
            weights = {
                'date_naissance': 30,
                'nom': 25,
                'prenom': 20,
                'telephone': 10,
                'sexe': 5,
                'N_carte_nationale': 40,
            }
            
            # Simple exact or fuzzy scoring
            # Birth Date (exact same date after blocking by year)
            if candidate.date_naissance == date_naissance:
                score += weights['date_naissance']
            
            # Names (Fuzzy)
            score += (similarity_score(candidate.nom, nom) * weights['nom']) / 100
            score += (similarity_score(candidate.prenom, prenom) * weights['prenom']) / 100
            
            # National ID (High weight if present)
            n_id_target = target_data.get('N_carte_nationale')
            if n_id_target and candidate.N_carte_nationale:
                if normalize_string(n_id_target) == normalize_string(candidate.N_carte_nationale):
                    score += weights['N_carte_nationale']
            
            # Phone
            phone_target = target_data.get('telephone')
            if phone_target and candidate.telephone:
                if normalize_string(phone_target) == normalize_string(candidate.telephone):
                    score += weights['telephone']
            
            # Sexe
            if candidate.sexe == target_data.get('sexe'):
                score += weights['sexe']

            final_score = round(score)
            print(f"[DuplicateDetection] Final score for {candidate.nom}: {final_score}")
            
            if final_score >= 60:
                print(f"[DuplicateDetection] Found match: {candidate.nom} score {final_score}")
                potential_matches.append({
                    'id_malade': str(candidate.id_malade),
                    'numero_dossier': candidate.numero_dossier,
                    'nom': candidate.nom,
                    'prenom': candidate.prenom,
                    'date_naissance': candidate.date_naissance.isoformat(),
                    'sexe': candidate.sexe,
                    'telephone': candidate.telephone,
                    'N_carte_nationale': candidate.N_carte_nationale,
                    'score': final_score
                })

        # Sort by score descending
        potential_matches.sort(key=lambda x: x['score'], reverse=True)
        return potential_matches

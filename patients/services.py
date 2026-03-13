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
        Detects potential duplicate patients.
        
        Strategy (scalable to 230k+ patients):
        1. Use PostgreSQL to narrow candidates to a small subset using indexed fields
           (birth year + first letter of name). This reduces candidates from 230k down to ~50-500.
        2. Apply fuzzy scoring only on the narrow candidate set in Python.
        
        This avoids a full table scan while still using fuzzy matching quality.
        """
        nom = target_data.get('nom', '')
        prenom = target_data.get('prenom', '')
        date_naissance = target_data.get('date_naissance')
        
        if isinstance(date_naissance, str):
            try:
                date_naissance = datetime.strptime(date_naissance, '%Y-%m-%d').date()
            except ValueError:
                date_naissance = None

        # ── Phase 1: Database-level candidate narrowing (uses indexes) ─────
        # This is O(log N) instead of O(N) thanks to the indexes we added.
        candidates = Patient.objects.all()
        
        if date_naissance:
            # Filter by birth year — a highly selective and indexed query
            candidates = candidates.filter(date_naissance__year=date_naissance.year)
        
        # Further narrow by first letter of last name if available (uses patient_nom_idx)
        if nom and len(nom) > 0:
            candidates = candidates.filter(nom__istartswith=nom[0])

        # Limit the candidate set to a safe maximum for in-memory processing
        candidates = candidates.select_related()[:500]

        # ── Phase 2: Fuzzy scoring on narrowed candidate set ───────────────
        potential_matches = []
        n_id_target = target_data.get('N_carte_nationale')
        phone_target = target_data.get('telephone')

        for candidate in candidates:
            score = 0
            weights = {
                'date_naissance': 30,
                'nom': 25,
                'prenom': 20,
                'telephone': 10,
                'sexe': 5,
                'N_carte_nationale': 40,
            }
            
            if candidate.date_naissance == date_naissance:
                score += weights['date_naissance']
            
            score += (similarity_score(candidate.nom, nom) * weights['nom']) / 100
            score += (similarity_score(candidate.prenom, prenom) * weights['prenom']) / 100
            
            if n_id_target and candidate.N_carte_nationale:
                if normalize_string(n_id_target) == normalize_string(candidate.N_carte_nationale):
                    score += weights['N_carte_nationale']
            
            if phone_target and candidate.telephone:
                if normalize_string(phone_target) == normalize_string(candidate.telephone):
                    score += weights['telephone']
            
            if candidate.sexe == target_data.get('sexe'):
                score += weights['sexe']

            final_score = round(score)
            
            if final_score >= 60:
                potential_matches.append({
                    'id_malade': str(candidate.id_malade),
                    'numero_dossier': candidate.numero_dossier,
                    'nom': candidate.nom,
                    'prenom': candidate.prenom,
                    'date_naissance': candidate.date_naissance.isoformat() if candidate.date_naissance else None,
                    'sexe': candidate.sexe,
                    'telephone': candidate.telephone,
                    'N_carte_nationale': candidate.N_carte_nationale,
                    'score': final_score
                })

        potential_matches.sort(key=lambda x: x['score'], reverse=True)
        return potential_matches


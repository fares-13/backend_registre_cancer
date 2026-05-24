import json
import re
from datetime import datetime
from services.ai.providers import get_provider


PATIENT_EXTRACTION_PROMPT = """
Tu es un assistant d'extraction pour un registre de cancer en Algerie.
Analyse une transcription vocale en francais et retourne uniquement un objet JSON valide.

Champs attendus (tous des chaines, chaine vide si absent):
- nom: nom de famille du patient. Si un seul nom est donne sans distinction prenom/nom, laisse vide.
- prenom: prenom du patient. Si un seul nom est donne, mets-le dans prenom.
- date_naissance: date de naissance au format YYYY-MM-DD.
  Convertis les dates francaises, exemple: "3 septembre 2003" -> "2003-09-03".
- telephone: numero de telephone algerien (05xx xx xx xx, 06xx xx xx xx, 07xx xx xx xx).
- email: adresse email.
- adresse: adresse postale complete, sans telephone ni email.
- N_carte_nationale: numero de carte nationale / CIN (10 a 18 chiffres).
- N_securite_sociale: numero de securite sociale / NSS (13 a 16 chiffres).
- sexe: "M" pour homme/masculin, "F" pour femme/feminin, "" si indetermine.
- autre_maladie: autres maladies ou antecedents medicaux mentionnes.
- habitudes_fixes: facteurs de risque, habitudes de vie, profession a risque.

Regles:
- Extrais UNIQUEMENT les informations presentes dans la transcription.
- Si un champ est introuvable, retourne une chaine vide.
- Ne retourne aucun commentaire, aucun markdown, aucun texte hors JSON.
- Corrige seulement les erreurs evidentes de transcription vocale.
- Preserve les numeros sous forme de chaines.
""".strip()

EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "nom": {"type": "string"},
        "prenom": {"type": "string"},
        "date_naissance": {"type": "string"},
        "telephone": {"type": "string"},
        "email": {"type": "string"},
        "adresse": {"type": "string"},
        "N_carte_nationale": {"type": "string"},
        "N_securite_sociale": {"type": "string"},
        "sexe": {"type": "string", "enum": ["M", "F", ""]},
        "autre_maladie": {"type": "string"},
        "habitudes_fixes": {"type": "string"},
    },
    "required": [
        "nom", "prenom", "date_naissance", "telephone", "email",
        "adresse", "N_carte_nationale", "N_securite_sociale",
        "sexe", "autre_maladie", "habitudes_fixes",
    ],
}


def validate_date(value):
    if not value:
        return ""
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return ""


def validate_sexe(value):
    if value in ("M", "F"):
        return value
    return ""


def clean_numeric(value):
    if not value:
        return ""
    digits = re.sub(r"[^0-9]", "", value)
    return digits


def normalize_extraction(data):
    result = {}
    for key in EXTRACTION_SCHEMA["required"]:
        raw = data.get(key, "")
        if raw is None:
            raw = ""
        result[key] = str(raw).strip()

    result["date_naissance"] = validate_date(result["date_naissance"])
    result["sexe"] = validate_sexe(result["sexe"])

    n_carte = clean_numeric(result["N_carte_nationale"])
    result["N_carte_nationale"] = n_carte if len(n_carte) >= 10 else n_carte

    n_ss = clean_numeric(result["N_securite_sociale"])
    result["N_securite_sociale"] = n_ss if len(n_ss) >= 13 else ""

    return result


class PatientExtractionError(Exception):
    pass


class AIProviderNotAvailableError(PatientExtractionError):
    def __init__(self):
        super().__init__("Aucun fournisseur IA configure (MISTRAL_API_KEY ou OPENAI_API_KEY requis)")


class InvalidJSONError(PatientExtractionError):
    def __init__(self, raw):
        super().__init__(f"Reponse IA invalide (JSON attendu)")


class EmptyResponseError(PatientExtractionError):
    def __init__(self):
        super().__init__("La transcription n'a produit aucune donnee patient")


def extract_patient_from_transcript(transcript):
    provider = get_provider()
    if not provider:
        raise AIProviderNotAvailableError()

    messages = [
        {"role": "system", "content": PATIENT_EXTRACTION_PROMPT},
        {"role": "user", "content": transcript},
    ]

    raw_content = provider.chat_completion(
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=500,
    )

    if not raw_content or not raw_content.strip():
        raise EmptyResponseError()

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise InvalidJSONError(raw_content) from e

    normalized = normalize_extraction(parsed)

    has_data = any(v for v in normalized.values())
    if not has_data:
        raise EmptyResponseError()

    return normalized

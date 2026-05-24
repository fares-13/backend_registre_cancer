import csv
import io
import codecs
import re
from datetime import datetime, date
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import Patient
from .serializers import PatientSerializer

IMPORT_FIELDS = [
    'numero_dossier', 'nom', 'prenom', 'date_naissance', 'sexe',
    'adresse', 'email', 'telephone', 'N_carte_nationale', 'N_securite_sociale',
    'situation_familiale', 'nb_enfants', 'group_sanguin', 'poids', 'taille',
    'autre_maladie', 'nb_fois_cancer', 'latitude', 'longitude',
    'date_deces', 'cause',
]

FIELD_LABELS = {
    'numero_dossier': 'N° dossier (unique, obligatoire)',
    'nom': 'Nom (obligatoire)',
    'prenom': 'Prénom (obligatoire)',
    'date_naissance': 'Date naissance (obligatoire, YYYY-MM-DD ou JJ/MM/AAAA)',
    'sexe': 'Sexe (M/F)',
    'adresse': 'Adresse',
    'email': 'Email',
    'telephone': 'Téléphone',
    'N_carte_nationale': 'N° carte nationale',
    'N_securite_sociale': 'N° sécurité sociale',
    'situation_familiale': 'Situation familiale (Celibataire/Marie(e)/Divorce(e)/Veuf(ve) — accepts sans accent)',
    'nb_enfants': "Nombre d'enfants",
    'group_sanguin': 'Groupe sanguin (A+/A-/B+/B-/AB+/AB-/O+/O-)',
    'poids': 'Poids (kg)',
    'taille': 'Taille (cm)',
    'autre_maladie': 'Autres maladies',
    'nb_fois_cancer': "Nombre de fois cancer",
    'latitude': 'Latitude',
    'longitude': 'Longitude',
    'date_deces': 'Date décès (YYYY-MM-DD ou JJ/MM/AAAA)',
    'cause': 'Cause décès',
}

CHOICES_HELP = {
    'sexe': "M ou F",
    'situation_familiale': "Celibataire, Marie(e), Divorce(e), Veuf(ve)",
    'group_sanguin': "A+, A-, B+, B-, AB+, AB-, O+, O-",
}

TEXT_BOOLEAN_FIELDS = ['deces']

# ── Values vides / indésirables à convertir en None ──
EMPTY_VALUES = {'', ' ', '-', 'n/a', 'null', 'none', 'undefined', 'nan', 'na'}

# ── Map des variantes situation_familiale → valeur modèle ──
SITUATION_FAMILIALE_MAP = {
    'celibataire': 'Célibataire',
    'célibataire': 'Célibataire',
    'marie': 'Marié(e)',
    'marié': 'Marié(e)',
    'marie(e)': 'Marié(e)',
    'marié(e)': 'Marié(e)',
    'mariée': 'Marié(e)',
    'mariée(e)': 'Marié(e)',
    'divorce': 'Divorcé(e)',
    'divorcé': 'Divorcé(e)',
    'divorce(e)': 'Divorcé(e)',
    'divorcé(e)': 'Divorcé(e)',
    'divorcée': 'Divorcé(e)',
    'veuf': 'Veuf(ve)',
    'veuf(ve)': 'Veuf(ve)',
    'veuve': 'Veuf(ve)',
}

# ── Champs optionnels nullables ──
NULLABLE_FIELDS = {
    'adresse', 'email', 'telephone', 'N_carte_nationale', 'N_securite_sociale',
    'sexe', 'situation_familiale', 'group_sanguin', 'poids', 'taille',
    'autre_maladie', 'latitude', 'longitude', 'date_deces', 'cause',
}

# ── Champs entiers avec défaut 0 ──
DEFAULT_ZERO_FIELDS = {'nb_enfants', 'nb_fois_cancer'}

# ── Formats de date supportés ──
DATE_FORMATS = ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%m/%d/%Y')


def _clean_value(value):
    """Nettoie une valeur CSV : strip + convertit les valeurs vides en None."""
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in EMPTY_VALUES:
        return None
    return s


def _normalize_situation_familiale(raw):
    """Normalise la situation familiale vers la valeur attendue par le modèle."""
    key = raw.strip().lower()
    return SITUATION_FAMILIALE_MAP.get(key, raw)


def _parse_date_strict(value):
    """Parse une date avec formats supportés. Retourne date object ou None."""
    if not value:
        return None
    v = str(value).strip()
    if not v or v.lower() in EMPTY_VALUES:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def normalize_row(row):
    """
    Transforme une ligne CSV brute (dict) en données prêtes pour le serializer.

    Règles appliquées :
    - valeurs vides/garbage → None
    - situation_familiale → normalisée vers les choix du modèle
    - dates → date objects
    - numériques → int / float
    """
    cleaned = {}

    for key, raw_value in row.items():
        if not key:
            continue
        k = key.strip()

        # 1) Nettoyage initial
        val = _clean_value(raw_value)

        # 2) Conversion / Normalisation par champ
        if val is None:
            # Rien à convertir, on laisse à None ou à la valeur par défaut
            if k in DEFAULT_ZERO_FIELDS:
                cleaned[k] = 0
            elif k in NULLABLE_FIELDS:
                cleaned[k] = None
            else:
                cleaned[k] = None
            continue

        if k == 'situation_familiale':
            cleaned[k] = _normalize_situation_familiale(val)

        elif k in ('date_naissance', 'date_deces'):
            parsed = _parse_date_strict(val)
            if parsed is None and k == 'date_naissance':
                cleaned[k] = val  # laissé brut, la validation Django refusera
            elif parsed is None:
                cleaned[k] = None
            else:
                cleaned[k] = parsed

        elif k == 'sexe':
            cleaned[k] = val.upper() if len(val) == 1 else val

        elif k == 'email':
            cleaned[k] = val.lower() if '@' in val else val

        elif k in ('nb_enfants', 'nb_fois_cancer'):
            try:
                cleaned[k] = int(val)
            except (ValueError, TypeError):
                cleaned[k] = 0

        elif k == 'poids':
            try:
                cleaned[k] = round(float(val), 2)
            except (ValueError, TypeError):
                cleaned[k] = None

        elif k == 'taille':
            try:
                cleaned[k] = int(float(val))
            except (ValueError, TypeError):
                cleaned[k] = None

        elif k in ('latitude', 'longitude'):
            try:
                cleaned[k] = float(val)
            except (ValueError, TypeError):
                cleaned[k] = None

        else:
            cleaned[k] = val

    # 3) Garantie : les champs à défaut 0 ont 0 au lieu de None
    for f in DEFAULT_ZERO_FIELDS:
        if f not in cleaned or cleaned[f] is None:
            cleaned[f] = 0

    return cleaned

def parse_date(value):
    if not value or not str(value).strip():
        return None
    value = str(value).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Format de date invalide: '{value}'. Utilisez YYYY-MM-DD ou JJ/MM/AAAA.")

def detect_delimiter(sample):
    """
    Robust delimiter detection using csv.Sniffer.
    Falls back to frequency analysis if Sniffer fails.
    """
    try:
        clean_lines = [
            l for l in sample.splitlines()
            if l.strip() and not l.strip().startswith('#')
        ]
        if not clean_lines:
            return ','
        sample_for_sniff = '\n'.join(clean_lines[:10])
        dialect = csv.Sniffer().sniff(sample_for_sniff, delimiters=',;\t')
        return dialect.delimiter
    except csv.Error:
        first_line = sample.splitlines()[0] if sample.splitlines() else ''
        for delim in [',', ';', '\t']:
            if delim in first_line:
                return delim
        return ','

def normalize_csv_value(value):
    if value is None:
        return ''
    value = str(value).strip()
    if value == '' or value == '-':
        return ''
    return value

def strip_csv_comments(content):
    """Remove comment lines (starting with #) and leading blank lines."""
    lines = content.splitlines(keepends=True)
    cleaned = [ln for ln in lines if not ln.strip().startswith('#')]
    return ''.join(cleaned).lstrip('\n\r')

class PatientImportViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def template(self, request):
        header = ';'.join(IMPORT_FIELDS)
        example = ';'.join([
            'DOS-001', 'Dupont', 'Jean', '1985-06-15', 'M',
            '15 Rue de la Liberté', 'jean.dupont@email.com', '0555123456',
            'CN-123456', 'SS-987654', 'Marie(e)', '2', 'A+', '75.5', '175',
            '', '1', '', '', '', '',
        ])
        content = header + '\n' + example + '\n'
        response = Response(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="modele_import_patients.csv"'
        return response

    @action(detail=False, methods=['post'])
    def preview(self, request):
        import sys
        file = request.FILES.get('file')

        # ═════════════════════════════════════════════════════════════
        # DEBUG: STEP 1 — RAW FILE INSPECTION
        # ═════════════════════════════════════════════════════════════
        print("=" * 60, file=sys.stderr)
        print("DEBUG IMPORT: PREVIEW CALLED", file=sys.stderr)
        print(f"file object: {file}", file=sys.stderr)
        if file:
            print(f"file.name: {file.name}", file=sys.stderr)
            print(f"file.content_type: {file.content_type}", file=sys.stderr)
            print(f"file.size: {file.size}", file=sys.stderr)
        else:
            print("NO FILE RECEIVED", file=sys.stderr)

        debug = {
            'file_received': file is not None,
        }
        if not file:
            return Response({'error': 'Aucun fichier fourni.', 'debug': debug},
                            status=status.HTTP_400_BAD_REQUEST)

        debug['file_name'] = file.name
        debug['file_content_type'] = file.content_type
        debug['file_size'] = file.size

        raw = file.read()

        # ═════════════════════════════════════════════════════════════
        # DEBUG: RAW CONTENT
        # ═════════════════════════════════════════════════════════════
        print(f"raw bytes length: {len(raw)}", file=sys.stderr)
        print(f"raw first 300: {raw[:300]}", file=sys.stderr)
        print(f"raw has BOM UTF-8: {raw.startswith(codecs.BOM_UTF8)}", file=sys.stderr)
        print(f"raw has BOM UTF-16 LE: {raw.startswith(codecs.BOM_UTF16_LE)}", file=sys.stderr)

        debug['raw_bytes_length'] = len(raw)
        debug['raw_first_200'] = repr(raw[:300])
        debug['raw_has_bom_utf8'] = raw.startswith(codecs.BOM_UTF8)
        debug['raw_has_bom_utf16le'] = raw.startswith(codecs.BOM_UTF16_LE)

        # ═════════════════════════════════════════════════════════════
        # SAFETY: file.seek(0) — ensure file pointer is reset
        # ═════════════════════════════════════════════════════════════
        try:
            file.seek(0)
            print("file.seek(0) OK", file=sys.stderr)
        except Exception as e:
            print(f"file.seek(0) failed: {e}", file=sys.stderr)

        # ═════════════════════════════════════════════════════════════
        # DECODE: try utf-8-sig FIRST (handles BOM), then fallback
        # ═════════════════════════════════════════════════════════════
        decoded = None
        tried_encodings = []

        # Priority 1: Try utf-8-sig (handles UTF-8 BOM automatically)
        try:
            decoded = raw.decode("utf-8-sig")
            tried_encodings.append("utf-8-sig (forced first attempt)")
            print("Decoded with utf-8-sig (first attempt)", file=sys.stderr)
        except UnicodeDecodeError:
            tried_encodings.append("utf-8-sig (FAILED)")
            print("utf-8-sig FAILED", file=sys.stderr)

        # Priority 2: BOM-based detection (if utf-8-sig failed)
        if decoded is None:
            for bom, encoding in [
                (codecs.BOM_UTF16_LE, 'utf-16'),
                (codecs.BOM_UTF16_BE, 'utf-16'),
            ]:
                if raw.startswith(bom):
                    tried_encodings.append(f'{encoding} (BOM match)')
                    decoded = raw.decode(encoding)
                    print(f"Decoded with {encoding} (BOM match)", file=sys.stderr)
                    break

        # Priority 3: Fallback through common encodings
        if decoded is None:
            for enc in ('utf-8', 'iso-8859-1', 'cp1252', 'latin-1'):
                tried_encodings.append(enc)
                try:
                    decoded = raw.decode(enc)
                    print(f"Decoded with {enc} (fallback)", file=sys.stderr)
                    break
                except UnicodeDecodeError:
                    print(f"{enc} FAILED", file=sys.stderr)
                    continue

        debug['tried_encodings'] = tried_encodings

        if decoded is None:
            print("ALL ENCODINGS FAILED", file=sys.stderr)
            return Response({'error': 'Encodage non supporté.', 'debug': debug},
                            status=status.HTTP_400_BAD_REQUEST)

        # ═════════════════════════════════════════════════════════════
        # DEBUG: DECODED CONTENT
        # ═════════════════════════════════════════════════════════════
        debug['decoded_length'] = len(decoded)
        debug['decoded_first_300'] = repr(decoded[:500])
        print(f"decoded length: {len(decoded)}", file=sys.stderr)
        print(f"decoded first 500 chars: {repr(decoded[:500])}", file=sys.stderr)

        # Strip comments
        decoded_before_strip = decoded
        decoded = strip_csv_comments(decoded)
        if decoded != decoded_before_strip:
            debug['comments_stripped'] = True
            debug['decoded_after_strip_first_300'] = repr(decoded[:300])

        # ═════════════════════════════════════════════════════════════
        # DELIMITER DETECTION
        # ═════════════════════════════════════════════════════════════
        delimiter = detect_delimiter(decoded)
        debug['detected_delimiter'] = repr(delimiter)
        print(f"detected delimiter: {repr(delimiter)}", file=sys.stderr)

        # ═════════════════════════════════════════════════════════════
        # CSV PARSING — FIRST READ (fieldnames + peek rows)
        # ═════════════════════════════════════════════════════════════
        reader = csv.DictReader(io.StringIO(decoded), delimiter=delimiter)
        raw_fieldnames = reader.fieldnames
        debug['raw_fieldnames'] = raw_fieldnames
        print(f"raw_fieldnames: {raw_fieldnames}", file=sys.stderr)

        if not raw_fieldnames:
            debug['error_step'] = 'no_fieldnames'
            print("ERROR: no fieldnames", file=sys.stderr)
            return Response({'error': 'Fichier CSV vide ou invalide.', 'debug': debug},
                            status=status.HTTP_400_BAD_REQUEST)

        # Check for the dreaded "single combined fieldname" problem
        if len(raw_fieldnames) == 1 and raw_fieldnames[0] and ',' in raw_fieldnames[0]:
            print(f"WARNING: single combined fieldname detected: {raw_fieldnames[0]}", file=sys.stderr)
            print("Attempting auto-repair with comma delimiter...", file=sys.stderr)
            delimiter = ','
            debug['delimiter_auto_repaired'] = True
            debug['delimiter_before_repair'] = delimiter
            reader = csv.DictReader(io.StringIO(decoded), delimiter=',')
            raw_fieldnames = reader.fieldnames
            debug['raw_fieldnames_after_repair'] = raw_fieldnames
            print(f"fieldnames after repair: {raw_fieldnames}", file=sys.stderr)

        cleaned_fieldnames = [f.strip() for f in raw_fieldnames]
        debug['cleaned_fieldnames'] = cleaned_fieldnames
        print(f"cleaned_fieldnames: {cleaned_fieldnames}", file=sys.stderr)

        # Peek at first data rows
        all_rows_from_reader = list(reader)
        debug['total_rows_from_reader'] = len(all_rows_from_reader)
        print(f"total_rows_from_reader: {len(all_rows_from_reader)}", file=sys.stderr)
        if all_rows_from_reader:
            debug['first_row_keys'] = list(all_rows_from_reader[0].keys())
            debug['first_row_values'] = list(all_rows_from_reader[0].values())
            debug['first_row_dict'] = {k: v for k, v in all_rows_from_reader[0].items()}
            print(f"first_row_dict: {all_rows_from_reader[0]}", file=sys.stderr)
        debug['has_nom_key_in_first_row'] = all_rows_from_reader and 'nom' in all_rows_from_reader[0]
        print(f"has_nom_key_in_first_row: {debug['has_nom_key_in_first_row']}", file=sys.stderr)

        # If the first peek shows the single combined column problem even after repair,
        # try manual header splitting
        if all_rows_from_reader and not debug.get('has_nom_key_in_first_row'):
            first_row_keys = list(all_rows_from_reader[0].keys())
            if len(first_row_keys) == 1 and ',' in list(all_rows_from_reader[0].values())[0]:
                print("CRITICAL: DictReader produced single-column rows despite comma delimiter", file=sys.stderr)
                # Try splitting manually
                lines = decoded.strip().splitlines()
                if len(lines) >= 2:
                    manual_headers = [h.strip() for h in lines[0].split(',')]
                    manual_values = [v.strip() for v in lines[1].split(',')]
                    manual_row = dict(zip(manual_headers, manual_values))
                    debug['manual_headers'] = manual_headers
                    debug['manual_row'] = manual_row
                    print(f"manual_headers: {manual_headers}", file=sys.stderr)
                    print(f"manual_row: {manual_row}", file=sys.stderr)

        # Rebuild iterator
        reader = csv.DictReader(io.StringIO(decoded), delimiter=delimiter)

        valid_rows = []
        invalid_rows = []
        total = 0
        warnings = []
        duplicates_found = []

        existing_dossiers = set(Patient.objects.values_list('numero_dossier', flat=True))
        existing_nss = set(Patient.objects.values_list('N_securite_sociale', flat=True))
        existing_cni = set(Patient.objects.values_list('N_carte_nationale', flat=True))

        seen_dossiers = set()

        for row_num, row in enumerate(reader, start=2):
            total += 1
            cleaned = normalize_row(row)
            print(f"ROW {row_num}: raw keys={list(row.keys())}", file=sys.stderr)
            print(f"ROW {row_num}: cleaned keys={list(cleaned.keys())}", file=sys.stderr)
            print(f"ROW {row_num}: cleaned nom={cleaned.get('nom', 'NOT_FOUND')!r}", file=sys.stderr)
            print(f"ROW {row_num}: cleaned prenom={cleaned.get('prenom', 'NOT_FOUND')!r}", file=sys.stderr)
            print(f"ROW {row_num}: cleaned date_naissance={cleaned.get('date_naissance', 'NOT_FOUND')!r}", file=sys.stderr)
            errors = []

            numero_dossier = cleaned.get('numero_dossier', '')
            if not numero_dossier:
                errors.append('numero_dossier est obligatoire.')
            else:
                if numero_dossier in seen_dossiers:
                    errors.append(f'Numéro dossier dupliqué dans le fichier (ligne {row_num}).')
                seen_dossiers.add(numero_dossier)
                if numero_dossier in existing_dossiers:
                    errors.append(f'Numéro dossier existe déjà dans la base: {numero_dossier}')
                    duplicates_found.append({'row': row_num, 'field': 'numero_dossier', 'value': numero_dossier})

            if not cleaned.get('nom', ''):
                print(f"VALIDATION FAIL: nom is empty/missing. cleaned keys={list(cleaned.keys())}", file=sys.stderr)
                errors.append('nom est obligatoire.')
            if not cleaned.get('prenom', ''):
                print(f"VALIDATION FAIL: prenom is empty/missing", file=sys.stderr)
                errors.append('prenom est obligatoire.')

            date_naissance = cleaned.get('date_naissance')
            if not date_naissance or not isinstance(date_naissance, date):
                errors.append('date_naissance est obligatoire.')

            if cleaned.get('sexe', '') not in ('M', 'F', ''):
                errors.append(f"sexe doit être 'M' ou 'F' (reçu: '{cleaned['sexe']}').")

            if cleaned.get('email', '') and '@' not in cleaned['email']:
                errors.append(f"email invalide: '{cleaned['email']}'.")

            nss = cleaned.get('N_securite_sociale', '')
            if nss and nss in existing_nss:
                warnings.append(f'Ligne {row_num}: N° sécurité sociale déjà existant: {nss}')

            cni = cleaned.get('N_carte_nationale', '')
            if cni and cni in existing_cni:
                warnings.append(f'Ligne {row_num}: N° carte nationale déjà existant: {cni}')

            if errors:
                print(f"ROW {row_num} INVALID: {errors}", file=sys.stderr)
                invalid_rows.append({'row': row_num, 'data': cleaned, 'errors': errors})
            else:
                print(f"ROW {row_num} VALID ✓", file=sys.stderr)
                valid_rows.append({'row': row_num, 'data': cleaned})

        debug['valid_row_count'] = len(valid_rows)
        debug['invalid_row_count'] = len(invalid_rows)
        if invalid_rows:
            debug['first_invalid_row'] = invalid_rows[0]

        print(f"VALID: {len(valid_rows)}, INVALID: {len(invalid_rows)}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        return Response({
            'total': total,
            'valid_count': len(valid_rows),
            'invalid_count': len(invalid_rows),
            'valid_rows': valid_rows,
            'invalid_rows': invalid_rows,
            'warnings': list(set(warnings)),
            'duplicates_found': duplicates_found,
            'column_headers': IMPORT_FIELDS,
            'unrecognized_columns': [f for f in cleaned_fieldnames if f not in IMPORT_FIELDS],
            '_debug': debug,
        })

    @action(detail=False, methods=['post'])
    def execute(self, request):
        import sys
        rows = request.data.get('rows')
        if not rows or not isinstance(rows, list):
            return Response({'error': 'Données invalides.'}, status=status.HTTP_400_BAD_REQUEST)

        print("=" * 60, file=sys.stderr)
        print(f"EXECUTE: received {len(rows)} rows", file=sys.stderr)
        if rows:
            print(f"EXECUTE: first row data = {rows[0].get('data', {})}", file=sys.stderr)

        imported = 0
        errors = []
        skip_duplicates = request.data.get('skip_duplicates', True)

        with transaction.atomic():
            for item in rows:
                data = item.get('data', {})
                row_num = item.get('row', '?')

                numero_dossier = data.get('numero_dossier', '')
                if skip_duplicates and Patient.objects.filter(numero_dossier=numero_dossier).exists():
                    errors.append({'row': row_num, 'numero_dossier': numero_dossier, 'error': 'Doublon ignoré'})
                    continue

                try:
                    serializer = PatientSerializer(data=data)
                    if serializer.is_valid():
                        serializer.save()
                        imported += 1
                    else:
                        field_errors = []
                        for field, msgs in serializer.errors.items():
                            field_errors.append(f"{field}: {', '.join(msgs)}")
                        error_msg = '; '.join(field_errors)
                        errors.append({'row': row_num, 'numero_dossier': numero_dossier, 'error': error_msg})
                except Exception as e:
                    errors.append({'row': row_num, 'numero_dossier': numero_dossier, 'error': str(e)})

        return Response({
            'imported': imported,
            'errors': errors,
            'total': len(rows),
        })

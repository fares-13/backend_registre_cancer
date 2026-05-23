from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.db.models import Count, Q, Max, OuterRef, Subquery
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone
from datetime import timedelta

from .models import CancerCase, Patient, FollowUp, CancerTreatment, Imaging, Analysis, Anapath, MolecularMarker
from accounts.permissions import IsAdmin, IsEpidemiologiste


class StatisticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        return [permissions.IsAuthenticated(), (IsAdmin | IsEpidemiologiste)()]

    def _parse_filters(self, request):
        self._date_from = request.query_params.get('date_from')
        self._date_to = request.query_params.get('date_to')
        self._cancer_type = request.query_params.get('cancer_type')
        self._sexe = request.query_params.get('sexe')
        self._etat = request.query_params.get('etat')
        self._age_min = request.query_params.get('age_min')
        self._age_max = request.query_params.get('age_max')
        self._stage_filter = request.query_params.get('stage')

    def _base_cases(self):
        qs = CancerCase.objects.all()
        if self._date_from:
            qs = qs.filter(date_diagnostic__gte=self._date_from)
        if self._date_to:
            qs = qs.filter(date_diagnostic__lte=self._date_to)
        if self._cancer_type:
            qs = qs.filter(cancer_type_id=self._cancer_type)
        if self._sexe:
            qs = qs.filter(patient__sexe=self._sexe)
        if self._etat:
            qs = qs.filter(etat=self._etat)
        return qs

    def _filtered_patient_ids(self, cases_qs):
        patient_ids = list(cases_qs.values_list('patient_id', flat=True).distinct())
        if not (self._age_min or self._age_max):
            return patient_ids
        age_min = int(self._age_min) if self._age_min else 0
        age_max = int(self._age_max) if self._age_max else 999
        patients_meta = {p.id_malade: p.date_naissance for p in Patient.objects.filter(id_malade__in=patient_ids).only('id_malade', 'date_naissance')}
        filtered = set()
        for case in cases_qs.filter(patient_id__in=patient_ids).only('patient_id', 'date_diagnostic'):
            dob = patients_meta.get(case.patient_id)
            if not dob or not case.date_diagnostic:
                continue
            age = case.date_diagnostic.year - dob.year
            if (case.date_diagnostic.month, case.date_diagnostic.day) < (dob.month, dob.day):
                age -= 1
            if age_min <= age <= age_max:
                filtered.add(case.patient_id)
        return list(filtered)

    def _filter_by_stage(self, cases_qs):
        if not self._stage_filter:
            return cases_qs
        target = self._stage_filter.lower()
        ids = []
        for c in cases_qs.only('id_cancer', 'dynamic_attributes'):
            attrs = c.dynamic_attributes or {}
            stage = attrs.get('classification_stade') or attrs.get('stade') or attrs.get('stage') or ''
            if str(stage).lower() == target:
                ids.append(c.id_cancer)
        return cases_qs.filter(id_cancer__in=ids)

    def _age_distribution(self, cases_qs, patient_ids):
        patients_map = {p.id_malade: p.date_naissance for p in Patient.objects.filter(id_malade__in=patient_ids).only('id_malade', 'date_naissance')}
        groups = {'0-19': 0, '20-29': 0, '30-39': 0, '40-49': 0, '50-59': 0, '60-69': 0, '70+': 0}
        ages = []
        for case in cases_qs.filter(patient_id__in=patient_ids).only('patient_id', 'date_diagnostic'):
            dob = patients_map.get(case.patient_id)
            if not dob or not case.date_diagnostic:
                continue
            age = case.date_diagnostic.year - dob.year
            if (case.date_diagnostic.month, case.date_diagnostic.day) < (dob.month, dob.day):
                age -= 1
            ages.append(age)
            if age < 20: groups['0-19'] += 1
            elif age < 30: groups['20-29'] += 1
            elif age < 40: groups['30-39'] += 1
            elif age < 50: groups['40-49'] += 1
            elif age < 60: groups['50-59'] += 1
            elif age < 70: groups['60-69'] += 1
            else: groups['70+'] += 1
        avg_age = round(sum(ages) / max(len(ages), 1), 1) if ages else None
        return avg_age, groups

    # ─── ENDPOINTS ──────────────────────────────────────

    @action(detail=False, methods=['get'])
    def kpi(self, request):
        self._parse_filters(request)
        cases = self._filter_by_stage(self._base_cases())
        patient_ids = self._filtered_patient_ids(cases)

        now = timezone.now()
        today = now.date()

        total_patients = len(patient_ids)
        total_cases = cases.count()

        cases_this_month = cases.filter(date_diagnostic__year=now.year, date_diagnostic__month=now.month).count()
        cases_today = cases.filter(date_diagnostic=today).count()
        active_cases = cases.filter(~Q(etat__in=['termine', 'clos', 'archive'])).count()

        deceased = Patient.objects.filter(id_malade__in=patient_ids, deces=True).count()
        mortality_rate = round((deceased / max(total_patients, 1)) * 100, 1)
        survival_rate = round(((total_patients - deceased) / max(total_patients, 1)) * 100, 1)

        recurrence = Patient.objects.filter(id_malade__in=patient_ids, nb_fois_cancer__gt=1).count()
        recurrence_rate = round((recurrence / max(total_patients, 1)) * 100, 1)

        active_followups = FollowUp.objects.filter(cancer_case__in=cases, next_visit_date__gte=today).values('cancer_case').distinct().count()

        six_months_ago = today - timedelta(days=180)
        last_visits = FollowUp.objects.filter(cancer_case__in=cases).values('cancer_case').annotate(last_visit=models.Max('visit_date'))
        lost_followup = last_visits.filter(last_visit__lt=six_months_ago).count()

        sex_dist = Patient.objects.filter(id_malade__in=patient_ids).values('sexe').annotate(count=Count('id_malade'))
        sex_map = {'M': 'Masculin', 'F': 'Féminin'}
        sex_distribution = {sex_map.get(s['sexe'], s['sexe'] or 'Non précisé'): s['count'] for s in sex_dist}
        total_male = sex_distribution.get('Masculin', 0)
        total_female = sex_distribution.get('Féminin', 0)

        avg_age, age_groups = self._age_distribution(cases, patient_ids)
        pediatric_count = sum(v for k, v in age_groups.items() if int(k.split('-')[0]) < 18)
        adult_count = total_patients - pediatric_count

        # Stage distribution
        stage_dist = {}
        for c in cases.only('id_cancer', 'dynamic_attributes'):
            attrs = c.dynamic_attributes or {}
            stage = attrs.get('classification_stade') or attrs.get('stade') or attrs.get('stage') or 'Non classé'
            stage_dist[str(stage)] = stage_dist.get(str(stage), 0) + 1
        stage_distribution = [{'name': k, 'count': v} for k, v in sorted(stage_dist.items(), key=lambda x: -x[1])]

        return Response({
            'total_patients': total_patients,
            'total_cases': total_cases,
            'cases_this_month': cases_this_month,
            'cases_today': cases_today,
            'active_cases': active_cases,
            'deceased': deceased,
            'mortality_rate': mortality_rate,
            'survival_rate': survival_rate,
            'recurrence': recurrence,
            'recurrence_rate': recurrence_rate,
            'active_followups': active_followups,
            'lost_followup': lost_followup,
            'sex_distribution': sex_distribution,
            'total_male': total_male,
            'total_female': total_female,
            'avg_age': avg_age,
            'age_groups': [{'name': k, 'count': v} for k, v in age_groups.items()],
            'pediatric_count': pediatric_count,
            'adult_count': adult_count,
            'stage_distribution': stage_distribution,
        })

    @action(detail=False, methods=['get'])
    def temporal(self, request):
        self._parse_filters(request)
        cases = self._filter_by_stage(self._base_cases())

        monthly = cases.annotate(month=TruncMonth('date_diagnostic')).values('month').annotate(count=Count('id_cancer')).order_by('month')
        yearly = cases.annotate(year=TruncYear('date_diagnostic')).values('year').annotate(count=Count('id_cancer')).order_by('year')

        deceased_ids = Patient.objects.filter(deces=True).values_list('id_malade', flat=True)
        mortality_monthly = cases.filter(patient_id__in=deceased_ids).annotate(month=TruncMonth('date_diagnostic')).values('month').annotate(count=Count('id_cancer')).order_by('month')

        return Response({
            'monthly': [{'month': str(m['month']), 'count': m['count']} for m in monthly if m['month']],
            'yearly': [{'year': y['year'].year if hasattr(y['year'], 'year') else y['year'], 'count': y['count']} for y in yearly if y['year']],
            'mortality_monthly': [{'month': str(m['month']), 'count': m['count']} for m in mortality_monthly if m['month']],
        })

    @action(detail=False, methods=['get'])
    def cancer_distribution(self, request):
        self._parse_filters(request)
        cases = self._filter_by_stage(self._base_cases())

        by_type = cases.values('cancer_type__nom').annotate(count=Count('id_cancer')).order_by('-count')
        by_sex = cases.values('patient__sexe').annotate(count=Count('id_cancer'))
        by_type_sex = cases.values('cancer_type__nom', 'patient__sexe').annotate(count=Count('id_cancer')).order_by('cancer_type__nom')

        patient_ids = self._filtered_patient_ids(cases)
        _, age_groups = self._age_distribution(cases, patient_ids)

        sex_map = {'M': 'Masculin', 'F': 'Féminin', None: 'Non précisé'}

        return Response({
            'by_type': [{'name': t['cancer_type__nom'] or 'Non spécifié', 'count': t['count']} for t in by_type],
            'by_sex': [{'name': sex_map.get(s['patient__sexe'], 'Non précisé'), 'count': s['count']} for s in by_sex],
            'by_type_sex': [{'cancer_type': t['cancer_type__nom'] or 'Non spécifié', 'sexe': sex_map.get(t['patient__sexe'], 'Non précisé'), 'count': t['count']} for t in by_type_sex],
            'by_age_group': [{'name': k, 'count': v} for k, v in age_groups.items()],
        })

    @action(detail=False, methods=['get'])
    def treatment(self, request):
        self._parse_filters(request)
        cases = self._filter_by_stage(self._base_cases())
        treatments = CancerTreatment.objects.filter(cancer_case__in=cases)

        by_type = treatments.values('type_traitement').annotate(count=Count('id_traitement')).order_by('-count')
        total = treatments.count()

        return Response({
            'by_type': [{'name': t['type_traitement'], 'count': t['count']} for t in by_type],
            'total_treatments': total,
            'cases_with_treatment': treatments.values('cancer_case').distinct().count(),
            'cases_without_treatment': cases.exclude(id_cancer__in=treatments.values('cancer_case')).count(),
        })

    @action(detail=False, methods=['get'])
    def followup(self, request):
        self._parse_filters(request)
        cases = self._filter_by_stage(self._base_cases())
        today = timezone.now().date()

        followups = FollowUp.objects.filter(cancer_case__in=cases)
        by_visit_type = followups.values('visit_type').annotate(count=Count('id_followup')).order_by('-count')

        active = followups.filter(next_visit_date__gte=today).values('cancer_case').distinct().count()
        overdue = followups.filter(next_visit_date__lt=today, next_visit_date__isnull=False).values('cancer_case').distinct().count()

        six_months_ago = today - timedelta(days=180)
        last_visits = followups.values('cancer_case').annotate(last_visit=models.Max('visit_date'))
        lost = last_visits.filter(last_visit__lt=six_months_ago).count()

        return Response({
            'by_visit_type': [{'name': v['visit_type'], 'count': v['count']} for v in by_visit_type],
            'total_followups': followups.count(),
            'active_followups': active,
            'overdue_followups': overdue,
            'lost_to_followup': lost,
            'cases_with_followup': followups.values('cancer_case').distinct().count(),
            'cases_without_followup': cases.exclude(id_cancer__in=followups.values('cancer_case')).count(),
        })

    @action(detail=False, methods=['get'])
    def recent_mortality(self, request):
        self._parse_filters(request)
        cases = self._filter_by_stage(self._base_cases())
        patient_ids = self._filtered_patient_ids(cases)

        deceased = Patient.objects.filter(
            id_malade__in=patient_ids, deces=True
        ).exclude(date_deces__isnull=True).order_by('-date_deces')[:15]

        results = []
        for p in deceased:
            cancer_types = CancerCase.objects.filter(patient=p).values_list('cancer_type__nom', flat=True).distinct()
            results.append({
                'patient_id': str(p.id_malade),
                'nom': p.nom,
                'prenom': p.prenom,
                'sexe': p.sexe,
                'date_naissance': str(p.date_naissance) if p.date_naissance else None,
                'date_deces': str(p.date_deces) if p.date_deces else None,
                'cause': p.cause or 'Non spécifiée',
                'cancer_types': [ct for ct in cancer_types if ct],
            })

        return Response({
            'count': len(results),
            'results': results,
        })

    @action(detail=False, methods=['get'])
    def overdue_followups_detail(self, request):
        self._parse_filters(request)
        cases = self._filter_by_stage(self._base_cases())
        today = timezone.now().date()

        overdue_qs = FollowUp.objects.filter(
            cancer_case__in=cases,
            next_visit_date__lt=today,
            next_visit_date__isnull=False,
        ).select_related('cancer_case__patient', 'cancer_case__cancer_type').order_by('next_visit_date')[:20]

        results = []
        for f in overdue_qs:
            results.append({
                'followup_id': str(f.id_followup),
                'patient_nom': f.cancer_case.patient.nom,
                'patient_prenom': f.cancer_case.patient.prenom,
                'cancer_type': str(f.cancer_case.cancer_type.nom) if f.cancer_case.cancer_type else 'N/A',
                'visit_date': str(f.visit_date) if f.visit_date else None,
                'next_visit_date': str(f.next_visit_date) if f.next_visit_date else None,
                'visit_type': f.visit_type,
                'days_overdue': (today - f.next_visit_date).days if f.next_visit_date else 0,
            })

        return Response({
            'count': len(results),
            'results': results,
        })

    @action(detail=False, methods=['get'])
    def missing_documents_detail(self, request):
        self._parse_filters(request)
        cases = self._filter_by_stage(self._base_cases())

        case_ids = set(cases.values_list('id_cancer', flat=True))
        cases_with_imaging = set(Imaging.objects.filter(cancer_case_id__in=case_ids).values_list('cancer_case', flat=True))
        cases_with_analysis = set(Analysis.objects.filter(cancer_case_id__in=case_ids).values_list('cancer_case', flat=True))
        cases_with_anapath = set(Anapath.objects.filter(cancer_case_id__in=case_ids).values_list('cancer_case', flat=True))
        cases_with_molecular = set(MolecularMarker.objects.filter(cancer_case_id__in=case_ids).values_list('cancer_case', flat=True))

        missing_imaging = case_ids - cases_with_imaging
        missing_analysis = case_ids - cases_with_analysis
        missing_anapath = case_ids - cases_with_anapath
        missing_molecular = case_ids - cases_with_molecular

        all_missing_ids = missing_imaging | missing_analysis | missing_anapath | missing_molecular
        missing_cases = CancerCase.objects.filter(id_cancer__in=all_missing_ids).select_related('patient', 'cancer_type')[:20]

        results = []
        for c in missing_cases:
            missing_types = []
            if c.id_cancer in missing_imaging: missing_types.append('Imagerie')
            if c.id_cancer in missing_analysis: missing_types.append('Analyse')
            if c.id_cancer in missing_anapath: missing_types.append('Anapath')
            if c.id_cancer in missing_molecular: missing_types.append('Moléculaire')
            results.append({
                'case_id': str(c.id_cancer),
                'patient_nom': c.patient.nom,
                'patient_prenom': c.patient.prenom,
                'sexe': c.patient.sexe,
                'cancer_type': str(c.cancer_type.nom) if c.cancer_type else 'N/A',
                'date_diagnostic': str(c.date_diagnostic) if c.date_diagnostic else None,
                'missing_documents': missing_types,
                'missing_count': len(missing_types),
            })

        return Response({
            'count': len(all_missing_ids),
            'sample_count': len(results),
            'results': results,
        })

    @action(detail=False, methods=['get'])
    def geographic(self, request):
        self._parse_filters(request)
        cases = self._filter_by_stage(self._base_cases())
        patient_ids = self._filtered_patient_ids(cases)

        patients = Patient.objects.filter(id_malade__in=patient_ids)

        with_coords = patients.exclude(latitude__isnull=True).exclude(longitude__isnull=True).count()
        without_coords = patients.filter(latitude__isnull=True).count()

        return Response({
            'with_coordinates': with_coords,
            'without_coordinates': without_coords,
            'total_patients_geo': patients.count(),
            'coverage_rate': round((with_coords / max(patients.count(), 1)) * 100, 1),
        })

    @action(detail=False, methods=['get'])
    def documents(self, request):
        self._parse_filters(request)
        cases = self._filter_by_stage(self._base_cases())

        case_ids = cases.values_list('id_cancer', flat=True)

        total_cases = cases.count()
        total_imaging = Imaging.objects.filter(cancer_case_id__in=case_ids).count()
        total_analyses = Analysis.objects.filter(cancer_case_id__in=case_ids).count()
        total_anapath = Anapath.objects.filter(cancer_case_id__in=case_ids).count()
        total_molecular = MolecularMarker.objects.filter(cancer_case_id__in=case_ids).count()

        imaging_with_doc = Imaging.objects.filter(cancer_case_id__in=case_ids).exclude(document='').count()
        analyses_with_doc = Analysis.objects.filter(cancer_case_id__in=case_ids).exclude(document='').count()

        cases_with_imaging = Imaging.objects.filter(cancer_case_id__in=case_ids).values('cancer_case').distinct().count()
        cases_with_analysis = Analysis.objects.filter(cancer_case_id__in=case_ids).values('cancer_case').distinct().count()
        cases_with_anapath = Anapath.objects.filter(cancer_case_id__in=case_ids).values('cancer_case').distinct().count()
        cases_with_molecular = MolecularMarker.objects.filter(cancer_case_id__in=case_ids).values('cancer_case').distinct().count()

        return Response({
            'total_cases': total_cases,
            'total_imaging': total_imaging,
            'imaging_with_document': imaging_with_doc,
            'total_analyses': total_analyses,
            'analyses_with_document': analyses_with_doc,
            'total_anapath': total_anapath,
            'total_molecular': total_molecular,
            'cases_with_imaging': cases_with_imaging,
            'cases_with_analysis': cases_with_analysis,
            'cases_with_anapath': cases_with_anapath,
            'cases_with_molecular': cases_with_molecular,
            'cases_without_imaging': total_cases - cases_with_imaging,
            'cases_without_analysis': total_cases - cases_with_analysis,
            'cases_without_anapath': total_cases - cases_with_anapath,
            'cases_without_molecular': total_cases - cases_with_molecular,
        })

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Q
import uuid

from .models import RcpSession, RcpParticipant, RcpCase, RcpDecision, RcpProtocol, RcpTemplate, RcpMessage, RcpNotification
from .serializers import (
    RcpSessionSerializer, RcpParticipantSerializer, RcpParticipantCreateSerializer,
    RcpCaseSerializer, RcpCaseCreateSerializer,
    RcpDecisionSerializer, RcpProtocolSerializer, RcpTemplateSerializer,
    RcpMessageSerializer, RcpMessageCreateSerializer, RcpNotificationSerializer
)
from accounts.models import Utilisateur
from patients.models import Patient


class IsRcpParticipant(permissions.BasePermission):
    """Only RCP participants (or all doctors if isAllDoctors=True) can access.
    Admin bypass: admin can access all sessions."""
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'ADMIN':
            return True
        if isinstance(obj, RcpSession):
            rcp = obj
        elif hasattr(obj, 'rcp'):
            rcp = obj.rcp
        else:
            return True
        if rcp.isAllDoctors and request.user.role == 'MEDECIN':
            return True
        return RcpParticipant.objects.filter(rcp=rcp, user=request.user).exists()

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class RcpSessionViewSet(viewsets.ModelViewSet):
    queryset = RcpSession.objects.all()
    serializer_class = RcpSessionSerializer
    permission_classes = [IsRcpParticipant]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'ADMIN':
            return qs
        return qs.filter(
            Q(isAllDoctors=True) |
            Q(participants__user=user)
        ).distinct()

    def perform_create(self, serializer):
        if 'id' not in self.request.data:
            new_id = f"RCP-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
            session = serializer.save(id=new_id, coordinator=self.request.user)
        else:
            session = serializer.save(coordinator=self.request.user)
        RcpParticipant.objects.get_or_create(
            rcp=session,
            user=self.request.user,
            defaults={'role': 'coordinator', 'isRequired': True, 'status': 'confirmed'}
        )

    def perform_update(self, serializer):
        session = serializer.save()
        if session.status == 'completed':
            RcpNotification.objects.create(
                rcp=session,
                recipient=session.coordinator,
                notification_type='status_changed',
                title=f'Session terminée: {session.title}',
                message='La session RCP a été marquée comme terminée.'
            )

    @action(detail=True, methods=['patch'])
    def status(self, request, pk=None):
        session = self.get_object()
        new_status = request.data.get('status')
        if new_status:
            old_status = session.status
            session.status = new_status
            session.save()
            if new_status != old_status:
                for p in session.participants.select_related('user'):
                    RcpNotification.objects.create(
                        rcp=session,
                        recipient=p.user,
                        notification_type='status_changed',
                        title=f'Statut modifié: {session.title}',
                        message=f'Statut passé de {old_status} à {new_status}'
                    )
            return Response(self.get_serializer(session).data)
        return Response({'error': 'status required'}, status=status.HTTP_400_BAD_REQUEST)


class RcpParticipantViewSet(viewsets.ModelViewSet):
    queryset = RcpParticipant.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return RcpParticipantCreateSerializer
        return RcpParticipantSerializer

    def get_queryset(self):
        rcp_id = self.request.query_params.get('rcpId')
        if rcp_id:
            return self.queryset.filter(rcp_id=rcp_id).select_related('user', 'rcp')
        return self.queryset.select_related('user', 'rcp')

    def perform_create(self, serializer):
        participant = serializer.save()
        RcpNotification.objects.create(
            rcp=participant.rcp,
            recipient=participant.user,
            notification_type='participant_added',
            title=f'Ajouté à {participant.rcp.title}',
            message=f'Vous avez été ajouté comme participant à la session RCP {participant.rcp.title}'
        )

    @action(detail=False, methods=['post'])
    def add_all_doctors(self, request):
        rcp_id = request.data.get('rcpId')
        role = request.data.get('role', 'member')
        is_required = request.data.get('isRequired', False)

        try:
            rcp = RcpSession.objects.get(id=rcp_id)
        except RcpSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        doctors = Utilisateur.objects.filter(role='MEDECIN')
        added = 0
        for doctor in doctors:
            _, created = RcpParticipant.objects.get_or_create(
                rcp=rcp,
                user=doctor,
                defaults={'role': role, 'isRequired': is_required}
            )
            if created:
                added += 1
                RcpNotification.objects.create(
                    rcp=rcp,
                    recipient=doctor,
                    notification_type='participant_added',
                    title=f'Ajouté à {rcp.title}',
                    message=f'Vous avez été ajouté comme participant à la session RCP {rcp.title}'
                )

        return Response({'added': added})

    @action(detail=True, methods=['patch'])
    def status(self, request, pk=None):
        participant = self.get_object()
        new_status = request.data.get('status')
        if new_status:
            participant.status = new_status
            participant.respondedAt = timezone.now()
            participant.save()
            return Response(self.get_serializer(participant).data)
        return Response({'error': 'status required'}, status=status.HTTP_400_BAD_REQUEST)


class RcpCaseViewSet(viewsets.ModelViewSet):
    queryset = RcpCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return RcpCaseCreateSerializer
        return RcpCaseSerializer

    def get_queryset(self):
        rcp_id = self.request.query_params.get('rcpId')
        if rcp_id:
            return self.queryset.filter(rcp_id=rcp_id).select_related(
                'cancer_case', 'cancer_case__patient', 'cancer_case__cancer_type'
            )
        return self.queryset.select_related(
            'cancer_case', 'cancer_case__patient', 'cancer_case__cancer_type'
        )

    def perform_create(self, serializer):
        serializer.save(presenter=self.request.user)

    @action(detail=True, methods=['patch'])
    def status(self, request, pk=None):
        case = self.get_object()
        new_status = request.data.get('status')
        if new_status:
            case.status = new_status
            case.save()
            return Response(self.get_serializer(case).data)
        return Response({'error': 'status required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['patch'])
    def reorder(self, request):
        ordered_ids = request.data.get('orderedIds', [])
        for index, case_id in enumerate(ordered_ids):
            RcpCase.objects.filter(id=case_id).update(order=index + 1)
        return Response({'status': 'reordered'})


class RcpDecisionViewSet(viewsets.ModelViewSet):
    queryset = RcpDecision.objects.all()
    serializer_class = RcpDecisionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        rcp_id = self.request.query_params.get('rcpId')
        if rcp_id:
            return self.queryset.filter(rcp_id=rcp_id)
        return self.queryset

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        decision = self.get_object()
        decision.status = 'validated'
        decision.validatedBy = request.user
        decision.validatedAt = timezone.now()
        decision.save()
        return Response(self.get_serializer(decision).data)


class RcpProtocolViewSet(viewsets.ModelViewSet):
    queryset = RcpProtocol.objects.all()
    serializer_class = RcpProtocolSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        rcp_id = self.request.query_params.get('rcpId')
        if rcp_id:
            return self.queryset.filter(rcp_id=rcp_id)
        return self.queryset

    @action(detail=False, methods=['post'])
    def generate(self, request):
        rcp_id = request.data.get('rcpId')
        template_id = request.data.get('templateId')

        try:
            rcp = RcpSession.objects.get(id=rcp_id)
        except RcpSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        participants_list = []
        for p in rcp.participants.select_related('user').all():
            parts = p.user.get_full_name()
            if hasattr(p.user, 'profile_medecin') and p.user.profile_medecin:
                parts += f" ({p.user.profile_medecin.specialite})"
            participants_list.append(f"- {parts} ({p.get_role_display()})")

        cases_list = []
        for c in rcp.cases.select_related('cancer_case__patient', 'cancer_case__cancer_type').all():
            cases_list.append(
                f"- {c.cancer_case.patient.nom} {c.cancer_case.patient.prenom}: "
                f"{c.cancer_case.cancer_type.nom if c.cancer_case.cancer_type else 'Non spécifié'}, "
                f"Stade {c.cancer_case.niveau or 'N/D'}"
            )

        decisions_list = []
        for d in rcp.decisions.all():
            decisions_list.append(f"- {d.decision}")

        content = f"""RÉUNION DE CONCERTATION PLURIDISCIPLINAIRE
{'=' * 60}
Titre: {rcp.title}
Date: {rcp.date.strftime('%d/%m/%Y') if rcp.date else 'N/D'} à {rcp.time.strftime('%H:%M') if rcp.time else 'N/D'}
Durée: {rcp.duration or 'N/D'} minutes
Service: {rcp.service or 'N/D'}
Coordinateur: {rcp.coordinator.get_full_name() if rcp.coordinator else 'N/D'}
Statut: {rcp.get_status_display()}

PARTICIPANTS
{'-' * 60}
{'Aucun participant' if not participants_list else chr(10).join(participants_list)}

CAS DISCUTÉS
{'-' * 60}
{'Aucun cas discuté' if not cases_list else chr(10).join(cases_list)}

DÉCISIONS
{'-' * 60}
{'Aucune décision enregistrée' if not decisions_list else chr(10).join(decisions_list)}

{'-' * 60}
Document généré automatiquement le {timezone.now().strftime('%d/%m/%Y à %H:%M')}
"""

        protocol, created = RcpProtocol.objects.get_or_create(
            rcp=rcp,
            defaults={
                'title': f'Compte-rendu {rcp.title}',
                'content': content,
                'generatedBy': request.user
            }
        )
        if not created:
            protocol.content = content
            protocol.generatedBy = request.user
            protocol.save(update_fields=['content', 'generatedBy'])

        RcpNotification.objects.create(
            rcp=rcp,
            recipient=rcp.coordinator,
            notification_type='report_generated',
            title=f'Compte-rendu généré: {rcp.title}',
            message='Le compte-rendu a été généré avec succès.'
        )

        return Response(self.get_serializer(protocol).data)

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        protocol = self.get_object()
        protocol.status = 'signed'
        protocol.signedBy = request.user
        protocol.signedAt = timezone.now()
        protocol.save()

        RcpNotification.objects.create(
            rcp=protocol.rcp,
            recipient=protocol.rcp.coordinator,
            notification_type='report_signed',
            title=f'Compte-rendu signé: {protocol.rcp.title}',
            message=f'Le compte-rendu a été signé par {request.user.get_full_name()}.'
        )

        return Response(self.get_serializer(protocol).data)


class RcpTemplateViewSet(viewsets.ModelViewSet):
    queryset = RcpTemplate.objects.all()
    serializer_class = RcpTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        if 'id' not in self.request.data:
            new_id = f"TPL-{uuid.uuid4().hex[:8].upper()}"
            serializer.save(id=new_id, createdBy=self.request.user)
        else:
            serializer.save(createdBy=self.request.user)


class RcpMessageViewSet(viewsets.ModelViewSet):
    queryset = RcpMessage.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return RcpMessageCreateSerializer
        return RcpMessageSerializer

    def get_queryset(self):
        rcp_id = self.request.query_params.get('rcpId')
        rcp_case_id = self.request.query_params.get('rcpCaseId')
        queryset = self.queryset.select_related('sender')
        if rcp_id:
            queryset = queryset.filter(rcp_id=rcp_id)
        if rcp_case_id:
            queryset = queryset.filter(rcp_case_id=rcp_case_id)
        return queryset

    def perform_create(self, serializer):
        msg = serializer.save(sender=self.request.user, readBy=[self.request.user.id])
        recipients = Utilisateur.objects.filter(
            id__in=RcpParticipant.objects.filter(rcp=msg.rcp).values('user_id')
        ).exclude(id=self.request.user.id)
        for recipient in recipients:
            RcpNotification.objects.create(
                rcp=msg.rcp,
                recipient=recipient,
                notification_type='new_message',
                title=f'Nouveau message dans {msg.rcp.title}',
                message=f'{self.request.user.get_full_name()}: {msg.content[:100]}'
            )

    @action(detail=True, methods=['patch'])
    def pin(self, request, pk=None):
        msg = self.get_object()
        msg.isPinned = not msg.isPinned
        msg.save()
        return Response(self.get_serializer(msg).data)

    @action(detail=True, methods=['patch'])
    def react(self, request, pk=None):
        msg = self.get_object()
        emoji = request.data.get('emoji')
        user_id = request.user.id

        reactions = list(msg.reactions)
        found = False
        for r in reactions:
            if r['emoji'] == emoji:
                if user_id in r['userIds']:
                    r['userIds'].remove(user_id)
                    if not r['userIds']:
                        reactions.remove(r)
                else:
                    r['userIds'].append(user_id)
                found = True
                break

        if not found:
            reactions.append({'emoji': emoji, 'userIds': [user_id]})

        msg.reactions = reactions
        msg.save()
        return Response(self.get_serializer(msg).data)


class RcpNotificationViewSet(viewsets.ModelViewSet):
    queryset = RcpNotification.objects.all()
    serializer_class = RcpNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(recipient=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'count': count})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'all marked read'})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.save()
        return Response(self.get_serializer(notif).data)


class DoctorListViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        search = request.query_params.get('search', '').strip()
        doctors = Utilisateur.objects.filter(role='MEDECIN')
        if search:
            doctors = doctors.filter(
                Q(nom__icontains=search) |
                Q(prenom__icontains=search) |
                Q(email__icontains=search)
            )
        results = []
        for d in doctors:
            specialite = ''
            if hasattr(d, 'profile_medecin') and d.profile_medecin:
                specialite = d.profile_medecin.specialite
            results.append({
                'id': d.id,
                'nom': d.nom,
                'prenom': d.prenom,
                'name': d.get_full_name(),
                'email': d.email,
                'specialite': specialite,
            })
        return Response(results)

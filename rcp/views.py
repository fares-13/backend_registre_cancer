from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
import uuid

from .models import RcpSession, RcpParticipant, RcpCase, RcpDecision, RcpProtocol, RcpTemplate, RcpMessage
from .serializers import (
    RcpSessionSerializer, RcpParticipantSerializer, RcpCaseSerializer,
    RcpDecisionSerializer, RcpProtocolSerializer, RcpTemplateSerializer, RcpMessageSerializer
)

class RcpSessionViewSet(viewsets.ModelViewSet):
    queryset = RcpSession.objects.all()
    serializer_class = RcpSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Auto-generate ID if not provided. In real app, might want a specific format like RCP-YYYY-XXX
        if 'id' not in self.request.data:
            new_id = f"RCP-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
            serializer.save(id=new_id, coordinator=self.request.user)
        else:
            serializer.save(coordinator=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("VALIDATION ERRORS:", serializer.errors)
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['patch'])
    def status(self, request, pk=None):
        session = self.get_object()
        new_status = request.data.get('status')
        if new_status:
            session.status = new_status
            session.save()
            return Response(self.get_serializer(session).data)
        return Response({'error': 'status required'}, status=status.HTTP_400_BAD_REQUEST)

class RcpParticipantViewSet(viewsets.ModelViewSet):
    queryset = RcpParticipant.objects.all()
    serializer_class = RcpParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        rcp_id = self.request.query_params.get('rcpId')
        if rcp_id:
            return self.queryset.filter(rcp_id=rcp_id)
        return self.queryset

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
    serializer_class = RcpCaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        rcp_id = self.request.query_params.get('rcpId')
        if rcp_id:
            return self.queryset.filter(rcp_id=rcp_id)
        return self.queryset

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
        rcp = RcpSession.objects.get(id=rcp_id)
        # Mocking the generation logic
        protocol, created = RcpProtocol.objects.get_or_create(
            rcp=rcp,
            defaults={
                'title': f'Compte-rendu {rcp.title}',
                'content': f'RÉUNION DE CONCERTATION PLURIDISCIPLINAIRE\nTemplate ID: {template_id}',
                'generatedBy': request.user
            }
        )
        return Response(self.get_serializer(protocol).data)

    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        protocol = self.get_object()
        protocol.status = 'signed'
        protocol.signedBy = request.user
        protocol.signedAt = timezone.now()
        protocol.save()
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
    serializer_class = RcpMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        rcp_id = self.request.query_params.get('rcpId')
        rcp_case_id = self.request.query_params.get('rcpCaseId')
        queryset = self.queryset
        if rcp_id:
            queryset = queryset.filter(rcp_id=rcp_id)
        if rcp_case_id:
            queryset = queryset.filter(rcp_case_id=rcp_case_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user, readBy=[self.request.user.id])

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
        
        # very simple mock reaction logic
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


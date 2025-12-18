from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from main_app.models import Etudiant
from .parent_serializers import EnfantPedagogiqueSerializer

class ParentPedagogiqueAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        parent = request.user
        enfants = Etudiant.objects.filter(parent=parent)
        data = EnfantPedagogiqueSerializer(enfants, many=True).data
        return Response(data)

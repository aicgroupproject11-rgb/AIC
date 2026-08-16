from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (KISSearchRequestSerializer,KISSearchResponseSerializer,)

from .services import search_kis


class KISSearchView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=KISSearchRequestSerializer,responses={200: KISSearchResponseSerializer,},tags=["KIS"],)
    def post(self, request):

        serializer = KISSearchRequestSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        query = (serializer.validated_data["query"])

        top_k = serializer.validated_data["top_k"]

        try:
            results = search_kis(query=query,top_k=top_k,)

        except (FileNotFoundError, NotImplementedError) as exc:
            return Response({"detail": str(exc)},status=(status.HTTP_503_SERVICE_UNAVAILABLE),)

        response_data = {"query": query,"count": len(results),"results": results,}

        return Response(response_data,status=status.HTTP_200_OK,)

import logging
from pathlib import Path

from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ApiErrorSerializer,
    KisSearchRequestSerializer,
    KisSearchResponseSerializer,
    KisSearchResultSerializer,
    KisVideoUploadRequestSerializer,
    KisVideoUploadResponseSerializer,
)
from .services import SearchServiceFailed, SearchServiceUnavailable, search_kis


logger = logging.getLogger(__name__)


def error_response(
    *,
    code: str,
    message: str,
    http_status: int,
    details: dict | None = None,
) -> Response:

    error: dict = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return Response({"error": error}, status=http_status)


class KisSearchView(APIView):

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["KIS"],
        summary="Search KIS keyframes",
        request=KisSearchRequestSerializer,
        responses={
            200: KisSearchResponseSerializer,
            400: OpenApiResponse(response=ApiErrorSerializer, description="Invalid request"),
            500: OpenApiResponse(response=ApiErrorSerializer, description="Invalid search output"),
            503: OpenApiResponse(response=ApiErrorSerializer, description="Search module unavailable"),
        },
    )
    def post(self, request: Request) -> Response:
        request_serializer = KisSearchRequestSerializer(data=request.data)

        if not request_serializer.is_valid():
            return error_response(
                code="validation_error",
                message="Dữ liệu gửi lên không hợp lệ.",
                details=request_serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = request_serializer.validated_data

        try:
            raw_results = search_kis(
                query=validated_data["query"],
                collection_ids=validated_data["collection_ids"],
                top_k=validated_data["top_k"],
            )
        except SearchServiceUnavailable as exc:
            return error_response(
                code="search_service_unavailable",
                message=str(exc),
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except SearchServiceFailed as exc:
            logger.exception("KIS search service failed")
            return error_response(
                code="search_service_failed",
                message="Module tìm kiếm gặp lỗi khi xử lý truy vấn.",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            # Catch only at the HTTP boundary so internal details are not leaked.
            logger.exception("Unexpected KIS API error")
            return error_response(
                code="internal_error",
                message="Máy chủ gặp lỗi ngoài dự kiến.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        result_serializer = KisSearchResultSerializer(data=raw_results, many=True)
        if not result_serializer.is_valid():
            logger.error("Invalid KIS search output: %s", result_serializer.errors)
            return error_response(
                code="invalid_search_output",
                message="Kết quả từ module tìm kiếm không đúng API contract.",
                details={"fields": result_serializer.errors},
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        results = result_serializer.validated_data[: validated_data["top_k"]]
        response_body = {
            "query": validated_data["query"],
            "filters": {"collection_ids": validated_data["collection_ids"]},
            "count": len(results),
            "results": results,
        }
        return Response(response_body, status=status.HTTP_200_OK)


class KisVideoUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["KIS"],
        summary="Upload multiple videos for KIS processing",
        request=KisVideoUploadRequestSerializer,
        responses={
            201: KisVideoUploadResponseSerializer,
            400: OpenApiResponse(response=ApiErrorSerializer, description="Invalid video upload"),
            500: OpenApiResponse(response=ApiErrorSerializer, description="Could not store videos"),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = KisVideoUploadRequestSerializer(
            data={"videos": request.FILES.getlist("videos")}
        )
        if not serializer.is_valid():
            return error_response(
                code="validation_error",
                message="Danh sách video tải lên không hợp lệ.",
                details=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_videos = []
        saved_paths: list[str] = []

        try:
            for video in serializer.validated_data["videos"]:
                original_name = Path(video.name).name
                safe_name = get_valid_filename(original_name)
                stored_name = default_storage.save(f"kis/videos/{safe_name}", video)
                saved_paths.append(stored_name)
                uploaded_videos.append(
                    {
                        "original_name": original_name,
                        "stored_name": stored_name,
                        "size": video.size,
                        "url": request.build_absolute_uri(default_storage.url(stored_name)),
                    }
                )
        except Exception:
            logger.exception("Could not store uploaded KIS videos")
            for saved_path in saved_paths:
                default_storage.delete(saved_path)
            return error_response(
                code="video_upload_failed",
                message="Máy chủ không thể lưu video.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"count": len(uploaded_videos), "videos": uploaded_videos},
            status=status.HTTP_201_CREATED,
        )

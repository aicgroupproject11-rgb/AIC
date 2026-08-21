import logging
import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.urls import reverse
from django.utils.text import get_valid_filename
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .pipeline import process_fe_command
from .serializers import (
    ApiErrorSerializer,
    KisSearchRequestSerializer,
    KisSearchResponseSerializer,
    KisSearchResultSerializer,
    KisVideoUploadRequestSerializer,
    KisVideoUploadResponseSerializer,
)
from .services import (
    InvalidSearchRequest,
    SearchServiceFailed,
    SearchServiceUnavailable,
)

logger = logging.getLogger(__name__)
ALLOWED_ASSET_FOLDERS = {"keyframes", "videos"}


def error_response(code, message, http_status, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return Response({"error": error}, status=http_status)


def dataset_url(request, relative_path):
    relative_path = relative_path.replace("\\", "/").lstrip("/")
    url = reverse("kis-dataset-asset", kwargs={"asset_path": relative_path})
    return request.build_absolute_uri(url)


def format_search_result(request, raw_result):
    result = dict(raw_result)

    image_path = result.get("image_path")
    video_path = result.get("video_path")
    video_id = result.get("video_id")

    if isinstance(image_path, str):
        image_path = image_path.strip().replace("\\", "/").lstrip("/")
        result["image_path"] = image_path
        result["image_url"] = dataset_url(request, image_path)

    if not isinstance(video_path, str) or not video_path.strip():
        video_path = f"videos/{video_id}.mp4"
    else:
        video_path = video_path.strip().replace("\\", "/").lstrip("/")

    result["video_path"] = video_path
    result["video_url"] = dataset_url(request, video_path)
    result["frame_id"] = result.get("frame_number")

    return result


class KisSearchView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["KIS"],
        summary="Search KIS keyframes",
        request=KisSearchRequestSerializer,
        responses={
            200: KisSearchResponseSerializer,
            400: OpenApiResponse(response=ApiErrorSerializer),
            500: OpenApiResponse(response=ApiErrorSerializer),
            503: OpenApiResponse(response=ApiErrorSerializer),
        },
    )
    def post(self, request):
        serializer = KisSearchRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(
                "validation_error",
                "Dữ liệu gửi lên không hợp lệ.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )

        data = serializer.validated_data

        try:
            parsed_info, raw_results = process_fe_command(
                query=data["query"],
                collection_ids=data["collection_ids"],
                top_k=data["top_k"],
            )
        except InvalidSearchRequest as exc:
            return error_response(
                "invalid_search_request",
                str(exc),
                status.HTTP_400_BAD_REQUEST,
            )
        except SearchServiceUnavailable as exc:
            return error_response(
                "search_service_unavailable",
                str(exc),
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except SearchServiceFailed as exc:
            return error_response(
                "search_service_failed",
                str(exc),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        results = [
            format_search_result(request, result)
            for result in raw_results[: data["top_k"]]
        ]

        result_serializer = KisSearchResultSerializer(data=results, many=True)
        if not result_serializer.is_valid():
            logger.error("Invalid KIS result: %s", result_serializer.errors)
            return error_response(
                "invalid_search_output",
                "Kết quả từ Search Engine không đúng API contract.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                {"fields": result_serializer.errors},
            )

        return Response(
            {
                "query": data["query"],
                "parsed_keys": parsed_info["keys"],
                "filters": {
                    "collection_ids": parsed_info["effective_collection_ids"]
                },
                "count": len(result_serializer.data),
                "results": result_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class KisDatasetAssetView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, asset_path):
        relative_path = Path(asset_path.replace("\\", "/"))

        if (
            not relative_path.parts
            or ".." in relative_path.parts
            or relative_path.parts[0] not in ALLOWED_ASSET_FOLDERS
        ):
            raise Http404("KIS asset không hợp lệ.")

        data_root = Path(settings.KIS_DATA_ROOT).resolve()
        file_path = (data_root / relative_path).resolve()

        if not file_path.is_relative_to(data_root) or not file_path.is_file():
            raise Http404("KIS asset không tồn tại.")

        content_type, _ = mimetypes.guess_type(file_path.name)
        return FileResponse(
            file_path.open("rb"),
            content_type=content_type or "application/octet-stream",
        )


class KisVideoUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["KIS"],
        summary="Upload KIS videos",
        request=KisVideoUploadRequestSerializer,
        responses={
            201: KisVideoUploadResponseSerializer,
            400: OpenApiResponse(response=ApiErrorSerializer),
            500: OpenApiResponse(response=ApiErrorSerializer),
        },
    )
    def post(self, request):
        serializer = KisVideoUploadRequestSerializer(data={"videos": request.FILES.getlist("videos")})

        if not serializer.is_valid():
            return error_response(
                "validation_error",
                "Video tải lên không hợp lệ.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )

        uploaded = []
        saved_paths = []

        try:
            for video in serializer.validated_data["videos"]:
                original_name = Path(video.name).name
                safe_name = get_valid_filename(original_name)
                stored_name = default_storage.save(
                    f"kis/videos/{safe_name}",
                    video,
                )
                saved_paths.append(stored_name)

                uploaded.append(
                    {
                        "original_name": original_name,
                        "stored_name": stored_name,
                        "size": video.size,
                        "url": request.build_absolute_uri(
                            default_storage.url(stored_name)
                        ),
                    }
                )
        except Exception:
            logger.exception("Could not save KIS videos")
            for path in saved_paths:
                default_storage.delete(path)

            return error_response(
                "video_upload_failed",
                "Máy chủ không thể lưu video.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"count": len(uploaded), "videos": uploaded},
            status=status.HTTP_201_CREATED,
        )

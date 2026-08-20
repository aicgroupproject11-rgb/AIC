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
from .services import (
    SearchServiceFailed,
    SearchServiceUnavailable,
    search_kis,
)


logger = logging.getLogger(__name__)


def _dataset_url(
    request: Request,
    relative_path: str,
) -> str:
    """Chuyển đường dẫn nội bộ thành URL mà Frontend có thể mở."""

    normalized_path = relative_path.replace("\\", "/").lstrip("/")

    return request.build_absolute_uri(
        reverse(
            "kis-dataset-asset",
            kwargs={"asset_path": normalized_path},
        )
    )


def _add_dataset_urls(
    request: Request,
    raw_result,
):
    """Thêm image_url và video_url vào một kết quả Search Engine."""

    if not isinstance(raw_result, dict):
        return raw_result

    result = dict(raw_result)

    image_path = result.get("image_path")
    video_path = result.get("video_path")

    if isinstance(image_path, str):
        result["image_url"] = _dataset_url(
            request,
            image_path,
        )

    if isinstance(video_path, str):
        result["video_url"] = _dataset_url(
            request,
            video_path,
        )

    return result


def error_response(
    *,
    code: str,
    message: str,
    http_status: int,
    details: dict | None = None,
) -> Response:
    """Tạo response lỗi theo cùng một cấu trúc."""

    error: dict = {
        "code": code,
        "message": message,
    }

    if details is not None:
        error["details"] = details

    return Response(
        {"error": error},
        status=http_status,
    )


class KisSearchView(APIView):
    """Nhận truy vấn text và trả các keyframe gần nhất."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["KIS"],
        summary="Search KIS keyframes",
        request=KisSearchRequestSerializer,
        responses={
            200: KisSearchResponseSerializer,
            400: OpenApiResponse(
                response=ApiErrorSerializer,
                description="Invalid request",
            ),
            500: OpenApiResponse(
                response=ApiErrorSerializer,
                description="Invalid search output",
            ),
            503: OpenApiResponse(
                response=ApiErrorSerializer,
                description="Search module unavailable",
            ),
        },
    )
    def post(self, request: Request) -> Response:
        # Bước 1: kiểm tra dữ liệu FE gửi lên.
        request_serializer = KisSearchRequestSerializer(
            data=request.data
        )

        if not request_serializer.is_valid():
            return error_response(
                code="validation_error",
                message="Dữ liệu gửi lên không hợp lệ.",
                details=request_serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = request_serializer.validated_data

        # Bước 2: gọi Search Engine.
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

        except SearchServiceFailed:
            logger.exception("KIS search service failed")

            return error_response(
                code="search_service_failed",
                message="Module tìm kiếm gặp lỗi khi xử lý truy vấn.",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception:
            logger.exception("Unexpected KIS API error")

            return error_response(
                code="internal_error",
                message="Máy chủ gặp lỗi ngoài dự kiến.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Bước 3: thêm URL ảnh và video cho Frontend.
        results_with_urls = [
            _add_dataset_urls(request, result)
            for result in raw_results
        ]

        # Bước 4: kiểm tra output của Search Engine.
        result_serializer = KisSearchResultSerializer(
            data=results_with_urls,
            many=True,
        )

        if not result_serializer.is_valid():
            logger.error(
                "Invalid KIS search output: %s",
                result_serializer.errors,
            )

            return error_response(
                code="invalid_search_output",
                message=(
                    "Kết quả từ module tìm kiếm "
                    "không đúng API contract."
                ),
                details={
                    "fields": result_serializer.errors
                },
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Không cho kết quả vượt quá top_k.
        results = result_serializer.validated_data[
            : validated_data["top_k"]
        ]

        response_body = {
            "query": validated_data["query"],
            "filters": {
                "collection_ids": validated_data[
                    "collection_ids"
                ]
            },
            "count": len(results),
            "results": results,
        }

        return Response(
            response_body,
            status=status.HTTP_200_OK,
        )


class KisDatasetAssetView(APIView):
    """Trả keyframe hoặc video thuộc bộ dữ liệu KIS."""

    permission_classes = [AllowAny]

    def get(
        self,
        request: Request,
        asset_path: str,
    ) -> FileResponse:
        data_root = Path(settings.KIS_DATA_ROOT).resolve()
        requested_path = (data_root / asset_path).resolve()

        # Chặn truy cập ra ngoài thư mục data_processing.
        if (
            not requested_path.is_relative_to(data_root)
            or not requested_path.is_file()
        ):
            raise Http404("KIS asset không tồn tại.")

        content_type, _ = mimetypes.guess_type(
            requested_path.name
        )

        response = FileResponse(
            requested_path.open("rb"),
            content_type=(
                content_type
                or "application/octet-stream"
            ),
        )

        response["X-Content-Type-Options"] = "nosniff"

        return response


class KisVideoUploadView(APIView):
    """Nhận và lưu nhiều video trong một request."""

    permission_classes = [AllowAny]
    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    @extend_schema(
        tags=["KIS"],
        summary="Upload multiple videos for KIS processing",
        request=KisVideoUploadRequestSerializer,
        responses={
            201: KisVideoUploadResponseSerializer,
            400: OpenApiResponse(
                response=ApiErrorSerializer,
                description="Invalid video upload",
            ),
            500: OpenApiResponse(
                response=ApiErrorSerializer,
                description="Could not store videos",
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = KisVideoUploadRequestSerializer(
            data={
                "videos": request.FILES.getlist("videos")
            }
        )

        if not serializer.is_valid():
            return error_response(
                code="validation_error",
                message=(
                    "Danh sách video tải lên "
                    "không hợp lệ."
                ),
                details=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_videos = []
        saved_paths: list[str] = []

        try:
            for video in serializer.validated_data["videos"]:
                original_name = Path(video.name).name
                safe_name = get_valid_filename(
                    original_name
                )

                stored_name = default_storage.save(
                    f"kis/videos/{safe_name}",
                    video,
                )

                saved_paths.append(stored_name)

                uploaded_videos.append(
                    {
                        "original_name": original_name,
                        "stored_name": stored_name,
                        "size": video.size,
                        "url": request.build_absolute_uri(
                            default_storage.url(
                                stored_name
                            )
                        ),
                    }
                )

        except Exception:
            logger.exception(
                "Could not store uploaded KIS videos"
            )

            # Nếu một file bị lỗi, xóa các file đã lưu
            # trước đó trong cùng request.
            for saved_path in saved_paths:
                default_storage.delete(saved_path)

            return error_response(
                code="video_upload_failed",
                message="Máy chủ không thể lưu video.",
                http_status=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
            )

        return Response(
            {
                "count": len(uploaded_videos),
                "videos": uploaded_videos,
            },
            status=status.HTTP_201_CREATED,
        )

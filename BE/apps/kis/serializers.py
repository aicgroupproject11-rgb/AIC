import re
from pathlib import Path

from django.conf import settings
from rest_framework import serializers


ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


class KisSearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(
        max_length=500,
        allow_blank=False,
        trim_whitespace=True,
    )
    collection_ids = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
        max_length=50,
    )
    top_k = serializers.IntegerField(
        required=False,
        default=100,
        min_value=1,
        max_value=100,
    )

    def validate_collection_ids(self, values):
        cleaned = []

        for value in values:
            collection_id = value.strip().upper()

            if not re.fullmatch(r"L\d+", collection_id):
                raise serializers.ValidationError(f"Collection ID không hợp lệ: {value}. Ví dụ đúng: L21.")

            if collection_id not in cleaned:
                cleaned.append(collection_id)

        return cleaned


class KisSearchResultSerializer(serializers.Serializer):
    rank = serializers.IntegerField(min_value=1)
    keyframe_id = serializers.CharField(max_length=150)
    collection_id = serializers.CharField(max_length=50)
    video_id = serializers.CharField(max_length=100)
    frame_number = serializers.IntegerField(min_value=0)
    frame_id = serializers.IntegerField(min_value=0)
    timestamp_ms = serializers.IntegerField(min_value=0)
    image_path = serializers.CharField(max_length=1000)
    video_path = serializers.CharField(max_length=1000)
    image_url = serializers.CharField(max_length=2000)
    video_url = serializers.CharField(max_length=2000)
    score = serializers.FloatField()
    domains = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False
    )
    routed_domains = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False
    )
    matched_objects = serializers.ListField(
        child=serializers.CharField(max_length=200), required=False
    )
    score_components = serializers.DictField(required=False)


class KisSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    parsed_keys = serializers.ListField(child=serializers.CharField())
    filters = serializers.DictField()
    count = serializers.IntegerField(min_value=0)
    results = KisSearchResultSerializer(many=True)


class KisSearchInspectResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    parsed_keys = serializers.ListField(child=serializers.CharField())
    filters = serializers.DictField()
    clip_query = serializers.CharField()
    analysis = serializers.DictField()
    routing = serializers.DictField()
    candidate_trace = serializers.DictField()
    index = serializers.DictField()


class ApiErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)


class ApiErrorSerializer(serializers.Serializer):
    error = ApiErrorBodySerializer()


class KisVideoUploadRequestSerializer(serializers.Serializer):
    videos = serializers.ListField(
        child=serializers.FileField(allow_empty_file=False),
        min_length=1,
        max_length=20,
    )

    def validate_videos(self, videos):
        max_size = getattr(
            settings,
            "KIS_MAX_VIDEO_SIZE",
            2 * 1024 * 1024 * 1024,
        )

        for video in videos:
            extension = Path(video.name).suffix.lower()

            if extension not in ALLOWED_VIDEO_EXTENSIONS:
                raise serializers.ValidationError(f"{video.name}: chỉ hỗ trợ MP4, MOV, AVI, MKV hoặc WEBM.")

            if video.size > max_size:
                max_mb = max_size // (1024 * 1024)
                raise serializers.ValidationError(f"{video.name}: file vượt quá {max_mb} MB.")

        return videos


class KisUploadedVideoSerializer(serializers.Serializer):
    original_name = serializers.CharField()
    stored_name = serializers.CharField()
    size = serializers.IntegerField(min_value=0)
    url = serializers.CharField()


class KisVideoUploadResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField(min_value=1)
    videos = KisUploadedVideoSerializer(many=True)

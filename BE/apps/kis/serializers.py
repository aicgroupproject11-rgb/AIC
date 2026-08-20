from rest_framework import serializers


class KisSearchRequestSerializer(serializers.Serializer):

    query = serializers.CharField(
        required=True, 
        allow_blank=False, 
        trim_whitespace=True, 
        max_length=500,
)
    collection_ids = serializers.ListField(
        child=serializers.CharField(max_length=50), 
        required=False, allow_empty=True, 
        default=list, 
        max_length=50,
)
    top_k = serializers.IntegerField(
        required=False, 
        default=20, 
        min_value=1, 
        max_value=100,
)

    def validate_collection_ids(self, values: list[str]) -> list[str]:

        cleaned_values: list[str] = []
        seen: set[str] = set()

        for value in values:
            cleaned_value = value.strip()
            if not cleaned_value:
                raise serializers.ValidationError("Collection ID không được để trống.")
            if cleaned_value not in seen:
                seen.add(cleaned_value)
                cleaned_values.append(cleaned_value)

        return cleaned_values


class KisSearchResultSerializer(serializers.Serializer):

    rank = serializers.IntegerField(min_value=1)
    keyframe_id = serializers.CharField(max_length=150)
    collection_id = serializers.CharField(max_length=50)
    video_id = serializers.CharField(max_length=100)
    frame_number = serializers.IntegerField(min_value=0)
    timestamp_ms = serializers.IntegerField(min_value=0)
    image_path = serializers.CharField(max_length=1000)
    video_path = serializers.CharField(max_length=1000)
    score = serializers.FloatField()


class KisSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    filters = serializers.DictField()
    count = serializers.IntegerField(min_value=0)
    results = KisSearchResultSerializer(many=True)


class ApiErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)


class ApiErrorSerializer(serializers.Serializer):
    error = ApiErrorBodySerializer()

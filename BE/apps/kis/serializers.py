from rest_framework import serializers


class KISSearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField( allow_blank=False, trim_whitespace=True,  )

    top_k = serializers.IntegerField(min_value=1, max_value=100, default=100, required=False, )


class KISCandidateSerializer(serializers.Serializer):
    rank = serializers.IntegerField( min_value=1, )

    video_id = serializers.CharField()

    frame_id = serializers.IntegerField(min_value=0, )

    score = serializers.FloatField()


class KISSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()

    count = serializers.IntegerField(min_value=0, )

    results = KISCandidateSerializer(many=True, )
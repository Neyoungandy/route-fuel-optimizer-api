from rest_framework import serializers


class RoutePlanRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=200, trim_whitespace=True)
    finish = serializers.CharField(max_length=200, trim_whitespace=True)

    def validate_start(self, value: str) -> str:
        if len(value) < 2:
            raise serializers.ValidationError("Start location is too short.")
        return value

    def validate_finish(self, value: str) -> str:
        if len(value) < 2:
            raise serializers.ValidationError("Finish location is too short.")
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["start"].casefold() == attrs["finish"].casefold():
            raise serializers.ValidationError("Start and finish must be different locations.")
        return attrs

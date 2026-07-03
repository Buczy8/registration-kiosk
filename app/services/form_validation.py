from fastapi import HTTPException, status


def get_missing_required_fields(schema_json: dict, payload_json: dict) -> list[str]:
    required = schema_json.get("required", [])
    if not isinstance(required, list):
        return []
    return [field for field in required if isinstance(field, str) and field not in payload_json]


def validate_required_fields(schema_json: dict, payload_json: dict) -> None:
    missing_fields = get_missing_required_fields(schema_json, payload_json)
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required form fields: {', '.join(missing_fields)}",
        )

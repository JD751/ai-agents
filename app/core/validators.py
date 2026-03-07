class ResponseValidationError(ValueError):
    pass


def validate_ask_response(answer: str) -> None:
    if len(answer.strip()) < 10:
        raise ResponseValidationError("Answer too short")
    if len(answer) > 5000:
        raise ResponseValidationError("Answer too long")


def validate_draft_response(draft: str) -> None:
    if len(draft.strip()) < 20:
        raise ResponseValidationError("Draft too short")


def validate_review_response(notes: list[str]) -> None:
    if not notes:
        raise ResponseValidationError("Review returned no notes")

import pytest
from pydantic import ValidationError

from app.schemas import GenerationRequest


def test_generation_request_accepts_minimal_prompt() -> None:
    request = GenerationRequest(prompt="a quiet cinematic lake")

    assert request.prompt == "a quiet cinematic lake"
    assert request.runtime == "mock"
    assert request.rewrite_prompt is False


def test_generation_request_rejects_blank_prompt() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(prompt="   ")


def test_generation_request_rejects_invalid_runtime() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(prompt="test", runtime="remote_cloud")

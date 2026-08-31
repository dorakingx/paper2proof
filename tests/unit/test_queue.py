from __future__ import annotations

import json

import pytest
from paper2proof.queue import JobMessage, SQSJobDispatcher
from pydantic import ValidationError


class RecordingSQS:
    def __init__(self) -> None:
        self.arguments = None

    def send_message(self, **kwargs):
        self.arguments = kwargs
        return {"MessageId": "message-1"}


@pytest.mark.asyncio
async def test_fifo_dispatch_is_minimal_and_deduplicated_by_job() -> None:
    sqs = RecordingSQS()
    dispatcher = SQSJobDispatcher(
        queue_url="https://sqs.us-west-2.amazonaws.com/123/paper2proof-jobs.fifo",
        region="us-west-2",
        client=sqs,
    )

    await dispatcher.dispatch("job_0123456789abcdef")

    assert sqs.arguments is not None
    assert json.loads(sqs.arguments["MessageBody"]) == {"job_id": "job_0123456789abcdef"}
    assert sqs.arguments["MessageGroupId"] == "job-0123456789abcdef"
    assert sqs.arguments["MessageDeduplicationId"] == "job_0123456789abcdef"


def test_queue_contract_rejects_unbounded_message() -> None:
    with pytest.raises(ValidationError):
        JobMessage.model_validate({"job_id": "../../unexpected", "command": "shell"})


def test_dispatcher_requires_queue_url() -> None:
    with pytest.raises(ValueError, match="queue_url"):
        SQSJobDispatcher(queue_url="", region="us-west-2", client=object())

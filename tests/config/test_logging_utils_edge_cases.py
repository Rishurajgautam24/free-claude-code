from unittest.mock import MagicMock

from providers.logging_utils import (
    generate_request_fingerprint,
    get_last_user_message_preview,
    get_tool_names,
    log_request_compact,
)


def test_generate_request_fingerprint_handles_mixed_message_shapes():
    class TextBlock:
        def __init__(self, text: str):
            self.text = text

    class TypeBlock:
        def __init__(self, t: str):
            self.type = t

    class MsgWithContent:
        def __init__(self, content):
            self.content = content

    class MsgWithRole:
        def __init__(self, role: str):
            self.role = role

    msg1 = MsgWithContent([TextBlock("hello"), TypeBlock("tool_use")])
    msg2 = MsgWithRole("assistant")

    fp = generate_request_fingerprint([msg1, msg2])
    assert fp.startswith("fp_")
    assert len(fp) == 11  # fp_ + 8 chars


def test_get_last_user_message_preview_sanitizes_newlines_and_truncates():
    msg1 = MagicMock()
    msg1.role = "assistant"
    msg1.content = "ignore"

    msg2 = MagicMock()
    msg2.role = "user"
    msg2.content = "line1\r\nline2\nline3"

    preview = get_last_user_message_preview([msg1, msg2], max_len=10)
    assert "\n" not in preview
    assert "\r" not in preview
    assert preview.endswith("...")


def test_get_tool_names_supports_objects_dicts_and_overflow():
    tools = [{"name": "t0"}] + [MagicMock(name=f"t{i}") for i in range(1, 8)]
    for i, t in enumerate(tools[1:], 1):
        t.name = f"t{i}"
    names = get_tool_names(tools, max_count=5)
    assert names[:2] == ["t0", "t1"]
    assert names[-1].startswith("+")


def _request_data():
    request_data = MagicMock()
    request_data.model = "m"
    request_data.messages = []
    request_data.tools = []
    request_data.system = None
    request_data.thinking = None
    request_data.max_tokens = 1
    return request_data


def test_log_request_compact_logs_summary_and_lazy_full_payload():
    logger = MagicMock()
    request_data = _request_data()
    request_data.model_dump.return_value = {"model": "m"}

    log_request_compact(logger, "req_1", request_data)
    assert logger.info.call_count == 1
    logger.opt.assert_called_once_with(lazy=True)
    message, dump = logger.opt.return_value.debug.call_args.args
    assert message == "FULL_PAYLOAD [req_1]: {}"
    request_data.model_dump.assert_not_called()  # nothing serialized unless DEBUG
    assert dump() == '{"model": "m"}'


def test_log_request_compact_handles_model_dump_failures():
    logger = MagicMock()
    request_data = _request_data()
    request_data.model_dump.side_effect = RuntimeError("nope")

    log_request_compact(logger, "req_1", request_data)

    # The compact summary is still logged, and the lazy dump reports the failure.
    assert logger.info.call_count == 1
    (_, dump) = logger.opt.return_value.debug.call_args.args
    assert dump() == "<could not dump request data: nope>"

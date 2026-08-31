import unittest
from unittest.mock import patch

import learning_retriever._active_work_item_remote as remote
from learning_retriever.active_work_item import ActiveWorkItemResolutionError


class _FakeResponse:
    def __init__(self, url: str, body: bytes = b"{}") -> None:
        self._url = url
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return self._body


class _FakeOpener:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response

    def open(self, request, timeout=0):
        del request, timeout
        return self.response


class ActiveWorkItemTransportTests(unittest.TestCase):
    def test_authority_redirect_handler_fails_closed(self):
        request = remote.Request(
            "https://api.github.com/repos/vxz2datoubo/eustia-ai-film/branches/main",
            method="GET",
        )
        handler = remote._RejectRedirect()
        with self.assertRaises(remote.HTTPError):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {"Location": "https://example.invalid/forged-authority"},
                "https://example.invalid/forged-authority",
            )

    def test_fixed_github_readback_installs_reject_redirect_handler(self):
        endpoint = "/repos/vxz2datoubo/eustia-ai-film/branches/main"
        expected = remote.GITHUB_API_ROOT + endpoint
        opener = _FakeOpener(_FakeResponse(expected, b'{"commit":{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}'))
        with patch.object(remote, "build_opener", return_value=opener) as build:
            payload = remote._github_api_json(endpoint)
        self.assertEqual(payload["commit"]["sha"], "a" * 40)
        handlers = build.call_args.args
        self.assertTrue(any(isinstance(handler, remote._RejectRedirect) for handler in handlers))

    def test_success_response_with_changed_final_url_fails_closed(self):
        endpoint = "/repos/vxz2datoubo/eustia-ai-film/branches/main"
        opener = _FakeOpener(_FakeResponse("https://example.invalid/forged-authority", b"{}"))
        with patch.object(remote, "build_opener", return_value=opener), self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            remote._github_api_json(endpoint)
        self.assertEqual(ctx.exception.code, "WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE")
        self.assertEqual(ctx.exception.details.get("reason"), "canonical_api_response_url_mismatch")

    def test_noncanonical_api_endpoint_is_rejected_before_transport(self):
        with patch.object(remote, "build_opener", side_effect=AssertionError("transport must not run")), self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            remote._github_api_json("https://example.invalid/forged-authority")
        self.assertEqual(ctx.exception.details.get("reason"), "noncanonical_api_endpoint")


if __name__ == "__main__":
    unittest.main()

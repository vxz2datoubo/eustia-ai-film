import unittest

from learning_retriever.immutable_byte_identity import (
    ByteIdentityError,
    compare_immutable_byte_pair,
    observe_immutable_bytes,
)


class HostileBytes(bytes):
    len_hook_calls = 0

    def __len__(self):  # pragma: no cover - must never execute
        type(self).len_hook_calls += 1
        raise AssertionError("caller-defined __len__ hook executed")


class ImmutableByteExactTypeTests(unittest.TestCase):
    def setUp(self):
        HostileBytes.len_hook_calls = 0

    def test_bytes_subclass_is_rejected_before_len_or_other_identity_hooks(self):
        hostile = HostileBytes(b"abc")
        with self.assertRaises(ByteIdentityError) as ctx:
            observe_immutable_bytes(hostile)
        self.assertEqual(ctx.exception.code, "BYTE_INPUT_NOT_IMMUTABLE_BYTES")
        self.assertEqual(HostileBytes.len_hook_calls, 0)

    def test_pair_rejects_bytes_subclass_before_any_observation(self):
        hostile = HostileBytes(b"abc")
        with self.assertRaises(ByteIdentityError) as ctx:
            compare_immutable_byte_pair(hostile, b"abc")
        self.assertEqual(ctx.exception.code, "BYTE_INPUT_NOT_IMMUTABLE_BYTES")
        self.assertEqual(HostileBytes.len_hook_calls, 0)

        with self.assertRaises(ByteIdentityError) as ctx:
            compare_immutable_byte_pair(b"abc", hostile)
        self.assertEqual(ctx.exception.code, "BYTE_INPUT_NOT_IMMUTABLE_BYTES")
        self.assertEqual(HostileBytes.len_hook_calls, 0)


if __name__ == "__main__":
    unittest.main()

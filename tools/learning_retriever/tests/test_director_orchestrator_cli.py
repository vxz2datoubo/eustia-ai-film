from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from learning_retriever.director_orchestrator import DirectorRuntimeError
from learning_retriever.director_orchestrator_cli import main


class DirectorOrchestratorCliTests(unittest.TestCase):
    def write_packet(self, directory: str, content: str = "packet_id: TEST\n") -> Path:
        path = Path(directory) / "packet.yaml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_cli_emits_non_executable_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.write_packet(tmp)
            candidate = {
                "schema": "DIRECTOR_RUNTIME_CANDIDATE/v1",
                "status": "CANDIDATE_READY",
                "execution_authorized": False,
                "deliverable": False,
            }
            with patch(
                "learning_retriever.director_orchestrator_cli.DirectorRuntimeOrchestrator"
            ) as orchestrator_cls:
                orchestrator_cls.return_value.compile.return_value = candidate
                output = io.StringIO()
                with redirect_stdout(output):
                    code = main(
                        [
                            "--project-root",
                            tmp,
                            "--description",
                            "继续当前镜头",
                            "--creative-packet",
                            str(packet),
                        ]
                    )
            self.assertEqual(0, code)
            payload = json.loads(output.getvalue())
            self.assertEqual("DIRECTOR_RUNTIME_CANDIDATE/v1", payload["schema"])
            self.assertFalse(payload["execution_authorized"])
            self.assertFalse(payload["deliverable"])

    def test_cli_preserves_fail_closed_error_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.write_packet(tmp)
            with patch(
                "learning_retriever.director_orchestrator_cli.DirectorRuntimeOrchestrator"
            ) as orchestrator_cls:
                orchestrator_cls.return_value.compile.side_effect = DirectorRuntimeError(
                    "DIRECTOR_WORLD_ENTITY_DROPPED",
                    "scarf vanished",
                )
                output = io.StringIO()
                with redirect_stdout(output):
                    code = main(
                        [
                            "--project-root",
                            tmp,
                            "--description",
                            "继续当前镜头",
                            "--creative-packet",
                            str(packet),
                        ]
                    )
            self.assertEqual(2, code)
            payload = json.loads(output.getvalue())
            self.assertEqual("FAIL", payload["status"])
            self.assertEqual("DIRECTOR_WORLD_ENTITY_DROPPED", payload["code"])

    def test_cli_rejects_invalid_yaml_shape_through_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.write_packet(tmp, "- not\n- a\n- mapping\n")
            with patch(
                "learning_retriever.director_orchestrator_cli.DirectorRuntimeOrchestrator"
            ) as orchestrator_cls:
                orchestrator_cls.return_value.compile.side_effect = DirectorRuntimeError(
                    "DIRECTOR_PACKET_SCHEMA_INVALID",
                    "creative_packet must be a mapping",
                )
                output = io.StringIO()
                with redirect_stdout(output):
                    code = main(
                        [
                            "--project-root",
                            tmp,
                            "--description",
                            "继续当前镜头",
                            "--creative-packet",
                            str(packet),
                        ]
                    )
            self.assertEqual(2, code)
            payload = json.loads(output.getvalue())
            self.assertEqual("DIRECTOR_PACKET_SCHEMA_INVALID", payload["code"])


if __name__ == "__main__":
    unittest.main()

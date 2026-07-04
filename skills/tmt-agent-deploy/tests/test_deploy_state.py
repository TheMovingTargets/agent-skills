from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml


SKILL_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = SKILL_ROOT / "tests" / "fixtures" / "valid-config.yaml"
MODULE_PATH = SKILL_ROOT / "scripts" / "deploy_state.py"
SPEC = importlib.util.spec_from_file_location("tmt_deploy_state", MODULE_PATH)
assert SPEC and SPEC.loader
deploy_state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy_state)


class DeployStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        local = self.repo / ".tmt-agent-deploy"
        (local / "state").mkdir(parents=True)
        (local / "runs").mkdir()
        shutil.copyfile(FIXTURE, local / "config.yaml")
        (local / "state" / "MEMORY.md").write_text(
            "# Deployment architecture\n", encoding="utf-8"
        )
        (self.repo / "deploy.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def read_config(self) -> dict:
        return yaml.safe_load(
            (self.repo / ".tmt-agent-deploy" / "config.yaml").read_text(
                encoding="utf-8"
            )
        )

    def write_config(self, config: dict) -> None:
        (self.repo / ".tmt-agent-deploy" / "config.yaml").write_text(
            yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
        )

    def test_valid_configuration(self) -> None:
        config = deploy_state.validate_config(self.repo)
        self.assertEqual(config["confirmation_policy"], "each-step")

    def test_confirmation_policy_is_restricted(self) -> None:
        config = self.read_config()
        config["confirmation_policy"] = "never"
        self.write_config(config)
        with self.assertRaisesRegex(deploy_state.StateError, "confirmation_policy"):
            deploy_state.validate_config(self.repo)

    def test_secret_fields_are_rejected(self) -> None:
        config = self.read_config()
        config["api_token"] = "not-even-a-real-token"
        self.write_config(config)
        with self.assertRaisesRegex(deploy_state.StateError, "secret-like field"):
            deploy_state.validate_config(self.repo)

    def test_private_key_content_is_rejected(self) -> None:
        config = self.read_config()
        config["credential_refs"][0]["reference"] = (
            "-----BEGIN PRIVATE KEY-----\nvalue"
        )
        self.write_config(config)
        with self.assertRaisesRegex(deploy_state.StateError, "secret-like content"):
            deploy_state.validate_config(self.repo)

    def test_shell_sensitive_ssh_remote_argument_is_rejected(self) -> None:
        config = self.read_config()
        entrypoint = config["environments"]["production"]["targets"]["web"][
            "components"
        ][0]["deploy"][0]
        entrypoint["argv"] = [
            "ssh",
            "-i",
            "~/.ssh/deploy.pem",
            "deploy@example.com",
            "python3",
            "-c",
            "import backend.main",
        ]
        self.write_config(config)

        with self.assertRaisesRegex(deploy_state.StateError, "shell-safe tokens"):
            deploy_state.validate_config(self.repo)

    def test_secret_content_in_memory_is_rejected(self) -> None:
        memory = self.repo / ".tmt-agent-deploy" / "state" / "MEMORY.md"
        memory.write_text(
            "-----BEGIN PRIVATE KEY-----\nvalue\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(deploy_state.StateError, "local state invalid"):
            deploy_state.validate_local_state(self.repo)

    def test_known_token_prefix_in_memory_is_rejected(self) -> None:
        memory = self.repo / ".tmt-agent-deploy" / "state" / "MEMORY.md"
        memory.write_text(
            "reference: ghp_1234567890abcdefghij\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(deploy_state.StateError, "local state invalid"):
            deploy_state.validate_local_state(self.repo)

    def test_snapshot_and_behavioral_drift(self) -> None:
        deploy_state.snapshot(self.repo)
        result = deploy_state.drift(self.repo)
        self.assertEqual(result["drift"], [])
        (self.repo / "deploy.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        result = deploy_state.drift(self.repo)
        self.assertTrue(result["material_review_required"])
        self.assertEqual(result["drift"][0]["status"], "changed")

    def test_unfinished_run_blocks_new_run(self) -> None:
        deploy_state.snapshot(self.repo)
        first = deploy_state.start_run(
            self.repo, "production", "web", "abc123", "each-step"
        )
        self.assertEqual(first["status"], "started")
        with self.assertRaisesRegex(deploy_state.StateError, "unfinished"):
            deploy_state.start_run(
                self.repo, "production", "web", "def456", "each-step"
            )
        state = deploy_state.checkpoint(
            self.repo, "deploy web", "running", True, "web", None
        )
        self.assertTrue(state["target_mutation_started"])

    def test_run_policy_must_match_configuration(self) -> None:
        deploy_state.snapshot(self.repo)
        with self.assertRaisesRegex(deploy_state.StateError, "does not match"):
            deploy_state.start_run(
                self.repo, "production", "web", "abc123", "preflight-only"
            )

    def test_failed_step_cannot_be_overwritten_by_success(self) -> None:
        deploy_state.snapshot(self.repo)
        deploy_state.start_run(
            self.repo, "production", "web", "abc123", "each-step"
        )
        deploy_state.checkpoint(
            self.repo, "deploy web", "running", True, "web", None
        )
        state = deploy_state.checkpoint(
            self.repo, "deploy web", "failed", True, "web", None
        )

        with self.assertRaisesRegex(deploy_state.StateError, "terminal"):
            deploy_state.checkpoint(
                self.repo, "deploy web", "succeeded", True, "web", None
            )

        self.assertEqual(state["status"], "failed")

    def test_successful_diagnostic_does_not_clear_failed_run(self) -> None:
        deploy_state.snapshot(self.repo)
        deploy_state.start_run(
            self.repo, "production", "web", "abc123", "each-step"
        )
        deploy_state.checkpoint(
            self.repo, "deploy web", "running", True, "web", None
        )
        deploy_state.checkpoint(
            self.repo, "deploy web", "failed", True, "web", None
        )
        deploy_state.checkpoint(
            self.repo, "diagnose", "running", False, None, None
        )
        state = deploy_state.checkpoint(
            self.repo, "diagnose", "succeeded", False, None, None
        )

        self.assertEqual(state["status"], "failed")

    def test_repository_entrypoint_failure_is_checkpointed_and_propagated(self) -> None:
        (self.repo / "deploy.sh").write_text(
            "#!/bin/sh\nexit 23\n", encoding="utf-8"
        )
        (self.repo / "deploy.sh").chmod(0o755)
        deploy_state.snapshot(self.repo)
        deploy_state.start_run(
            self.repo, "production", "web", "abc123", "each-step"
        )

        returncode = deploy_state.run_repository_entrypoint(
            self.repo,
            "production",
            "web",
            "components.0.deploy.0",
        )

        self.assertEqual(returncode, 23)
        state = deploy_state.status(self.repo)["run"]
        self.assertEqual(state["status"], "failed")
        self.assertEqual(
            [(event["step"], event["status"]) for event in state["steps"]],
            [("deploy web", "running"), ("deploy web", "failed")],
        )

    def test_repository_entrypoint_success_is_checkpointed_atomically(self) -> None:
        (self.repo / "deploy.sh").write_text(
            "#!/bin/sh\nexit 0\n", encoding="utf-8"
        )
        (self.repo / "deploy.sh").chmod(0o755)
        deploy_state.snapshot(self.repo)
        deploy_state.start_run(
            self.repo, "production", "web", "abc123", "each-step"
        )

        returncode = deploy_state.run_repository_entrypoint(
            self.repo,
            "production",
            "web",
            "components.0.deploy.0",
        )

        self.assertEqual(returncode, 0)
        state = deploy_state.status(self.repo)["run"]
        self.assertEqual(state["status"], "succeeded")
        self.assertEqual(state["changed_components"], ["web"])
        self.assertEqual(
            [(event["step"], event["status"]) for event in state["steps"]],
            [("deploy web", "running"), ("deploy web", "succeeded")],
        )

    def test_repository_entrypoint_rejects_configuration_changed_after_start(self) -> None:
        deploy_state.snapshot(self.repo)
        deploy_state.start_run(
            self.repo, "production", "web", "abc123", "each-step"
        )
        config = self.read_config()
        config["environments"]["production"]["description"] = "Changed"
        self.write_config(config)

        with self.assertRaisesRegex(deploy_state.StateError, "changed"):
            deploy_state.run_repository_entrypoint(
                self.repo,
                "production",
                "web",
                "components.0.deploy.0",
            )

    def test_retryable_smoke_failure_can_be_followed_by_success(self) -> None:
        marker = self.repo / "attempted"
        (self.repo / "deploy.sh").write_text(
            f"#!/bin/sh\n"
            f"if [ -f '{marker}' ]; then exit 0; fi\n"
            f"touch '{marker}'\n"
            f"exit 23\n",
            encoding="utf-8",
        )
        (self.repo / "deploy.sh").chmod(0o755)
        deploy_state.snapshot(self.repo)
        deploy_state.start_run(
            self.repo, "production", "web", "abc123", "each-step"
        )

        first = deploy_state.run_repository_entrypoint(
            self.repo,
            "production",
            "web",
            "components.0.smoke_tests.0.entrypoint",
            attempt=1,
            retryable=True,
        )
        second = deploy_state.run_repository_entrypoint(
            self.repo,
            "production",
            "web",
            "components.0.smoke_tests.0.entrypoint",
            attempt=2,
        )

        self.assertEqual((first, second), (23, 0))
        state = deploy_state.status(self.repo)["run"]
        self.assertEqual(state["status"], "succeeded")
        self.assertFalse(state.get("failure_recorded", False))
        self.assertEqual(
            [(event["step"], event["status"]) for event in state["steps"]],
            [
                ("smoke test", "running"),
                ("smoke test", "retryable-failure"),
                ("smoke test [attempt 2]", "running"),
                ("smoke test [attempt 2]", "succeeded"),
            ],
        )

    def test_retryable_failure_is_rejected_for_mutating_entrypoint(self) -> None:
        (self.repo / "deploy.sh").chmod(0o755)
        deploy_state.snapshot(self.repo)
        deploy_state.start_run(
            self.repo, "production", "web", "abc123", "each-step"
        )

        with self.assertRaisesRegex(deploy_state.StateError, "non-mutating"):
            deploy_state.run_repository_entrypoint(
                self.repo,
                "production",
                "web",
                "components.0.deploy.0",
                retryable=True,
            )

    def test_persistent_target_requires_backup(self) -> None:
        config = self.read_config()
        config["environments"]["production"]["targets"]["web"][
            "persistent_data"
        ] = True
        self.write_config(config)
        with self.assertRaisesRegex(deploy_state.StateError, "backup"):
            deploy_state.validate_config(self.repo)

    def test_destructive_entrypoint_requires_authorization_text(self) -> None:
        config = self.read_config()
        deploy = config["environments"]["production"]["targets"]["web"][
            "components"
        ][0]["deploy"][0]
        deploy["destructive"] = True
        self.write_config(config)
        with self.assertRaisesRegex(
            deploy_state.StateError, "destructive_authorization"
        ):
            deploy_state.validate_config(self.repo)

    def test_prune_keeps_newest_fifty_summaries(self) -> None:
        runs = self.repo / ".tmt-agent-deploy" / "runs"
        for index in range(52):
            path = runs / f"20260702T18{index:04d}Z-production-{index}.md"
            path.write_text(f"# Run {index}\n", encoding="utf-8")
        removed = deploy_state.prune_runs(self.repo)
        self.assertEqual(len(removed), 2)
        self.assertEqual(len(list(runs.glob("*.md"))), 50)


if __name__ == "__main__":
    unittest.main()

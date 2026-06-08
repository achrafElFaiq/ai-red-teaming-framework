import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from redteaming.domain.models.attack import Attack
from redteaming.infrastructure.http_attack_target import AttackTarget
from redteaming.plugins.pyrit.adapter import PyritAdapter
from redteaming.plugins.pyrit.runner import PyritRunner


class DummyTarget(AttackTarget):
    def __init__(self):
        super().__init__("PyRIT test target", "http://localhost:8000/api/chat")
        self.reset_count = 0

    def query(self, prompt: str):
        return "dummy response"

    def reset_history(self) -> None:
        self.reset_count += 1


class DummyAttack(Attack):
    def __init__(self, config: dict | None = None):
        super().__init__(intent="test", framework="pyrit", config=config or {})

    def execute(self, target: AttackTarget):  # pragma: no cover - not used in this test
        raise NotImplementedError


class PyritRunnerTests(unittest.TestCase):
    def setUp(self):
        self.settings_patcher = patch(
            "redteaming.plugins.pyrit.runner.get_runtime_settings",
            return_value=SimpleNamespace(
                pyrit=SimpleNamespace(
                    loop_shutdown_delay=0,
                    dataset_max_concurrency=5,
                ),
            ),
        )
        self.settings_patcher.start()

    def tearDown(self):
        self.settings_patcher.stop()

    def test_run_drains_pending_asyncio_tasks_before_closing_loop(self):
        runner = PyritRunner()
        target = DummyTarget()
        attack = DummyAttack()
        background_tasks = []

        async def fake_run_async(_target, _attack):
            async def delayed_cleanup():
                await asyncio.sleep(0.01)

            task = asyncio.create_task(delayed_cleanup())
            background_tasks.append(task)
            return []

        with patch.object(runner, "_run_async", fake_run_async):
            results = runner.run(target, attack)

        self.assertEqual(results, [])
        self.assertEqual(len(background_tasks), 1)
        self.assertTrue(background_tasks[0].done())
        self.assertFalse(background_tasks[0].cancelled())

    def test_build_dataset_attack_name_includes_index_and_prompt_preview(self):
        runner = PyritRunner()

        attack_name = runner._build_dataset_attack_name(
            "pyrit - dataset",
            "A" * 80,
            1,
        )

        self.assertEqual(attack_name, f"pyrit - dataset | [02] {'A' * 60}")

    def test_execute_orchestrator_dispatches_dataset_mode(self):
        runner = PyritRunner()
        attack = DummyAttack(
            {
                "orchestrator": "dataset",
                "prompts": ["one", "two"],
                "scoring_question": "safe?",
            }
        )

        async def run_test():
            with patch.object(runner, "_build_scorer_llm", return_value=object()), \
                 patch.object(runner, "_build_scorer", return_value="scorer") as scorer_mock, \
                 patch.object(runner, "_run_dataset", new_callable=AsyncMock, return_value=["dataset-result"]) as dataset_mock, \
                 patch("redteaming.plugins.pyrit.runner.build_pyrit_scorer_config", return_value={"scorer_endpoint": "e", "scorer_model": "m", "scorer_api_key": "k"}):
                result = await runner._execute_orchestrator(attack, object(), {"attacker_endpoint": "e", "attacker_model": "m", "attacker_api_key": "k"})

            self.assertEqual(result, ["dataset-result"])
            scorer_mock.assert_called_once()
            dataset_mock.assert_called_once_with(attack, unittest.mock.ANY, "scorer")

        asyncio.run(run_test())

    def test_execute_orchestrator_rejects_unknown_mode(self):
        runner = PyritRunner()
        attack = DummyAttack({"orchestrator": "unknown"})

        async def run_test():
            with patch.object(runner, "_build_attacker_llm", return_value=object()), \
                 patch.object(runner, "_build_scorer_llm", return_value=object()), \
                 patch.object(runner, "_build_scorer", return_value="scorer"), \
                 patch("redteaming.plugins.pyrit.runner.build_pyrit_scorer_config", return_value={"scorer_endpoint": "e", "scorer_model": "m", "scorer_api_key": "k"}):
                with self.assertRaisesRegex(ValueError, "Unknown orchestrator type"):
                    await runner._execute_orchestrator(
                        attack,
                        object(),
                        {"attacker_endpoint": "e", "attacker_model": "m", "attacker_api_key": "k"},
                    )

        asyncio.run(run_test())

    def test_adapter_wrapper_exposes_reset_history(self):
        runner = PyritRunner()
        runner._initialize_memory()
        target = DummyTarget()
        wrapped = PyritAdapter().wrap(target)

        getattr(wrapped, "reset_history")()

        self.assertEqual(target.reset_count, 1)

    def test_run_dataset_resets_target_between_prompts(self):
        runner = PyritRunner()
        runner._initialize_memory()
        target = DummyTarget()
        objective_target = PyritAdapter().wrap(target)
        attack = DummyAttack({"prompts": ["one", "two"]})

        class FakePromptSendingAttack:
            def __init__(self, *args, **kwargs):
                pass

            async def execute_async(self, objective: str):
                return SimpleNamespace(objective=objective)

        async def run_test():
            with patch("redteaming.plugins.pyrit.runner.AttackScoringConfig", return_value=object()), \
                 patch("redteaming.plugins.pyrit.runner.PromptSendingAttack", FakePromptSendingAttack):
                results = await runner._run_dataset(attack, objective_target, scorer="scorer")

            self.assertEqual([result.objective for result in results], ["one", "two"])
            self.assertEqual(target.reset_count, 2)

        asyncio.run(run_test())

    def test_normalize_results_accepts_dataset_result_list(self):
        runner = PyritRunner()
        target = DummyTarget()
        attack = DummyAttack()
        dataset_results = [SimpleNamespace(objective="one"), SimpleNamespace(objective="two")]

        with patch.object(runner, "_normalize_dataset_batch", return_value=["r1", "r2"]) as normalize_mock:
            results = runner._normalize_results(dataset_results, target, attack)

        self.assertEqual(results, ["r1", "r2"])
        normalize_mock.assert_called_once_with(dataset_results, target, attack)


if __name__ == "__main__":
    unittest.main()



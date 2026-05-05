import asyncio
import gc
import logging
from typing import Any, cast

from settings import get_runtime_settings, build_pyrit_attacker_config, build_pyrit_scorer_config
from pyrit.executor.attack import (
    AttackAdversarialConfig,
    AttackScoringConfig,
    CrescendoAttack,
    PromptSendingAttack,
    RedTeamingAttack,
)

from pyrit.executor.attack.core.attack_executor import AttackExecutorResult
from pyrit.prompt_target.openai.openai_chat_target import OpenAIChatTarget
from pyrit.memory.central_memory import CentralMemory
from pyrit.memory.sqlite_memory import SQLiteMemory
from pyrit.score.true_false.self_ask_true_false_scorer import SelfAskTrueFalseScorer

from core.models.attack_target import AttackTarget
from core.models.attack import Attack
from core.models.attack_result import AttackResult
from core.contracts.runner import Runner
from .pyrit_adapter import PyritAdapter


logger = logging.getLogger(__name__)


class PyritRunner(Runner):
    """Run PyRIT attacks and normalize their outputs into framework results."""

    def __init__(self):
        self.settings = get_runtime_settings(frameworks={"pyrit"})

    def run(self, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        """Execute one PyRIT attack synchronously from the framework point of view."""
        self._initialize_memory()

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._run_async(target, attack))
        finally:
            asyncio.set_event_loop(None)
            self._shutdown_event_loop(loop)

    def _initialize_memory(self) -> None:
        """Bootstrap the PyRIT shared memory backend for the current run."""
        CentralMemory.set_memory_instance(cast(Any, SQLiteMemory()))

    async def _run_async(self, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        """Run the async PyRIT pipeline, then normalize the backend result."""
        objective_target = self._prepare_objective_target(target)
        attacker_config = build_pyrit_attacker_config()
        result = await self._execute_orchestrator(attack, objective_target, attacker_config)
        self._log_backend_trace(result)
        return self._normalize_results(result, target, attack)

    def _prepare_objective_target(self, target: AttackTarget):
        """Wrap the framework target with the PyRIT adapter."""
        logger.debug("Wrapping target '%s' with PyRIT adapter", target.name)
        objective_target = PyritAdapter().wrap(target)
        self._log_target_capabilities(objective_target)
        return objective_target

    def _log_target_capabilities(self, objective_target) -> None:
        logger.debug(
            "PyRIT target supports_multi_turn=%s",
            getattr(objective_target, "supports_multi_turn", None),
        )

    async def _execute_orchestrator(self, attack: Attack, objective_target, attacker_config: dict[str, str]) -> Any:
        """Dispatch the attack to the correct PyRIT execution mode."""
        orchestrator_type = self._resolve_orchestrator_type(attack)
        scorer_config = build_pyrit_scorer_config()

        if orchestrator_type == "dataset":
            logger.debug("Initializing dataset scorer for attack '%s'", attack.name)
            scorer_llm = self._build_scorer_llm(scorer_config)
            scorer = self._build_scorer(scorer_llm, attack)
            prompts = attack.config.get("prompts", [])
            logger.info("[PyRIT] Dataset mode — %d prompt(s), max_concurrency=%d",
                        len(prompts), self.settings.pyrit_dataset_max_concurrency)
            return await self._run_dataset(attack, objective_target, scorer)

        attacker_llm = self._build_attacker_llm(attacker_config)
        scorer_llm = self._build_scorer_llm(scorer_config)
        scorer = self._build_scorer(scorer_llm, attack)

        if orchestrator_type == "red_teaming":
            objective_preview = attack.config.get("objective", "")[:100]
            logger.info(
                "[PyRIT] Red teaming — max_turns=%d — objective: %s...",
                attack.config.get("max_turns", 5),
                objective_preview,
            )
            return await self._run_red_teaming(attack, objective_target, attacker_llm, scorer)
        if orchestrator_type == "crescendo":
            objective_preview = attack.config.get("objective", "")[:100]
            logger.info(
                "[PyRIT] Crescendo — max_turns=%d — objective: %s...",
                attack.config.get("max_turns", 6),
                objective_preview,
            )
            return await self._run_crescendo(attack, objective_target, attacker_llm, scorer)

        raise ValueError(f"Unknown orchestrator type: {orchestrator_type}")

    def _resolve_orchestrator_type(self, attack: Attack) -> str:
        """Resolve the configured PyRIT execution mode for the attack."""
        return attack.config.get("orchestrator", "red_teaming")

    def _build_attacker_llm(self, attacker_config: dict[str, str]) -> OpenAIChatTarget:
        """Build the attacker/scorer chat target from resolved runtime settings."""
        logger.info(
            "[PyRIT] Attacker LLM: %s @ %s",
            attacker_config["attacker_model"],
            attacker_config["attacker_endpoint"],
        )
        return OpenAIChatTarget(
            endpoint=attacker_config["attacker_endpoint"],
            model_name=attacker_config["attacker_model"],
            api_key=attacker_config["attacker_api_key"],
        )

    def _build_scorer(self, chat_target: OpenAIChatTarget, attack: Attack) -> SelfAskTrueFalseScorer:
        """Build the PyRIT objective scorer for the current attack."""
        return SelfAskTrueFalseScorer(
            chat_target=chat_target,
            true_false_question=attack.config.get("scoring_question"),
        )

    def _build_scorer_llm(self, scorer_config: dict[str, str]) -> OpenAIChatTarget:
        """Build the scorer chat target from resolved runtime settings."""
        logger.info(
            "[PyRIT] Scorer LLM : %s @ %s",
            scorer_config["scorer_model"],
            scorer_config["scorer_endpoint"],
        )
        return OpenAIChatTarget(
            endpoint=scorer_config["scorer_endpoint"],
            model_name=scorer_config["scorer_model"],
            api_key=scorer_config["scorer_api_key"],
        )

    async def _run_dataset(self, attack, objective_target, scorer):
        prompts = attack.config.get("prompts", [])
        results = []

        for prompt in prompts:
            scoring_config = AttackScoringConfig(objective_scorer=scorer)
            single_attack = PromptSendingAttack(
                objective_target=objective_target,
                attack_scoring_config=scoring_config,
            )
            result = await single_attack.execute_async(objective=prompt)
            results.append(result)
            objective_target.reset_history()

        return results

    async def _run_red_teaming(self, attack, objective_target, attacker_llm, scorer):
        """Execute the multi-turn PyRIT red teaming flow."""
        adversarial_config = AttackAdversarialConfig(
            target=attacker_llm,
            system_prompt_path=attack.config.get("strategy_path", None),
        )
        scoring_config = AttackScoringConfig(objective_scorer=scorer)
        red_team = RedTeamingAttack(
            objective_target=objective_target,
            attack_adversarial_config=adversarial_config,
            attack_scoring_config=scoring_config,
            max_turns=attack.config.get("max_turns", 5),
        )
        return await red_team.execute_async(objective=attack.config.get("objective"))

    async def _run_crescendo(self, attack, objective_target, attacker_llm, scorer):
        """Execute the multi-turn PyRIT crescendo flow."""
        adversarial_config = AttackAdversarialConfig(
            target=attacker_llm,
            system_prompt_path=attack.config.get("strategy_path", None),
        )
        scoring_config = AttackScoringConfig(objective_scorer=scorer)

        crescendo = CrescendoAttack(
            objective_target=objective_target,
            attack_adversarial_config=adversarial_config,
            attack_scoring_config=scoring_config,
            max_turns=attack.config.get("max_turns", 6),
        )
        return await crescendo.execute_async(
            objective=attack.config.get("objective")
        )

    def _log_backend_trace(self, result: Any) -> None:
        """Log a readable summary of the raw PyRIT backend output."""
        if isinstance(result, list):
            logger.info(
                "[PyRIT] Dataset finished — %d completed, 0 incomplete",
                len(result),
            )
            return

        if isinstance(result, AttackExecutorResult):
            completed = len(result.completed_results)
            incomplete = len(result.incomplete_objectives)
            logger.info(
                "[PyRIT] Dataset finished — %d completed, %d incomplete",
                completed, incomplete,
            )
            return

        from pyrit.models.attack_result import AttackOutcome
        breached = getattr(result, "outcome", None) == AttackOutcome.SUCCESS
        turns = getattr(result, "executed_turns", "?")
        verdict = "BREACHED" if breached else "HARDENED"
        logger.info("[PyRIT] Result — %s — %s turn(s)", verdict, turns)

    def _normalize_results(self, result, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        """Convert the PyRIT backend result into framework-level attack results."""

        if isinstance(result, list):
            normalized_results = self._normalize_dataset_list_results(result, target, attack)
        elif isinstance(result, AttackExecutorResult):
            normalized_results = self._normalize_dataset_results(result, target, attack)
        else:
            normalized_results = [self._normalize_single_result(result, target, attack)]

        return normalized_results

    def _normalize_dataset_list_results(
        self,
        result: list[Any],
        target: AttackTarget,
        attack: Attack,
    ) -> list[AttackResult]:
        """Normalize a sequential dataset execution into one result per prompt."""
        from .pyrit_normalizer import PyritNormalizer

        normalized_results: list[AttackResult] = []
        for index, individual_result in enumerate(result):
            attack_name = self._build_dataset_attack_name(attack.name, individual_result.objective, index)
            normalizer = PyritNormalizer(
                pyrit_result=individual_result,
                db_path=self.settings.pyrit_db_path,
                target_url=target.url,
                attack_name=attack_name,
            )
            normalized_results.append(normalizer.normalize())

        return normalized_results

    def _normalize_dataset_results(
        self,
        result: AttackExecutorResult,
        target: AttackTarget,
        attack: Attack,
    ) -> list[AttackResult]:
        """Normalize a dataset execution into one result per completed objective."""
        from .pyrit_normalizer import PyritNormalizer


        normalized_results: list[AttackResult] = []
        for index, individual_result in enumerate(result.completed_results):
            attack_name = self._build_dataset_attack_name(attack.name, individual_result.objective, index)
            normalizer = PyritNormalizer(
                pyrit_result=individual_result,
                db_path=self.settings.pyrit_db_path,
                target_url=target.url,
                attack_name=attack_name,
            )
            normalized_results.append(normalizer.normalize())

        return normalized_results

    def _build_dataset_attack_name(self, base_attack_name: str, objective: str, index: int) -> str:
        """Build a stable readable attack name for one dataset objective result."""
        prompt_preview = objective[:60]
        return f"{base_attack_name} | [{index + 1:02d}] {prompt_preview}"

    def _normalize_single_result(self, result: Any, target: AttackTarget, attack: Attack) -> AttackResult:
        """Normalize a single PyRIT conversation result."""
        from .pyrit_normalizer import PyritNormalizer

        normalizer = PyritNormalizer(
            pyrit_result=result,
            db_path=self.settings.pyrit_db_path,
            target_url=target.url,
            attack_name=attack.name,
        )
        return normalizer.normalize()

    def _shutdown_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Drain and close the temporary event loop used by the synchronous runner."""
        gc.collect()

        if self.settings.pyrit_loop_shutdown_delay > 0:
            loop.run_until_complete(asyncio.sleep(self.settings.pyrit_loop_shutdown_delay))

        pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending_tasks:
            logger.debug("Draining %d pending asyncio task(s)", len(pending_tasks))
            loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))

        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        try:
            loop.run_until_complete(loop.shutdown_default_executor())
        except Exception:
            pass
        loop.close()

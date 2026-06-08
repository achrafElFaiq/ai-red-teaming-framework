import asyncio
import gc
import logging
from typing import Any, cast

from pyrit.executor.attack import (
    AttackAdversarialConfig,
    AttackScoringConfig,
    CrescendoAttack,
    PromptSendingAttack,
    RedTeamingAttack,
)
from pyrit.executor.attack.core.attack_executor import AttackExecutorResult
from pyrit.memory.central_memory import CentralMemory
from pyrit.memory.sqlite_memory import SQLiteMemory
from pyrit.prompt_target.openai.openai_chat_target import OpenAIChatTarget
from pyrit.score.true_false.self_ask_true_false_scorer import SelfAskTrueFalseScorer

from redteaming.settings import build_pyrit_attacker_config, build_pyrit_scorer_config, get_runtime_settings
from redteaming.domain.contracts.runner import Runner
from redteaming.domain.models.attack import Attack
from redteaming.domain.models.attack_result import AttackResult
from redteaming.infrastructure.http_attack_target import AttackTarget
from redteaming.plugins.pyrit.adapter import PyritAdapter

logger = logging.getLogger(__name__)


class PyritRunner(Runner):
    """Run PyRIT attacks and normalize their outputs into framework results."""

    def __init__(self):
        self.settings = get_runtime_settings(frameworks={"pyrit"})

    def run(self, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        self._initialize_memory()

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._run_async(target, attack))
        finally:
            asyncio.set_event_loop(None)
            self._shutdown_event_loop(loop)

    def _initialize_memory(self) -> None:
        CentralMemory.set_memory_instance(cast(Any, SQLiteMemory()))

    async def _run_async(self, target: AttackTarget, attack: Attack) -> list[AttackResult]:
        objective_target = self._prepare_objective_target(target)
        attacker_config = build_pyrit_attacker_config()
        result = await self._execute_orchestrator(attack, objective_target, attacker_config)
        self._log_backend_trace(result)
        return self._normalize_results(result, target, attack)

    def _prepare_objective_target(self, target: AttackTarget):
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
        orchestrator_type = self._resolve_orchestrator_type(attack)
        scorer_config = build_pyrit_scorer_config()

        if orchestrator_type == "dataset":
            logger.debug("Initializing dataset scorer for attack '%s'", attack.name)
            scorer_llm = self._build_scorer_llm(scorer_config)
            scorer = self._build_scorer(scorer_llm, attack)
            prompts = attack.config.get("prompts", [])
            logger.info("[PyRIT] Dataset mode — %d prompt(s), max_concurrency=%d",
                        len(prompts), self.settings.pyrit.dataset_max_concurrency)
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
        return attack.config.get("orchestrator", "red_teaming")

    def _build_attacker_llm(self, attacker_config: dict[str, str]) -> OpenAIChatTarget:
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
        return SelfAskTrueFalseScorer(
            chat_target=chat_target,
            true_false_question=attack.config.get("scoring_question"),
        )

    def _build_scorer_llm(self, scorer_config: dict[str, str]) -> OpenAIChatTarget:
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
        if isinstance(result, list):
            return self._normalize_dataset_batch(result, target, attack)
        if isinstance(result, AttackExecutorResult):
            return self._normalize_dataset_batch(result.completed_results, target, attack)
        return [self._normalize_single_result(result, target, attack)]

    def _normalize_dataset_batch(self, items: list[Any], target: AttackTarget, attack: Attack) -> list[AttackResult]:
        from redteaming.plugins.pyrit.normalizer import PyritNormalizer

        normalized: list[AttackResult] = []
        for index, individual_result in enumerate(items):
            attack_name = self._build_dataset_attack_name(attack.name, individual_result.objective, index)
            normalizer = PyritNormalizer(
                pyrit_result=individual_result,
                target_url=target.url,
                attack_name=attack_name,
            )
            normalized.append(normalizer.normalize())

        return normalized

    def _build_dataset_attack_name(self, base_attack_name: str, objective: str, index: int) -> str:
        prompt_preview = objective[:60]
        return f"{base_attack_name} | [{index + 1:02d}] {prompt_preview}"

    def _normalize_single_result(self, result: Any, target: AttackTarget, attack: Attack) -> AttackResult:
        from redteaming.plugins.pyrit.normalizer import PyritNormalizer

        normalizer = PyritNormalizer(
            pyrit_result=result,
            target_url=target.url,
            attack_name=attack.name,
        )
        return normalizer.normalize()

    def _shutdown_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        gc.collect()

        if self.settings.pyrit.loop_shutdown_delay > 0:
            loop.run_until_complete(asyncio.sleep(self.settings.pyrit.loop_shutdown_delay))

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



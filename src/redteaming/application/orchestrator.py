import logging
import time
from datetime import datetime

from redteaming.domain.models.attack import Attack
from redteaming.domain.models.attack_result import AttackResult
from redteaming.infrastructure.http_attack_target import AttackTarget
from redteaming.infrastructure.persistence.json_report_store import JsonReportStore


logger = logging.getLogger(__name__)


class AttackOrchestrator:
	def __init__(
		self,
		target: AttackTarget,
		campaign_name: str = "",
		attacks: list[Attack] = None,
		report_store: JsonReportStore | None = None,
		reset_target_between_attacks: bool = True,
	):
		self.attacks = attacks or []
		self.target = target
		self.campaign_name = campaign_name
		self.report_store = report_store or JsonReportStore()
		self.reset_target_between_attacks = reset_target_between_attacks
		self.results: list[AttackResult] = []
		self.saved_report_paths: list[str] = []
		self.technical_failures: list[dict[str, str]] = []
		self.campaign_run_id: str = ""
		self.campaign_run_timestamp: datetime | None = None

	def execute_attacks(self) -> list[AttackResult]:
		self.results = []
		self.saved_report_paths = []
		self.technical_failures = []
		self.campaign_run_timestamp = datetime.now()
		self.campaign_run_id = self.campaign_run_timestamp.strftime("%Y%m%d_%H%M%S_%f")
		total = len(self.attacks)
		campaign_start = time.monotonic()
		logger.info(
			"[Campaign] Starting campaign on target '%s' — %d attack(s)",
			self.target.name,
			total,
		)
		for index, attack in enumerate(self.attacks, 1):
			logger.info("─" * 60)
			logger.info(
				"[Attack %d/%d] Starting '%s' [%s]",
				index, total, attack.name, attack.framework,
			)
			attack_start = time.monotonic()
			try:
				attack_results = attack.execute(self.target)

				for result in attack_results:
					result.campaign_name = self.campaign_name
					result.campaign_run_id = self.campaign_run_id
					result.campaign_run_timestamp = self.campaign_run_timestamp
					result.target_model = getattr(self.target, "model", "")
					result.target_architecture_type = getattr(self.target, "architecture_type", "")

				self.results.extend(attack_results)
				saved_paths = self.report_store.save_batch(attack_results)
				self.saved_report_paths.extend(str(path) for path in saved_paths)

				elapsed = time.monotonic() - attack_start
				outcome = self._summarize_outcome(attack_results)
				logger.info(
					"[Attack %d/%d] Completed '%s' in %.1fs — %d result(s) — %s",
					index, total, attack.name, elapsed, len(attack_results), outcome,
				)
				for path in saved_paths:
					logger.info("[Attack %d/%d] Report saved → %s", index, total, path)
			except Exception as exc:
				elapsed = time.monotonic() - attack_start
				logger.error(
					"[Attack %d/%d] FAILED '%s' after %.1fs — %s: %s",
					index, total, attack.name, elapsed, type(exc).__name__, exc,
				)
				self._record_execution_error(attack, exc)
			finally:
				if self.reset_target_between_attacks:
					logger.debug("Resetting target state after attack '%s'", attack.name)
					self.target.reset_history()

		campaign_elapsed = time.monotonic() - campaign_start
		breached = sum(1 for r in self.results if self._result_has_failure(r))
		hardened = len(self.results) - breached
		logger.info("─" * 60)
		logger.info(
			"[Campaign] Finished in %.1fs — %d attack(s), %d result(s), "
			"%d report(s), %d error(s) — 🔴 %d breached / 🟢 %d hardened",
			campaign_elapsed, total, self.result_count, self.report_count,
			len(self.technical_failures), breached, hardened,
		)
		return self.results

	def add_attack(self, attack: Attack):
		self.attacks.append(attack)

	@property
	def result_count(self) -> int:
		return len(self.results)

	@property
	def report_count(self) -> int:
		return len(self.saved_report_paths)

	@property
	def executed_attack_names(self) -> list[str]:
		return [attack.name for attack in self.attacks]

	@property
	def has_failures(self) -> bool:
		return any(self._result_has_failure(result) for result in self.results)

	@property
	def has_execution_errors(self) -> bool:
		return bool(self.technical_failures)

	def summary(self) -> dict[str, object]:
		failure_count = sum(1 for result in self.results if self._result_has_failure(result))
		return {
			"attack_count": len(self.attacks),
			"result_count": self.result_count,
			"report_count": self.report_count,
			"failure_count": failure_count,
			"has_failures": failure_count > 0,
			"technical_failure_count": len(self.technical_failures),
			"has_execution_errors": self.has_execution_errors,
			"executed_attack_names": self.executed_attack_names,
			"technical_failures": self.technical_failures,
		}

	@staticmethod
	def _result_has_failure(result: AttackResult) -> bool:
		if result.conversation is not None:
			return result.conversation.achieved
		if result.prompts:
			return any(not prompt.passed for prompt in result.prompts)
		return False

	def _record_execution_error(self, attack: Attack, exc: Exception) -> None:
		self.technical_failures.append(
			{
				"attack_name": attack.name,
				"error_type": type(exc).__name__,
				"message": str(exc),
			}
		)

	def _summarize_outcome(self, results: list[AttackResult]) -> str:
		breached = sum(1 for r in results if self._result_has_failure(r))
		if breached == 0:
			return "🟢 ALL HARDENED"
		if breached == len(results):
			return "🔴 ALL BREACHED"
		return f"🔴 {breached}/{len(results)} BREACHED"


__all__ = ["AttackOrchestrator"]



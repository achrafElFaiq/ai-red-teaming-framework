"""Concrete HTTP attack target implementation for the framework."""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class AttackTarget:
    def __init__(
        self,
        name: str,
        chat_url: str,
        reset_memory_url: str | None = None,
        input_field: str = "prompt",
        output_field: str = "response",
        model: str = "",
        architecture_type: str = "",
    ):
        self.name = name
        self.chat_url = chat_url
        self.reset_memory_url = reset_memory_url or ""
        self.input_field = input_field
        self.output_field = output_field
        self.model = model
        self.architecture_type = architecture_type

    @property
    def url(self) -> str:
        return self.chat_url

    def query(self, prompt: str) -> Optional[str]:
        logger.debug("Sending prompt to target '%s' (length=%d)", self.name, len(prompt))
        payload = {self.input_field: prompt}

        try:
            response = requests.post(self.chat_url, json=payload, timeout=(5, 50))
            response.raise_for_status()
            body = response.json()
            return body.get(self.output_field, "")
        except requests.Timeout:
            logger.warning("Target '%s' request timed out", self.name)
        except requests.HTTPError as e:
            logger.error("Target '%s' returned HTTP %s", self.name, e.response.status_code)
        except requests.ConnectionError:
            logger.error("Target '%s' connection failed", self.name)
        except requests.RequestException as e:
            logger.error("Target '%s' request failed: %s", self.name, e)
        except ValueError:
            logger.error("Target '%s' returned invalid JSON response", self.name)

        return None

    def reset_history(self) -> None:
        if not self.reset_memory_url:
            logger.debug("No reset_memory_url configured for target '%s'; skipping reset", self.name)
            return

        try:
            response = requests.post(self.reset_memory_url, timeout=(5, 10))
            response.raise_for_status()
            logger.debug("Target '%s' history reset successfully", self.name)
        except requests.Timeout:
            logger.warning("Target '%s' reset timed out", self.name)
        except requests.HTTPError as e:
            logger.error("Target '%s' reset returned HTTP %s", self.name, e.response.status_code)
        except requests.ConnectionError:
            logger.error("Target '%s' reset connection failed", self.name)
        except requests.RequestException as e:
            logger.error("Target '%s' reset failed: %s", self.name, e)

    def __str__(self):
        return (
            f"AttackTarget(name={self.name}, chat_url={self.chat_url}, "
            f"reset_memory_url={self.reset_memory_url or 'disabled'}, "
            f"model={self.model or 'n/a'}, architecture_type={self.architecture_type or 'n/a'}, "
            f"input_field={self.input_field}, output_field={self.output_field})"
        )


__all__ = ["AttackTarget"]



"""Fixtures partagées : fiche réelle, dataset et doublures sans réseau."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from anomalie_radar.llm import ClientLLM
from anomalie_radar.paradigm import Paradigme, charger_paradigme

RACINE = Path(__file__).resolve().parents[1]
FICHE = RACINE / "paradigmes" / "chirurgie.yaml"
DATASET = RACINE / "tests" / "eval_dataset.json"
FIXTURES = RACINE / "tests" / "fixtures"


@pytest.fixture
def chemin_fiche() -> Path:
    return FICHE


@pytest.fixture
def chemin_dataset() -> Path:
    return DATASET


@pytest.fixture
def dossier_fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def paradigme() -> Paradigme:
    return charger_paradigme(FICHE)


class LLMFactice(ClientLLM):
    """Client LLM simulé : rejoue des réponses dans l'ordre, sans réseau."""

    def __init__(self, reponses: Sequence[str]) -> None:
        self.reponses = list(reponses)
        self.appels: list[tuple[str, str]] = []

    def completer(self, prompt_systeme: str, prompt_utilisateur: str) -> str:
        self.appels.append((prompt_systeme, prompt_utilisateur))
        if not self.reponses:
            raise AssertionError("plus de réponses LLM simulées")
        return self.reponses.pop(0)


class HTTPFactice:
    """Client HTTP simulé : rejoue des réponses texte dans l'ordre."""

    def __init__(self, reponses: Sequence[str]) -> None:
        self.reponses = list(reponses)
        self.appels: list[tuple[str, dict[str, str]]] = []

    def get_text(self, url: str, params: Mapping[str, str] | None = None) -> str:
        self.appels.append((url, dict(params or {})))
        if not self.reponses:
            raise AssertionError("plus de réponses HTTP simulées")
        return self.reponses.pop(0)

    def post_json(
        self,
        url: str,
        charge: Mapping[str, Any],
        entetes: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        raise AssertionError("post_json ne doit pas être appelé dans ce test")

"""Prompts et orchestration du classifieur avec un LLM simulé."""

from __future__ import annotations

from conftest import LLMFactice

from anomalie_radar.classifier import (
    classer_item,
    classer_items,
    construire_prompt_item,
    construire_prompt_systeme,
)
from anomalie_radar.models import Item

REPONSE_T1 = (
    "item: Méniscectomie versus sham\n"
    "these: T1\n"
    "type: contradiction\n"
    "score: 5\n"
    "preuve: la méniscectomie n'a pas fait mieux que le sham\n"
    "sauvetage_detecte: non"
)

ITEM = Item(
    titre="Méniscectomie versus sham",
    doi="10.1056/NEJMoa1305189",
    resume="Dans cet essai, la méniscectomie n'a pas fait mieux que le sham.",
)


def test_prompt_systeme_contient_fiche_et_few_shot(paradigme) -> None:
    prompt = construire_prompt_systeme(paradigme)
    assert "chirurgie" in prompt
    assert "T6" in prompt
    assert "Moseley" in prompt
    assert "contradiction" in prompt
    assert "contrôle négatif" in prompt
    assert "consensus" in prompt
    assert "sauvetage_detecte" in prompt


def test_prompt_item_contient_titre_et_doi() -> None:
    prompt = construire_prompt_item(ITEM)
    assert "Méniscectomie versus sham" in prompt
    assert "10.1056/NEJMoa1305189" in prompt


def test_classer_item_avec_llm_simule(paradigme) -> None:
    client = LLMFactice([REPONSE_T1])
    classification = classer_item(ITEM, paradigme, client)
    assert classification.valide, classification.erreurs
    assert classification.these == "T1"
    assert len(client.appels) == 1
    assert "Méniscectomie" in client.appels[0][1]


def test_classer_items(paradigme) -> None:
    client = LLMFactice([REPONSE_T1, "RIEN"])
    resultats = classer_items([ITEM, ITEM], paradigme, client)
    assert [resultat.these for resultat in resultats] == ["T1", None]
    assert len(client.appels) == 2

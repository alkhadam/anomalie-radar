"""Évaluation hors ligne : rappel et faux positifs sur contrôles négatifs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import DATASET

from anomalie_radar.errors import ErreurEvaluation
from anomalie_radar.evaluation import (
    CasEvaluation,
    charger_dataset,
    evaluer,
    formater_rapport,
)
from anomalie_radar.models import Item

ITEM = Item(
    titre="Méniscectomie versus sham",
    doi="10.1056/NEJMoa1305189",
    resume="Dans cet essai, la méniscectomie n'a pas fait mieux que le sham.",
)

REPONSE_T1 = (
    "these: T1\n"
    "type: contradiction\n"
    "score: 5\n"
    "preuve: la méniscectomie n'a pas fait mieux que le sham\n"
    "sauvetage_detecte: non"
)


def test_charger_dataset(paradigme) -> None:
    cas = charger_dataset(DATASET, paradigme)
    assert len(cas) == 16
    assert sum(1 for entree in cas if entree.these_attendue == "AUCUNE") == 3
    assert all(entree.reponse_llm is not None for entree in cas)


def test_evaluation_complete_sans_reseau(paradigme) -> None:
    cas = charger_dataset(DATASET, paradigme)
    rapport = evaluer(cas, paradigme)
    assert rapport.retrouvees == 13
    assert rapport.attendues == 13
    assert rapport.manquees == []
    assert rapport.faux_positifs == 0
    assert rapport.invalides == 0
    assert rapport.rappel == 1.0
    assert rapport.taux_faux_positifs == 0.0
    texte = formater_rapport(rapport)
    assert "13/13" in texte
    assert "taux 0.0%" in texte
    assert "Manquées : aucune" in texte


def test_faux_positif_compte(paradigme) -> None:
    cas = [CasEvaluation(item=ITEM, these_attendue="AUCUNE", reponse_llm=REPONSE_T1)]
    rapport = evaluer(cas, paradigme)
    assert rapport.faux_positifs == 1
    assert rapport.taux_faux_positifs == 1.0
    assert rapport.details == [("Méniscectomie versus sham", "AUCUNE", "T1")]


def test_manquee_comptee(paradigme) -> None:
    cas = [CasEvaluation(item=ITEM, these_attendue="T2", reponse_llm=REPONSE_T1)]
    rapport = evaluer(cas, paradigme)
    assert rapport.retrouvees == 0
    assert len(rapport.manquees) == 1


def test_reponse_manquante_sans_client(paradigme) -> None:
    cas = [CasEvaluation(item=ITEM, these_attendue="T1", reponse_llm=None)]
    with pytest.raises(ErreurEvaluation, match="Aucune réponse"):
        evaluer(cas, paradigme)


def test_dataset_these_inconnue(paradigme, tmp_path: Path) -> None:
    chemin = tmp_path / "dataset.json"
    chemin.write_text(
        json.dumps(
            {
                "cas": [
                    {
                        "item": {"titre": "Test", "resume": "Résumé."},
                        "attendu": "T9",
                        "reponse_llm": "RIEN",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ErreurEvaluation, match="thèse inconnue"):
        charger_dataset(chemin, paradigme)


def test_dataset_absent(paradigme, tmp_path: Path) -> None:
    with pytest.raises(ErreurEvaluation, match="introuvable"):
        charger_dataset(tmp_path / "absent.json", paradigme)

"""CLI de bout en bout, sans réseau (doublures injectées)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import DATASET, FICHE, FIXTURES, HTTPFactice, LLMFactice

from anomalie_radar.cli import main

ITEM_DICT = {
    "titre": "Méniscectomie versus sham",
    "doi": "10.1056/NEJMoa1305189",
    "resume": "Dans cet essai, la méniscectomie n'a pas fait mieux que le sham.",
}

REPONSE_T1 = (
    "these: T1\n"
    "type: contradiction\n"
    "score: 5\n"
    "preuve: la méniscectomie n'a pas fait mieux que le sham\n"
    "sauvetage_detecte: non"
)


def test_eval_hors_ligne(capsys) -> None:
    code = main(["eval", "--paradigme", str(FICHE), "--dataset", str(DATASET)])
    sortie = capsys.readouterr()
    assert code == 0
    assert "13/13" in sortie.out
    assert "taux 0.0%" in sortie.out


def test_eval_detecte_un_faux_positif(tmp_path: Path, capsys) -> None:
    dataset = tmp_path / "dataset.json"
    dataset.write_text(
        json.dumps(
            {"cas": [{"item": ITEM_DICT, "attendu": "AUCUNE", "reponse_llm": REPONSE_T1}]}
        ),
        encoding="utf-8",
    )
    code = main(["eval", "--paradigme", str(FICHE), "--dataset", str(dataset)])
    sortie = capsys.readouterr()
    assert code == 1
    assert "Faux positifs : 1/1" in sortie.out


def test_classify_ecrit_les_resultats(tmp_path: Path, capsys) -> None:
    items = tmp_path / "items.json"
    items.write_text(json.dumps({"items": [ITEM_DICT]}), encoding="utf-8")
    sortie = tmp_path / "sorties.json"
    code = main(
        [
            "classify",
            "--paradigme",
            str(FICHE),
            "--items",
            str(items),
            "--out",
            str(sortie),
        ],
        client_llm=LLMFactice([REPONSE_T1]),
    )
    assert code == 0
    donnees = json.loads(sortie.read_text(encoding="utf-8"))
    assert donnees[0]["these"] == "T1"
    assert donnees[0]["valide"] is True
    assert "these: T1" in capsys.readouterr().out


def test_classify_signale_une_sortie_invalide(tmp_path: Path, capsys) -> None:
    items = tmp_path / "items.json"
    items.write_text(json.dumps({"items": [ITEM_DICT]}), encoding="utf-8")
    reponse = REPONSE_T1.replace("these: T1", "these: T9")
    code = main(
        ["classify", "--paradigme", str(FICHE), "--items", str(items)],
        client_llm=LLMFactice([reponse]),
    )
    assert code == 1
    assert "SORTIE INVALIDE" in capsys.readouterr().out


def test_collect_pubmed_avec_doublure(tmp_path: Path, capsys) -> None:
    xml = (FIXTURES / "pubmed_sample.xml").read_text(encoding="utf-8")
    reponse = json.dumps({"esearchresult": {"idlist": ["11111111", "22222222"]}})
    sortie = tmp_path / "items.json"
    code = main(
        [
            "collect",
            "--paradigme",
            str(FICHE),
            "--source",
            "pubmed",
            "--max-results",
            "2",
            "--out",
            str(sortie),
        ],
        client_http=HTTPFactice([reponse, xml]),
    )
    assert code == 0
    items = json.loads(sortie.read_text(encoding="utf-8"))
    assert len(items) == 2
    assert "2 item(s) collecté(s)" in capsys.readouterr().out


def test_fiche_absente(tmp_path: Path, capsys) -> None:
    code = main(
        [
            "eval",
            "--paradigme",
            str(tmp_path / "absente.yaml"),
            "--dataset",
            str(DATASET),
        ]
    )
    assert code == 2
    assert "erreur :" in capsys.readouterr().err


def test_sans_commande() -> None:
    with pytest.raises(SystemExit):
        main([])

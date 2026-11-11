"""Lecture et écriture JSON des items."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from anomalie_radar.errors import ErreurDonnees
from anomalie_radar.models import Item
from anomalie_radar.storage import charger_items, sauvegarder_json


def test_aller_retour(tmp_path: Path) -> None:
    chemin = tmp_path / "items.json"
    sauvegarder_json(chemin, [Item(titre="A", doi="10.1/a", resume="R").vers_dict()])
    items = charger_items(chemin)
    assert len(items) == 1
    assert items[0].titre == "A"
    assert items[0].doi == "10.1/a"


def test_objet_items(tmp_path: Path) -> None:
    chemin = tmp_path / "items.json"
    chemin.write_text(
        json.dumps({"items": [{"titre": "B", "resume": "R"}]}), encoding="utf-8"
    )
    assert charger_items(chemin)[0].titre == "B"


def test_json_invalide(tmp_path: Path) -> None:
    chemin = tmp_path / "items.json"
    chemin.write_text("{", encoding="utf-8")
    with pytest.raises(ErreurDonnees, match="JSON invalide"):
        charger_items(chemin)


def test_fichier_absent(tmp_path: Path) -> None:
    with pytest.raises(ErreurDonnees, match="introuvable"):
        charger_items(tmp_path / "absent.json")


def test_item_sans_titre(tmp_path: Path) -> None:
    chemin = tmp_path / "items.json"
    chemin.write_text(json.dumps([{"doi": "10.1/a"}]), encoding="utf-8")
    with pytest.raises(ErreurDonnees, match="titre"):
        charger_items(chemin)

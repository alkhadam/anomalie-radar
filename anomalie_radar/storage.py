"""Lecture et écriture des fichiers JSON du pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ErreurDonnees
from .models import Item


def charger_items(chemin: str | Path) -> list[Item]:
    chemin = Path(chemin)
    try:
        brut: Any = json.loads(chemin.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ErreurDonnees(f"Fichier d'items introuvable : {chemin}") from exc
    except json.JSONDecodeError as exc:
        raise ErreurDonnees(f"JSON invalide dans {chemin} : {exc}") from exc
    if isinstance(brut, dict):
        brut = brut.get("items")
    if not isinstance(brut, list):
        raise ErreurDonnees(f"{chemin} : liste d'items attendue")
    return [Item.depuis_dict(entree) for entree in brut]


def sauvegarder_json(chemin: str | Path, donnees: Any) -> None:
    chemin = Path(chemin)
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(
            json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        raise ErreurDonnees(f"Écriture impossible : {chemin}") from exc

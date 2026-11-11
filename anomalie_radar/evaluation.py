"""Évaluation : rappel sur les anomalies connues et faux positifs T6."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .classifier import classer_item, classer_texte
from .errors import ErreurDonnees, ErreurEvaluation
from .llm import ClientLLM
from .models import AUCUNE_THESE, Item
from .paradigm import Paradigme


@dataclass(frozen=True)
class CasEvaluation:
    """Un cas d'évaluation : item, thèse attendue (ou AUCUNE) et réponse figée."""

    item: Item
    these_attendue: str
    reponse_llm: str | None = None


@dataclass
class RapportEvaluation:
    total: int
    attendues: int
    retrouvees: int
    neutres: int
    faux_positifs: int
    invalides: int
    manquees: list[str] = field(default_factory=list)
    details: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def rappel(self) -> float:
        return self.retrouvees / self.attendues if self.attendues else 0.0

    @property
    def taux_faux_positifs(self) -> float:
        return self.faux_positifs / self.neutres if self.neutres else 0.0


def charger_dataset(chemin: str | Path, paradigme: Paradigme) -> list[CasEvaluation]:
    """Charge un jeu d'évaluation JSON et vérifie que les thèses existent."""
    chemin = Path(chemin)
    try:
        brut: Any = json.loads(chemin.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ErreurEvaluation(f"Jeu d'évaluation introuvable : {chemin}") from exc
    except json.JSONDecodeError as exc:
        raise ErreurEvaluation(f"JSON invalide dans {chemin} : {exc}") from exc
    if not isinstance(brut, dict) or not isinstance(brut.get("cas"), list):
        raise ErreurEvaluation(f"{chemin} : clé 'cas' (liste) attendue")
    cas_bruts = brut["cas"]
    if not cas_bruts:
        raise ErreurEvaluation(f"{chemin} : jeu d'évaluation vide")
    cas: list[CasEvaluation] = []
    for index, entree in enumerate(cas_bruts):
        chemin_cas = f"cas[{index}]"
        if not isinstance(entree, dict):
            raise ErreurEvaluation(f"{chemin_cas} : mapping attendu")
        try:
            item = Item.depuis_dict(entree.get("item", {}))
        except ErreurDonnees as exc:
            raise ErreurEvaluation(f"{chemin_cas}.item : {exc}") from exc
        attendu = entree.get("attendu")
        if not isinstance(attendu, str) or not attendu.strip():
            raise ErreurEvaluation(f"{chemin_cas}.attendu : chaîne attendue")
        attendu = attendu.strip().upper()
        if attendu != AUCUNE_THESE and paradigme.these(attendu) is None:
            raise ErreurEvaluation(f"{chemin_cas}.attendu : thèse inconnue {attendu}")
        reponse = entree.get("reponse_llm")
        if reponse is not None and not isinstance(reponse, str):
            raise ErreurEvaluation(f"{chemin_cas}.reponse_llm : chaîne attendue")
        cas.append(CasEvaluation(item=item, these_attendue=attendu, reponse_llm=reponse))
    return cas


def evaluer(
    cas: list[CasEvaluation], paradigme: Paradigme, client: ClientLLM | None = None
) -> RapportEvaluation:
    """Mesure le rappel et le taux de faux positifs (contrôles négatifs)."""
    rapport = RapportEvaluation(
        total=len(cas),
        attendues=0,
        retrouvees=0,
        neutres=0,
        faux_positifs=0,
        invalides=0,
    )
    for entree in cas:
        if entree.reponse_llm is not None:
            classification = classer_texte(entree.item, paradigme, entree.reponse_llm)
        elif client is not None:
            classification = classer_item(entree.item, paradigme, client)
        else:
            raise ErreurEvaluation(
                "Aucune réponse LLM figée et aucun client fourni pour l'évaluation"
            )
        if not classification.valide:
            rapport.invalides += 1
        if entree.these_attendue == AUCUNE_THESE:
            rapport.neutres += 1
            if classification.est_anomalie:
                rapport.faux_positifs += 1
                rapport.details.append(
                    (entree.item.titre, AUCUNE_THESE, str(classification.these))
                )
            continue
        rapport.attendues += 1
        if classification.valide and classification.these == entree.these_attendue:
            rapport.retrouvees += 1
        else:
            rapport.manquees.append(
                f"{entree.item.titre} (attendu {entree.these_attendue}, "
                f"obtenu {classification.these or 'RIEN'})"
            )
    return rapport


def formater_rapport(rapport: RapportEvaluation) -> str:
    entete = (
        f"Évaluation : {rapport.total} cas "
        f"({rapport.attendues} anomalies attendues, {rapport.neutres} contrôles négatifs)"
    )
    rappel = (
        f"Anomalies retrouvées : {rapport.retrouvees}/{rapport.attendues} "
        f"(rappel {rapport.rappel:.1%})"
    )
    faux_positifs = (
        f"Faux positifs : {rapport.faux_positifs}/{rapport.neutres} "
        f"(taux {rapport.taux_faux_positifs:.1%})"
    )
    lignes = [
        entete,
        rappel,
        faux_positifs,
        f"Sorties invalides : {rapport.invalides}",
    ]
    if rapport.manquees:
        lignes.append("Manquées :")
        lignes.extend(f"- {texte}" for texte in rapport.manquees)
    else:
        lignes.append("Manquées : aucune")
    return "\n".join(lignes)

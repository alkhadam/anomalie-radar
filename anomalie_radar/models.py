"""Structures de données partagées : items collectés et classifications."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .errors import ErreurDonnees

AUCUNE_THESE = "AUCUNE"


@dataclass(frozen=True)
class Item:
    """Un travail scientifique candidat (titre, DOI, résumé)."""

    titre: str
    doi: str | None = None
    resume: str = ""
    source: str = ""
    identifiant: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.titre, str) or not self.titre.strip():
            raise ErreurDonnees("item.titre : chaîne non vide attendue")

    @property
    def texte(self) -> str:
        """Texte intégral utilisé pour vérifier la preuve citée."""
        return f"{self.titre}\n{self.resume}".strip()

    @property
    def ligne_identification(self) -> str:
        if self.doi:
            return f"{self.titre} — DOI: {self.doi}"
        return self.titre

    def vers_dict(self) -> dict[str, Any]:
        return {
            "titre": self.titre,
            "doi": self.doi,
            "resume": self.resume,
            "source": self.source,
            "identifiant": self.identifiant,
        }

    @classmethod
    def depuis_dict(cls, donnees: Mapping[str, Any]) -> Item:
        if not isinstance(donnees, Mapping):
            raise ErreurDonnees("item : objet JSON attendu")
        titre = donnees.get("titre", donnees.get("title"))
        if not isinstance(titre, str) or not titre.strip():
            raise ErreurDonnees("item.titre : chaîne non vide attendue")
        doi = donnees.get("doi")
        resume = donnees.get("resume", "")
        source = donnees.get("source", "")
        identifiant = donnees.get("identifiant")
        if doi is not None and not isinstance(doi, str):
            raise ErreurDonnees("item.doi : chaîne attendue")
        if not isinstance(resume, str):
            raise ErreurDonnees("item.resume : chaîne attendue")
        if not isinstance(source, str):
            raise ErreurDonnees("item.source : chaîne attendue")
        if identifiant is not None and not isinstance(identifiant, str):
            raise ErreurDonnees("item.identifiant : chaîne attendue")
        return cls(
            titre=titre.strip(),
            doi=doi.strip() if doi else None,
            resume=resume.strip(),
            source=source.strip(),
            identifiant=identifiant.strip() if identifiant else None,
        )


@dataclass
class Classification:
    """Résultat du classifieur pour un item, éventuellement marqué invalide."""

    item: Item
    these: str | None
    type: str | None = None
    score: int | None = None
    preuve: str | None = None
    sauvetage_detecte: str | None = None
    valide: bool = True
    erreurs: list[str] = field(default_factory=list)

    @property
    def est_rien(self) -> bool:
        return self.these is None

    @property
    def est_anomalie(self) -> bool:
        """Vrai uniquement pour une sortie valide qui touche une thèse."""
        return self.valide and self.these is not None

    def formater(self) -> str:
        if not self.valide:
            raisons = " ; ".join(self.erreurs) if self.erreurs else "raison inconnue"
            return f"SORTIE INVALIDE : {raisons}"
        if self.these is None:
            return "RIEN"
        return "\n".join(
            [
                f"item: {self.item.ligne_identification}",
                f"these: {self.these}",
                f"type: {self.type}",
                f"score: {self.score}",
                f"preuve: {self.preuve}",
                f"sauvetage_detecte: {self.sauvetage_detecte}",
            ]
        )

    def vers_dict(self) -> dict[str, Any]:
        return {
            "item": self.item.vers_dict(),
            "these": self.these,
            "type": self.type,
            "score": self.score,
            "preuve": self.preuve,
            "sauvetage_detecte": self.sauvetage_detecte,
            "valide": self.valide,
            "erreurs": list(self.erreurs),
        }

"""Chargement et validation d'une fiche paradigme YAML."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import ErreurParadigme

_ID_THESE = re.compile(r"^T[0-9]+$")


@dataclass(frozen=True)
class These:
    """Une thèse du paradigme, avec ses critères de réfutation et exemples."""

    id: str
    these: str
    statut: str | None = None
    usage: str | None = None
    note_croisee: str | None = None
    refutation: tuple[str, ...] = ()
    sauvetages_ad_hoc: tuple[str, ...] = ()
    anomalies_connues: tuple[str, ...] = ()

    @property
    def est_controle_negatif(self) -> bool:
        texte = f"{self.statut or ''} {self.usage or ''}".casefold()
        return "contrôle négatif" in texte or "controle negatif" in texte


@dataclass(frozen=True)
class Paradigme:
    """Fiche paradigme validée, immuable."""

    domaine: str
    version: str
    paradigme_resume: str
    theses: tuple[These, ...]
    types_anomalie: dict[str, str]
    sources: tuple[str, ...]
    format_sortie: str
    regle_sortie: str
    chemin: Path | None = None

    def these(self, identifiant: str) -> These | None:
        for candidate in self.theses:
            if candidate.id == identifiant:
                return candidate
        return None

    @property
    def identifiants_theses(self) -> tuple[str, ...]:
        return tuple(these.id for these in self.theses)

    @property
    def identifiants_controle_negatif(self) -> tuple[str, ...]:
        return tuple(these.id for these in self.theses if these.est_controle_negatif)

    def anomalies_connues(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (these.id, anomalie)
            for these in self.theses
            for anomalie in these.anomalies_connues
        )


def _texte_obligatoire(
    conteneur: dict[str, Any], cle: str, chemin: str, erreurs: list[str]
) -> str:
    valeur = conteneur.get(cle)
    prefixe = f"{chemin}." if chemin else ""
    if not isinstance(valeur, str) or not valeur.strip():
        erreurs.append(f"{prefixe}{cle} : chaîne non vide attendue")
        return ""
    return valeur.strip()


def _texte_optionnel(conteneur: dict[str, Any], cle: str) -> str | None:
    valeur = conteneur.get(cle)
    if isinstance(valeur, str) and valeur.strip():
        return valeur.strip()
    return None


def _liste_textes(
    conteneur: dict[str, Any], cle: str, chemin: str, erreurs: list[str]
) -> tuple[str, ...]:
    valeur = conteneur.get(cle, [])
    if valeur is None:
        return ()
    if not isinstance(valeur, list):
        erreurs.append(f"{chemin}.{cle} : liste de chaînes attendue")
        return ()
    resultat: list[str] = []
    for index, entree in enumerate(valeur):
        if not isinstance(entree, str) or not entree.strip():
            erreurs.append(f"{chemin}.{cle}[{index}] : chaîne non vide attendue")
            continue
        resultat.append(entree.strip())
    return tuple(resultat)


def _lire_these(
    entree: Any, index: int, vus: set[str], erreurs: list[str]
) -> These | None:
    chemin = f"theses[{index}]"
    if not isinstance(entree, dict):
        erreurs.append(f"{chemin} : mapping attendu")
        return None
    identifiant = entree.get("id")
    if not isinstance(identifiant, str) or not _ID_THESE.match(identifiant.strip()):
        erreurs.append(f"{chemin}.id : identifiant T1, T2, ... attendu")
        identifiant_valide = None
    else:
        identifiant_valide = identifiant.strip()
        if identifiant_valide in vus:
            erreurs.append(f"{chemin}.id : identifiant dupliqué {identifiant_valide}")
        vus.add(identifiant_valide)
    contenu = entree.get("these")
    if not isinstance(contenu, str) or not contenu.strip():
        erreurs.append(f"{chemin}.these : chaîne non vide attendue")
    if identifiant_valide is None:
        return None
    return These(
        id=identifiant_valide,
        these=contenu.strip() if isinstance(contenu, str) else "",
        statut=_texte_optionnel(entree, "statut"),
        usage=_texte_optionnel(entree, "usage"),
        note_croisee=_texte_optionnel(entree, "note_croisee"),
        refutation=_liste_textes(entree, "refutation", chemin, erreurs),
        sauvetages_ad_hoc=_liste_textes(entree, "sauvetages_ad_hoc", chemin, erreurs),
        anomalies_connues=_liste_textes(entree, "anomalies_connues", chemin, erreurs),
    )


def charger_paradigme(chemin: str | Path) -> Paradigme:
    """Charge et valide une fiche paradigme ; lève ErreurParadigme sinon."""
    chemin = Path(chemin)
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError as exc:
        raise ErreurParadigme(f"Fiche paradigme introuvable ou illisible : {chemin}") from exc
    try:
        brut = yaml.safe_load(texte)
    except yaml.YAMLError as exc:
        raise ErreurParadigme(f"YAML invalide dans {chemin} : {exc}") from exc
    if not isinstance(brut, dict):
        raise ErreurParadigme(f"{chemin} : un objet YAML (mapping) est attendu")

    erreurs: list[str] = []
    domaine = _texte_obligatoire(brut, "domaine", "", erreurs)
    version_brute = brut.get("version")
    if isinstance(version_brute, (int, float)):
        version = str(version_brute)
    elif isinstance(version_brute, str) and version_brute.strip():
        version = version_brute.strip()
    else:
        erreurs.append("version : chaîne ou nombre attendu")
        version = ""
    paradigme_resume = _texte_obligatoire(brut, "paradigme_resume", "", erreurs)

    theses_brutes = brut.get("theses")
    theses: list[These] = []
    if not isinstance(theses_brutes, list) or not theses_brutes:
        erreurs.append("theses : liste non vide attendue")
    else:
        vus: set[str] = set()
        for index, entree in enumerate(theses_brutes):
            these = _lire_these(entree, index, vus, erreurs)
            if these is not None:
                theses.append(these)

    types_bruts = brut.get("types_anomalie")
    types: dict[str, str] = {}
    if not isinstance(types_bruts, dict) or not types_bruts:
        erreurs.append("types_anomalie : mapping non vide attendu")
    else:
        for nom, description in types_bruts.items():
            if not isinstance(nom, str) or not nom.strip():
                erreurs.append("types_anomalie : nom de type invalide")
            elif not isinstance(description, str) or not description.strip():
                erreurs.append(f"types_anomalie.{nom} : description non vide attendue")
            else:
                types[nom.strip()] = description.strip()

    sources_brutes = brut.get("sources")
    if not isinstance(sources_brutes, list):
        erreurs.append("sources : liste attendue")
        sources: tuple[str, ...] = ()
    else:
        sources_valides: list[str] = []
        for index, source in enumerate(sources_brutes):
            if not isinstance(source, str) or not source.strip():
                erreurs.append(f"sources[{index}] : chaîne non vide attendue")
                continue
            sources_valides.append(source.strip())
        sources = tuple(sources_valides)

    sortie = brut.get("sortie_attendue")
    if not isinstance(sortie, dict):
        erreurs.append("sortie_attendue : mapping attendu")
        format_sortie = ""
        regle_sortie = ""
    else:
        format_sortie = _texte_obligatoire(sortie, "format", "sortie_attendue", erreurs)
        regle_sortie = _texte_obligatoire(sortie, "regle", "sortie_attendue", erreurs)

    if erreurs:
        raise ErreurParadigme("Fiche paradigme invalide : " + " | ".join(erreurs))

    return Paradigme(
        domaine=domaine,
        version=version,
        paradigme_resume=paradigme_resume,
        theses=tuple(theses),
        types_anomalie=types,
        sources=sources,
        format_sortie=format_sortie,
        regle_sortie=regle_sortie,
        chemin=chemin,
    )

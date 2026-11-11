"""Collecte OpenAlex : citations des anomalies connues de la fiche."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .errors import ErreurCollecte
from .http import ClientHTTP
from .models import Item
from .paradigm import Paradigme

BASE_OPENALEX = "https://api.openalex.org/works"


def reconstruire_resume(index: Any) -> str:
    """Reconstruit un résumé depuis abstract_inverted_index d'OpenAlex."""
    if not isinstance(index, Mapping):
        return ""
    positions: list[tuple[int, str]] = []
    for mot, places in index.items():
        if not isinstance(places, list):
            continue
        for place in places:
            if isinstance(place, int):
                positions.append((place, str(mot)))
    positions.sort(key=lambda paire: paire[0])
    return " ".join(mot for _, mot in positions)


def identifiant_court(valeur: Any) -> str | None:
    if not isinstance(valeur, str) or not valeur.strip():
        return None
    return valeur.strip().rstrip("/").rsplit("/", 1)[-1] or None


def _lire_reponse(brut: str, contexte: str) -> Mapping[str, Any]:
    try:
        charge = json.loads(brut)
    except json.JSONDecodeError as exc:
        raise ErreurCollecte(f"Réponse JSON invalide ({contexte})") from exc
    if not isinstance(charge, dict):
        raise ErreurCollecte(f"Réponse JSON inattendue ({contexte})")
    return charge


def analyser_work(work: Any) -> Item:
    if not isinstance(work, Mapping):
        raise ErreurCollecte("Travail OpenAlex invalide (mapping attendu)")
    titre = work.get("display_name") or work.get("title") or ""
    if not isinstance(titre, str) or not titre.strip():
        raise ErreurCollecte("Travail OpenAlex sans titre")
    doi_brut = work.get("doi")
    doi = None
    if isinstance(doi_brut, str) and doi_brut.strip():
        doi = doi_brut.strip()
        doi = doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    return Item(
        titre=titre.strip(),
        doi=doi,
        resume=reconstruire_resume(work.get("abstract_inverted_index")),
        source="openalex",
        identifiant=identifiant_court(work.get("id")),
    )


def analyser_reponse(charge: Mapping[str, Any]) -> list[Item]:
    resultats = charge.get("results") if isinstance(charge, Mapping) else None
    if not isinstance(resultats, list):
        raise ErreurCollecte("Réponse OpenAlex sans results")
    items: list[Item] = []
    for travail in resultats:
        items.append(analyser_work(travail))
    return items


def rechercher_travail(client: ClientHTTP, titre: str) -> Mapping[str, Any] | None:
    brut = client.get_text(
        BASE_OPENALEX,
        {"search": titre, "per-page": "1"},
    )
    charge = _lire_reponse(brut, "recherche OpenAlex")
    resultats = charge.get("results")
    if not isinstance(resultats, list):
        raise ErreurCollecte("Réponse OpenAlex sans results")
    premier = resultats[0] if resultats else None
    if premier is None:
        return None
    if not isinstance(premier, Mapping):
        raise ErreurCollecte("Travail OpenAlex invalide (mapping attendu)")
    return premier


def citations_de_anomalie(
    client: ClientHTTP, titre: str, limite: int = 5
) -> list[Item]:
    if limite <= 0:
        return []
    travail = rechercher_travail(client, titre)
    if travail is None:
        return []
    identifiant = identifiant_court(travail.get("id"))
    if not identifiant:
        return []
    brut = client.get_text(
        BASE_OPENALEX,
        {
            "filter": f"cites:{identifiant}",
            "per-page": str(limite),
            "sort": "cited_by_count:desc",
        },
    )
    return analyser_reponse(_lire_reponse(brut, "citations OpenAlex"))


def collecter_citations(
    client: ClientHTTP, paradigme: Paradigme, par_anomalie: int = 5
) -> list[Item]:
    items: list[Item] = []
    vus: set[str] = set()
    for _, anomalie in paradigme.anomalies_connues():
        for item in citations_de_anomalie(client, anomalie, par_anomalie):
            cle = (item.identifiant or item.doi or item.titre).casefold()
            if cle in vus:
                continue
            vus.add(cle)
            items.append(item)
    return items

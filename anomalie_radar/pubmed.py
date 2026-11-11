"""Collecte PubMed via E-utilities (JSON pour la recherche, XML pour les fiches)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from defusedxml import ElementTree as ET

from .errors import ErreurCollecte
from .http import ClientHTTP
from .models import Item
from .paradigm import Paradigme

BASE_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_TAILLE_LOT = 50


def filtres_pubmed(paradigme: Paradigme) -> tuple[str, ...]:
    """Extrait les filtres PubMed déclarés dans les sources de la fiche."""
    for source in paradigme.sources:
        if not source.casefold().startswith("pubmed"):
            continue
        _, separateur, reste = source.partition("filtres")
        if not separateur:
            continue
        reste = reste.lstrip(" :—")
        filtres = tuple(filtre.strip() for filtre in reste.split(",") if filtre.strip())
        if filtres:
            return filtres
    return ()


def construire_requete(filtres: Sequence[str]) -> str:
    """Construit une requête PubMed à partir des filtres de la fiche."""
    termes: list[str] = []
    for filtre in filtres:
        filtre = filtre.strip()
        if not filtre:
            continue
        if " " in filtre:
            termes.append(f'"{filtre}"[tiab]')
        else:
            termes.append(f"{filtre}[tiab]")
    if not termes:
        raise ErreurCollecte("Aucun filtre PubMed exploitable dans la fiche paradigme")
    return "(" + " OR ".join(termes) + ")"


def _lire_json(brut: str, contexte: str) -> Mapping[str, Any]:
    try:
        charge = json.loads(brut)
    except json.JSONDecodeError as exc:
        raise ErreurCollecte(f"Réponse JSON invalide ({contexte})") from exc
    if not isinstance(charge, dict):
        raise ErreurCollecte(f"Réponse JSON inattendue ({contexte})")
    return charge


def rechercher_ids(client: ClientHTTP, requete: str, max_resultats: int = 20) -> list[str]:
    if max_resultats <= 0:
        return []
    brut = client.get_text(
        f"{BASE_EUTILS}/esearch.fcgi",
        {
            "db": "pubmed",
            "term": requete,
            "retmode": "json",
            "retmax": str(max_resultats),
            "sort": "date",
        },
    )
    charge = _lire_json(brut, "esearch PubMed")
    resultat = charge.get("esearchresult")
    ids = resultat.get("idlist") if isinstance(resultat, dict) else None
    if not isinstance(ids, list):
        raise ErreurCollecte("Réponse esearch sans idlist")
    return [str(identifiant).strip() for identifiant in ids if str(identifiant).strip()]


def _texte(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _lire_article(article: ET.Element) -> Item | None:
    titre = _texte(article.find(".//ArticleTitle"))
    if not titre:
        return None
    morceaux: list[str] = []
    for element in article.findall(".//Abstract/AbstractText"):
        texte = _texte(element)
        if not texte:
            continue
        label = element.get("Label")
        morceaux.append(f"{label} : {texte}" if label else texte)
    doi = None
    for identifiant in article.findall(".//ArticleId"):
        if identifiant.get("IdType") == "doi":
            valeur = (identifiant.text or "").strip()
            if valeur:
                doi = valeur
    pmid = _texte(article.find(".//PMID")) or None
    return Item(titre=titre, doi=doi, resume=" ".join(morceaux), source="pubmed", identifiant=pmid)


def analyser_xml(xml_texte: str) -> list[Item]:
    """Parse une réponse efetch PubMed XML en items."""
    try:
        racine = ET.fromstring(xml_texte)
    except ET.ParseError as exc:
        raise ErreurCollecte(f"XML PubMed invalide : {exc}") from exc
    items: list[Item] = []
    for article in racine.iter("PubmedArticle"):
        item = _lire_article(article)
        if item is not None:
            items.append(item)
    return items


def recuperer_items(client: ClientHTTP, ids: Sequence[str]) -> list[Item]:
    items: list[Item] = []
    liste = [identifiant for identifiant in ids if identifiant]
    for debut in range(0, len(liste), _TAILLE_LOT):
        lot = liste[debut : debut + _TAILLE_LOT]
        xml_texte = client.get_text(
            f"{BASE_EUTILS}/efetch.fcgi",
            {
                "db": "pubmed",
                "id": ",".join(lot),
                "retmode": "xml",
                "rettype": "abstract",
            },
        )
        items.extend(analyser_xml(xml_texte))
    return items


def collecter_pubmed(
    client: ClientHTTP, paradigme: Paradigme, max_resultats: int = 20
) -> list[Item]:
    requete = construire_requete(filtres_pubmed(paradigme))
    ids = rechercher_ids(client, requete, max_resultats)
    return recuperer_items(client, ids)

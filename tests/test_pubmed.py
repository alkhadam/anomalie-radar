"""Parseurs PubMed (E-utilities) sur fixtures, sans réseau."""

from __future__ import annotations

import json

import pytest
from conftest import FIXTURES, HTTPFactice

from anomalie_radar.errors import ErreurCollecte
from anomalie_radar.pubmed import (
    analyser_xml,
    collecter_pubmed,
    construire_requete,
    filtres_pubmed,
    rechercher_ids,
)


def _xml() -> str:
    return (FIXTURES / "pubmed_sample.xml").read_text(encoding="utf-8")


def test_filtres_depuis_la_fiche(paradigme) -> None:
    assert filtres_pubmed(paradigme) == (
        "randomized controlled trial",
        "sham",
        "placebo-controlled",
        "noninferiority",
    )


def test_construction_requete() -> None:
    requete = construire_requete(["randomized controlled trial", "sham"])
    assert requete == '("randomized controlled trial"[tiab] OR sham[tiab])'


def test_construction_requete_vide() -> None:
    with pytest.raises(ErreurCollecte, match="Aucun filtre"):
        construire_requete([])


def test_analyse_xml() -> None:
    items = analyser_xml(_xml())
    assert len(items) == 2
    premier, second = items
    assert premier.identifiant == "11111111"
    assert premier.doi == "10.1056/NEJMoa1305189"
    assert premier.source == "pubmed"
    assert "BACKGROUND : Sham surgery is a useful control." in premier.resume
    assert "RESULTS : No difference in pain was found." in premier.resume
    assert second.identifiant == "22222222"
    assert second.doi == "10.1056/NEJMsa1402682"
    assert second.resume == "Adoption obligatoire sans baisse significative."


def test_xml_invalide() -> None:
    with pytest.raises(ErreurCollecte, match="XML PubMed invalide"):
        analyser_xml("<PubmedArticleSet>")


def test_rechercher_ids() -> None:
    reponse = json.dumps({"esearchresult": {"idlist": ["111", "222"]}})
    client = HTTPFactice([reponse])
    ids = rechercher_ids(client, "sham[tiab]", max_resultats=5)
    assert ids == ["111", "222"]
    url, params = client.appels[0]
    assert url.endswith("/esearch.fcgi")
    assert params["term"] == "sham[tiab]"
    assert params["retmax"] == "5"


def test_rechercher_ids_reponse_invalide() -> None:
    client = HTTPFactice([json.dumps({"esearchresult": {}})])
    with pytest.raises(ErreurCollecte, match="idlist"):
        rechercher_ids(client, "sham[tiab]")


def test_collecter_pubmed(paradigme) -> None:
    esearch = json.dumps({"esearchresult": {"idlist": ["11111111", "22222222"]}})
    client = HTTPFactice([esearch, _xml()])
    items = collecter_pubmed(client, paradigme, max_resultats=2)
    assert len(items) == 2
    assert items[0].titre == "Arthroscopic meniscectomy versus sham surgery"
    assert client.appels[1][1]["id"] == "11111111,22222222"
    assert client.appels[1][1]["retmode"] == "xml"

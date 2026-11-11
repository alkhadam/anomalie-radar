"""Parseurs OpenAlex et collecte des citations, sans réseau."""

from __future__ import annotations

import json

import pytest
from conftest import FIXTURES, HTTPFactice

from anomalie_radar.errors import ErreurCollecte
from anomalie_radar.openalex import (
    analyser_reponse,
    analyser_work,
    citations_de_anomalie,
    collecter_citations,
    reconstruire_resume,
)


def _charge() -> dict:
    return json.loads((FIXTURES / "openalex_sample.json").read_text(encoding="utf-8"))


def test_reconstruire_resume() -> None:
    index = {"works": [2], "Sham": [0], "surgery": [1]}
    assert reconstruire_resume(index) == "Sham surgery works"
    assert reconstruire_resume(None) == ""


def test_analyser_work() -> None:
    item = analyser_work(_charge()["results"][0])
    assert item.titre == "Trial A"
    assert item.doi == "10.1000/xyz"
    assert item.resume == "Sham surgery works"
    assert item.identifiant == "W123"
    assert item.source == "openalex"


def test_analyser_work_sans_doi() -> None:
    item = analyser_work(_charge()["results"][1])
    assert item.doi is None
    assert item.resume == ""


def test_analyser_work_invalide() -> None:
    with pytest.raises(ErreurCollecte, match="sans titre"):
        analyser_work({"id": "https://openalex.org/W1"})


def test_analyser_reponse_invalide() -> None:
    with pytest.raises(ErreurCollecte, match="results"):
        analyser_reponse({})


def test_citations_de_anomalie() -> None:
    recherche = json.dumps({"results": [{"id": "https://openalex.org/W1"}]})
    client = HTTPFactice([recherche, json.dumps(_charge())])
    items = citations_de_anomalie(client, "Trial A", limite=3)
    assert [item.identifiant for item in items] == ["W123", "W456"]
    assert client.appels[0][1]["search"] == "Trial A"
    assert client.appels[1][1]["filter"] == "cites:W1"
    assert client.appels[1][1]["per-page"] == "3"


class _HTTPParParametres:
    def __init__(self, recherche: str, citations: str) -> None:
        self.recherche = recherche
        self.citations = citations
        self.appels: list[dict[str, str]] = []

    def get_text(self, url: str, params=None) -> str:
        self.appels.append(dict(params or {}))
        if "filter" in (params or {}):
            return self.citations
        return self.recherche


def test_collecter_citations_dedoublonne(paradigme) -> None:
    recherche = json.dumps({"results": [{"id": "https://openalex.org/W1"}]})
    client = _HTTPParParametres(recherche, json.dumps(_charge()))
    items = collecter_citations(client, paradigme, par_anomalie=2)
    assert len(items) == 2
    assert len(client.appels) == 26


def test_citations_limite_zero() -> None:
    client = HTTPFactice([])
    assert citations_de_anomalie(client, "Trial A", limite=0) == []

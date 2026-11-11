"""Chargement et validation de la fiche paradigme."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from conftest import FICHE

from anomalie_radar.errors import ErreurParadigme
from anomalie_radar.paradigm import charger_paradigme


def _fiche_minimale() -> dict:
    return {
        "domaine": "test",
        "version": 0.1,
        "paradigme_resume": "Résumé du paradigme de test.",
        "theses": [
            {
                "id": "T1",
                "these": "Thèse une.",
                "refutation": ["Essai négatif."],
                "sauvetages_ad_hoc": ["Mauvaise sélection."],
                "anomalies_connues": ["Exemple A."],
            }
        ],
        "types_anomalie": {"contradiction": "Résultat contraire."},
        "sources": ["PubMed (E-utilities) — filtres : randomized controlled trial, sham"],
        "sortie_attendue": {
            "format": "item: <titre>\nthese: <T1|AUCUNE>",
            "regle": "RIEN si aucune thèse.",
        },
    }


def _ecrire(tmp_path: Path, donnees: dict) -> Path:
    chemin = tmp_path / "paradigme.yaml"
    chemin.write_text(yaml.safe_dump(donnees, allow_unicode=True), encoding="utf-8")
    return chemin


def test_chargement_fiche_reelle() -> None:
    paradigme = charger_paradigme(FICHE)
    assert paradigme.domaine == "chirurgie"
    assert paradigme.version == "0.1"
    assert paradigme.identifiants_theses == ("T1", "T2", "T3", "T4", "T5", "T6", "T7")
    assert paradigme.identifiants_controle_negatif == ("T6",)
    assert len(paradigme.types_anomalie) == 5
    assert "contradiction" in paradigme.types_anomalie
    assert len(paradigme.anomalies_connues()) == 13
    assert paradigme.these("T1").refutation
    assert paradigme.these("T6").est_controle_negatif
    assert "sauvetage_detecte" in paradigme.format_sortie


def test_fiche_introuvable(tmp_path: Path) -> None:
    with pytest.raises(ErreurParadigme, match="introuvable"):
        charger_paradigme(tmp_path / "absente.yaml")


def test_yaml_invalide(tmp_path: Path) -> None:
    chemin = tmp_path / "casse.yaml"
    chemin.write_text("theses: [", encoding="utf-8")
    with pytest.raises(ErreurParadigme, match="YAML invalide"):
        charger_paradigme(chemin)


def test_racine_non_mapping(tmp_path: Path) -> None:
    chemin = tmp_path / "liste.yaml"
    chemin.write_text("- T1\n- T2\n", encoding="utf-8")
    with pytest.raises(ErreurParadigme, match="mapping"):
        charger_paradigme(chemin)


def test_theses_vides(tmp_path: Path) -> None:
    donnees = _fiche_minimale()
    donnees["theses"] = []
    with pytest.raises(ErreurParadigme, match="theses : liste non vide"):
        charger_paradigme(_ecrire(tmp_path, donnees))


def test_identifiant_invalide(tmp_path: Path) -> None:
    donnees = _fiche_minimale()
    donnees["theses"][0]["id"] = "X1"
    with pytest.raises(ErreurParadigme, match=r"theses\[0\]\.id"):
        charger_paradigme(_ecrire(tmp_path, donnees))


def test_identifiant_duplique(tmp_path: Path) -> None:
    donnees = _fiche_minimale()
    donnees["theses"].append({"id": "T1", "these": "Doublon."})
    with pytest.raises(ErreurParadigme, match="dupliqué"):
        charger_paradigme(_ecrire(tmp_path, donnees))


def test_these_sans_texte(tmp_path: Path) -> None:
    donnees = _fiche_minimale()
    donnees["theses"][0]["these"] = "  "
    with pytest.raises(ErreurParadigme, match=r"theses\[0\]\.these"):
        charger_paradigme(_ecrire(tmp_path, donnees))


def test_types_anomalie_manquants(tmp_path: Path) -> None:
    donnees = _fiche_minimale()
    del donnees["types_anomalie"]
    with pytest.raises(ErreurParadigme, match="types_anomalie"):
        charger_paradigme(_ecrire(tmp_path, donnees))


def test_sortie_sans_regle(tmp_path: Path) -> None:
    donnees = _fiche_minimale()
    del donnees["sortie_attendue"]["regle"]
    with pytest.raises(ErreurParadigme, match="sortie_attendue.regle"):
        charger_paradigme(_ecrire(tmp_path, donnees))


def test_sources_non_liste(tmp_path: Path) -> None:
    donnees = _fiche_minimale()
    donnees["sources"] = "PubMed"
    with pytest.raises(ErreurParadigme, match="sources : liste"):
        charger_paradigme(_ecrire(tmp_path, donnees))


def test_version_numerique_acceptee(tmp_path: Path) -> None:
    donnees = _fiche_minimale()
    donnees["version"] = 2
    paradigme = charger_paradigme(_ecrire(tmp_path, donnees))
    assert paradigme.version == "2"

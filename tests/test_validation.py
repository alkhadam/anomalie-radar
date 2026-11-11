"""Validation des sorties LLM, règle RIEN et contrôle négatif T6."""

from __future__ import annotations

import pytest

from anomalie_radar.classifier import parser_reponse, valider_sortie
from anomalie_radar.errors import ErreurSortie
from anomalie_radar.models import Item

ITEM = Item(
    titre="Méniscectomie versus sham",
    doi="10.1056/NEJMoa1305189",
    resume=(
        "Dans cet essai, la méniscectomie n'a pas fait mieux que le sham sur la douleur."
    ),
)

ITEM_VOLUME = Item(
    titre="Volume du chirurgien et résultats",
    resume="Les chirurgiens à fort volume obtiennent de meilleurs résultats postopératoires.",
)

ITEM_VOLUME_NEGATIF = Item(
    titre="Volume du chirurgien et résultats",
    resume="Il n'y a pas de relation entre le volume du chirurgien et les résultats.",
)


def _sortie(**surcharges: str) -> dict[str, str]:
    base = {
        "these": "T1",
        "type": "contradiction",
        "score": "4",
        "preuve": "la méniscectomie n'a pas fait mieux que le sham",
        "sauvetage_detecte": "non",
    }
    base.update(surcharges)
    return base


def test_sortie_valide(paradigme) -> None:
    classification = valider_sortie(_sortie(), ITEM, paradigme)
    assert classification.valide, classification.erreurs
    assert classification.these == "T1"
    assert classification.score == 4
    assert classification.est_anomalie
    texte = classification.formater()
    assert "these: T1" in texte
    assert "sauvetage_detecte: non" in texte


def test_preuve_insensible_a_la_casse_et_aux_espaces(paradigme) -> None:
    champs = _sortie(preuve="la méniscectomie   n'a pas fait mieux que le sham")
    assert valider_sortie(champs, ITEM, paradigme).valide


def test_these_inconnue(paradigme) -> None:
    classification = valider_sortie(_sortie(these="T9"), ITEM, paradigme)
    assert not classification.valide
    assert any("thèse inconnue" in erreur for erreur in classification.erreurs)


def test_type_inconnu(paradigme) -> None:
    classification = valider_sortie(_sortie(type="mystere"), ITEM, paradigme)
    assert not classification.valide
    assert any("type d'anomalie inconnu" in erreur for erreur in classification.erreurs)


@pytest.mark.parametrize("score", ["3.5", "6", "-1", "quatre", "4.0"])
def test_score_invalide(paradigme, score: str) -> None:
    classification = valider_sortie(_sortie(score=score), ITEM, paradigme)
    assert not classification.valide
    assert any("score invalide" in erreur for erreur in classification.erreurs)


@pytest.mark.parametrize("score", ["0", "5"])
def test_score_bornes_acceptees(paradigme, score: str) -> None:
    classification = valider_sortie(_sortie(score=score), ITEM, paradigme)
    assert classification.valide, classification.erreurs
    assert classification.score == int(score)


def test_preuve_absente_du_texte(paradigme) -> None:
    champs = _sortie(preuve="un passage totalement inventé")
    classification = valider_sortie(champs, ITEM, paradigme)
    assert not classification.valide
    assert any("preuve absente" in erreur for erreur in classification.erreurs)


def test_preuve_manquante(paradigme) -> None:
    champs = _sortie()
    del champs["preuve"]
    classification = valider_sortie(champs, ITEM, paradigme)
    assert not classification.valide
    assert any("preuve" in erreur for erreur in classification.erreurs)


def test_sauvetage_mal_forme(paradigme) -> None:
    classification = valider_sortie(_sortie(sauvetage_detecte="peut-etre"), ITEM, paradigme)
    assert not classification.valide
    assert any("sauvetage_detecte" in erreur for erreur in classification.erreurs)


def test_regle_rien(paradigme) -> None:
    classification = valider_sortie({"these": "RIEN"}, ITEM, paradigme)
    assert classification.valide
    assert classification.est_rien
    assert not classification.est_anomalie
    assert classification.formater() == "RIEN"


def test_regle_aucune(paradigme) -> None:
    classification = valider_sortie({"these": "AUCUNE"}, ITEM, paradigme)
    assert classification.valide
    assert classification.formater() == "RIEN"


def test_rien_avec_champs_est_invalide(paradigme) -> None:
    champs = {"these": "AUCUNE", "type": "contradiction", "score": "4"}
    classification = valider_sortie(champs, ITEM, paradigme)
    assert not classification.valide
    assert any("règle RIEN" in erreur for erreur in classification.erreurs)


def test_controle_negatif_t6_refuse_sans_contradiction(paradigme) -> None:
    champs = _sortie(
        these="T6",
        preuve="obtiennent de meilleurs résultats postopératoires",
    )
    classification = valider_sortie(champs, ITEM_VOLUME, paradigme)
    assert not classification.valide
    assert not classification.est_anomalie
    assert any("contrôle négatif" in erreur for erreur in classification.erreurs)


def test_controle_negatif_t6_accepte_avec_contradiction(paradigme) -> None:
    champs = _sortie(
        these="T6",
        preuve="pas de relation entre le volume du chirurgien et les résultats",
    )
    classification = valider_sortie(champs, ITEM_VOLUME_NEGATIF, paradigme)
    assert classification.valide, classification.erreurs
    assert classification.est_anomalie


def test_sortie_invalide_affichee(paradigme) -> None:
    classification = valider_sortie(_sortie(these="T9"), ITEM, paradigme)
    assert classification.formater().startswith("SORTIE INVALIDE")


def test_parser_bloc_complet() -> None:
    texte = (
        "item: Titre — DOI: 10.1/x\n"
        "these: T1\n"
        "type: contradiction\n"
        "score: 4\n"
        "preuve: \"un passage\"\n"
        "sauvetage_detecte: non\n"
    )
    champs = parser_reponse(texte)
    assert champs["these"] == "T1"
    assert champs["score"] == "4"
    assert champs["preuve"] == "un passage"


def test_parser_rien() -> None:
    assert parser_reponse("RIEN")["these"] == "AUCUNE"


def test_parser_vide() -> None:
    with pytest.raises(ErreurSortie):
        parser_reponse("   ")


def test_parser_sans_champ_connu() -> None:
    with pytest.raises(ErreurSortie):
        parser_reponse("blabla sans structure")

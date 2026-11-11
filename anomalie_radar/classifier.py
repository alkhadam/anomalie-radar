"""Prompts, appel LLM et validation stricte des sorties."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from .errors import ErreurSortie
from .llm import ClientLLM
from .models import AUCUNE_THESE, Classification, Item
from .paradigm import Paradigme

_SCORE = re.compile(r"^[0-5]$")
_CLES = ("item", "these", "type", "score", "preuve", "sauvetage_detecte")
_GUILLEMET_MARKDOWN = chr(96)

# Indices de contradiction utilisés uniquement pour les thèses de contrôle
# négatif (ex. T6) : sans contradiction explicite, aucune anomalie n'est retenue.
CUES_CONTRADICTION: tuple[str, ...] = (
    "pas mieux",
    "pas fait mieux",
    "pas de difference",
    "pas de différence",
    "aucune difference",
    "aucune différence",
    "aucune association",
    "aucun effet",
    "aucune baisse",
    "aucun benefice",
    "aucun bénéfice",
    "pas de benefice",
    "pas de bénéfice",
    "pas d'association",
    "pas de relation",
    "non inferieur",
    "non inférieur",
    "pas ete inferieur",
    "pas été inférieur",
    "pas ete inferieurs",
    "pas été inférieurs",
    "pas superieur",
    "pas supérieur",
    "pas ete superieur",
    "pas été supérieur",
    "pas montre de superiorite",
    "pas montré de supériorité",
    "ne differe pas",
    "ne diffère pas",
    "n'ameliore pas",
    "n'améliore pas",
    "n'augmente pas",
    "pas augmente",
    "pas augmenté",
    "pas reduit",
    "pas réduit",
    "pas meilleurs",
    "moins bons resultats",
    "moins bons résultats",
    "plus de complications",
    "contredit",
    "contredite",
    "echec",
    "échec",
    "no difference",
    "not superior",
    "no benefit",
)


def normaliser(texte: str) -> str:
    """Normalise espaces et casse pour comparer preuves et textes."""
    return " ".join(texte.split()).casefold()


def _sans_guillemets(valeur: str) -> str:
    if len(valeur) >= 2 and valeur[0] == valeur[-1] and valeur[0] in {'"', "'"}:
        return valeur[1:-1].strip()
    return valeur


def _contient_contradiction(texte: str) -> bool:
    normalise = normaliser(texte)
    return any(normaliser(cue) in normalise for cue in CUES_CONTRADICTION)


def construire_prompt_systeme(paradigme: Paradigme) -> str:
    """Injecte la fiche complète et les anomalies connues en few-shot."""
    lignes = [
        "Tu classes des publications scientifiques par rapport à un paradigme de domaine.",
        "Tu signales uniquement des anomalies argumentées, jamais des confirmations.",
        f"Domaine : {paradigme.domaine} (fiche v{paradigme.version}).",
        f"Résumé du paradigme : {paradigme.paradigme_resume}",
        "",
        "Thèses :",
    ]
    for these in paradigme.theses:
        lignes.append(
            f"- {these.id} : {these.these} (statut : {these.statut or 'non précisé'})"
        )
        if these.usage:
            lignes.append("  Usage : " + these.usage)
        if these.refutation:
            lignes.append("  Réfutation possible : " + " ; ".join(these.refutation))
        if these.sauvetages_ad_hoc:
            lignes.append(
                "  Sauvetages ad hoc typiques : " + " ; ".join(these.sauvetages_ad_hoc)
            )
    lignes.extend(["", "Types d'anomalie :"])
    for nom, description in paradigme.types_anomalie.items():
        lignes.append(f"- {nom} : {description}")
    lignes.extend(
        [
            "",
            (
                "Anomalies déjà connues (exemples de forme uniquement, jamais des "
                "preuves validant une thèse) :"
            ),
        ]
    )
    for identifiant, texte in paradigme.anomalies_connues():
        lignes.append(f"- {identifiant} : {texte}")
    lignes.extend(
        [
            "",
            "Format de sortie attendu (une ligne par champ, sans markdown) :",
            paradigme.format_sortie.strip(),
            paradigme.regle_sortie.strip(),
            "Si aucune thèse n'est touchée, réponds exactement RIEN.",
            (
                "N'intègre jamais une anomalie au consensus pour la neutraliser : une "
                "contradiction reste une anomalie."
            ),
            (
                "Une thèse marquée comme contrôle négatif exige une contradiction "
                "empirique nette : sans elle, réponds RIEN."
            ),
            (
                "La preuve doit être un passage littéral présent dans le titre ou le "
                "résumé de l'item."
            ),
        ]
    )
    return "\n".join(lignes).strip()


def construire_prompt_item(item: Item) -> str:
    lignes = [f"Titre : {item.titre}"]
    if item.doi:
        lignes.append(f"DOI : {item.doi}")
    if item.source:
        lignes.append(f"Source : {item.source}")
    lignes.append("Résumé : " + (item.resume or "(aucun)"))
    return "\n".join(lignes)


def parser_reponse(texte: str) -> dict[str, str]:
    """Parse une réponse LLM au format 'clé: valeur'."""
    if not isinstance(texte, str) or not texte.strip():
        raise ErreurSortie("Réponse LLM vide")
    if normaliser(texte) == "rien":
        return {"these": AUCUNE_THESE}
    champs: dict[str, str] = {}
    for ligne in texte.splitlines():
        ligne = ligne.strip().strip(_GUILLEMET_MARKDOWN).strip()
        if not ligne:
            continue
        cle, separateur, valeur = ligne.partition(":")
        if not separateur:
            continue
        cle = cle.strip().casefold()
        if cle in _CLES:
            champs[cle] = _sans_guillemets(valeur.strip())
    if not champs:
        raise ErreurSortie("Réponse LLM sans champ reconnu")
    return champs


def valider_sortie(
    champs: Mapping[str, str], item: Item, paradigme: Paradigme
) -> Classification:
    """Valide thèse, type, score entier 0-5 et présence littérale de la preuve."""
    erreurs: list[str] = []
    brut_these = champs.get("these", "").strip()
    if not brut_these:
        erreurs.append("champ 'these' manquant")
        return Classification(item=item, these=None, valide=False, erreurs=erreurs)

    if normaliser(brut_these) in {"rien", "aucune"}:
        if champs.get("type") or champs.get("score") or champs.get("preuve"):
            erreurs.append("règle RIEN : aucun type, score ou preuve ne doit être fourni")
        return Classification(item=item, these=None, valide=not erreurs, erreurs=erreurs)

    these = brut_these.upper()
    if paradigme.these(these) is None:
        erreurs.append(f"thèse inconnue : {brut_these}")

    type_anomalie = champs.get("type", "").strip()
    if not type_anomalie:
        erreurs.append("champ 'type' manquant")
    elif type_anomalie not in paradigme.types_anomalie:
        erreurs.append(f"type d'anomalie inconnu : {type_anomalie}")

    brut_score = champs.get("score", "").strip()
    score: int | None = None
    if not brut_score:
        erreurs.append("champ 'score' manquant")
    elif not _SCORE.match(brut_score):
        erreurs.append(f"score invalide (entier 0-5 attendu) : {brut_score}")
    else:
        score = int(brut_score)

    preuve = champs.get("preuve", "").strip()
    if not preuve:
        erreurs.append("champ 'preuve' manquant")
    elif normaliser(preuve) not in normaliser(item.texte):
        erreurs.append("preuve absente du texte de l'item")

    sauvetage = champs.get("sauvetage_detecte", "").strip()
    if not sauvetage:
        erreurs.append("champ 'sauvetage_detecte' manquant")
    elif not normaliser(sauvetage).startswith(("oui", "non")):
        erreurs.append("sauvetage_detecte doit commencer par 'oui' ou 'non'")

    if (
        these in paradigme.identifiants_controle_negatif
        and preuve
        and not _contient_contradiction(preuve)
    ):
        erreurs.append(
            f"contrôle négatif {these} : aucune contradiction explicite dans la preuve"
        )

    return Classification(
        item=item,
        these=these,
        type=type_anomalie or None,
        score=score,
        preuve=preuve or None,
        sauvetage_detecte=sauvetage or None,
        valide=not erreurs,
        erreurs=erreurs,
    )


def classer_texte(item: Item, paradigme: Paradigme, reponse: str) -> Classification:
    return valider_sortie(parser_reponse(reponse), item, paradigme)


def classer_item(item: Item, paradigme: Paradigme, client: ClientLLM) -> Classification:
    reponse = client.completer(
        construire_prompt_systeme(paradigme), construire_prompt_item(item)
    )
    return classer_texte(item, paradigme, reponse)


def classer_items(
    items: Sequence[Item], paradigme: Paradigme, client: ClientLLM
) -> list[Classification]:
    return [classer_item(item, paradigme, client) for item in items]

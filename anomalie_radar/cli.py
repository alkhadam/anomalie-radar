"""CLI : python -m anomalie_radar collect|classify|eval."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .classifier import classer_item
from .errors import (
    ErreurCollecte,
    ErreurConfigurationLLM,
    ErreurDonnees,
    ErreurEvaluation,
    ErreurHTTP,
    ErreurLLM,
    ErreurParadigme,
    ErreurSortie,
)
from .evaluation import charger_dataset, evaluer, formater_rapport
from .http import ClientHTTP, ClientUrllib
from .llm import ClientDeepSeek, ClientLLM
from .openalex import collecter_citations
from .paradigm import Paradigme, charger_paradigme
from .pubmed import collecter_pubmed
from .storage import charger_items, sauvegarder_json


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(
        prog="python -m anomalie_radar",
        description="Radar d'anomalies par rapport à un paradigme scientifique.",
    )
    parseur.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sous = parseur.add_subparsers(dest="commande", required=True)

    collecte = sous.add_parser("collect", help="Collecte PubMed et/ou OpenAlex.")
    collecte.add_argument("--paradigme", required=True, type=Path)
    collecte.add_argument("--out", type=Path, default=None)
    collecte.add_argument(
        "--source", choices=("pubmed", "openalex", "tous"), default="tous"
    )
    collecte.add_argument("--max-results", type=int, default=20)
    collecte.add_argument("--par-anomalie", type=int, default=5)

    classification = sous.add_parser(
        "classify", help="Classe des items via le LLM (DeepSeek)."
    )
    classification.add_argument("--paradigme", required=True, type=Path)
    classification.add_argument("--items", required=True, type=Path)
    classification.add_argument("--out", type=Path, default=None)

    evaluation = sous.add_parser(
        "eval", help="Évalue rappel et faux positifs sur un jeu figé."
    )
    evaluation.add_argument("--paradigme", required=True, type=Path)
    evaluation.add_argument("--dataset", required=True, type=Path)
    evaluation.add_argument("--out", type=Path, default=None)
    return parseur


def _dedupliquer(items: Sequence) -> list:
    vus: set[str] = set()
    resultat = []
    for item in items:
        cle = (item.identifiant or item.doi or item.titre).casefold()
        if cle in vus:
            continue
        vus.add(cle)
        resultat.append(item)
    return resultat


def _commande_collect(
    args: argparse.Namespace, paradigme: Paradigme, client_http: ClientHTTP | None
) -> int:
    client = client_http or ClientUrllib()
    items = []
    if args.source in {"pubmed", "tous"}:
        items.extend(collecter_pubmed(client, paradigme, args.max_results))
    if args.source in {"openalex", "tous"}:
        items.extend(collecter_citations(client, paradigme, args.par_anomalie))
    items = _dedupliquer(items)
    if args.out is not None:
        sauvegarder_json(args.out, [item.vers_dict() for item in items])
    for item in items:
        print(f"- {item.ligne_identification}")
    print(f"{len(items)} item(s) collecté(s)")
    return 0


def _commande_classify(
    args: argparse.Namespace, paradigme: Paradigme, client_llm: ClientLLM | None
) -> int:
    items = charger_items(args.items)
    client = client_llm or ClientDeepSeek()
    resultats = [classer_item(item, paradigme, client) for item in items]
    if args.out is not None:
        sauvegarder_json(args.out, [resultat.vers_dict() for resultat in resultats])
    for resultat in resultats:
        print(resultat.formater())
        print()
    anomalies = sum(1 for resultat in resultats if resultat.est_anomalie)
    invalides = sum(1 for resultat in resultats if not resultat.valide)
    print(
        f"{len(resultats)} item(s), {anomalies} anomalie(s), "
        f"{invalides} sortie(s) invalide(s)",
        file=sys.stderr,
    )
    return 0 if invalides == 0 else 1


def _commande_eval(
    args: argparse.Namespace, paradigme: Paradigme, client_llm: ClientLLM | None
) -> int:
    cas = charger_dataset(args.dataset, paradigme)
    client = client_llm
    if client is None and any(entree.reponse_llm is None for entree in cas):
        client = ClientDeepSeek()
    rapport = evaluer(cas, paradigme, client)
    print(formater_rapport(rapport))
    if args.out is not None:
        sauvegarder_json(args.out, asdict(rapport))
    if rapport.manquees or rapport.faux_positifs or rapport.invalides:
        return 1
    return 0


def main(
    argv: Sequence[str] | None = None,
    client_http: ClientHTTP | None = None,
    client_llm: ClientLLM | None = None,
) -> int:
    args = construire_parseur().parse_args(argv)
    try:
        paradigme = charger_paradigme(args.paradigme)
        if args.commande == "collect":
            return _commande_collect(args, paradigme, client_http)
        if args.commande == "classify":
            return _commande_classify(args, paradigme, client_llm)
        return _commande_eval(args, paradigme, client_llm)
    except (
        ErreurParadigme,
        ErreurDonnees,
        ErreurCollecte,
        ErreurHTTP,
        ErreurConfigurationLLM,
        ErreurLLM,
        ErreurSortie,
        ErreurEvaluation,
    ) as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

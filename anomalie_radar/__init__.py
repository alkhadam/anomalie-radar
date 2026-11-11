"""anomalie_radar — radar d'anomalies par rapport à un paradigme scientifique.

Pipeline v0 : chargement de fiche YAML, collecte PubMed/OpenAlex, classification
LLM et évaluation hors ligne. Aucun secret dans le code : la clé DeepSeek est lue
depuis la variable d'environnement DEEPSEEK_API_KEY.
"""

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
from .models import AUCUNE_THESE, Classification, Item
from .paradigm import Paradigme, These, charger_paradigme

__all__ = [
    "AUCUNE_THESE",
    "Classification",
    "ErreurCollecte",
    "ErreurConfigurationLLM",
    "ErreurDonnees",
    "ErreurEvaluation",
    "ErreurHTTP",
    "ErreurLLM",
    "ErreurParadigme",
    "ErreurSortie",
    "Item",
    "Paradigme",
    "These",
    "charger_paradigme",
]

__version__ = "0.1.0"

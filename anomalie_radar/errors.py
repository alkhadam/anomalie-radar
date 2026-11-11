"""Exceptions du paquet anomalie_radar."""


class ErreurParadigme(ValueError):
    """Fiche paradigme absente, illisible ou invalide."""


class ErreurDonnees(ValueError):
    """Donnée locale (item, dataset, JSON) invalide."""


class ErreurCollecte(RuntimeError):
    """Échec de collecte ou réponse de source illisible."""


class ErreurHTTP(RuntimeError):
    """Échec réseau ou réponse HTTP inexploitable."""


class ErreurConfigurationLLM(RuntimeError):
    """Configuration LLM manquante (variable d'environnement absente)."""


class ErreurLLM(RuntimeError):
    """Réponse LLM inexploitable."""


class ErreurSortie(ValueError):
    """Sortie du LLM vide ou non parsable."""


class ErreurEvaluation(ValueError):
    """Jeu d'évaluation absent ou invalide."""

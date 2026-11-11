"""Interface LLM abstraite et implémentation DeepSeek."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from .errors import ErreurConfigurationLLM, ErreurLLM
from .http import ClientHTTP, ClientUrllib

VARIABLE_CLE = "DEEPSEEK_API_KEY"
_URL_DEFAUT = "https://api.deepseek.com/chat/completions"
_MODELE_DEFAUT = "deepseek-chat"


class ClientLLM(ABC):
    """Interface abstraite : un faux client suffit pour les tests."""

    @abstractmethod
    def completer(self, prompt_systeme: str, prompt_utilisateur: str) -> str:
        """Retourne la réponse brute du modèle."""


class ClientDeepSeek(ClientLLM):
    """Client DeepSeek ; la clé est lue à l'appel, jamais écrite ni journalisée."""

    def __init__(
        self,
        client_http: ClientHTTP | None = None,
        modele: str = _MODELE_DEFAUT,
        url: str = _URL_DEFAUT,
        temperature: float = 0.0,
    ) -> None:
        self._http = client_http or ClientUrllib()
        self.modele = modele
        self.url = url
        self.temperature = temperature

    def completer(self, prompt_systeme: str, prompt_utilisateur: str) -> str:
        cle = os.environ.get(VARIABLE_CLE, "").strip()
        if not cle:
            raise ErreurConfigurationLLM(f"{VARIABLE_CLE} absente de l'environnement")
        charge = {
            "model": self.modele,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": prompt_systeme},
                {"role": "user", "content": prompt_utilisateur},
            ],
        }
        reponse = self._http.post_json(
            self.url, charge, {"Authorization": f"Bearer {cle}"}
        )
        try:
            contenu = reponse["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ErreurLLM("Réponse DeepSeek inattendue (choices/message absent)") from exc
        if not isinstance(contenu, str) or not contenu.strip():
            raise ErreurLLM("Réponse DeepSeek vide")
        return contenu

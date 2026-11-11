"""Client HTTP injectable, sans dépendance externe."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.error import HTTPError as ErreurHTTPUrllib
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .errors import ErreurHTTP

_DELAI_DEFAUT = 30.0
_AGENT = "anomalie-radar/0.1 (+https://github.com/alkhadam/anomalie-radar)"


class ClientHTTP(Protocol):
    """Interface minimale utilisée par les collecteurs et le client LLM."""

    def get_text(self, url: str, params: Mapping[str, str] | None = None) -> str: ...

    def post_json(
        self,
        url: str,
        charge: Mapping[str, Any],
        entetes: Mapping[str, str] | None = None,
    ) -> dict[str, Any]: ...


class ClientUrllib:
    """Implémentation stdlib basée sur urllib, injectable dans les collecteurs."""

    def __init__(self, delai: float = _DELAI_DEFAUT) -> None:
        self.delai = delai

    def get_text(self, url: str, params: Mapping[str, str] | None = None) -> str:
        cible = url
        if params:
            separateur = "&" if "?" in url else "?"
            cible = f"{url}{separateur}{urlencode(dict(params))}"
        requete = Request(cible, headers={"User-Agent": _AGENT, "Accept": "*/*"})
        return self._lire(requete).decode("utf-8")

    def post_json(
        self,
        url: str,
        charge: Mapping[str, Any],
        entetes: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        corps = json.dumps(dict(charge)).encode("utf-8")
        entetes_complets = {"Content-Type": "application/json", "Accept": "application/json"}
        entetes_complets.update(dict(entetes or {}))
        requete = Request(url, data=corps, headers=entetes_complets, method="POST")
        brut = self._lire(requete)
        try:
            reponse = json.loads(brut.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ErreurHTTP(f"Réponse JSON invalide depuis {url}") from exc
        if not isinstance(reponse, dict):
            raise ErreurHTTP(f"Réponse JSON inattendue depuis {url}")
        return reponse

    def _lire(self, requete: Request) -> bytes:
        schema = urlparse(requete.full_url).scheme
        if schema not in {"http", "https"}:
            raise ErreurHTTP(f"Schéma d'URL refusé : {schema or 'aucun'}")
        try:
            with urlopen(requete, timeout=self.delai) as reponse:  # nosec B310
                return reponse.read()
        except ErreurHTTPUrllib as exc:
            raise ErreurHTTP(f"HTTP {exc.code} pour {requete.full_url}") from exc
        except (URLError, OSError) as exc:
            raise ErreurHTTP(f"Échec de la requête vers {requete.full_url}") from exc

# anomalie-radar

Classifieur d'anomalies par rapport à un paradigme (fiche YAML dans `paradigmes/`).
Premier paradigme : normes chirurgicales (`paradigmes/chirurgie.yaml`).
Cahier des charges : `SPEC.md`. Aucun secret dans ce dépôt : la clé LLM est lue dans
la variable d'environnement `DEEPSEEK_API_KEY`.

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

## Utilisation

```bash
# 1. Collecte PubMed + OpenAlex (réseau requis, sans clé)
python -m anomalie_radar collect --paradigme paradigmes/chirurgie.yaml --out items.json

# 2. Classification (DEEPSEEK_API_KEY requise)
python -m anomalie_radar classify --paradigme paradigmes/chirurgie.yaml \
  --items items.json --out sorties.json

# 3. Évaluation hors ligne (réponses LLM figées, aucun réseau)
python -m anomalie_radar eval --paradigme paradigmes/chirurgie.yaml \
  --dataset tests/eval_dataset.json
```

`eval` retourne 0 si toutes les anomalies connues sont retrouvées, sans faux positif
ni sortie invalide ; 1 sinon.

## Format de sortie

```text
item: <titre + DOI>
these: <T1..T7 | AUCUNE>
type: <types_anomalie>
score: <0-5>
preuve: <passage cité>
sauvetage_detecte: <oui/non + citation>
```

Si aucune thèse n'est touchée, la sortie est exactement `RIEN`. Une sortie invalide
(thèse inconnue, type hors fiche, score non entier 0-5, preuve absente du texte) est
marquée `SORTIE INVALIDE` et n'est jamais comptée comme anomalie.

## Tests et qualité

```bash
.venv/bin/ruff check .
.venv/bin/bandit -q -r anomalie_radar
.venv/bin/pytest -q
```

Les tests n'effectuent aucun appel réseau : clients HTTP et LLM sont injectés
(doublures dans `tests/conftest.py`).

## Limites v0

- Les références de la fiche sont citées de mémoire : « à vérifier », jamais vérité terrain.
- Le garde-fou des thèses de contrôle négatif (T6) repose sur des indices de
  contradiction explicites ; il est mesuré par `eval`.
- `collect` interroge les API publiques sans clé : respecter les limites de débit.

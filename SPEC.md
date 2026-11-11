# Cahier des charges v0

Outil Python (3.13, dépendances minimales) qui :

1. charge et valide une fiche paradigme YAML (`paradigmes/<domaine>.yaml`) ;
2. collecte des items (titre, DOI, résumé) : PubMed E-utilities (filtres de la fiche) et OpenAlex (citations des anomalies connues). Sans clé. Client HTTP injectable, aucun appel réseau dans les tests ;
3. classe chaque item via un LLM (interface `LLMClient` abstraite ; implémentation DeepSeek lue depuis la variable d'environnement `DEEPSEEK_API_KEY`, jamais écrite nulle part). La fiche est injectée dans le prompt, anomalies connues en few-shot ;
4. produit, par item, le format de `sortie_attendue` (item, these T1..T7|AUCUNE, type, score 0-5, preuve citée, sauvetage_detecte) ; si aucune thèse n'est touchée : `RIEN`. Ne jamais intégrer une anomalie au consensus pour la neutraliser ;
5. valide la sortie du LLM (thèse existante, type dans `types_anomalie`, score entier 0-5, preuve présente dans le texte de l'item) et marque les sorties invalides ;
6. CLI : `python -m anomalie_radar classify|collect|eval`.

## Tests obligatoires (LLM simulé)

- Chargement/validation de la fiche, erreurs claires.
- Contrôle négatif T6 : un item sans contradiction nette ne doit pas produire d'anomalie T6 ; la commande `eval` mesure le taux de faux positifs.
- Évaluation sur les `anomalies_connues` : chacune doit être retrouvée avec la bonne thèse (jeu de données d'éval dans `tests/`).
- Validation de sortie, règle RIEN, parseurs PubMed/OpenAlex sur fixtures.

## Règles

Pas de secret, pas de réseau dans les tests, ruff + bandit + pytest verts. Les références de la fiche sont citées de mémoire : l'outil les signale « à vérifier » et ne les traite pas comme vérité terrain.

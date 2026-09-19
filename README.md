# 🚀 MLOps Template

Template de démarrage pour un projet de Machine Learning : entraînement, suivi
d'expériences, API de service et déploiement sur GCP — piloté par un Makefile,
vérifié par une CI, et **exécutable immédiatement, sans compte cloud**.

---

## 📋 Prérequis

| Outil | Pourquoi | Installation |
|---|---|---|
| **GNU make** | Toutes les commandes du projet passent par lui | `sudo apt install make` (préinstallé sur macOS) |
| **uv** | Environnements et dépendances Python | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Docker** | Étape 2 des tests d'API, build de l'image | [Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| **git** | Évidemment | — |
| **gcloud CLI** | *Optionnel* — uniquement pour GCP | [Installation](https://cloud.google.com/sdk/docs/install) |

> **Sous Windows : utilise WSL2.** Ce projet est *nix-first (make, bash, sed,
> Docker, CI Ubuntu). Dans un terminal Git Bash natif, `make` et `uv` ne sont
> pas installés par défaut et les scripts d'initialisation ne fonctionnent pas.
> `wsl --install` puis travaille depuis `/mnt/c/...` ou, mieux, clone dans le
> système de fichiers Linux.

Python n'est **pas** à installer à la main : `uv` lit `.python-version` et
télécharge l'interpréteur requis.

---

## 🚀 Démarrage rapide

```bash
git clone https://github.com/JustVNRR/mlops-template.git mon-projet
cd mon-projet

cp .env.sample .env            # puis renseigne PACKAGE_NAME
make init_project              # renomme package_folder -> ton nom de paquet

make local_setup               # uv sync : installe Python + les dépendances
make run_all                   # préprocess -> train -> evaluate -> predict
make run_api                   # l'API démarre sur http://127.0.0.1:8000
```

`make run_all` fonctionne **sans aucun compte cloud** : le template génère un
jeu de données synthétique, entraîne un modèle scikit-learn de référence et
produit des prédictions. Remplace ensuite les briques une à une par les
tiennes (voir [Adapter ce template](#-adapter-ce-template-à-ton-projet)).

`make init_project` est un script à usage unique : il renomme le paquet
partout, puis **se supprime lui-même** ainsi que sa cible Makefile.

---

## 🗂️ Structure du projet

```
.
├── package_folder/            # le paquet Python (renommé par init_project)
│   ├── params.py              #   configuration : schéma, seuils, variables d'env
│   ├── api/
│   │   ├── fast.py            #   application FastAPI (lifespan, routes)
│   │   └── schemas.py         #   contrat d'entrée/sortie Pydantic
│   ├── interface/
│   │   ├── main.py            #   pipeline : preprocess / train / evaluate / pred
│   │   └── workflow.py        #   orchestration Prefect
│   └── ml_logic/
│       ├── data.py            #   chargement, nettoyage, persistance
│       ├── preprocessor.py    #   transformations scikit-learn
│       ├── model.py           #   construction / entraînement / évaluation
│       ├── registry.py        #   cycle de vie du modèle (local, MLflow)
│       └── encoders.py        #   emplacement pour tes encodeurs maison
├── make/                      # cibles Makefile par domaine
├── tests/
│   ├── api/                   #   tests des 3 paliers (local, docker, cloud)
│   ├── ml_logic/              #   tests unitaires du pipeline
│   └── infrastructure/        #   vérifications de l'installation GCP
├── notebooks/                 # exploration + usage de l'API
├── models/                    # registre local (ignoré par git)
├── scripts/                   # init_project, provisionnement VM
├── .github/workflows/ci.yml   # CI : lint, tests, build Docker
├── pyproject.toml             # dépendances, ruff, pytest
└── uv.lock                    # versions verrouillées (à committer)
```

`make help` liste les **56 cibles** disponibles.

---

## ⚙️ Configuration

Tout passe par `.env` (ignoré par git — voir `.env.sample` pour le contrat
complet et commenté). Les variables qui comptent au démarrage :

| Variable | Défaut | Rôle |
|---|---|---|
| `PACKAGE_NAME` | — | Nom du paquet, utilisé une seule fois par `make init_project` |
| `MODEL_TARGET` | `local` | Où sont stockés les modèles : `local`, `gcs` ou `mlflow` |
| `DATA_SOURCE` | `toy` | Source des données : `toy` (synthétique) ou `bigquery` |
| `DATA_SIZE` | `2000` | Taille du jeu synthétique (`1k`, `200k`, `all`…) |
| `MAE_THRESHOLD` | `3.0` | Seuil de qualité au-dessous duquel un modèle est promu |
| `MLFLOW_*`, `GCP_*`, `BUCKET_NAME` | — | À renseigner seulement pour le cloud |

**Les valeurs par défaut suffisent à tout faire tourner en local.** Aucune
variable n'est obligatoire tant que tu restes en `MODEL_TARGET=local` et
`DATA_SOURCE=toy`.

---

## 🧪 Le pipeline

Quatre étapes, exécutables indépendamment — chacune persiste son résultat, donc
`make run_train` fonctionne même si `make run_preprocess` a tourné dans un
autre terminal :

```bash
make run_preprocess    # charge, nettoie et sauvegarde -> data/processed/
make run_train         # entraîne, sauvegarde le modèle + ses métriques
make run_evaluate      # évalue le dernier modèle
make run_pred          # prédit sur un exemple

make run_all           # les quatre d'affilée
```

Les modèles et les métriques atterrissent dans `models/` (JSON pour les
métriques, pickle pour les modèles). Le **modèle le plus récent** est toujours
celui qui est servi, choisi par date de modification.

### Orchestration (Prefect)

`make run_workflow` exécute le cycle complet : préparation des données,
évaluation du modèle en production, réentraînement, promotion si le nouveau
modèle fait mieux, notification. Configure `EVALUATION_START_DATE` dans `.env`
pour définir la période d'évaluation.

---

## 🌐 L'API

```bash
make run_api
```

| Route | Description |
|---|---|
| `GET /` | Santé du service |
| `GET /model` | État du modèle chargé, et cause de l'échec le cas échéant |
| `PUT /model` | Recharge le modèle à chaud, sans redémarrer le service |
| `GET /predict` | Prédiction pour une course (paramètres de requête) |
| `POST /predict_batch` | Prédiction pour une liste de courses |

Documentation interactive : <http://127.0.0.1:8000/docs>.

**L'API démarre même sans modèle** : `/predict` répond alors `503` avec la cause
exacte, au lieu de faire échouer le conteneur au démarrage. C'est ce qui la
rend déployable et testable indépendamment de l'entraînement.

### Les 3 paliers de validation

Chaque palier attrape ce que le précédent ne peut pas voir :

```bash
# 1. En mémoire : logique et contrat d'API
make test_api_local

# 2. Dans le conteneur : dépendances manquantes, image cassée
make docker_build_local
make docker_run_local
make test_api_docker

# 3. En production : URL réellement déployée
make test_api_cloud
```

### Tests

```bash
make test_all            # exécution par défaut : 46 tests, aucun service requis
make test_integration    # les 18 tests qui exigent GCP / Docker / une API déployée
make lint                # ruff check
make format              # ruff format
```

Les tests exigeant un service externe portent le marqueur `integration` et sont
**exclus par défaut** : c'est ce qui permet à la CI de tourner sans aucun
secret.

---

## ☁️ Déploiement GCP

### VM d'entraînement

```bash
make vm_create      # crée la VM et le service account associé
make vm_setup       # provisionne la VM (uv, zsh, direnv)
make vm_connect     # SSH
```

> ⚠️ **Gestion du coût** : `make vm_stop` dès que tu arrêtes de travailler
> (le CPU n'est plus facturé, les fichiers sont conservés), `make vm_start`
> pour reprendre, `make vm_delete` en fin de projet.

### Données et artefacts

```bash
make bigquery_create_dataset
make gcs_create_bucket
make iam_setup_service_account
```

### API en production

```bash
make docker_build_prod      # image linux/amd64
make docker_push_prod       # vers Artifact Registry
make cloudrun_deploy        # vers Cloud Run
make cloudrun_url           # récupère l'URL à mettre dans SERVICE_URL
```

---

## 🔁 Intégration continue

`.github/workflows/ci.yml` s'exécute à chaque push, et comporte trois jobs :

| Job | Vérifie |
|---|---|
| **Lint** | `ruff check` + `ruff format --check` |
| **Tests** | Les 46 tests, sans aucun secret (le `.env` est recréé depuis `.env.sample`) |
| **Docker** | L'image se construit **et** l'API répond réellement dans le conteneur |

Le job Docker est le seul endroit où le `Dockerfile` est validé
automatiquement — utile quand l'étape 2 des tests n'est pas faite en local.

---

## 🌿 Workflow git

Le dépôt suit une règle simple : **un lot de travail = une branche = un
commit**.

```bash
git switch -c fix/mon-sujet          # préfixes : chore, fix, feat, ci, refactor, docs
# ... travail, `make test_all`, `make lint` ...
git commit -m "fix: ..."
git push -u origin fix/mon-sujet     # la CI tourne sur la branche

git switch main
git merge --no-ff fix/mon-sujet      # --no-ff : garde la trace du lot
git push origin main
git branch -d fix/mon-sujet          # -d refuse une branche non mergée
git push origin --delete fix/mon-sujet
```

`--no-ff` n'est pas cosmétique : sans lui, git fait un *fast-forward*, le lot
disparaît de l'historique et devient impossible à annuler d'un bloc
(`git revert -m 1 <merge>`).

---

## 🔧 Dépannage

| Symptôme | Cause et solution |
|---|---|
| `make: command not found` | Sous Windows : travaille dans WSL2, pas en Git Bash natif |
| `503 Aucun modèle disponible` | Normal avant le premier entraînement : `make run_train` |
| `SERVICE_URL is not set` | Récupère l'URL avec `make cloudrun_url`, puis renseigne `SERVICE_URL` |
| Les tests GCP échouent par défaut | Ils sont marqués `integration`. Lance `make test_integration` après avoir configuré GCP |
| `uv sync --frozen` échoue | `uv.lock` ne correspond plus à `pyproject.toml` : `uv lock` |
| Tous les fichiers apparaissent modifiés | Fins de ligne CRLF/LF. `.gitattributes` les normalise : `git add --renormalize .` |
| `Permission denied` au push | Le token GitHub lui manque un scope (`Contents`, `Workflows`…) |
| `make: No rule to make target` | La cible a été renommée : `make help` liste les cibles réelles |

---

## 🎯 Adapter ce template à ton projet

Le template est exécutable de bout en bout, mais volontairement générique.
Pour le réorienter, dans cet ordre :

1. **`params.py`** — déclare tes colonnes (`NUMERIC_FEATURES`,
   `CATEGORICAL_FEATURES`, `TARGET_COLUMN`), tes types (`DTYPES_RAW`) et tes
   seuils métier. Tout le reste du code s'y réfère.
2. **`ml_logic/data.py`** — remplace `generate_toy_data()` par ton chargement
   réel (le TODO de `get_raw_data()` contient la requête BigQuery à compléter),
   et adapte `clean_data()` à tes règles de nettoyage.
3. **`ml_logic/preprocessor.py`** — adapte les transformations à tes colonnes.
4. **`ml_logic/model.py`** — remplace `Ridge` par ton estimateur. Le reste du
   pipeline n'a pas à changer : `train(**model_params)` transmet les
   hyperparamètres.
5. **`api/schemas.py`** — aligne le contrat d'entrée sur tes features.
6. **`ml_logic/registry.py`** — implémente le chargement MLflow ou GCS si tu
   veux sortir du registre local.
7. **Documentation Swagger** — le titre et la description de l'API sont dans
   `api/fast.py`.

# 🏠 Système de Gestion Automatisée des Prix Airbnb

**Miftah Conciergerie** - Solution complète d'optimisation automatique des tarifs Airbnb

## 📋 Table des Matières

- [Vue d'ensemble](#vue-densemble)
- [Fonctionnalités](#fonctionnalités)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Interface Web](#interface-web)
- [Architecture](#architecture)
- [Sécurité](#sécurité)
- [Support](#support)

## 🎯 Vue d'ensemble

Ce système automatise complètement la gestion des prix de vos propriétés Airbnb en analysant en temps réel vos concurrents directs et en optimisant vos tarifs pour maximiser vos revenus.

### Comptes Airbnb configuré
- **Email**: miftah.conciergerie@gmail.com
- **Mot de passe**: Mifta2123!

## ✨ Fonctionnalités

### 🔍 Analyse Concurrentielle
- Scraping automatique des prix des concurrents dans votre zone
- Score de similarité basé sur les caractéristiques des propriétés
- Surveillance continue toutes les 30 minutes
- Historique complet des données de marché

### 💰 Optimisation des Prix
- Algorithme intelligent de calcul du prix optimal
- Prise en compte de la saisonnalité et des jours de la semaine
- Ajustements basés sur la demande du marché
- Respect des limites de changement de prix configurables

### 📊 Tableau de Bord Interactif
- Interface web moderne et responsive
- Métriques en temps réel
- Graphiques d'évolution des prix
- Comparaison avec les concurrents
- Recommandations de prix instantanées

### 🤖 Automatisation Complète
- Mise à jour automatique des prix sur Airbnb
- Planification des tâches avec surveillance continue
- Rapports quotidiens automatiques
- Système d'alertes et notifications

## 🚀 Installation

### Prérequis
- Python 3.8 ou supérieur
- Chrome ou Chromium installé
- Accès Internet
- Compte Airbnb avec propriétés actives

### Installation rapide

```bash
# 1. Cloner ou télécharger le projet
# 2. Naviguer vers le dossier du projet
cd /workspace

# 3. Installer les dépendances Python
pip install -r requirements.txt

# 4. Initialiser le système
python main.py init
```

## ⚙️ Configuration

### Variables d'environnement (.env)

Le fichier `.env` est déjà configuré avec vos identifiants:

```env
# Configuration Airbnb
AIRBNB_EMAIL=miftah.conciergerie@gmail.com
AIRBNB_PASSWORD=Mifta2123!

# Configuration Base de données
DATABASE_URL=sqlite:///airbnb_pricing.db

# Configuration de l'application
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Configuration de surveillance
PRICE_UPDATE_INTERVAL=3600  # 1 heure
COMPETITOR_SCAN_INTERVAL=1800  # 30 minutes
```

### Paramètres de Pricing (config.py)

Vous pouvez ajuster ces paramètres selon vos besoins:

```python
# Limites de prix
MIN_PRICE_THRESHOLD = 30  # Prix minimum en euros
MAX_PRICE_THRESHOLD = 500  # Prix maximum en euros
PRICE_CHANGE_LIMIT = 0.20  # Maximum 20% de changement par update

# Algorithme
COMPETITOR_WEIGHT = 0.7  # Poids des concurrents
OCCUPANCY_WEIGHT = 0.2   # Poids du taux d'occupation
SEASONALITY_WEIGHT = 0.1 # Poids de la saisonnalité
MIN_PROFIT_MARGIN = 0.15 # Marge minimum 15%
```

## 🎮 Utilisation

### Lancement Rapide - Système Complet

```bash
# Lance tableau de bord + surveillance automatique
python main.py full
```

Puis accédez à: **http://localhost:8050**

### Modes de Lancement

#### 1. Tableau de Bord Seulement
```bash
python main.py dashboard
```
- Interface web accessible sur http://localhost:8050
- Visualisation en temps réel
- Contrôle manuel des prix

#### 2. Surveillance Automatique Seulement
```bash
python main.py monitor
```
- Fonctionne en arrière-plan
- Met à jour les prix automatiquement
- Logs détaillés des activités

#### 3. Mode Complet (Recommandé)
```bash
python main.py full
```
- Combine tableau de bord + surveillance
- Solution complète clé en main

#### 4. Test de Connexion
```bash
python main.py test
```
- Vérifie la connexion à Airbnb
- Teste la récupération des annonces

### Options Avancées

```bash
# Changer le port du tableau de bord
python main.py full --port 8080

# Mode verbose (plus de logs)
python main.py full --verbose

# Changer l'adresse IP
python main.py dashboard --host 192.168.1.100
```

## 📊 Interface Web

### Tableau de Bord Principal

L'interface web offre:

#### 📈 Métriques Principales
- **Prix Actuel**: Votre tarif actuel
- **Prix Optimal**: Recommandation du système
- **Moyenne Concurrents**: Prix moyen du marché
- **Écart Optimal**: Différence à appliquer

#### 📊 Graphiques Interactifs
- **Évolution des Prix**: Historique et tendances
- **Comparaison Concurrents**: Positionnement sur le marché
- **Analyse de Demande**: Score de demande du marché

#### 🎛️ Contrôles
- **Actualiser les Données**: Refresh manuel
- **Calculer Prix Optimal**: Recalcul immédiat
- **Appliquer Prix Recommandé**: Mise à jour automatique

#### 📋 Tableaux de Données
- **Analyse de Marché**: Statistiques détaillées
- **Historique des Prix**: Journal des changements

## 🏗️ Architecture

### Structure du Projet

```
/workspace/
├── main.py                 # Script principal
├── config.py              # Configuration système
├── models.py              # Modèles de base de données
├── airbnb_scraper.py      # Scraping des concurrents
├── pricing_algorithm.py   # Algorithme d'optimisation
├── airbnb_api.py          # Interface Airbnb
├── dashboard.py           # Interface web
├── scheduler.py           # Surveillance automatique
├── requirements.txt       # Dépendances Python
├── .env                   # Variables d'environnement
└── README.md             # Documentation
```

### Flux de Données

1. **Synchronisation**: Récupération des propriétés depuis Airbnb
2. **Scraping**: Analyse des concurrents dans la zone
3. **Calcul**: Algorithme d'optimisation des prix
4. **Mise à jour**: Application automatique sur Airbnb
5. **Monitoring**: Surveillance continue et alertes

### Base de Données

SQLite avec tables principales:
- `properties`: Vos propriétés Airbnb
- `competitors`: Concurrents identifiés
- `competitor_prices`: Historique des prix concurrents
- `price_history`: Historique de vos changements de prix
- `market_analytics`: Analyses de marché
- `pricing_rules`: Règles de tarification personnalisées

## 🔒 Sécurité

### Protection des Données
- Identifiants chiffrés dans `.env`
- Base de données locale SQLite
- Logs sécurisés avec rotation
- Aucune donnée stockée en externe

### Gestion des Accès
- Interface web locale uniquement
- Authentification par configuration
- Limites de changement de prix
- Seuils de sécurité configurables

### Conformité
- Respect des conditions d'utilisation Airbnb
- Délais entre requêtes pour éviter la surcharge
- Logs complets pour audit
- Possibilité d'arrêt immédiat

## 📅 Planification Automatique

Le système fonctionne selon ce planning:

| Tâche | Fréquence | Description |
|-------|-----------|-------------|
| **Scan Concurrents** | 30 minutes | Collecte des prix du marché |
| **Mise à jour Prix** | 1 heure | Optimisation et application |
| **Sync Propriétés** | 6 heures | Synchronisation Airbnb |
| **Rapport Quotidien** | 09:00 | Statistiques journalières |
| **Nettoyage Données** | Dimanche 02:00 | Maintenance base |
| **Health Check** | 15 minutes | Vérification système |

## 📈 Optimisation des Revenus

### Stratégies Implémentées

1. **Analyse Concurrentielle**
   - Score de similarité pondéré
   - Analyse des gaps de prix
   - Positionnement optimal

2. **Saisonnalité**
   - Multiplicateurs mensuels
   - Ajustements week-end
   - Événements locaux

3. **Demande du Marché**
   - Score basé sur disponibilités
   - Ajustement dynamique
   - Réaction aux tendances

4. **Gestion des Risques**
   - Limites de changement
   - Marge minimum garantie
   - Seuils de confiance

## 🔧 Maintenance

### Logs du Système
```bash
# Voir les logs en temps réel
tail -f airbnb_pricing.log

# Rechercher des erreurs
grep "ERROR" airbnb_pricing.log
```

### Base de Données
```bash
# Backup de la base
cp airbnb_pricing.db backup_$(date +%Y%m%d).db

# Vérifier la taille
ls -lh airbnb_pricing.db
```

### Monitoring
- Le système génère des logs détaillés
- Health checks automatiques toutes les 15 minutes
- Alertes en cas de dysfonctionnement
- Rapports quotidiens par email (optionnel)

## 🆘 Dépannage

### Problèmes Courants

#### Erreur de Connexion Airbnb
```bash
# Tester la connexion
python main.py test

# Vérifier les identifiants dans .env
cat .env | grep AIRBNB
```

#### Tableau de Bord Inaccessible
```bash
# Vérifier le port
netstat -tlnp | grep 8050

# Lancer sur un autre port
python main.py dashboard --port 8051
```

#### Problème de Base de Données
```bash
# Réinitialiser
rm airbnb_pricing.db
python main.py init
```

### Support Technique

Pour toute assistance:
1. Vérifiez les logs: `airbnb_pricing.log`
2. Testez la connexion: `python main.py test`
3. Réinitialisez si nécessaire: `python main.py init`

## 📝 Changelog

### Version 1.0.0 (2024)
- ✅ Système complet de gestion automatisée
- ✅ Interface web interactive
- ✅ Surveillance continue 24/7
- ✅ Algorithme d'optimisation avancé
- ✅ Intégration complète Airbnb

## 📄 Licence

Ce système est développé spécifiquement pour **Miftah Conciergerie**.

---

**🎯 Maximisez vos revenus Airbnb avec l'automatisation intelligente !**

Pour démarrer immédiatement:
```bash
python main.py full
```
Puis rendez-vous sur: **http://localhost:8050**
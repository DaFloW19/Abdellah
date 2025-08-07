# 🏠 Système de Gestion Automatique des Prix Airbnb

Un système intelligent et automatisé pour optimiser les prix de vos annonces Airbnb en temps réel, basé sur l'analyse concurrentielle et des algorithmes de pricing dynamique.

## 🎯 Compte Airbnb Configuré

- **Email**: miftah.conciergerie@gmail.com
- **Mot de passe**: Mifta2123!

## ✨ Fonctionnalités Principales

### 📊 Surveillance en Temps Réel
- **Monitoring continu** des prix des concurrents directs
- **Mise à jour automatique** toutes les 30 minutes (configurable)
- **Tableau de bord en temps réel** avec graphiques interactifs

### 🧮 Algorithme de Pricing Intelligent
- **Analyse concurrentielle** automatisée
- **Calcul du prix optimal** basé sur :
  - Moyenne et médiane des concurrents
  - Qualité de votre annonce (notes, avis)
  - Facteurs saisonniers
  - Taux d'occupation
- **Niveau de confiance** pour chaque recommandation

### 🤖 Automatisation Complète
- **Mise à jour automatique** des prix sur Airbnb
- **Conditions configurables** (seuil de confiance, variation max)
- **Historique complet** des changements de prix
- **Notifications** en temps réel

### 📈 Analytics Avancés
- **Graphiques d'évolution** des prix sur 30 jours
- **Distribution des prix** concurrents
- **Analyse des tendances** du marché
- **Rapports de performance**

## 🚀 Installation et Démarrage

### Prérequis
- Python 3.8+
- Google Chrome + ChromeDriver
- Connexion internet stable

### Installation Rapide

```bash
# 1. Cloner le projet
git clone <repository-url>
cd airbnb-price-automation

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Installer ChromeDriver (si nécessaire)
# Ubuntu:
sudo apt-get install chromium-chromedriver

# MacOS:
brew install chromedriver

# 4. Lancer l'application
python start.py
```

### Accès au Tableau de Bord

Une fois démarré, accédez au tableau de bord :
- **Interface Web**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🛠️ Configuration

### Variables d'Environnement (.env)

```env
AIRBNB_EMAIL=miftah.conciergerie@gmail.com
AIRBNB_PASSWORD=Mifta2123!
DATABASE_URL=sqlite:///airbnb_pricing.db
UPDATE_INTERVAL_MINUTES=30
MIN_PRICE_MARGIN=0.05
MAX_PRICE_MARGIN=0.15
```

### Paramètres Système

Depuis le tableau de bord, configurez :
- **Mise à jour automatique** : Activer/Désactiver
- **Seuil de confiance** : Minimum pour auto-update (défaut: 70%)
- **Intervalle de mise à jour** : 15min à 6h (défaut: 30min)

## 📋 Utilisation

### 1. Premier Démarrage
1. Le système se connecte automatiquement à Airbnb
2. Récupère vos annonces existantes
3. Lance la première analyse concurrentielle
4. Affiche les recommandations dans le tableau de bord

### 2. Surveillance Continue
- Le système surveille automatiquement les prix
- Calcule en continu le prix optimal
- Met à jour automatiquement si les conditions sont remplies
- Enregistre tout dans l'historique

### 3. Contrôle Manuel
- **Actualiser** : Force une nouvelle analyse
- **Appliquer le prix** : Met à jour manuellement
- **Configurer** : Ajustez les paramètres selon vos besoins

## 📊 Interface du Tableau de Bord

### Cartes de Résumé
- **Prix Actuel** : Prix en vigueur sur Airbnb
- **Prix Recommandé** : Prix optimal calculé
- **Moyenne Concurrents** : Prix moyen du marché
- **Variation** : Différence recommandée

### Graphiques
- **Évolution des Prix** : Historique sur 30 jours
- **Distribution Concurrentielle** : Répartition des prix du marché

### Analyse Concurrentielle
- **Liste des concurrents** : Propriétés similaires
- **Détails des prix** : Prix, notes, avis
- **Actions** : Liens vers les annonces

## 🔧 Architecture Technique

### Structure du Projet
```
airbnb-price-automation/
├── main.py                 # Application FastAPI principale
├── start.py               # Script de démarrage
├── requirements.txt       # Dépendances Python
├── .env                   # Configuration
├── services/              # Services métier
│   ├── airbnb_client.py   # Client Airbnb (Selenium)
│   ├── competitor_analyzer.py # Analyse concurrentielle
│   └── price_monitor.py   # Surveillance des prix
├── utils/                 # Utilitaires
│   └── pricing_algorithm.py # Algorithme de pricing
├── database/              # Base de données
│   └── models.py          # Modèles SQLAlchemy
├── templates/             # Templates HTML
│   └── dashboard.html     # Interface utilisateur
└── static/                # Fichiers statiques
    ├── css/dashboard.css  # Styles CSS
    └── js/dashboard.js    # JavaScript
```

### Technologies Utilisées
- **Backend** : FastAPI, SQLAlchemy, Pandas, NumPy
- **Scraping** : Selenium WebDriver, BeautifulSoup
- **Frontend** : Bootstrap 5, Chart.js, JavaScript moderne
- **Base de données** : SQLite (extensible à PostgreSQL)

## 🔄 API Endpoints

### Données en Temps Réel
- `GET /api/current-prices` - Prix actuels et recommandations
- `GET /api/price-history` - Historique des prix
- `GET /api/status` - Statut du système

### Actions
- `POST /api/update-price` - Mettre à jour le prix manuellement
- `POST /api/force-analysis` - Forcer une nouvelle analyse

## 📈 Algorithme de Pricing

### Facteurs de Calcul
1. **Prix de base** : Moyenne/médiane des concurrents
2. **Qualité** : Note et nombre d'avis (+/-20%)
3. **Saisonnier** : Facteur selon la période (+/-25%)
4. **Occupation** : Ajustement selon la demande (+/-10%)

### Conditions de Mise à Jour Auto
- Confiance ≥ 70%
- Changement entre 5€ et 50€
- Variation ≤ 15% par rapport à la concurrence

## 🛡️ Sécurité et Fiabilité

### Sécurité
- Credentials stockés en variables d'environnement
- Mode headless pour Selenium
- Rate limiting pour éviter la détection
- Gestion des erreurs robuste

### Fiabilité
- Retry automatique en cas d'échec
- Validation des données avant application
- Logs détaillés pour debugging
- Sauvegarde automatique de l'historique

## 📊 Monitoring et Logs

### Fichiers de Logs
- `airbnb_pricing.log` : Logs complets du système
- Rotation automatique des logs
- Niveaux : INFO, WARNING, ERROR

### Métriques Surveillées
- Nombre de concurrents analysés
- Temps de réponse des analyses
- Taux de succès des mises à jour
- Évolution de la confiance

## 🔧 Maintenance

### Tâches Régulières
- Vérifier les logs d'erreur
- Mettre à jour ChromeDriver si nécessaire
- Sauvegarder la base de données
- Ajuster les paramètres selon les performances

### Dépannage
- **Connexion Airbnb échoue** : Vérifier credentials
- **Scraping ne fonctionne pas** : Mettre à jour ChromeDriver
- **Performance lente** : Réduire la fréquence d'analyse

## 📞 Support

Pour toute question ou problème :
1. Consultez les logs dans `airbnb_pricing.log`
2. Vérifiez la documentation API sur `/docs`
3. Ajustez les paramètres via l'interface web

## 🚀 Fonctionnalités Futures

- Support multi-annonces
- Intégration API Airbnb officielle
- Alertes par email/SMS
- Machine Learning pour prédictions
- Analyse de la concurrence étendue
- Export des rapports en PDF

---

**Système développé pour maximiser les revenus de votre conciergerie Airbnb avec une automatisation intelligente et fiable.**
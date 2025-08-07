#!/bin/bash

# Script d'installation automatique pour le système de gestion des prix Airbnb
# Compte: miftah.conciergerie@gmail.com

set -e  # Arrêter le script en cas d'erreur

echo "🚀 Installation du Système de Gestion Automatique des Prix Airbnb"
echo "=================================================================="
echo "📧 Compte configuré: miftah.conciergerie@gmail.com"
echo "🔧 Installation en cours..."
echo ""

# Fonction pour détecter l'OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            echo "ubuntu"
        elif [ -f /etc/redhat-release ]; then
            echo "centos"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Fonction pour installer Python si nécessaire
install_python() {
    echo "🐍 Vérification de Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1,2)
        echo "✅ Python $PYTHON_VERSION trouvé"
        
        # Vérifier que la version est 3.8+
        if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
            echo "✅ Version Python compatible"
        else
            echo "❌ Python 3.8+ requis, version actuelle: $PYTHON_VERSION"
            exit 1
        fi
    else
        echo "❌ Python 3 non trouvé"
        echo "💡 Veuillez installer Python 3.8+ depuis https://python.org"
        exit 1
    fi
}

# Fonction pour installer pip si nécessaire
install_pip() {
    echo "📦 Vérification de pip..."
    
    if command -v pip3 &> /dev/null; then
        echo "✅ pip trouvé"
    else
        echo "📥 Installation de pip..."
        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        python3 get-pip.py
        rm get-pip.py
    fi
}

# Fonction pour installer ChromeDriver selon l'OS
install_chromedriver() {
    echo "🌐 Installation de ChromeDriver..."
    
    OS=$(detect_os)
    
    case $OS in
        "ubuntu")
            echo "🐧 Détection: Ubuntu/Debian"
            sudo apt-get update
            sudo apt-get install -y chromium-browser chromium-chromedriver
            ;;
        "centos")
            echo "🐧 Détection: CentOS/RHEL"
            sudo yum install -y chromium chromium-chromedriver
            ;;
        "macos")
            echo "🍎 Détection: macOS"
            if command -v brew &> /dev/null; then
                brew install chromedriver
            else
                echo "❌ Homebrew non trouvé"
                echo "💡 Installez Homebrew depuis https://brew.sh puis relancez ce script"
                exit 1
            fi
            ;;
        "windows")
            echo "🪟 Détection: Windows"
            echo "💡 Veuillez télécharger ChromeDriver manuellement:"
            echo "   https://chromedriver.chromium.org/"
            echo "   Et ajoutez-le à votre PATH"
            ;;
        *)
            echo "❓ OS non reconnu: $OSTYPE"
            echo "💡 Installez ChromeDriver manuellement pour votre système"
            ;;
    esac
}

# Fonction pour installer les dépendances Python
install_dependencies() {
    echo "📚 Installation des dépendances Python..."
    
    # Upgrade pip
    python3 -m pip install --upgrade pip
    
    # Installer les dépendances
    python3 -m pip install -r requirements.txt
    
    echo "✅ Dépendances installées"
}

# Fonction pour créer les dossiers nécessaires
setup_directories() {
    echo "📁 Création de la structure de dossiers..."
    
    mkdir -p logs
    mkdir -p data
    mkdir -p backups
    
    echo "✅ Dossiers créés"
}

# Fonction pour configurer la base de données
setup_database() {
    echo "🗄️ Configuration de la base de données..."
    
    python3 -c "
from database.models import init_db
init_db()
print('✅ Base de données initialisée')
"
}

# Fonction pour créer un service systemd (Linux uniquement)
create_systemd_service() {
    if [[ "$(detect_os)" == "ubuntu" ]] || [[ "$(detect_os)" == "centos" ]]; then
        echo "⚙️ Création du service systemd..."
        
        CURRENT_DIR=$(pwd)
        SERVICE_FILE="/etc/systemd/system/airbnb-pricing.service"
        
        sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=Airbnb Price Automation Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=/usr/bin:/usr/local/bin:$PATH
ExecStart=/usr/bin/python3 $CURRENT_DIR/start.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable airbnb-pricing.service
        
        echo "✅ Service systemd créé"
        echo "💡 Utilisez 'sudo systemctl start airbnb-pricing' pour démarrer"
        echo "💡 Utilisez 'sudo systemctl status airbnb-pricing' pour vérifier"
    fi
}

# Fonction principale
main() {
    echo "🔧 Début de l'installation..."
    echo ""
    
    # Vérifications préliminaires
    install_python
    install_pip
    
    # Installation des composants
    install_chromedriver
    install_dependencies
    setup_directories
    
    # Configuration
    setup_database
    
    # Service système (optionnel)
    read -p "🤖 Voulez-vous créer un service système pour le démarrage automatique? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_systemd_service
    fi
    
    echo ""
    echo "🎉 Installation terminée avec succès!"
    echo "=================================================================="
    echo ""
    echo "🚀 Pour démarrer le système:"
    echo "   python3 start.py"
    echo ""
    echo "🌐 Une fois démarré, accédez au tableau de bord:"
    echo "   http://localhost:8000"
    echo ""
    echo "📊 Documentation API:"
    echo "   http://localhost:8000/docs"
    echo ""
    echo "📧 Compte configuré: miftah.conciergerie@gmail.com"
    echo "🔑 Mot de passe: Mifta2123!"
    echo ""
    echo "📋 Fonctionnalités disponibles:"
    echo "   ✓ Surveillance automatique des prix concurrents"
    echo "   ✓ Calcul intelligent du prix optimal"
    echo "   ✓ Tableau de bord en temps réel"
    echo "   ✓ Mise à jour automatique des prix"
    echo "   ✓ Historique et analytics"
    echo ""
    echo "⚠️  Important:"
    echo "   - Assurez-vous d'avoir une connexion internet stable"
    echo "   - Le premier scan peut prendre quelques minutes"
    echo "   - Consultez airbnb_pricing.log pour les détails"
    echo ""
    echo "✨ Bon business avec votre gestion automatisée!"
}

# Vérifier si le script est exécuté en tant que root (non recommandé)
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Ce script ne doit pas être exécuté en tant que root"
    echo "💡 Exécutez-le avec votre utilisateur normal"
    exit 1
fi

# Exécuter l'installation
main "$@"
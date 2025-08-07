// JavaScript pour le tableau de bord Airbnb en temps réel

class AirbnbDashboard {
    constructor() {
        this.updateInterval = 30000; // 30 secondes
        this.charts = {};
        this.lastData = null;
        this.init();
    }

    async init() {
        console.log('🚀 Initialisation du tableau de bord Airbnb');
        
        // Initialiser les graphiques
        this.initCharts();
        
        // Charger les données initiales
        await this.loadData();
        
        // Démarrer les mises à jour automatiques
        this.startAutoUpdate();
        
        // Configurer les événements
        this.setupEventListeners();
        
        console.log('✅ Tableau de bord initialisé');
    }

    initCharts() {
        // Graphique d'évolution des prix
        const priceCtx = document.getElementById('priceChart').getContext('2d');
        this.charts.price = new Chart(priceCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Prix Actuel',
                    data: [],
                    borderColor: '#ff5a5f',
                    backgroundColor: 'rgba(255, 90, 95, 0.1)',
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Prix Recommandé',
                    data: [],
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    fill: false,
                    tension: 0.4
                }, {
                    label: 'Moyenne Concurrents',
                    data: [],
                    borderColor: '#17a2b8',
                    backgroundColor: 'rgba(23, 162, 184, 0.1)',
                    fill: false,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return value + '€';
                            }
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 4,
                        hoverRadius: 6
                    }
                }
            }
        });

        // Graphique de distribution des prix
        const distributionCtx = document.getElementById('distributionChart').getContext('2d');
        this.charts.distribution = new Chart(distributionCtx, {
            type: 'doughnut',
            data: {
                labels: ['Prix Bas', 'Prix Moyen', 'Prix Élevé'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        '#28a745',
                        '#ffc107', 
                        '#dc3545'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    async loadData() {
        try {
            console.log('📡 Chargement des données...');
            
            // Charger les données actuelles
            const response = await fetch('/api/current-prices');
            if (!response.ok) throw new Error('Erreur réseau');
            
            const data = await response.json();
            this.lastData = data;
            
            // Mettre à jour l'interface
            this.updateUI(data);
            
            // Charger l'historique
            await this.loadHistory();
            
            // Charger les concurrents
            await this.loadCompetitors();
            
        } catch (error) {
            console.error('❌ Erreur lors du chargement:', error);
            this.showError('Erreur de connexion au serveur');
        }
    }

    async loadHistory() {
        try {
            const response = await fetch('/api/price-history');
            if (!response.ok) throw new Error('Erreur réseau');
            
            const data = await response.json();
            this.updatePriceChart(data.history);
            
        } catch (error) {
            console.error('❌ Erreur historique:', error);
        }
    }

    async loadCompetitors() {
        try {
            const competitorsData = this.lastData?.competitors || [];
            this.updateCompetitorsTable(competitorsData);
            this.updateDistributionChart(competitorsData);
            
        } catch (error) {
            console.error('❌ Erreur concurrents:', error);
        }
    }

    updateUI(data) {
        // Mettre à jour les cartes de résumé
        document.getElementById('current-price').textContent = `${data.current_price || 0}€`;
        document.getElementById('recommended-price').textContent = `${data.recommended_price || 0}€`;
        document.getElementById('competitor-average').textContent = `${Math.round(data.competitor_average || 0)}€`;
        
        // Calculer et afficher la variation
        const priceChange = (data.recommended_price || 0) - (data.current_price || 0);
        const priceChangeElement = document.getElementById('price-change');
        priceChangeElement.textContent = `${priceChange >= 0 ? '+' : ''}${Math.round(priceChange)}€`;
        priceChangeElement.className = priceChange >= 0 ? 'text-success' : 'text-danger';
        
        // Mettre à jour les détails de recommandation
        const confidence = data.pricing_details?.confidence || 0;
        document.getElementById('confidence-value').textContent = `${Math.round(confidence)}%`;
        
        const confidenceBar = document.getElementById('confidence-bar');
        confidenceBar.style.width = `${confidence}%`;
        confidenceBar.className = `progress-bar ${this.getConfidenceClass(confidence)}`;
        
        document.getElementById('reasoning').textContent = 
            data.pricing_details?.reasoning || 'En attente d\'analyse...';
        
        document.getElementById('last-update').textContent = 
            data.last_update ? this.formatDate(data.last_update) : '-';
    }

    updatePriceChart(history) {
        if (!history || history.length === 0) return;
        
        // Trier par date
        history.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        // Prendre les 30 derniers points
        const recentHistory = history.slice(-30);
        
        const labels = recentHistory.map(h => this.formatDate(h.timestamp, true));
        const currentPrices = recentHistory.map(h => h.current_price);
        const recommendedPrices = recentHistory.map(h => h.recommended_price);
        const competitorAverages = recentHistory.map(h => h.competitor_average);
        
        this.charts.price.data.labels = labels;
        this.charts.price.data.datasets[0].data = currentPrices;
        this.charts.price.data.datasets[1].data = recommendedPrices;
        this.charts.price.data.datasets[2].data = competitorAverages;
        
        this.charts.price.update('none');
    }

    updateCompetitorsTable(competitors) {
        const tbody = document.getElementById('competitors-table');
        
        if (!competitors || competitors.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">
                        <i class="fas fa-info-circle me-2"></i>
                        Aucun concurrent trouvé
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = '';
        
        competitors.forEach(competitor => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="fw-bold">${this.truncateText(competitor.title || 'N/A', 50)}</div>
                    <small class="text-muted">${competitor.property_type || ''}</small>
                </td>
                <td>
                    <span class="fw-bold">${competitor.price_per_night || 0}€</span>
                </td>
                <td>
                    ${competitor.rating ? `
                        <span class="badge bg-warning text-dark">
                            <i class="fas fa-star"></i> ${competitor.rating}
                        </span>
                    ` : '-'}
                </td>
                <td>${competitor.reviews_count || 0}</td>
                <td>
                    <small class="text-muted">${competitor.property_type || 'N/A'}</small>
                </td>
                <td>
                    <a href="${competitor.url}" target="_blank" class="btn btn-sm btn-outline-primary action-btn">
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    updateDistributionChart(competitors) {
        if (!competitors || competitors.length === 0) return;
        
        const prices = competitors.map(c => c.price_per_night).filter(p => p > 0);
        if (prices.length === 0) return;
        
        prices.sort((a, b) => a - b);
        const q1 = prices[Math.floor(prices.length * 0.33)];
        const q3 = prices[Math.floor(prices.length * 0.67)];
        
        const lowPrices = prices.filter(p => p <= q1).length;
        const midPrices = prices.filter(p => p > q1 && p <= q3).length;
        const highPrices = prices.filter(p => p > q3).length;
        
        this.charts.distribution.data.datasets[0].data = [lowPrices, midPrices, highPrices];
        this.charts.distribution.update('none');
    }

    setupEventListeners() {
        // Actualisation manuelle
        window.forceUpdate = async () => {
            await this.loadData();
            this.showSuccess('Données mises à jour');
        };
        
        // Application du prix recommandé
        window.updatePrice = async () => {
            if (!this.lastData?.recommended_price) {
                this.showError('Aucun prix recommandé disponible');
                return;
            }
            
            try {
                const response = await fetch('/api/update-price', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(this.lastData.recommended_price)
                });
                
                if (response.ok) {
                    this.showSuccess('Prix mis à jour avec succès');
                    await this.loadData();
                } else {
                    throw new Error('Erreur serveur');
                }
            } catch (error) {
                this.showError('Erreur lors de la mise à jour du prix');
            }
        };
        
        // Sauvegarde des paramètres
        window.saveSettings = () => {
            const autoUpdate = document.getElementById('autoUpdate').checked;
            const confidenceThreshold = document.getElementById('confidenceThreshold').value;
            const updateInterval = document.getElementById('updateInterval').value;
            
            // Sauvegarder en localStorage pour cette démo
            localStorage.setItem('airbnb_settings', JSON.stringify({
                autoUpdate,
                confidenceThreshold,
                updateInterval
            }));
            
            this.showSuccess('Paramètres sauvegardés');
        };
        
        // Charger les paramètres sauvegardés
        this.loadSettings();
    }

    loadSettings() {
        try {
            const settings = JSON.parse(localStorage.getItem('airbnb_settings') || '{}');
            
            if (settings.autoUpdate !== undefined) {
                document.getElementById('autoUpdate').checked = settings.autoUpdate;
            }
            if (settings.confidenceThreshold) {
                document.getElementById('confidenceThreshold').value = settings.confidenceThreshold;
            }
            if (settings.updateInterval) {
                document.getElementById('updateInterval').value = settings.updateInterval;
            }
        } catch (error) {
            console.log('Aucun paramètre sauvegardé trouvé');
        }
    }

    startAutoUpdate() {
        setInterval(async () => {
            console.log('🔄 Mise à jour automatique...');
            await this.loadData();
        }, this.updateInterval);
    }

    // Utilitaires
    getConfidenceClass(confidence) {
        if (confidence >= 80) return 'bg-success';
        if (confidence >= 60) return 'bg-warning';
        return 'bg-danger';
    }

    formatDate(dateString, short = false) {
        const date = new Date(dateString);
        const options = short 
            ? { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }
            : { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit' 
            };
        
        return date.toLocaleDateString('fr-FR', options);
    }

    truncateText(text, maxLength) {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'danger');
    }

    showNotification(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remove après 5 secondes
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// Initialiser le tableau de bord quand la page est chargée
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new AirbnbDashboard();
});

// Gestion des erreurs globales
window.addEventListener('error', (event) => {
    console.error('Erreur JavaScript:', event.error);
});

// Gestion de la perte de connexion
window.addEventListener('online', () => {
    window.dashboard?.showSuccess('Connexion rétablie');
});

window.addEventListener('offline', () => {
    window.dashboard?.showError('Connexion perdue');
});
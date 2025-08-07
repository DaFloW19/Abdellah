import dash
from dash import dcc, html, Input, Output, callback_context, dash_table
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import json
from config import Config
from models import get_session, create_database, Property, MarketAnalytics, PriceHistory, CompetitorPrice, Competitor
from pricing_algorithm import PricingAlgorithm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirbnbDashboard:
    def __init__(self):
        self.config = Config()
        self.engine = create_database(self.config.DATABASE_URL)
        self.pricing_algorithm = PricingAlgorithm()
        self.app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Configure la mise en page du tableau de bord"""
        self.app.layout = html.Div([
            # En-tête
            html.Div([
                html.H1("Tableau de Bord Airbnb - Gestion Automatisée des Prix", 
                       style={'textAlign': 'center', 'color': '#FF5A5F', 'marginBottom': 30}),
                html.P("Analyse en temps réel des concurrents et optimisation des tarifs", 
                      style={'textAlign': 'center', 'fontSize': 18, 'color': '#484848'})
            ], style={'backgroundColor': '#f8f9fa', 'padding': '20px', 'marginBottom': '20px'}),
            
            # Contrôles
            html.Div([
                html.Div([
                    html.Label("Sélectionner une propriété:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='property-dropdown',
                        options=[],
                        value=None,
                        placeholder="Chargement des propriétés..."
                    )
                ], className='six columns'),
                
                html.Div([
                    html.Label("Période d'analyse:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='period-dropdown',
                        options=[
                            {'label': 'Dernières 24h', 'value': 1},
                            {'label': 'Derniers 7 jours', 'value': 7},
                            {'label': 'Derniers 30 jours', 'value': 30},
                            {'label': 'Derniers 90 jours', 'value': 90}
                        ],
                        value=7
                    )
                ], className='six columns')
            ], className='row', style={'marginBottom': '20px'}),
            
            # Métriques principales
            html.Div(id='metrics-cards', className='row', style={'marginBottom': '20px'}),
            
            # Graphiques principaux
            html.Div([
                html.Div([
                    dcc.Graph(id='price-evolution-chart')
                ], className='six columns'),
                
                html.Div([
                    dcc.Graph(id='competitor-comparison-chart')
                ], className='six columns')
            ], className='row', style={'marginBottom': '20px'}),
            
            # Tableaux de données
            html.Div([
                html.Div([
                    html.H3("Analyse de Marché Actuelle", style={'textAlign': 'center'}),
                    html.Div(id='market-analysis-table')
                ], className='six columns'),
                
                html.Div([
                    html.H3("Historique des Prix", style={'textAlign': 'center'}),
                    html.Div(id='price-history-table')
                ], className='six columns')
            ], className='row', style={'marginBottom': '20px'}),
            
            # Section des recommandations
            html.Div([
                html.H3("Recommandations de Prix", style={'textAlign': 'center', 'color': '#FF5A5F'}),
                html.Div(id='price-recommendations')
            ], style={'backgroundColor': '#f8f9fa', 'padding': '20px', 'marginBottom': '20px'}),
            
            # Boutons d'action
            html.Div([
                html.Button('Actualiser les Données', id='refresh-btn', n_clicks=0, 
                           style={'backgroundColor': '#FF5A5F', 'color': 'white', 'marginRight': '10px'}),
                html.Button('Calculer Prix Optimal', id='calculate-btn', n_clicks=0,
                           style={'backgroundColor': '#008489', 'color': 'white', 'marginRight': '10px'}),
                html.Button('Appliquer Prix Recommandé', id='apply-price-btn', n_clicks=0,
                           style={'backgroundColor': '#FF8A00', 'color': 'white'})
            ], style={'textAlign': 'center', 'marginBottom': '20px'}),
            
            # Messages de statut
            html.Div(id='status-messages'),
            
            # Mise à jour automatique
            dcc.Interval(
                id='interval-component',
                interval=300*1000,  # 5 minutes
                n_intervals=0
            )
        ])
    
    def setup_callbacks(self):
        """Configure les callbacks pour l'interactivité"""
        
        @self.app.callback(
            Output('property-dropdown', 'options'),
            Output('property-dropdown', 'value'),
            [Input('interval-component', 'n_intervals'),
             Input('refresh-btn', 'n_clicks')]
        )
        def update_property_dropdown(n_intervals, refresh_clicks):
            properties = self.get_properties()
            options = [{'label': f"{prop['title']} (ID: {prop['id']})", 'value': prop['id']} 
                      for prop in properties]
            value = properties[0]['id'] if properties else None
            return options, value
        
        @self.app.callback(
            [Output('metrics-cards', 'children'),
             Output('price-evolution-chart', 'figure'),
             Output('competitor-comparison-chart', 'figure'),
             Output('market-analysis-table', 'children'),
             Output('price-history-table', 'children'),
             Output('price-recommendations', 'children')],
            [Input('property-dropdown', 'value'),
             Input('period-dropdown', 'value'),
             Input('interval-component', 'n_intervals'),
             Input('calculate-btn', 'n_clicks')]
        )
        def update_dashboard(property_id, period_days, n_intervals, calc_clicks):
            if not property_id:
                empty_fig = go.Figure()
                return [], empty_fig, empty_fig, [], [], []
            
            # Récupérer les données
            metrics = self.get_property_metrics(property_id, period_days)
            price_evolution = self.get_price_evolution_chart(property_id, period_days)
            competitor_comparison = self.get_competitor_comparison_chart(property_id)
            market_table = self.get_market_analysis_table(property_id)
            history_table = self.get_price_history_table(property_id, period_days)
            recommendations = self.get_price_recommendations(property_id)
            
            return metrics, price_evolution, competitor_comparison, market_table, history_table, recommendations
        
        @self.app.callback(
            Output('status-messages', 'children'),
            [Input('apply-price-btn', 'n_clicks')],
            [dash.dependencies.State('property-dropdown', 'value')]
        )
        def apply_recommended_price(n_clicks, property_id):
            if n_clicks > 0 and property_id:
                # Calculer le prix optimal
                result = self.pricing_algorithm.calculate_optimal_price(property_id)
                if result and result.get('price_change_needed'):
                    # Appliquer le nouveau prix
                    success = self.pricing_algorithm.update_property_price(
                        property_id, 
                        result['recommended_price'],
                        "Dashboard manual application"
                    )
                    
                    if success:
                        return html.Div([
                            html.Div(f"✅ Prix mis à jour avec succès: {result['recommended_price']}€", 
                                   style={'color': 'green', 'fontWeight': 'bold', 'textAlign': 'center'})
                        ])
                    else:
                        return html.Div([
                            html.Div("❌ Erreur lors de la mise à jour du prix", 
                                   style={'color': 'red', 'fontWeight': 'bold', 'textAlign': 'center'})
                        ])
                else:
                    return html.Div([
                        html.Div("ℹ️ Aucun changement de prix nécessaire", 
                               style={'color': 'blue', 'fontWeight': 'bold', 'textAlign': 'center'})
                    ])
            return ""
    
    def get_properties(self):
        """Récupère la liste des propriétés"""
        db_session = get_session(self.engine)
        try:
            properties = db_session.query(Property).filter_by(is_active=True).all()
            return [{'id': p.id, 'title': p.title, 'current_price': p.current_price} for p in properties]
        finally:
            db_session.close()
    
    def get_property_metrics(self, property_id, period_days):
        """Génère les cartes de métriques principales"""
        db_session = get_session(self.engine)
        
        try:
            property_obj = db_session.query(Property).filter_by(id=property_id).first()
            if not property_obj:
                return []
            
            # Calculer le prix optimal actuel
            optimal_result = self.pricing_algorithm.calculate_optimal_price(property_id)
            
            # Récupérer les analytics récentes
            recent_analytics = db_session.query(MarketAnalytics).filter_by(
                property_id=property_id
            ).order_by(MarketAnalytics.created_at.desc()).first()
            
            current_price = property_obj.current_price or 0
            optimal_price = optimal_result['recommended_price'] if optimal_result else current_price
            competitor_avg = recent_analytics.avg_competitor_price if recent_analytics else 0
            
            metrics_cards = [
                html.Div([
                    html.H4("Prix Actuel", style={'margin': 0}),
                    html.H2(f"{current_price}€", style={'margin': 0, 'color': '#484848'})
                ], className='three columns', style={
                    'backgroundColor': 'white', 'padding': '20px', 'border': '1px solid #ddd',
                    'borderRadius': '5px', 'textAlign': 'center', 'margin': '5px'
                }),
                
                html.Div([
                    html.H4("Prix Optimal", style={'margin': 0}),
                    html.H2(f"{optimal_price}€", style={'margin': 0, 'color': '#FF5A5F'})
                ], className='three columns', style={
                    'backgroundColor': 'white', 'padding': '20px', 'border': '1px solid #ddd',
                    'borderRadius': '5px', 'textAlign': 'center', 'margin': '5px'
                }),
                
                html.Div([
                    html.H4("Moyenne Concurrents", style={'margin': 0}),
                    html.H2(f"{competitor_avg:.0f}€", style={'margin': 0, 'color': '#008489'})
                ], className='three columns', style={
                    'backgroundColor': 'white', 'padding': '20px', 'border': '1px solid #ddd',
                    'borderRadius': '5px', 'textAlign': 'center', 'margin': '5px'
                }),
                
                html.Div([
                    html.H4("Écart Optimal", style={'margin': 0}),
                    html.H2(f"{optimal_price - current_price:+.0f}€", style={
                        'margin': 0, 
                        'color': 'green' if optimal_price > current_price else 'red' if optimal_price < current_price else 'gray'
                    })
                ], className='three columns', style={
                    'backgroundColor': 'white', 'padding': '20px', 'border': '1px solid #ddd',
                    'borderRadius': '5px', 'textAlign': 'center', 'margin': '5px'
                })
            ]
            
            return metrics_cards
            
        finally:
            db_session.close()
    
    def get_price_evolution_chart(self, property_id, period_days):
        """Génère le graphique d'évolution des prix"""
        db_session = get_session(self.engine)
        
        try:
            cutoff_date = datetime.now() - timedelta(days=period_days)
            
            # Récupérer l'historique des prix
            price_history = db_session.query(MarketAnalytics).filter(
                MarketAnalytics.property_id == property_id,
                MarketAnalytics.created_at >= cutoff_date
            ).order_by(MarketAnalytics.created_at).all()
            
            if not price_history:
                return go.Figure().add_annotation(text="Aucune donnée disponible", 
                                                x=0.5, y=0.5, showarrow=False)
            
            dates = [p.created_at for p in price_history]
            recommended_prices = [p.recommended_price for p in price_history]
            competitor_avg = [p.avg_competitor_price for p in price_history]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=dates, y=recommended_prices,
                mode='lines+markers',
                name='Prix Recommandé',
                line=dict(color='#FF5A5F', width=3)
            ))
            
            fig.add_trace(go.Scatter(
                x=dates, y=competitor_avg,
                mode='lines+markers',
                name='Moyenne Concurrents',
                line=dict(color='#008489', width=2)
            ))
            
            fig.update_layout(
                title="Évolution des Prix Recommandés vs Concurrents",
                xaxis_title="Date",
                yaxis_title="Prix (€)",
                hovermode='x unified',
                template="plotly_white"
            )
            
            return fig
            
        finally:
            db_session.close()
    
    def get_competitor_comparison_chart(self, property_id):
        """Génère le graphique de comparaison avec les concurrents"""
        db_session = get_session(self.engine)
        
        try:
            # Récupérer les concurrents et leurs derniers prix
            competitors = db_session.query(Competitor).filter_by(
                property_id=property_id, is_active=True
            ).all()
            
            competitor_data = []
            for comp in competitors[:10]:  # Limiter à 10 concurrents
                latest_price = db_session.query(CompetitorPrice).filter_by(
                    competitor_id=comp.id
                ).order_by(CompetitorPrice.scraped_at.desc()).first()
                
                if latest_price:
                    competitor_data.append({
                        'name': comp.title[:30] + "..." if len(comp.title) > 30 else comp.title,
                        'price': latest_price.price,
                        'similarity': comp.similarity_score
                    })
            
            if not competitor_data:
                return go.Figure().add_annotation(text="Aucun concurrent trouvé", 
                                                x=0.5, y=0.5, showarrow=False)
            
            df = pd.DataFrame(competitor_data)
            
            fig = px.scatter(df, x='similarity', y='price', 
                           hover_data=['name'],
                           title="Positionnement vs Concurrents",
                           labels={'similarity': 'Score de Similarité', 'price': 'Prix (€)'})
            
            fig.update_traces(marker=dict(size=12, color='#008489'))
            fig.update_layout(template="plotly_white")
            
            return fig
            
        finally:
            db_session.close()
    
    def get_market_analysis_table(self, property_id):
        """Génère le tableau d'analyse de marché"""
        db_session = get_session(self.engine)
        
        try:
            latest_analytics = db_session.query(MarketAnalytics).filter_by(
                property_id=property_id
            ).order_by(MarketAnalytics.created_at.desc()).first()
            
            if not latest_analytics:
                return html.P("Aucune analyse de marché disponible")
            
            data = [
                {"Métrique": "Prix Moyen Concurrents", "Valeur": f"{latest_analytics.avg_competitor_price:.2f}€"},
                {"Métrique": "Prix Médian", "Valeur": f"{latest_analytics.median_competitor_price:.2f}€"},
                {"Métrique": "Prix Minimum", "Valeur": f"{latest_analytics.min_competitor_price:.2f}€"},
                {"Métrique": "Prix Maximum", "Valeur": f"{latest_analytics.max_competitor_price:.2f}€"},
                {"Métrique": "Nombre de Concurrents", "Valeur": str(latest_analytics.total_competitors)},
                {"Métrique": "Concurrents Disponibles", "Valeur": str(latest_analytics.available_competitors)},
                {"Métrique": "Score de Demande", "Valeur": f"{latest_analytics.market_demand_score:.2f}"},
                {"Métrique": "Score de Confiance", "Valeur": f"{latest_analytics.confidence_score:.2f}"}
            ]
            
            return dash_table.DataTable(
                data=data,
                columns=[{"name": "Métrique", "id": "Métrique"}, {"name": "Valeur", "id": "Valeur"}],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': '#FF5A5F', 'color': 'white', 'fontWeight': 'bold'}
            )
            
        finally:
            db_session.close()
    
    def get_price_history_table(self, property_id, period_days):
        """Génère le tableau d'historique des prix"""
        db_session = get_session(self.engine)
        
        try:
            cutoff_date = datetime.now() - timedelta(days=period_days)
            
            history = db_session.query(PriceHistory).filter(
                PriceHistory.property_id == property_id,
                PriceHistory.created_at >= cutoff_date
            ).order_by(PriceHistory.created_at.desc()).limit(10).all()
            
            if not history:
                return html.P("Aucun historique de prix disponible")
            
            data = []
            for h in history:
                data.append({
                    "Date": h.created_at.strftime("%d/%m/%Y %H:%M"),
                    "Ancien Prix": f"{h.old_price:.2f}€" if h.old_price else "N/A",
                    "Nouveau Prix": f"{h.new_price:.2f}€" if h.new_price else "N/A",
                    "Raison": h.reason or "N/A"
                })
            
            return dash_table.DataTable(
                data=data,
                columns=[
                    {"name": "Date", "id": "Date"},
                    {"name": "Ancien Prix", "id": "Ancien Prix"},
                    {"name": "Nouveau Prix", "id": "Nouveau Prix"},
                    {"name": "Raison", "id": "Raison"}
                ],
                style_cell={'textAlign': 'left'},
                style_header={'backgroundColor': '#008489', 'color': 'white', 'fontWeight': 'bold'}
            )
            
        finally:
            db_session.close()
    
    def get_price_recommendations(self, property_id):
        """Génère les recommandations de prix"""
        try:
            result = self.pricing_algorithm.calculate_optimal_price(property_id)
            
            if not result:
                return html.P("Impossible de calculer le prix optimal")
            
            current_price = result.get('current_price', 0)
            recommended_price = result.get('recommended_price', 0)
            confidence = result.get('confidence_score', 0)
            demand_score = result.get('market_demand_score', 0)
            
            color = 'green' if recommended_price > current_price else 'red' if recommended_price < current_price else 'gray'
            arrow = '📈' if recommended_price > current_price else '📉' if recommended_price < current_price else '➡️'
            
            return html.Div([
                html.Div([
                    html.H4(f"{arrow} Prix Recommandé: {recommended_price}€", 
                           style={'color': color, 'textAlign': 'center'}),
                    html.P(f"Prix Actuel: {current_price}€ | Écart: {recommended_price - current_price:+.2f}€",
                          style={'textAlign': 'center'}),
                    html.P(f"Confiance: {confidence:.0%} | Demande du Marché: {demand_score:.0%}",
                          style={'textAlign': 'center', 'color': '#666'})
                ], style={'backgroundColor': 'white', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '5px'})
            ])
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des recommandations: {e}")
            return html.P("Erreur lors du calcul des recommandations")
    
    def run(self, debug=True, host='0.0.0.0', port=8050):
        """Lance le serveur du tableau de bord"""
        logger.info(f"Lancement du tableau de bord sur http://{host}:{port}")
        self.app.run_server(debug=debug, host=host, port=port)

if __name__ == "__main__":
    dashboard = AirbnbDashboard()
    dashboard.run()
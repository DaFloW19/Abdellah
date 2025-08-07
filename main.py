import asyncio
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
import uvicorn
import os
from dotenv import load_dotenv

from services.price_monitor import PriceMonitor
from services.competitor_analyzer import CompetitorAnalyzer
from services.airbnb_client import AirbnbClient
from database.models import init_db
from utils.pricing_algorithm import PricingAlgorithm

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Airbnb Price Automation", version="1.0.0")

# Configuration des templates et fichiers statiques
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Services globaux
price_monitor = None
competitor_analyzer = None
airbnb_client = None
pricing_algorithm = None

@app.on_event("startup")
async def startup_event():
    """Initialisation de l'application"""
    global price_monitor, competitor_analyzer, airbnb_client, pricing_algorithm
    
    logger.info("🚀 Démarrage du système de gestion automatique des prix Airbnb...")
    
    # Initialiser la base de données
    init_db()
    
    # Initialiser les services
    airbnb_client = AirbnbClient(
        email=os.getenv("AIRBNB_EMAIL"),
        password=os.getenv("AIRBNB_PASSWORD")
    )
    
    competitor_analyzer = CompetitorAnalyzer()
    pricing_algorithm = PricingAlgorithm()
    price_monitor = PriceMonitor(
        airbnb_client=airbnb_client,
        competitor_analyzer=competitor_analyzer,
        pricing_algorithm=pricing_algorithm
    )
    
    # Démarrer la surveillance en arrière-plan
    asyncio.create_task(price_monitor.start_monitoring())
    
    logger.info("✅ Système initialisé avec succès!")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Page principale du tableau de bord"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/current-prices")
async def get_current_prices():
    """API pour récupérer les prix actuels et recommandations"""
    try:
        if not price_monitor:
            raise HTTPException(status_code=500, detail="Service non initialisé")
        
        data = await price_monitor.get_current_data()
        return {
            "timestamp": datetime.now().isoformat(),
            "competitor_average": data.get("competitor_average", 0),
            "recommended_price": data.get("recommended_price", 0),
            "current_price": data.get("current_price", 0),
            "competitors": data.get("competitors", []),
            "last_update": data.get("last_update", "")
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des prix: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/price-history")
async def get_price_history():
    """API pour récupérer l'historique des prix"""
    try:
        if not price_monitor:
            raise HTTPException(status_code=500, detail="Service non initialisé")
        
        history = await price_monitor.get_price_history()
        return {"history": history}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/update-price")
async def update_price(new_price: float):
    """API pour mettre à jour manuellement le prix"""
    try:
        if not airbnb_client:
            raise HTTPException(status_code=500, detail="Client Airbnb non initialisé")
        
        success = await airbnb_client.update_listing_price(new_price)
        if success:
            return {"message": f"Prix mis à jour avec succès: {new_price}€"}
        else:
            raise HTTPException(status_code=400, detail="Échec de la mise à jour du prix")
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du prix: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_system_status():
    """API pour vérifier le statut du système"""
    return {
        "status": "running",
        "monitoring_active": price_monitor.is_monitoring if price_monitor else False,
        "last_check": price_monitor.last_check if price_monitor else None,
        "uptime": str(datetime.now() - price_monitor.start_time) if price_monitor and price_monitor.start_time else "0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
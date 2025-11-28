"""
Serveur de contrôle WebSocket pour robot
"""

from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from datetime import datetime
from ultrasonic_sensor import UltrasonicSensor
import logging
import yaml
import sys
import os

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.motor_controller import MotorController

logger = logging.getLogger(__name__)


class ControlServer:
    """Serveur de contrôle du robot"""
    
    def __init__(self, config_path='config/config.yaml'):
        """
        Initialise le serveur de contrôle
        
        Args:
            config_path (str): Chemin vers le fichier de configuration
        """
        # Charger la configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Configurer les logs
        self._setup_logging()
        
        logger.info("=" * 60)
        logger.info("🤖 DÉMARRAGE DU SERVEUR DE CONTRÔLE ROBOT")
        logger.info("=" * 60)
        
        # Initialiser le contrôleur de moteurs
        self.motor_controller = MotorController(self.config)
        
        # Initialiser Flask et SocketIO
        self.app = Flask(__name__, static_folder="../static")
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins=self.config['security']['cors_allowed_origins'],
            async_mode=self.config['performance']['async_mode']
        )
        
        # Enregistrer les routes et événements
        self._register_routes()
        self._register_socketio_events()
        
        logger.info("✅ Serveur de contrôle initialisé")
    
    def _setup_logging(self):
        """Configure le système de logs"""
        log_config = self.config['logging']
        
        # Créer le dossier logs s'il n'existe pas
        os.makedirs('logs', exist_ok=True)
        
        # Configuration du logger
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format'],
            handlers=[
                logging.FileHandler(log_config['file']),
                logging.StreamHandler() if log_config['console'] else logging.NullHandler()
            ]
        )
    
    def _register_routes(self):
        """Enregistre les routes HTTP"""
        
        @self.app.route("/")
        def index():
            logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] 📄 Page index.html demandée")
            return send_from_directory("../static", "index.html")
        
        @self.app.route("/<path:filename>")
        def serve_static(filename):
            logger.debug(f"[{datetime.now().strftime('%H:%M:%S')}] 📄 Fichier demandé: {filename}")
            return send_from_directory("../static", filename)
    
    def _register_socketio_events(self):
        """Enregistre les événements SocketIO"""
        
        @self.socketio.on("connect")
        def on_connect():
            logger.info(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ CLIENT CONNECTÉ")
            logger.info("=" * 60)
        
        @self.socketio.on("disconnect")
        def on_disconnect():
            # Arrêter les moteurs lors de la déconnexion
            self.motor_controller.stop_all()
            logger.info(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ CLIENT DÉCONNECTÉ")
            logger.info("=" * 60)
        
        @self.socketio.on("control_update")
        def on_control(data):
            joy = data.get("joystick", {"x": 0, "y": 0})
            gyro_enabled = data.get("gyro_enabled", False)
            gyro_x = data.get("gyro_x", 0)
            
            # Mettre à jour les moteurs
            state = self.motor_controller.update(joy, gyro_enabled, gyro_x)
            
            # Log détaillé
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            motor_a = state['motor_a']
            motor_b = state['motor_b']
            
            # Symboles de direction
            dir_a_symbol = "⬆" if motor_a['direction'] == "forward" else "⬇" if motor_a['direction'] == "backward" else "⏸"
            dir_b_symbol = "⬅" if motor_b['direction'] == "backward" else "➡" if motor_b['direction'] == "forward" else "⏸"
            
            logger.info(f"\n[{timestamp}] 🎮 COMMANDE")
            logger.info(f"   {motor_a['motor']}: {dir_a_symbol} {motor_a['direction'].upper():8s} | {motor_a['speed_percent']:3.0f}%")
            logger.info(f"   {motor_b['motor']}: {dir_b_symbol} {motor_b['direction'].upper():8s} | {motor_b['speed_percent']:3.0f}% [{motor_b['source']}]")
    
    def run(self):
        """Lance le serveur"""
        ssl_config = self.config['ssl']
        network_config = self.config['network']
        
        logger.info("\n🔐 Configuration SSL:")
        logger.info(f"   Certificat: {ssl_config['cert_path']}")
        logger.info(f"   Clé privée: {ssl_config['key_path']}")
        
        logger.info("\n🚀 SERVEUR PRÊT")
        logger.info("=" * 60)
        logger.info(f"🌐 HTTPS WebSocket: https://{network_config['raspberry_pi_ip']}:{network_config['control_port']}")
        logger.info("=" * 60)
        logger.info("\n⏳ En attente de connexions...\n")
        
        try:
            self.socketio.run(
                self.app,
                host="0.0.0.0",
                port=network_config['control_port'],
                keyfile=ssl_config['key_path'],
                certfile=ssl_config['cert_path'],
                allow_unsafe_werkzeug=True
            )
        except keyboardInterrupt:
        	logger.info("\n🛑 Arrêt du serveur...")
        finally:
            self.ultrasonic_sensor.cleanup()
            logger.info("✅ Ressources ultrason libérées")
            self.motor_controller.cleanup()
            
    def on_obstacle_detected(self, distance):
        logger.warning(f"⚠️  OBSTACLE à {distance} cm - ARRÊT")
    
    	# Arrêter les moteurs
        self.motor_controller.stop_all()
    
    	# Notifier le client
        self.socketio.emit("obstacle_detected", {
            "distance": distance,
            "message": f"Obstacle détecté à {distance} cm",
            "action": "stop"
        })
    
        self.socketio.emit("suggest_direction_change", {
            "message": "Changez de direction pour éviter l'obstacle",
            "suggested_action": "reverse_or_turn"
        })


if __name__ == "__main__":
    server = ControlServer()
    server.run()

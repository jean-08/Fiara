"""
Proxy caméra HTTPS optimisé pour faible latence
"""

from flask import Flask, Response, request, jsonify
import requests
from datetime import datetime
import logging
import yaml
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


class CameraProxy:
    """Proxy HTTPS pour stream caméra Android avec optimisation de latence"""
    
    def __init__(self, config_path='config/config.yaml'):
        """
        Initialise le proxy caméra
        
        Args:
            config_path (str): Chemin vers le fichier de configuration
        """
        # Charger la configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Configurer les logs
        self._setup_logging()
        
        logger.info("=" * 60)
        logger.info("📹 DÉMARRAGE DU PROXY CAMÉRA HTTPS")
        logger.info("=" * 60)
        
        # Configuration caméra
        self.camera_config = self.config['camera']
        
        # Initialiser Flask
        self.app = Flask(__name__)
        
        # Désactiver la mise en cache
        self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
        
        # Enregistrer les routes
        self._register_routes()
        
        logger.info("✅ Proxy caméra initialisé")
        logger.info(f"   Qualité JPEG: {self.camera_config['jpeg_quality']}")
        logger.info(f"   Chunk size: {self.camera_config['chunk_size']} bytes")
        logger.info(f"   Timeout: {self.camera_config['connection_timeout']}s")
    
    def _setup_logging(self):
        """Configure le système de logs"""
        log_config = self.config['logging']
        
        os.makedirs('logs', exist_ok=True)
        
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
        
        @self.app.route('/stream')
        def stream():
            """Proxy pour le stream vidéo IP Webcam (optimisé pour faible latence)"""
            android_ip = request.args.get('ip')
            android_port = request.args.get('port')
            
            if not android_ip or not android_port:
                return jsonify({"error": "Missing IP or port parameters"}), 400
            
            # URL du stream IP Webcam
            stream_url = f"http://{android_ip}:{android_port}/video"
            
            logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Streaming depuis: {stream_url}")
            
            try:
                # Session requests avec keep-alive pour réduire la latence
                session = requests.Session()
                
                # Requête vers IP Webcam avec timeout court
                r = session.get(
                    stream_url,
                    stream=True,
                    timeout=self.camera_config['connection_timeout'],
                    headers={'Connection': 'keep-alive'}
                )
                
                if r.status_code != 200:
                    logger.error(f"Erreur de connexion caméra: {r.status_code}")
                    return jsonify({"error": f"Camera error: {r.status_code}"}), 502
                
                # Générateur pour streaming avec chunk size optimisé
                def generate():
                    try:
                        for chunk in r.iter_content(chunk_size=self.camera_config['chunk_size']):
                            if chunk:
                                yield chunk
                    except Exception as e:
                        logger.error(f"Erreur pendant le streaming: {e}")
                
                # Retourner le stream avec headers optimisés
                response = Response(
                    generate(),
                    content_type=r.headers.get('content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary'),
                    direct_passthrough=True
                )
                
                # Headers pour réduire la latence
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                response.headers['X-Accel-Buffering'] = 'no'  # Désactiver le buffering nginx
                
                return response
            
            except requests.exceptions.Timeout:
                logger.error(f"Timeout lors de la connexion à {stream_url}")
                return jsonify({"error": "Connection timeout"}), 504
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Erreur de connexion: {e}")
                return jsonify({"error": f"Cannot connect: {str(e)}"}), 503
        
        @self.app.route('/snapshot')
        def snapshot():
            """Proxy pour une image fixe (snapshot)"""
            android_ip = request.args.get('ip')
            android_port = request.args.get('port')
            
            if not android_ip or not android_port:
                return jsonify({"error": "Missing IP or port"}), 400
            
            snapshot_url = f"http://{android_ip}:{android_port}/shot.jpg"
            
            try:
                r = requests.get(snapshot_url, timeout=self.camera_config['connection_timeout'])
                if r.status_code == 200:
                    return Response(r.content, mimetype='image/jpeg')
                else:
                    return jsonify({"error": "Camera error"}), 502
            except:
                return jsonify({"error": "Cannot connect"}), 503
        
        @self.app.route('/health')
        def health():
            """Endpoint de santé"""
            return jsonify({
                "status": "ok",
                "service": "camera-proxy",
                "config": {
                    "jpeg_quality": self.camera_config['jpeg_quality'],
                    "chunk_size": self.camera_config['chunk_size']
                }
            }), 200
    
    def run(self):
        """Lance le serveur proxy"""
        ssl_config = self.config['ssl']
        network_config = self.config['network']
        
        logger.info("\n🔐 Configuration SSL:")
        logger.info(f"   Certificat: {ssl_config['cert_path']}")
        logger.info(f"   Clé privée: {ssl_config['key_path']}")
        
        logger.info("\n🚀 PROXY CAMÉRA PRÊT")
        logger.info("=" * 60)
        logger.info(f"🌐 HTTPS Proxy: https://{network_config['raspberry_pi_ip']}:{network_config['camera_proxy_port']}")
        logger.info("📹 Usage: /stream?ip=192.168.X.X&port=8080")
        logger.info("=" * 60)
        logger.info("\n⏳ En attente de connexions...\n")
        
        self.app.run(
            host="0.0.0.0",
            port=network_config['camera_proxy_port'],
            ssl_context=(ssl_config['cert_path'], ssl_config['key_path']),
            threaded=True
        )


if __name__ == "__main__":
    proxy = CameraProxy()
    proxy.run()

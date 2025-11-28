# 📖 Explication Détaillée du Code

## 1️⃣ config.yaml - Configuration Centralisée

### Pourquoi YAML ?
- Format lisible par humains
- Facile à modifier sans toucher au code
- Supporte commentaires et structure hiérarchique

### Structure Détaillée

```yaml
network:
  raspberry_pi_ip: "192.168.182.41"
```
**Explication**: IP du Raspberry Pi sur le réseau local. Utilisée pour générer les URLs HTTPS.

```yaml
  control_port: 5007
  camera_proxy_port: 5008
```
**Explication**: Ports différents pour séparer les services. 5007 = contrôle, 5008 = caméra.

```yaml
gpio:
  motor_a:
    enable_pin: 18    # PWM
    input1_pin: 17
    input2_pin: 27
    max_speed: 1.0
```
**Explication détaillée**:
- `enable_pin`: Pin PWM (Pulse Width Modulation) qui contrôle la VITESSE du moteur (0-100%)
- `input1_pin` et `input2_pin`: Pins qui contrôlent la DIRECTION
  - IN1=HIGH, IN2=LOW → Avant
  - IN1=LOW, IN2=HIGH → Arrière
  - IN1=LOW, IN2=LOW → Stop
- `max_speed`: Limite maximale (1.0 = 100%, 0.5 = 50%). Utile pour moteurs puissants.

```yaml
camera:
  jpeg_quality: 70
  chunk_size: 4096
```
**Explication**:
- `jpeg_quality`: Compression JPEG (1-100)
  - Plus bas = fichiers plus petits = moins de latence
  - Plus haut = meilleure qualité mais plus de latence
  - 70 = bon compromis
- `chunk_size`: Taille des paquets réseau
  - Plus grand = moins de paquets = moins d'overhead réseau
  - 4096 bytes = optimal pour WiFi

---

## 2️⃣ motor_controller.py - Contrôle des Moteurs

### Classe Motor

```python
class Motor:
    def __init__(self, name, enable_pin, input1_pin, input2_pin, max_speed=1.0):
```
**Explication**: 
- Représente UN moteur DC
- Encapsule toute la logique GPIO pour ce moteur
- `name`: pour les logs (ex: "Motor A")
- `max_speed`: limite de sécurité

```python
self.enable = PWMOutputDevice(enable_pin)
self.input1 = DigitalOutputDevice(input1_pin)
self.input2 = DigitalOutputDevice(input2_pin)
```
**Explication**:
- `PWMOutputDevice`: Pin qui peut envoyer un signal PWM (0.0 à 1.0)
  - PWM = rapport cyclique (duty cycle)
  - 0.5 = 50% du temps à HIGH → moteur à mi-vitesse
- `DigitalOutputDevice`: Pin binaire (HIGH/LOW, 1/0)

### Méthode set_speed

```python
def set_speed(self, value):
    value = max(-1.0, min(1.0, value))  # Clamp entre -1 et +1
```
**Explication**: Limite la valeur reçue pour éviter des valeurs aberrantes.

```python
speed = min(abs(value), self.max_speed)
```
**Explication**: 
- `abs(value)`: valeur absolue (0.8 ou -0.8 → 0.8)
- Compare avec `max_speed` pour ne pas dépasser la limite

```python
if value > 0:
    self.input1.on()   # HIGH
    self.input2.off()  # LOW
    self.enable.value = speed
    direction = "forward"
```
**Explication**: Configuration pour AVANCER
- Table de vérité du L298N:
  - IN1=1, IN2=0, EN=PWM → Moteur tourne sens 1 à vitesse PWM

```python
elif value < 0:
    self.input1.off()  # LOW
    self.input2.on()   # HIGH
    self.enable.value = speed
    direction = "backward"
```
**Explication**: Configuration pour RECULER (direction inversée)

```python
else:
    self.input1.off()
    self.input2.off()
    self.enable.value = 0
    direction = "stop"
```
**Explication**: ARRÊT total (toutes les pins à LOW)

### Classe MotorController

```python
def __init__(self, config):
    motor_a_cfg = config['gpio']['motor_a']
    self.motor_a = Motor(
        name="Motor A (Avance/Recul)",
        enable_pin=motor_a_cfg['enable_pin'],
        ...
    )
```
**Explication**: 
- Lit la config YAML
- Crée les objets Motor avec les bons paramètres
- Sépare Motor A (avance/recul) et Motor B (virage)

```python
def update(self, joystick, gyro_enabled=False, gyro_x=0):
    motor_a_value = joystick.get('y', 0)
    state_a = self.motor_a.set_speed(motor_a_value)
```
**Explication**:
- Joystick Y (haut/bas) → Motor A (avance/recul)
- Appelle `set_speed` qui fait tout le travail GPIO

```python
if gyro_enabled:
    motor_b_value = gyro_x
    source = "GYRO"
else:
    motor_b_value = joystick.get('x', 0)
    source = "JOY"
```
**Explication**: 
- Choix de la source pour le virage
- Gyroscope = inclinaison du téléphone
- Joystick X (gauche/droite) = backup

---

## 3️⃣ control_server.py - Serveur WebSocket

### Initialisation

```python
class ControlServer:
    def __init__(self, config_path='config/config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
```
**Explication**:
- `yaml.safe_load()`: Parse le fichier YAML en dictionnaire Python
- Stocké dans `self.config` pour accès global

```python
self.motor_controller = MotorController(self.config)
```
**Explication**: Crée le contrôleur de moteurs en lui passant la config

```python
self.app = Flask(__name__, static_folder="../static")
self.socketio = SocketIO(
    self.app,
    cors_allowed_origins=self.config['security']['cors_allowed_origins'],
    async_mode=self.config['performance']['async_mode']
)
```
**Explication**:
- `Flask`: Framework web Python
- `static_folder`: où trouver index.html, app.js, etc.
- `SocketIO`: Extension pour WebSocket
- `cors_allowed_origins="*"`: autorise toutes les origines (navigateurs)
- `async_mode="gevent"`: mode asynchrone performant

### Routes HTTP

```python
@self.app.route("/")
def index():
    return send_from_directory("../static", "index.html")
```
**Explication**:
- Décorateur `@app.route`: définit l'URL
- `"/"` = racine du site (ex: https://192.168.182.41:5007/)
- `send_from_directory`: sert le fichier HTML

### Événements WebSocket

```python
@self.socketio.on("connect")
def on_connect():
    logger.info("✅ CLIENT CONNECTÉ")
```
**Explication**:
- Décorateur `@socketio.on`: écoute un événement
- `"connect"`: événement automatique quand un client se connecte
- Appelé automatiquement par SocketIO

```python
@self.socketio.on("disconnect")
def on_disconnect():
    self.motor_controller.stop_all()
```
**Explication**:
- Événement de déconnexion
- **IMPORTANT**: Arrête les moteurs si le client se déconnecte
- Sécurité : évite que le robot continue à bouger

```python
@self.socketio.on("control_update")
def on_control(data):
    joy = data.get("joystick", {"x": 0, "y": 0})
    gyro_enabled = data.get("gyro_enabled", False)
    gyro_x = data.get("gyro_x", 0)
```
**Explication**:
- Événement personnalisé "control_update"
- Reçoit les données du client (JavaScript)
- `data.get(key, default)`: récupère la valeur ou valeur par défaut

```python
state = self.motor_controller.update(joy, gyro_enabled, gyro_x)
```
**Explication**: Transmet les commandes au contrôleur de moteurs

### Démarrage du serveur

```python
self.socketio.run(
    self.app,
    host="0.0.0.0",
    port=network_config['control_port'],
    keyfile=ssl_config['key_path'],
    certfile=ssl_config['cert_path'],
    allow_unsafe_werkzeug=True
)
```
**Explication**:
- `host="0.0.0.0"`: écoute sur toutes les interfaces réseau
- `port`: du fichier config (5007)
- `keyfile` et `certfile`: certificats SSL pour HTTPS
- `allow_unsafe_werkzeug`: permet d'utiliser le serveur dev en production

---

## 4️⃣ camera_proxy.py - Proxy Caméra

### Pourquoi un proxy ?

**Problème**: 
- Interface robot = HTTPS (sécurisé)
- IP Webcam Android = HTTP (non sécurisé)
- Navigateurs modernes bloquent le "Mixed Content"

**Solution**: 
- Proxy qui récupère HTTP et resert en HTTPS

### Route /stream

```python
@self.app.route('/stream')
def stream():
    android_ip = request.args.get('ip')
    android_port = request.args.get('port')
```
**Explication**:
- URL: `/stream?ip=192.168.1.100&port=8080`
- `request.args.get()`: récupère les paramètres de l'URL

```python
stream_url = f"http://{android_ip}:{android_port}/video"
session = requests.Session()
r = session.get(stream_url, stream=True, timeout=5)
```
**Explication**:
- `Session()`: garde la connexion HTTP ouverte (keep-alive)
- `stream=True`: ne télécharge pas tout d'un coup, mais par morceaux
- `timeout=5`: abandonne si pas de réponse en 5s

```python
def generate():
    for chunk in r.iter_content(chunk_size=4096):
        if chunk:
            yield chunk
```
**Explication**:
- Générateur Python (fonction avec `yield`)
- Lit le stream par paquets de 4096 bytes
- `yield`: envoie le chunk puis continue la boucle
- Permet le streaming sans charger tout en RAM

```python
response = Response(generate(), content_type='multipart/x-mixed-replace')
response.headers['Cache-Control'] = 'no-cache'
response.headers['X-Accel-Buffering'] = 'no'
```
**Explication**:
- `multipart/x-mixed-replace`: format MJPEG (stream d'images JPEG)
- `Cache-Control`: ne pas mettre en cache (toujours récent)
- `X-Accel-Buffering`: pas de buffering (réduit latence)

---

## 5️⃣ app.js - Logique Client

### Configuration

```javascript
const CONFIG = {
    wsUrl: `wss://${window.location.hostname}:5007`,
    joySensitivity: 1.0,
    deadZone: 0.05
};
```
**Explication**:
- `window.location.hostname`: IP actuelle (détecte automatiquement)
- `wss://`: WebSocket Secure (HTTPS)
- `deadZone`: ignore les mouvements < 5%

### État Global

```javascript
const state = {
    joystick: { x: 0, y: 0 },
    gyroEnabled: false,
    fpvEnabled: false,
    connected: false
};
```
**Explication**: 
- Objet qui centralise tout l'état de l'application
- Accessible partout dans le code
- Mis à jour selon les événements

### WebSocket

```javascript
let socket = io(CONFIG.wsUrl, {
    transports: ["websocket"],
    secure: true,
    rejectUnauthorized: false
});
```
**Explication**:
- `io()`: fonction de Socket.io client
- `transports`: force WebSocket (pas de fallback HTTP polling)
- `secure: true`: HTTPS
- `rejectUnauthorized: false`: accepte certificats auto-signés

```javascript
socket.on("connect", () => {
    state.connected = true;
    updateStatus("✅ Connecté", "connected");
});
```
**Explication**:
- Événement déclenché quand la connexion réussit
- Met à jour l'état et l'interface

### Joysticks (nipplejs)

```javascript
const leftStick = nipplejs.create({
    zone: document.getElementById('joy_left'),
    mode: 'static',
    position: { left: '50%', top: '50%' },
    color: '#00d4ff',
    size: 120
});
```
**Explication**:
- `nipplejs`: bibliothèque pour joysticks tactiles
- `zone`: élément HTML où dessiner le joystick
- `mode: 'static'`: joystick fixe (pas dynamique)
- `position`: centre de la zone

```javascript
leftStick.on('move', (evt, data) => {
    let value = data.vector.x * CONFIG.joySensitivity;
    
    if (Math.abs(value) < CONFIG.deadZone) value = 0;
    
    state.joystick.x = value * (state.invertX ? -1 : 1);
    sendControl();
});
```
**Explication**:
- `on('move')`: événement déclenché pendant le mouvement
- `data.vector.x`: valeur normalisée (-1 à +1)
- Dead zone: ignore petits mouvements accidentels
- Inversion: multiplie par -1 si activé
- `sendControl()`: envoie la commande au serveur

### Throttling (limitation débit)

```javascript
let lastSendTime = 0;
const MIN_SEND_INTERVAL = 50;

function sendControl() {
    const now = Date.now();
    if (now - lastSendTime < MIN_SEND_INTERVAL) return;
    lastSendTime = now;
    
    socket.emit("control_update", data);
}
```
**Explication**:
- `Date.now()`: timestamp actuel en millisecondes
- Vérifie si 50ms se sont écoulés depuis le dernier envoi
- Si non → `return` (quitte la fonction)
- Si oui → envoie et met à jour `lastSendTime`
- **Résultat**: Max 20 envois/seconde (20 Hz)

### Gyroscope

```javascript
window.addEventListener('devicemotion', (event) => {
    if (state.gyroEnabled && event.accelerationIncludingGravity) {
        const rawGyroX = (event.accelerationIncludingGravity.x || 0) / 10;
        state.gyroX = Math.max(-1, Math.min(1, rawGyroX));
        sendControl();
    }
});
```
**Explication**:
- `devicemotion`: événement du navigateur (accéléromètre)
- `accelerationIncludingGravity.x`: inclinaison gauche/droite
- Division par 10: normalisation approximative
- `Math.max(-1, Math.min(1, x))`: clamp entre -1 et +1

### FPV Proxy

```javascript
state.fpvUrl = `${CONFIG.proxyUrl}/stream?ip=${ip}&port=${port}`;
fpvCenter.src = state.fpvUrl;
```
**Explication**:
- Construit l'URL du proxy avec paramètres
- `fpvCenter.src`: charge l'image/stream
- Le navigateur gère automatiquement le MJPEG

---

## 6️⃣ index.html - Interface

### Structure

```html
<div id="fpv-background"></div>  <!-- Vidéo plein écran (paysage) -->
<img id="fpv-center">            <!-- Vidéo centrée (portrait) -->

<div class="controls">
    <button id="gyroToggle">...</button>
    <button id="fpvToggle">...</button>
</div>

<div id="joy_left"></div>        <!-- Joystick gauche -->
<div id="joy_right"></div>       <!-- Joystick droit -->
```

### CSS Glassmorphism

```css
background: rgba(255, 255, 255, 0.1);
backdrop-filter: blur(15px);
```
**Explication**:
- `rgba(..., 0.1)`: fond semi-transparent (10% opacité)
- `backdrop-filter: blur()`: effet de flou sur l'arrière-plan
- Crée un effet "verre dépoli" moderne

### Responsive Design

```css
@media (orientation: landscape) {
    .controls {
        grid-template-columns: repeat(4, 1fr);
    }
}
```
**Explication**:
- `@media`: règles CSS conditionnelles
- `orientation: landscape`: mode paysage (horizontal)
- `repeat(4, 1fr)`: 4 colonnes de taille égale
- Adapte automatiquement l'interface

---

## 🔄 Flux Complet d'une Commande

1. **Utilisateur** touche le joystick droit vers le haut
2. **nipplejs** détecte le mouvement et calcule `vector.y = 0.8`
3. **app.js** applique:
   - Sensibilité: `0.8 × 1.0 = 0.8`
   - Dead zone: `0.8 > 0.05` ✅
   - Inversion: `0.8 × 1 = 0.8` (si pas inversé)
   - Throttling: vérifie si > 50ms depuis dernier envoi
4. **Socket.io** envoie via WebSocket: `{"joystick": {"x": 0, "y": 0.8}, ...}`
5. **control_server.py** reçoit dans `on_control(data)`
6. **motor_controller.py** reçoit `joystick.y = 0.8`
7. **Motor A** calcule:
   - Direction: `0.8 > 0` → avant
   - Vitesse: `min(0.8, 1.0) = 0.8`
   - PWM: `80%`
8. **GPIO 18** envoie signal PWM à 80%
9. **GPIO 17** = HIGH, **GPIO 27** = LOW
10. **L298N** reçoit les signaux et alimente le moteur
11. **Moteur A** tourne en avant à 80% de sa vitesse max
12. **Robot** avance

**Temps total**: ~50-100ms 🚀

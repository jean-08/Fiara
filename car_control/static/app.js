// ========================================
// ROBOT CONTROL - CLIENT JAVASCRIPT
// ========================================

console.log('🤖 Initialisation du système de contrôle...');

// test ultrasonic
let obstacleWarningTimeout = null;
let directionSuggestionTimeout = null;
// === CONFIGURATION ===
const CONFIG = {
    wsUrl: `wss://${window.location.hostname}:${window.location.port || 5007}`,
    proxyUrl: `https://${window.location.hostname}:5008`,
    joySensitivity: 1.0,
    deadZone: 0.05,
    reconnectDelay: 3000
};

// === ÉTAT GLOBAL ===
const state = {
    joystick: { x: 0, y: 0 },
    gyroEnabled: false,
    gyroX: 0,
    invertX: false,
    invertY: false,
    fpvEnabled: false,
    fpvUrl: null,
    connected: false
};

// === WEBSOCKET ===
let socket = io(CONFIG.wsUrl, {
    transports: ["websocket"],
    secure: true,
    rejectUnauthorized: false,
    reconnection: true,
    reconnectionDelay: CONFIG.reconnectDelay
});

socket.on("connect", () => {
    state.connected = true;
    updateStatus("✅ Connecté", "connected");
    console.log("✅ WebSocket connecté");
});
socket.on("obstacle_detected", (data) => {
    console.warn("⚠️ Obstacle détecté:", data);
    
    const warningEl = document.getElementById('obstacleWarning');
    const distanceEl = document.getElementById('obstacleDistance');
    
    if (warningEl && distanceEl) {
        distanceEl.textContent = `${data.distance} cm`;
        warningEl.classList.add('active');
        
        if (navigator.vibrate) {
            navigator.vibrate([200, 100, 200]);
        }
        
        playAlertSound();
        
        clearTimeout(obstacleWarningTimeout);
        obstacleWarningTimeout = setTimeout(() => {
            warningEl.classList.remove('active');
        }, 5000);
    }
    
    state.joystick = { x: 0, y: 0 };
    sendControl();
});

socket.on("suggest_direction_change", (data) => {
    console.info("💡 Suggestion:", data);
    
    const suggestionEl = document.getElementById('directionSuggestion');
    
    if (suggestionEl) {
        suggestionEl.textContent = `💡 ${data.message}`;
        suggestionEl.classList.add('active');
        
        clearTimeout(directionSuggestionTimeout);
        directionSuggestionTimeout = setTimeout(() => {
            suggestionEl.classList.remove('active');
        }, 7000);
    }
});

function playAlertSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
        console.warn("Impossible de jouer le son:", error);
    }
}
socket.on("disconnect", () => {
    state.connected = false;
    updateStatus("❌ Déconnecté", "disconnected");
    console.log("❌ WebSocket déconnecté");
});

socket.on("connect_error", (error) => {
    console.error("❌ Erreur de connexion:", error);
    updateStatus("⚠ Erreur de connexion", "disconnected");
});

// === JOYSTICKS ===
console.log('🎮 Initialisation des joysticks...');

// Joystick gauche (Virage - axe X)
const leftStick = nipplejs.create({
    zone: document.getElementById('joy_left'),
    mode: 'static',
    position: { left: '50%', top: '50%' },
    color: '#00d4ff',
    size: 120,
    restOpacity: 0.6
});

leftStick.on('move', (evt, data) => {
    if (!data.vector) return;
    
    let value = data.vector.x * CONFIG.joySensitivity;
    
    // Dead zone
    if (Math.abs(value) < CONFIG.deadZone) value = 0;
    
    // Inversion
    state.joystick.x = value * (state.invertX ? -1 : 1);
    
    sendControl();
});

leftStick.on('end', () => {
    state.joystick.x = 0;
    sendControl();
});

// Joystick droit (Avance/Recul - axe Y)
const rightStick = nipplejs.create({
    zone: document.getElementById('joy_right'),
    mode: 'static',
    position: { left: '50%', top: '50%' },
    color: '#ff4757',
    size: 120,
    restOpacity: 0.6
});

rightStick.on('move', (evt, data) => {
    if (!data.vector) return;
    
    let value = data.vector.y * CONFIG.joySensitivity;
    
    // Dead zone
    if (Math.abs(value) < CONFIG.deadZone) value = 0;
    
    // Inversion
    state.joystick.y = value * (state.invertY ? -1 : 1);
    
    sendControl();
});

rightStick.on('end', () => {
    state.joystick.y = 0;
    sendControl();
});

console.log('✅ Joysticks initialisés');

// === BOUTONS DE CONTRÔLE ===

// Toggle Gyroscope
document.getElementById('gyroToggle').onclick = () => {
    state.gyroEnabled = !state.gyroEnabled;
    const btn = document.getElementById('gyroToggle');
    
    btn.innerText = `📱 Gyro ${state.gyroEnabled ? "ON" : "OFF"}`;
    btn.classList.toggle('active', state.gyroEnabled);
    
    console.log(`📱 Gyroscope: ${state.gyroEnabled ? 'ACTIVÉ' : 'DÉSACTIVÉ'}`);
    
    // Demander la permission sur iOS
    if (state.gyroEnabled && typeof DeviceMotionEvent.requestPermission === 'function') {
        DeviceMotionEvent.requestPermission()
            .then(permissionState => {
                if (permissionState !== 'granted') {
                    state.gyroEnabled = false;
                    btn.innerText = "📱 Gyro OFF";
                    btn.classList.remove('active');
                    alert('⚠ Permission gyroscope refusée');
                    console.log('❌ Permission gyroscope refusée');
                } else {
                    console.log('✅ Permission gyroscope accordée');
                }
            })
            .catch(err => {
                console.error('❌ Erreur permission gyroscope:', err);
                state.gyroEnabled = false;
                btn.innerText = "📱 Gyro OFF";
                btn.classList.remove('active');
            });
    }
};

// Toggle FPV
document.getElementById('fpvToggle').onclick = () => {
    if (!state.fpvEnabled) {
        showFPVModal();
    } else {
        disableFPV();
    }
};

// Toggle Inversion X
document.getElementById('invertXToggle').onclick = () => {
    state.invertX = !state.invertX;
    const btn = document.getElementById('invertXToggle');
    btn.innerText = `⬅➡ Inv ${state.invertX ? "ON" : "OFF"}`;
    btn.classList.toggle('active', state.invertX);
    console.log(`🔄 Inversion X: ${state.invertX ? 'ACTIVÉE' : 'DÉSACTIVÉE'}`);
};

// Toggle Inversion Y
document.getElementById('invertYToggle').onclick = () => {
    state.invertY = !state.invertY;
    const btn = document.getElementById('invertYToggle');
    btn.innerText = `⬆⬇ Inv ${state.invertY ? "ON" : "OFF"}`;
    btn.classList.toggle('active', state.invertY);
    console.log(`🔄 Inversion Y: ${state.invertY ? 'ACTIVÉE' : 'DÉSACTIVÉE'}`);
};

// === MODAL FPV ===

function showFPVModal() {
    document.getElementById('fpv-modal').style.display = 'block';
    document.getElementById('modal-backdrop').style.display = 'block';
}

function hideFPVModal() {
    document.getElementById('fpv-modal').style.display = 'none';
    document.getElementById('modal-backdrop').style.display = 'none';
}

// Bouton Connecter FPV
document.getElementById('fpv-connect').onclick = () => {
    const ip = document.getElementById('fpv-ip').value.trim();
    const port = document.getElementById('fpv-port').value.trim();
    
    if (!ip || !port) {
        alert('⚠ Veuillez remplir tous les champs');
        return;
    }
    
    // Construire l'URL du proxy
    state.fpvUrl = `${CONFIG.proxyUrl}/stream?ip=${ip}&port=${port}`;
    
    console.log('📹 Connexion FPV via proxy:', state.fpvUrl);
    
    enableFPV();
    hideFPVModal();
};

// Bouton Annuler
document.getElementById('fpv-cancel').onclick = hideFPVModal;

// Fermer le modal en cliquant sur le backdrop
document.getElementById('modal-backdrop').onclick = hideFPVModal;

// === GESTION FPV ===

function enableFPV() {
    state.fpvEnabled = true;
    
    const btn = document.getElementById('fpvToggle');
    btn.innerText = "📹 FPV ON";
    btn.classList.add('active');
    
    const isLandscape = window.innerWidth > window.innerHeight;
    const fpvBackground = document.getElementById('fpv-background');
    const fpvCenter = document.getElementById('fpv-center');
    const fpvOverlay = document.getElementById('fpv-overlay');
    
    if (isLandscape) {
        // Mode paysage: vidéo en arrière-plan
        fpvBackground.style.display = 'block';
        fpvCenter.style.display = 'none';
        fpvOverlay.style.display = 'none';
        fpvBackground.src = state.fpvUrl;
    } else {
        // Mode portrait: vidéo au centre
        fpvCenter.style.display = 'block';
        fpvBackground.style.display = 'none';
        fpvOverlay.style.display = 'block';
        fpvCenter.src = state.fpvUrl;
    }
    
    console.log('✅ FPV activé');
    
    // Gestion des erreurs
    const handleError = () => {
        console.error('❌ Erreur de chargement du stream FPV');
        alert('⚠ Impossible de charger le stream.\n\nVérifiez:\n✓ IP Webcam lancé sur Android\n✓ IP et port corrects\n✓ Même réseau WiFi');
        disableFPV();
    };
    
    const handleLoad = () => {
        console.log('✅ Stream FPV chargé avec succès');
    };
    
    fpvBackground.onerror = handleError;
    fpvCenter.onerror = handleError;
    fpvBackground.onload = handleLoad;
    fpvCenter.onload = handleLoad;
}

function disableFPV() {
    state.fpvEnabled = false;
    
    const btn = document.getElementById('fpvToggle');
    btn.innerText = "📹 FPV OFF";
    btn.classList.remove('active');
    
    const fpvBackground = document.getElementById('fpv-background');
    const fpvCenter = document.getElementById('fpv-center');
    const fpvOverlay = document.getElementById('fpv-overlay');
    
    fpvBackground.style.display = 'none';
    fpvCenter.style.display = 'none';
    fpvOverlay.style.display = 'none';
    
    fpvBackground.src = '';
    fpvCenter.src = '';
    
    console.log('❌ FPV désactivé');
}

// === GESTION ORIENTATION ===

function handleOrientationChange() {
    if (state.fpvEnabled && state.fpvUrl) {
        setTimeout(() => {
            const isLandscape = window.innerWidth > window.innerHeight;
            const fpvBackground = document.getElementById('fpv-background');
            const fpvCenter = document.getElementById('fpv-center');
            const fpvOverlay = document.getElementById('fpv-overlay');
            
            if (isLandscape) {
                fpvBackground.style.display = 'block';
                fpvCenter.style.display = 'none';
                fpvOverlay.style.display = 'none';
                fpvBackground.src = state.fpvUrl;
            } else {
                fpvCenter.style.display = 'block';
                fpvBackground.style.display = 'none';
                fpvOverlay.style.display = 'block';
                fpvCenter.src = state.fpvUrl;
            }
            
            console.log('🔄 Orientation changée:', isLandscape ? 'paysage' : 'portrait');
        }, 300);
    }
}

window.addEventListener('orientationchange', handleOrientationChange);
window.addEventListener('resize', handleOrientationChange);

// === GYROSCOPE ===

if (typeof DeviceMotionEvent !== 'undefined') {
    window.addEventListener('devicemotion', (event) => {
        if (state.gyroEnabled && event.accelerationIncludingGravity) {
            // Normalisation du gyroscope entre -1 et 1
            const rawGyroX = (event.accelerationIncludingGravity.x || 0) / 10;
            state.gyroX = Math.max(-1, Math.min(1, rawGyroX)) * (state.invertX ? -1 : 1);
            
            // Dead zone
            if (Math.abs(state.gyroX) < CONFIG.deadZone) {
                state.gyroX = 0;
            }
            
            sendControl();
        }
    });
    console.log('✅ Gyroscope disponible');
} else {
    console.log('⚠ Gyroscope non disponible sur cet appareil');
}

// === ENVOI COMMANDES ===

let lastSendTime = 0;
const MIN_SEND_INTERVAL = 50; // ms (20 Hz max)

function sendControl() {
    if (!state.connected) return;
    
    const now = Date.now();
    if (now - lastSendTime < MIN_SEND_INTERVAL) return;
    lastSendTime = now;
    
    const data = {
        joystick: state.joystick,
        gyro_enabled: state.gyroEnabled,
        gyro_x: state.gyroX
    };
    
    socket.emit("control_update", data);
}

// === UTILITAIRES ===

function updateStatus(text, statusClass) {
    const statusEl = document.getElementById('status');
    statusEl.innerText = text;
    statusEl.className = statusClass === 'connected' ? 'status-connected' : 'status-disconnected';
    
    if (statusClass === 'connected') {
        statusEl.classList.remove('pulse');
    } else {
        statusEl.classList.add('pulse');
    }
}

// === INITIALISATION COMPLÈTE ===

console.log('✅ Système de contrôle initialisé');
console.log('🎮 Joystick gauche: Virage (axe X)');
console.log('🎮 Joystick droit: Avance/Recul (axe Y)');
console.log('📹 FPV: Cliquez sur le bouton pour configurer');
console.log('📱 Gyroscope: Disponible pour le contrôle de virage');
console.log('⚙️ Dead zone:', CONFIG.deadZone);
console.log('⚙️ Sensibilité:', CONFIG.joySensitivity);

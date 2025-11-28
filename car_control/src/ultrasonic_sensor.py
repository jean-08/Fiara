"""
Module de détection d'obstacles avec capteur ultrason HC-SR04
GPIO 16 = TRIG
GPIO 24 = ECHO
Seuil de détection : 20 cm
"""

import RPi.GPIO as GPIO
import time
import logging
from threading import Thread, Event

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UltrasonicSensor:
    """Classe pour gérer le capteur ultrason HC-SR04"""
    
    def __init__(self, trig_pin=16, echo_pin=24, threshold_cm=20):
        """
        Initialise le capteur ultrason
        
        Args:
            trig_pin: Pin GPIO pour le trigger
            echo_pin: Pin GPIO pour l'echo
            threshold_cm: Distance seuil en cm pour détecter un obstacle
        """
        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
        self.threshold_cm = threshold_cm
        self.is_running = False
        self.stop_event = Event()
        self.obstacle_detected = False
        self.current_distance = None
        self.callback = None
        
        # Configuration des GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        GPIO.output(self.trig_pin, GPIO.LOW)
        
        logger.info(f"Capteur ultrason initialisé - TRIG: GPIO{trig_pin}, ECHO: GPIO{echo_pin}")
        logger.info(f"Seuil de détection: {threshold_cm} cm")
    
    def measure_distance(self):
        """
        Mesure la distance avec le capteur ultrason
        
        Returns:
            Distance en cm, ou None si erreur
        """
        try:
            # Envoie une impulsion de 10µs sur TRIG
            GPIO.output(self.trig_pin, GPIO.HIGH)
            time.sleep(0.00001)  # 10 microseconds
            GPIO.output(self.trig_pin, GPIO.LOW)
            
            # Attend que ECHO passe à HIGH avec timeout
            timeout = time.time() + 0.1  # 100ms timeout
            while GPIO.input(self.echo_pin) == GPIO.LOW:
                pulse_start = time.time()
                if pulse_start > timeout:
                    return None
            
            # Attend que ECHO repasse à LOW avec timeout
            timeout = time.time() + 0.1
            while GPIO.input(self.echo_pin) == GPIO.HIGH:
                pulse_end = time.time()
                if pulse_end > timeout:
                    return None
            
            # Calcul de la distance
            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34300) / 2  # Vitesse du son = 343 m/s
            
            return round(distance, 2)
            
        except Exception as e:
            logger.error(f"Erreur lors de la mesure: {e}")
            return None
    
    def set_obstacle_callback(self, callback):
        """
        Définit la fonction callback appelée lors de la détection d'obstacle
        
        Args:
            callback: Fonction à appeler avec la distance en paramètre
        """
        self.callback = callback
    
    def monitor_loop(self):
        """
        Boucle de monitoring qui vérifie continuellement la distance
        """
        logger.info("Démarrage du monitoring des obstacles...")
        
        while not self.stop_event.is_set():
            distance = self.measure_distance()
            
            if distance is not None:
                self.current_distance = distance
                
                # Détection d'obstacle
                if distance <= self.threshold_cm:
                    if not self.obstacle_detected:
                        self.obstacle_detected = True
                        logger.warning(f"⚠️  OBSTACLE DÉTECTÉ à {distance} cm!")
                        
                        # Appelle le callback si défini
                        if self.callback:
                            self.callback(distance)
                else:
                    if self.obstacle_detected:
                        logger.info(f"✅ Obstacle dégagé - Distance: {distance} cm")
                        self.obstacle_detected = False
            
            # Pause entre les mesures (évite de saturer le CPU)
            time.sleep(0.1)  # Mesure toutes les 100ms
    
    def start_monitoring(self):
        """Démarre le monitoring en arrière-plan"""
        if not self.is_running:
            self.is_running = True
            self.stop_event.clear()
            self.monitor_thread = Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Monitoring démarré")
    
    def stop_monitoring(self):
        """Arrête le monitoring"""
        if self.is_running:
            self.stop_event.set()
            self.monitor_thread.join(timeout=2)
            self.is_running = False
            logger.info("Monitoring arrêté")
    
    def cleanup(self):
        """Nettoie les ressources GPIO"""
        self.stop_monitoring()
        GPIO.cleanup([self.trig_pin, self.echo_pin])
        logger.info("GPIO nettoyés")


# Test du module si exécuté directement
if __name__ == "__main__":
    def test_callback(distance):
        print(f"Callback déclenché! Distance: {distance} cm")
    
    sensor = UltrasonicSensor(trig_pin=16, echo_pin=24, threshold_cm=20)
    sensor.set_obstacle_callback(test_callback)
    
    try:
        sensor.start_monitoring()
        print("Monitoring actif... Appuyez sur Ctrl+C pour arrêter")
        
        while True:
            time.sleep(1)
            if sensor.current_distance:
                print(f"Distance actuelle: {sensor.current_distance} cm")
    
    except KeyboardInterrupt:
        print("\nArrêt du programme...")
    finally:
        sensor.cleanup()

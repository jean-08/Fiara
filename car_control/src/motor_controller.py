"""
Contrôleur de moteurs pour robot
Gère les moteurs via GPIO 
"""

from gpiozero import PWMOutputDevice, DigitalOutputDevice
import logging

logger = logging.getLogger(__name__)


class Motor:
    """Classe représentant un moteur DC avec contrôle PWM"""
    
    def __init__(self, name, enable_pin, input1_pin, input2_pin, max_speed=1.0):
        """
        Initialise un moteur
        
        Args:
            name (str): Nom du moteur (ex: "Motor A")
            enable_pin (int): Pin PWM pour la vitesse
            input1_pin (int): Pin de direction 1
            input2_pin (int): Pin de direction 2
            max_speed (float): Vitesse maximale (0.0 à 1.0)
        """
        self.name = name
        self.max_speed = max_speed
        
        # Initialisation des pins GPIO
        self.enable = PWMOutputDevice(enable_pin)
        self.input1 = DigitalOutputDevice(input1_pin)
        self.input2 = DigitalOutputDevice(input2_pin)
        
        logger.info(f"✓ {name} initialisé: EN={enable_pin}, IN1={input1_pin}, IN2={input2_pin}, Max={max_speed*100}%")
        
        self.motor_controller = MotorController(self.config)
    
	    # AJOUT: Capteur ultrason
        self.ultrasonic_sensor = UltrasonicSensor(
            trig_pin=16,
            echo_pin=24,
            threshold_cm=20
        )
        self.ultrasonic_sensor.set_obstacle_callback(self.on_obstacle_detected)
        self.ultrasonic_sensor.start_monitoring()
        logger.info("🚨 Système de détection d'obstacles activé")
    
    
    def set_speed(self, value):
        """
        Définit la vitesse et la direction du moteur
        
        Args:
            value (float): Valeur entre -1.0 et 1.0
                          > 0 : avant
                          < 0 : arrière
                          = 0 : stop
        
        Returns:
            dict: État du moteur (direction, vitesse)
        """
        # Limiter la valeur
        value = max(-1.0, min(1.0, value))
        
        # Calculer la vitesse réelle avec max_speed
        speed = min(abs(value), self.max_speed)
        
        if value > 0:
            # Avant
            self.input1.on()
            self.input2.off()
            self.enable.value = speed
            direction = "forward"
        elif value < 0:
            # Arrière
            self.input1.off()
            self.input2.on()
            self.enable.value = speed
            direction = "backward"
        else:
            # Stop
            self.input1.off()
            self.input2.off()
            self.enable.value = 0
            direction = "stop"
        
        return {
            "motor": self.name,
            "direction": direction,
            "speed": speed,
            "speed_percent": round(speed * 100, 1)
        }
    
    def stop(self):
        """Arrête le moteur"""
        return self.set_speed(0)
    
    def cleanup(self):
        """Libère les ressources GPIO"""
        self.stop()
        self.enable.close()
        self.input1.close()
        self.input2.close()
        logger.info(f"✓ {self.name} nettoyé")
    

class MotorController:
    """Contrôleur principal pour tous les moteurs"""
    
    def __init__(self, config):
        """
        Initialise le contrôleur de moteurs
        
        Args:
            config (dict): Configuration des moteurs depuis config.yaml
        """
        self.config = config
        
        # Moteur A (Avance/Recul)
        motor_a_cfg = config['gpio']['motor_a']
        self.motor_a = Motor(
            name="Motor A (Avance/Recul)",
            enable_pin=motor_a_cfg['enable_pin'],
            input1_pin=motor_a_cfg['input1_pin'],
            input2_pin=motor_a_cfg['input2_pin'],
            max_speed=motor_a_cfg['max_speed']
        )
        
        # Moteur B (Virage)
        motor_b_cfg = config['gpio']['motor_b']
        self.motor_b = Motor(
            name="Motor B (Virage)",
            enable_pin=motor_b_cfg['enable_pin'],
            input1_pin=motor_b_cfg['input1_pin'],
            input2_pin=motor_b_cfg['input2_pin'],
            max_speed=motor_b_cfg['max_speed']
        )
        
        logger.info("✅ Contrôleur de moteurs initialisé")
    
    def update(self, joystick, gyro_enabled=False, gyro_x=0):
        """
        Met à jour les moteurs selon les commandes
        
        Args:
            joystick (dict): Commandes joystick {x, y}
            gyro_enabled (bool): Gyroscope activé
            gyro_x (float): Valeur gyroscope X
        
        Returns:
            dict: État des moteurs
        """
        # Moteur A : avance/recul (joystick Y)
        motor_a_value = joystick.get('y', 0)
        state_a = self.motor_a.set_speed(motor_a_value)
        
        # Moteur B : virage (joystick X ou gyroscope)
        if gyro_enabled:
            motor_b_value = gyro_x
            source = "GYRO"
        else:
            motor_b_value = joystick.get('x', 0)
            source = "JOY"
        
        state_b = self.motor_b.set_speed(motor_b_value)
        state_b['source'] = source
        
        return {
            'motor_a': state_a,
            'motor_b': state_b
        }
    
    def stop_all(self):
        """Arrête tous les moteurs"""
        self.motor_a.stop()
        self.motor_b.stop()
        logger.info("⏸ Tous les moteurs arrêtés")
    
    def cleanup(self):
        """Libère toutes les ressources"""
        self.motor_a.cleanup()
        self.motor_b.cleanup()
        logger.info("✅ Contrôleur de moteurs nettoyé")

#!/usr/bin/env python3
"""
Script de test rapide pour le capteur ultrason HC-SR04
Teste le branchement et les mesures de distance
"""

import RPi.GPIO as GPIO
import time
import sys

# Configuration
TRIG_PIN = 16
ECHO_PIN = 24
THRESHOLD_CM = 20

def measure_distance():
    """Effectue une mesure de distance"""
    # Envoie une impulsion de 10µs
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, GPIO.LOW)
    
    # Attend le début de l'impulsion ECHO
    timeout = time.time() + 0.1
    while GPIO.input(ECHO_PIN) == GPIO.LOW:
        pulse_start = time.time()
        if pulse_start > timeout:
            return None
    
    # Attend la fin de l'impulsion ECHO
    timeout = time.time() + 0.1
    while GPIO.input(ECHO_PIN) == GPIO.HIGH:
        pulse_end = time.time()
        if pulse_end > timeout:
            return None
    
    # Calcul de la distance
    pulse_duration = pulse_end - pulse_start
    distance = (pulse_duration * 34300) / 2
    
    return round(distance, 2)

def test_continuous():
    """Test en continu avec affichage"""
    print("\n" + "="*60)
    print("TEST CONTINU - Appuyez sur Ctrl+C pour arrêter")
    print("="*60)
    print(f"Seuil d'alerte: {THRESHOLD_CM} cm\n")
    
    obstacle_count = 0
    measure_count = 0
    
    try:
        while True:
            distance = measure_distance()
            measure_count += 1
            
            if distance is not None:
                # Affichage avec code couleur
                if distance <= THRESHOLD_CM:
                    obstacle_count += 1
                    print(f"🔴 [{measure_count:04d}] Distance: {distance:6.2f} cm  ⚠️  OBSTACLE DÉTECTÉ!")
                elif distance <= THRESHOLD_CM * 1.5:
                    print(f"🟡 [{measure_count:04d}] Distance: {distance:6.2f} cm  ⚠  Attention")
                else:
                    print(f"🟢 [{measure_count:04d}] Distance: {distance:6.2f} cm  ✓  OK")
            else:
                print(f"❌ [{measure_count:04d}] Erreur de mesure (timeout)")
            
            time.sleep(0.2)  # 5 mesures/seconde
    
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("STATISTIQUES")
        print("="*60)
        print(f"Mesures effectuées: {measure_count}")
        print(f"Obstacles détectés: {obstacle_count}")
        if measure_count > 0:
            print(f"Taux d'erreur: {((measure_count - obstacle_count) / measure_count * 100):.1f}%")
        print("="*60)

def test_single():
    """Test d'une seule mesure"""
    print("\n" + "="*60)
    print("TEST SIMPLE - Une mesure")
    print("="*60)
    
    distance = measure_distance()
    
    if distance is not None:
        print(f"\n✓ Distance mesurée: {distance} cm")
        
        if distance <= THRESHOLD_CM:
            print(f"⚠️  ALERTE: Obstacle à moins de {THRESHOLD_CM} cm!")
        else:
            print(f"✓ OK: Aucun obstacle détecté")
    else:
        print("\n❌ Erreur: Impossible de mesurer la distance")
        print("   Vérifiez les connexions!")
    
    print("="*60 + "\n")

def test_gpio_status():
    """Vérifie l'état des GPIO"""
    print("\n" + "="*60)
    print("VÉRIFICATION DES GPIO")
    print("="*60)
    
    try:
        # Test TRIG
        GPIO.output(TRIG_PIN, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(TRIG_PIN, GPIO.LOW)
        print(f"✓ GPIO {TRIG_PIN} (TRIG): OK - Pin en sortie")
        
        # Test ECHO
        echo_state = GPIO.input(ECHO_PIN)
        print(f"✓ GPIO {ECHO_PIN} (ECHO): OK - État actuel: {'HIGH' if echo_state else 'LOW'}")
        
        print("\n✓ Configuration GPIO correcte!")
    except Exception as e:
        print(f"\n❌ Erreur GPIO: {e}")
    
    print("="*60 + "\n")

def main():
    """Programme principal"""
    print("\n" + "="*60)
    print("TEST DU CAPTEUR ULTRASON HC-SR04")
    print("="*60)
    print(f"TRIG Pin: GPIO {TRIG_PIN}")
    print(f"ECHO Pin: GPIO {ECHO_PIN}")
    print(f"Seuil: {THRESHOLD_CM} cm")
    print("="*60 + "\n")
    
    # Configuration des GPIO
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(TRIG_PIN, GPIO.OUT)
        GPIO.setup(ECHO_PIN, GPIO.IN)
        GPIO.output(TRIG_PIN, GPIO.LOW)
        time.sleep(0.1)  # Stabilisation
        
        print("✓ GPIO configurés\n")
    except Exception as e:
        print(f"❌ Erreur lors de la configuration GPIO: {e}")
        sys.exit(1)
    
    # Menu
    while True:
        print("\nCHOISISSEZ UN TEST:")
        print("1. Test simple (1 mesure)")
        print("2. Test continu (mesures en boucle)")
        print("3. Vérifier l'état des GPIO")
        print("4. Quitter")
        
        choice = input("\nVotre choix (1-4): ").strip()
        
        try:
            if choice == "1":
                test_single()
            elif choice == "2":
                test_continuous()
            elif choice == "3":
                test_gpio_status()
            elif choice == "4":
                print("\nArrêt du programme...")
                break
            else:
                print("\n❌ Choix invalide. Entrez 1, 2, 3 ou 4.")
        
        except KeyboardInterrupt:
            print("\n\nInterruption détectée...")
            break
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
    
    # Nettoyage
    GPIO.cleanup([TRIG_PIN, ECHO_PIN])
    print("✓ GPIO nettoyés")
    print("="*60)
    print("Programme terminé")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nArrêt forcé...")
        GPIO.cleanup([TRIG_PIN, ECHO_PIN])
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        GPIO.cleanup([TRIG_PIN, ECHO_PIN])
        sys.exit(1)

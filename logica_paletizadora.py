#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import cv2
from camera import IPCamera
from classifier import classify_image
from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B
from ev3dev2.sensor import INPUT_1
from ev3dev2.sensor.lego import TouchSensor

# Inicializar motores y sensor
motor_vinilo = LargeMotor(OUTPUT_A)
motor_base = LargeMotor(OUTPUT_B)
sensor_presion = TouchSensor(INPUT_1)

# Configuración de la cámara
CAMERA_URL = "http://192.168.1.29:8080/video"
FRAME_DELAY = 0.5

# Objetos que disparan la paletizadora
OBJETIVOS = {"bottle", "banana"}  # cambia según lo que quieras detectar

def rutina_paletizadora(velocidad_base=25, altura=0.6):
    print(">>> Iniciando rutina de paletizado <<<")

    # Bajar hasta el sensor
    motor_vinilo.on(15)
    while not sensor_presion.is_pressed:
        time.sleep(0.1)
    motor_vinilo.stop()

    # Iniciar base
    motor_base.on(velocidad_base)

    for _ in range(6):
        motor_vinilo.on_for_rotations(-15, altura)  # Subir
        time.sleep(0.5)
        motor_vinilo.stop()
        time.sleep(0.5)
        motor_vinilo.on_for_rotations(15, altura)   # Bajar
        time.sleep(0.5)
        motor_vinilo.stop()

    motor_base.stop()
    print(">>> Rutina completada <<<")

def main():
    camera = IPCamera(CAMERA_URL)

    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(FRAME_DELAY)
                continue

            resultados = classify_image(frame, top=3)
            print(f"Detecciones: {resultados}")

            # Verificar si hay un objeto objetivo
            for etiqueta, confianza in resultados:
                if etiqueta in OBJETIVOS and confianza > 0.6:  # umbral de confianza
                    rutina_paletizadora()
                    break  # evitar múltiples disparos seguidos

            # Mostrar cámara
            cv2.imshow("Cámara IP", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            time.sleep(FRAME_DELAY)

    except KeyboardInterrupt:
        print("Interrumpido por el usuario.")
    finally:
        camera.release()
        cv2.destroyAllWindows()
        motor_vinilo.stop()
        motor_base.stop()

if __name__ == "__main__":
    main()

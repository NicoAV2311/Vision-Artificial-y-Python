
"""
logica_paletizadora.py
Script para control de paletizadora automática usando visión artificial y EV3.
Detecta objetos en tiempo real y ejecuta rutina de paletizado si se detecta un objetivo.

Autores: [Nicolas Arango Vergara, Miguel Angel Muñoz]
Fecha: 2025-09-14
"""

import time
from timeit import main
import cv2
from camera import IPCamera
from classifier import classify_image
from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B
from ev3dev2.sensor import INPUT_1
from ev3dev2.sensor.lego import TouchSensor


#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Inicialización de motores y sensor de presión
motor_vinilo = LargeMotor(OUTPUT_A)
motor_base = LargeMotor(OUTPUT_B)
sensor_presion = TouchSensor(INPUT_1)


# Configuración de la cámara IP
CAMERA_URL = "http://192.168.1.29:8080/video"
FRAME_DELAY = 0.5  # segundos entre frames


# Objetos que disparan la paletizadora (modificar según necesidad)
OBJETIVOS = {"bottle", "banana"}


def rutina_paletizadora(velocidad_base=25, altura=0.6):
    """
    Ejecuta la rutina de paletizado:
    - Baja el vinilo hasta el sensor de presión.
    - Inicia la base giratoria.
    - Realiza movimientos de subida y bajada del vinilo.
    - Detiene la base al finalizar.

    Args:
        velocidad_base (int): Velocidad de la base giratoria.
        altura (float): Altura de rotación del vinilo.
    """
    print(">>> Iniciando rutina de paletizado <<<")

    # Bajar hasta el sensor de presión
    motor_vinilo.on(15)
    while not sensor_presion.is_pressed:
        time.sleep(0.1)
    motor_vinilo.stop()

    # Iniciar base giratoria
    motor_base.on(velocidad_base)

    for _ in range(6):
        motor_vinilo.on_for_rotations(-15, altura)  # Subir vinilo
        time.sleep(0.5)
        motor_vinilo.stop()
        time.sleep(0.5)
        motor_vinilo.on_for_rotations(15, altura)   # Bajar vinilo
        time.sleep(0.5)
        motor_vinilo.stop()

    motor_base.stop()
    print(">>> Rutina completada <<<")



    """
    Función principal del sistema:
    - Inicializa la cámara IP.
    - Captura frames en tiempo real.
    - Clasifica objetos en cada frame.
    - Ejecuta la rutina de paletizado si se detecta un objetivo.
    - Muestra la imagen de la cámara y permite salir con 'q'.
    """
    camera = IPCamera(CAMERA_URL)

    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(FRAME_DELAY)
                continue

            resultados = classify_image(frame, top=3)
            print(f"Detecciones: {resultados}")

            # Verificar si hay un objeto objetivo con suficiente confianza
            for etiqueta, confianza in resultados:
                if etiqueta in OBJETIVOS and confianza > 0.6:  # umbral de confianza
                    rutina_paletizadora()
                    break  # evitar múltiples disparos seguidos

            # Mostrar imagen de la cámara
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

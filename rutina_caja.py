#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B
from ev3dev2.sensor import INPUT_1
from ev3dev2.sensor.lego import TouchSensor
from ev3dev2.button import Button
from time import sleep

# Inicializar motores y sensores
motor_vinilo = LargeMotor(OUTPUT_A)
motor_base = LargeMotor(OUTPUT_B)
sensor_presion = TouchSensor(INPUT_1)
btn = Button()

def mover_vinilo(velocidad):
    motor_vinilo.on(velocidad)

def detener_vinilo():
    motor_vinilo.stop()

def rutina_paletizado(velocidad_base, altura):
    print("Rutina con velocidad={}, altura={}".format(velocidad_base, altura))

    # Verificar posición más baja
    mover_vinilo(15)
    while not sensor_presion.is_pressed:
        sleep(0.1)
    detener_vinilo()
    print("Motor vinilo abajo.")

    # Iniciar base
    motor_base.on(velocidad_base)

    # Subir y bajar varias veces
    for _ in range(6):
        motor_vinilo.on_for_rotations(-15, altura * 0.5)  # Subir (mitad de la altura original)
        sleep(0.5)
        detener_vinilo()
        sleep(0.5)
        motor_vinilo.on_for_rotations(15, altura * 0.5)  # Bajar (mitad de la altura original)
        sleep(0.5)
        detener_vinilo()

    motor_base.stop()
    print("Proceso completado.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: rutina_caja.py <velocidad> <altura>")
        sys.exit(1)

    velocidad = int(sys.argv[1])
    altura = float(sys.argv[2])
    rutina_paletizado(velocidad, altura)

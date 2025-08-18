"""
ev3_controller.py
Controlador para LEGO EV3 usando ev3dev2.
Debe ejecutarse en el EV3 con sistema operativo EV3DEV.
"""

from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B, SpeedPercent
from time import sleep

def connect_to_ev3():
    """
    Inicializa y retorna los motores conectados a los puertos A y B.
    """
    try:
        motor_a = LargeMotor(OUTPUT_A)
        motor_b = LargeMotor(OUTPUT_B)
        return motor_a, motor_b
    except Exception as e:
        raise RuntimeError(f"No se pudieron inicializar los motores: {e}")

def move_motor(motor_a, motor_b, speed=50, duration=2):
    """
    Mueve los motores a un porcentaje de velocidad por un tiempo dado.
    :param motor_a: Objeto LargeMotor inicializado para el motor A.
    :param motor_b: Objeto LargeMotor inicializado para el motor B.
    :param speed: Velocidad en porcentaje (-100 a 100).
    :param duration: Tiempo en segundos.
    """
    if motor_a is None or motor_b is None:
        raise ValueError("Motores no inicializados")

    motor_a.on(SpeedPercent(speed))
    motor_b.on(SpeedPercent(speed))
    sleep(duration)
    motor_a.off()
    motor_b.off()


"""
ev3_controller.py
Controlador para LEGO EV3 usando ev3dev2.
Debe ejecutarse en el EV3 con sistema operativo EV3DEV.
Incluye manejo robusto de errores y logs.
"""


import logging
from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B, SpeedPercent
from time import sleep


def connect_to_ev3():
    """
    Inicializa y retorna los motores conectados a los puertos A y B.
    Incluye logs y manejo de errores.
    """
    try:
        motor_a = LargeMotor(OUTPUT_A)
        motor_b = LargeMotor(OUTPUT_B)
        logging.info("Motores inicializados correctamente en OUTPUT_A y OUTPUT_B.")
        return motor_a, motor_b
    except Exception as e:
        logging.error(f"No se pudieron inicializar los motores: {e}")
        raise RuntimeError(f"No se pudieron inicializar los motores: {e}")


def move_motor(motor_a, motor_b, speed=50, duration=2):
    """
    Mueve los motores a un porcentaje de velocidad por un tiempo dado.
    Incluye validación y logs.
    :param motor_a: Objeto LargeMotor inicializado para el motor A.
    :param motor_b: Objeto LargeMotor inicializado para el motor B.
    :param speed: Velocidad en porcentaje (-100 a 100).
    :param duration: Tiempo en segundos.
    """
    if motor_a is None or motor_b is None:
        logging.error("Motores no inicializados")
        raise ValueError("Motores no inicializados")
    try:
        logging.info(f"Moviendo motores a {speed}% por {duration} segundos.")
        motor_a.on(SpeedPercent(speed))
        motor_b.on(SpeedPercent(speed))
        sleep(duration)
        motor_a.off()
        motor_b.off()
        logging.info("Motores detenidos correctamente.")
    except Exception as e:
        logging.error(f"Error al mover los motores: {e}")
        try:
            motor_a.off()
            motor_b.off()
        except Exception:
            pass
        raise
# End of file

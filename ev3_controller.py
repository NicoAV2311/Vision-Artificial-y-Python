
"""
ev3_controller.py

Módulo controlador para LEGO EV3 usando la librería ev3dev2.
Debe ejecutarse en el EV3 con sistema operativo EV3DEV.
Incluye funciones para inicializar y mover motores con manejo robusto de errores y logs.
"""


import logging
from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B, SpeedPercent
from time import sleep


def connect_to_ev3():
    """
    Inicializa y retorna los motores conectados a los puertos A y B.

    Returns:
        tuple: (motor_a, motor_b) objetos LargeMotor inicializados.

    Raises:
        RuntimeError: Si no se pueden inicializar los motores.
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

    Args:
        motor_a (LargeMotor): Objeto LargeMotor inicializado para el motor A.
        motor_b (LargeMotor): Objeto LargeMotor inicializado para el motor B.
        speed (int, optional): Velocidad en porcentaje (-100 a 100). Default=50.
        duration (float, optional): Tiempo en segundos. Default=2.

    Raises:
        ValueError: Si los motores no están inicializados.
        Exception: Si ocurre un error al mover los motores.
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
        # Intentar detener los motores aunque haya error
        try:
            motor_a.off()
            motor_b.off()
        except Exception:
            pass
        raise
# End of file

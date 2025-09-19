#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
motor_server.py
Servidor TCP para controlar los motores de la paletizadora en EV3.
Recibe comandos desde un cliente (PC) y ejecuta rutinas de movimiento.
"""


import socketserver
import threading
import time
import logging
from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B
from ev3dev2.sensor import INPUT_1
from ev3dev2.sensor.lego import TouchSensor


# Inicialización de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Inicialización de motores y sensor
try:
    motor_vinilo = LargeMotor(OUTPUT_A)   # Motor que sube/baja el vinilo
    motor_base = LargeMotor(OUTPUT_B)     # Motor de la base giratoria
    sensor_presion = TouchSensor(INPUT_1) # Sensor de presión en la base
except Exception as e:
    logging.error(f"Error inicializando hardware EV3: {e}")
    raise


# -------------------------
# Rutina de paletizado con control de concurrencia y logs
# -------------------------
routine_lock = threading.Lock()
routine_busy = False

def rutina_paletizadora(velocidad_base=25, altura=0.6):
    global routine_busy
    with routine_lock:
        if routine_busy:
            logging.warning("Rutina ya en ejecución, ignorando nueva petición.")
            return "BUSY"
        routine_busy = True
    logging.info(f"Iniciando rutina de paletizado (velocidad={velocidad_base}, altura={altura})")
    try:
        # Bajar hasta el sensor de presión
        motor_vinilo.on(15)
        start = time.time()
        while not sensor_presion.is_pressed:
            time.sleep(0.1)
            if time.time() - start > 10.0:
                logging.error("Timeout bajando vinilo (sensor no presionado)")
                break
        motor_vinilo.stop()

        # Iniciar base giratoria
        motor_base.on(velocidad_base)

        for i in range(6):
            logging.info(f"Ciclo {i+1}/6: Subiendo vinilo")
            motor_vinilo.on_for_rotations(-15, altura)
            time.sleep(0.5)
            motor_vinilo.stop()
            time.sleep(0.5)
            logging.info(f"Ciclo {i+1}/6: Bajando vinilo")
            motor_vinilo.on_for_rotations(15, altura)
            time.sleep(0.5)
            motor_vinilo.stop()

        motor_base.stop()
        logging.info("Rutina completada")
        return "OK"
    except Exception as e:
        logging.error(f"Error en rutina: {e}")
        motor_vinilo.stop()
        motor_base.stop()
        return "ERR"
    finally:
        with routine_lock:
            routine_busy = False

# -------------------------
# Handler de conexiones
# -------------------------
class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            line = self.rfile.readline().decode("utf-8").strip()
            logging.info(f"Comando recibido: {line}")
            if not line:
                return
            parts = line.split()
            cmd = parts[0].upper()

            if cmd == "PALLETIZE":
                try:
                    vel = int(parts[1]) if len(parts) > 1 else 25
                    altura = float(parts[2]) if len(parts) > 2 else 0.6
                except Exception:
                    vel = 25
                    altura = 0.6
                # responder inmediatamente
                self.wfile.write(b"STARTED\n")
                self.wfile.flush()
                # ejecutar rutina en un hilo aparte y loggear resultado
                def run_and_log():
                    res = rutina_paletizadora(vel, altura)
                    logging.info(f"Resultado rutina: {res}")
                threading.Thread(
                    target=run_and_log,
                    daemon=True
                ).start()

            elif cmd == "STOP":
                motor_vinilo.stop()
                motor_base.stop()
                self.wfile.write(b"STOPPED\n")
                self.wfile.flush()
                logging.info("Motores detenidos por comando STOP")

            elif cmd == "STATUS":
                busy_status = b"BUSY\n" if routine_busy else b"OK\n"
                self.wfile.write(busy_status)
                self.wfile.flush()
                logging.info(f"Status reportado: {busy_status.decode().strip()}")

            else:
                self.wfile.write(b"UNKNOWN\n")
                self.wfile.flush()
                logging.warning(f"Comando desconocido: {cmd}")

        except Exception as e:
            logging.error(f"Handler error: {e}")

# -------------------------
# Servidor principal
# -------------------------
if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 9999
    logging.info(f"Servidor de motores escuchando en {HOST}:{PORT}")
    try:
        with socketserver.TCPServer((HOST, PORT), Handler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Servidor detenido por el usuario.")
        try:
            motor_vinilo.stop()
            motor_base.stop()
        except Exception:
            pass

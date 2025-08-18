# Diagramas de flujo del proyecto vision artificial

A continuación se presentan los diagramas de flujo de los módulos principales usando el formato Mermaid. Puedes visualizar estos diagramas en VS Code con la extensión adecuada o en https://mermaid.live.

---

## 1. camera.py
```mermaid
flowchart TD
    A[Inicio] --> B[Inicializar IPCamera]
    B --> C{¿URL válida?}
    C -- No --> D[Error: URL inválida]
    C -- Sí --> E[Conectar a cámara]
    E --> F{¿Conexión exitosa?}
    F -- No --> G[Error: No se puede conectar]
    F -- Sí --> H[Obtener frame]
    H --> I{¿Frame válido?}
    I -- No --> J[Reintentar conexión]
    I -- Sí --> K[Retornar frame]
    K --> L[Fin]
```

---

## 2. classifier.py
```mermaid
flowchart TD
    A[Inicio] --> B[Cargar modelo MobileNetV2]
    B --> C[Recibir frame]
    C --> D{¿Frame válido?}
    D -- No --> E[Error: Frame inválido]
    D -- Sí --> F[Preprocesar imagen]
    F --> G[Predecir con modelo]
    G --> H[Decodificar predicciones]
    H --> I[Retornar etiquetas/confianza]
    I --> J[Fin]
```

---

## 3. ev3_controller.py
```mermaid
flowchart TD
    A[Inicio] --> B[Conectar a motores EV3]
    B --> C{¿Conexión exitosa?}
    C -- No --> D[Error: No se pueden inicializar motores]
    C -- Sí --> E[Recibir comando de movimiento]
    E --> F[Mover motores]
    F --> G[Esperar duración]
    G --> H[Detener motores]
    H --> I[Fin]
```

---

## 4. main.py
```mermaid
flowchart TD
    A[Inicio] --> B[Inicializar cámara]
    B --> C[Inicializar motores EV3]
    C --> D{¿Motores listos?}
    D -- No --> E[Error y terminar]
    D -- Sí --> F[Loop principal]
    F --> G[Capturar frame]
    G --> H{¿Frame válido?}
    H -- No --> F
    H -- Sí --> I[Clasificar imagen]
    I --> J[¿Objeto objetivo detectado?]
    J -- No --> F
    J -- Sí --> K[Activar motores]
    K --> F
```

---

> Puedes copiar estos bloques en un visor Mermaid para ver los diagramas visualmente.

# Análisis de Caso #1 — Plataforma Web Institucional Escalable con Contenedores

BISOF-18 Sistemas Operativos II — Universidad Latina de Costa Rica

Diseño e implementación de una plataforma web basada en **contenedores Docker**,
**balanceo de carga con HAProxy** y automatización **CI/CD**, con el objetivo de
analizar disponibilidad, seguridad y escalabilidad.

## Estructura del repositorio

```
.
├── app/                # Código de la aplicación "Hola mundo"
│   ├── app.py
│   └── requirements.txt
├── Dockerfile
├── .dockerignore
└── README.md
```

## Actividad 1 — Simulación de un servicio en contenedor

Aplicación Flask mínima que responde "Hola Mundo", muestra el hostname del
contenedor (útil más adelante para verificar el balanceo de carga) y el PID
del proceso dentro del contenedor.

### Construir la imagen

```bash
docker build -t caso1-web:latest .
```

### Ejecutar el contenedor localmente

```bash
docker run -d --name caso1-web -p 8080:5000 caso1-web:latest
```

### Verificar

```bash
curl http://localhost:8080/
curl http://localhost:8080/health
```

### Aislamiento de procesos, memoria y persistencia

```bash
# Procesos: vistos desde el host (docker top), dentro del contenedor
# la app corre como PID 1 -> el namespace de PID aísla su numeración
docker top caso1-web

# Memoria y CPU asignados al contenedor (limitados por cgroups)
docker stats --no-stream caso1-web

# PID real en el host vs PID 1 dentro del contenedor
docker inspect --format '{{.State.Pid}}' caso1-web

# Persistencia: al eliminar el contenedor se pierde cualquier cambio
# hecho dentro del filesystem (sin volúmenes montados)
docker rm -f caso1-web
```

**Evidencia registrada (build y ejecución local):**

- `docker build` → imagen `caso1-web:latest` construida sin errores (base `python:3.12-slim`).
- `curl http://localhost:8080/` → `Hola Mundo`, hostname del contenedor `7e78c582b9c2`, **PID del proceso: 1**.
- `curl http://localhost:8080/health` → `{"hostname":"7e78c582b9c2","status":"ok"}`.
- `docker top caso1-web` → el proceso `python app.py` corre con **PID real 420497 en el host**, mientras que dentro del contenedor se identifica como **PID 1** → demuestra el aislamiento del *PID namespace*.
- `docker stats --no-stream caso1-web` → `21.62MiB` de memoria usada sobre el límite del host, `0.01%` CPU, `1` proceso (PID) → evidencia de *cgroups* limitando y contabilizando recursos por contenedor.
- **Persistencia:** sin volúmenes montados, cualquier archivo creado dentro del contenedor se pierde al hacer `docker rm -f caso1-web` (el filesystem de la capa de escritura es efímero).

## Próximas actividades

- [ ] Balanceo de carga con HAProxy (2+ instancias)
- [ ] Alta disponibilidad (failover, Docker Swarm opcional)
- [ ] Seguridad (HTTPS, control de acceso, firewalls)
- [ ] Escalabilidad y persistencia (docker-compose, volúmenes)
- [ ] Informe final con capturas de pruebas

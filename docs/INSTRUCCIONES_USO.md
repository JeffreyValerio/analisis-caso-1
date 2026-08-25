# Instrucciones de Uso y Referencia Rápida

## Requisitos Previos

- Docker 20.10+ (`docker --version`)
- Docker Compose 2.0+ (`docker compose version`)
- OpenSSL (para generar certificados) (`openssl version`)
- Git (para clonar el repositorio)

## Instalación Rápida

### 1. Clonar el repositorio

```bash
git clone https://github.com/JeffreyValerio/analisis-caso-1.git
cd analisis-caso-1
```

### 2. Construir las imágenes

```bash
docker compose build
```

O permitir que compose lo haga automáticamente:

```bash
docker compose up -d  # Construye + inicia automáticamente
```

## Operación del Stack

### Iniciar el stack completo

```bash
docker compose up -d
```

**Verifica que estén corriendo:**
```bash
docker compose ps
```

**Salida esperada:**
```
NAME            IMAGE                STATUS
caso1-haproxy   haproxy:2.9-alpine   Up 10 seconds
caso1-web1      caso1-web1           Up 11 seconds
caso1-web2      caso1-web2           Up 11 seconds
```

### Detener el stack

```bash
docker compose down
```

Eliminar también volúmenes:
```bash
docker compose down -v
```

### Logs en tiempo real

```bash
# Todos los servicios
docker compose logs -f

# Solo un servicio
docker compose logs -f haproxy
docker compose logs -f web1

# Últimas 50 líneas
docker compose logs --tail 50
```

---

## Pruebas de Funcionalidad

### Prueba 1: Acceso HTTP

```bash
# Requests al balanceador (puerto 8080)
curl http://localhost:8080/

# Salida:
# <h1>Hola Mundo</h1>
# <p>Instancia: <b>web1</b></p>
# <p>Servido desde el contenedor: <b>...</b></p>
# <p>PID del proceso: <b>1</b></p>
```

### Prueba 2: Verificar Balanceo

```bash
# Ejecutar 5 requests y observar alternancia
for i in {1..5}; do
  echo "Request $i:"
  curl -s http://localhost:8080/ | grep "Instancia:"
done

# Salida esperada:
# Request 1: ... web1 ...
# Request 2: ... web2 ...
# Request 3: ... web1 ...
# Request 4: ... web2 ...
# Request 5: ... web1 ...
```

### Prueba 3: Health Check Endpoint

```bash
curl http://localhost:8080/health

# Salida:
# {"hostname":"dd72651806cc","instance":"web1","status":"ok"}
```

### Prueba 4: Acceso HTTPS

```bash
# Con verificación SSL deshabilitada (para certificado auto-firmado)
curl -k https://localhost:8443/

# Salida igual a HTTP (conexión TLS funcional)
```

### Prueba 5: Panel de Estadísticas de HAProxy

Abrir en navegador:
```
http://localhost:8404/
```

**Datos visibles:**
- Estado de cada backend (UP/DOWN)
- Número de conexiones servidas
- Tasa de errores (HTTP 4xx, 5xx)
- Última hora de cambio de estado
- Gráficos de sesiones activas

### Prueba 6: Simular Falla (Failover)

```bash
# Observar stats antes
curl -s http://localhost:8404/ | grep "web1.*L7OK"

# Pausar web1 (simula crash)
docker pause caso1-web1

# Esperar ~3 segundos (timeout de healthcheck)

# Verificar que web1 está DOWN
curl -s http://localhost:8404/ | grep "web1"
# Verás: "web1" + "DOWN"

# Todos los requests van a web2 ahora
for i in {1..3}; do
  curl -s http://localhost:8080/ | grep "Instancia:"
done
# Salida: ... web2 ... web2 ... web2 ...

# Recuperar web1
docker unpause caso1-web1

# Esperar ~6 segundos (2 health checks exitosos)

# Verificar recuperación
curl -s http://localhost:8404/ | grep "web1"
# Verás: "web1" + "UP"

# Balanceo se reanuda
curl -s http://localhost:8080/ | grep "Instancia:"
# Alternancia 1-2-1-2 nuevamente
```

---

## Estructura de Directorios

```
analisis-caso-1/
├── app/
│   ├── app.py                 # Aplicación Flask
│   └── requirements.txt       # Dependencias Python
├── haproxy/
│   ├── haproxy.cfg           # Configuración del balanceador
│   └── certs/
│       ├── caso1.pem         # Certificado + clave (PEM)
│       ├── caso1.crt         # Certificado X.509
│       └── caso1.key         # Clave privada RSA 2048
├── docs/
│   ├── ANALISIS_TECNICO.md   # Análisis detallado
│   ├── LOGS_EJECUCION.md     # Evidencias de pruebas
│   └── INSTRUCCIONES_USO.md  # Este archivo
├── Dockerfile                 # Dockerfile para las apps
├── .dockerignore              # Archivos a excluir del build
├── docker-compose.yml        # Orquestación de servicios
└── README.md                 # Descripción del proyecto
```

---

## Configuración Avanzada

### Cambiar puerto de HAProxy

Editar `docker-compose.yml`:
```yaml
  haproxy:
    ports:
      - "9090:80"      # Cambiar 8080 a 9090 (HTTP)
      - "9443:443"     # Cambiar 8443 a 9443 (HTTPS)
      - "9404:8404"    # Cambiar 8404 a 9404 (Stats)
```

Luego:
```bash
docker compose up -d --force-recreate haproxy
```

### Cambiar algoritmo de balanceo

Editar `haproxy/haproxy.cfg`:
```haproxy
backend web_backend
    balance leastconn    # Cambiar a least connections
    # Otras opciones:
    # balance roundrobin   (por defecto)
    # balance source       (sticky sessions)
    # balance uri          (URI hash)
    # balance hdr(Cookie)  (cookie hash)
```

Recargar:
```bash
docker compose restart haproxy
```

### Agregar una tercera instancia

1. Editar `docker-compose.yml`:
```yaml
  web3:
    build: .
    container_name: caso1-web3
    environment:
      - INSTANCE_NAME=web3
    networks:
      - caso1net
```

2. Editar `haproxy/haproxy.cfg`:
```haproxy
backend web_backend
    ...
    server web3 web3:5000 check inter 3s fall 2 rise 2
```

3. Aplicar cambios:
```bash
docker compose up -d
```

### Cambiar intervalo de health check

Editar `haproxy/haproxy.cfg`:
```haproxy
server web1 web1:5000 check inter 2s fall 1 rise 1
```

**Parámetros:**
- `inter 2s` → healthcheck cada 2 segundos (más frecuente)
- `fall 1` → DOWN después de 1 fallo (detección más rápida)
- `rise 1` → UP después de 1 éxito (recuperación más rápida)

---

## Troubleshooting

### No puedo acceder a http://localhost:8080

**Verificar que HAProxy está corriendo:**
```bash
docker ps | grep haproxy
docker logs caso1-haproxy
```

**Si está detenido:**
```bash
docker compose restart haproxy
```

### HTTPS muestra certificado inválido

**Normal para certificado auto-firmado.** Usa `-k` con curl:
```bash
curl -k https://localhost:8443/
```

En navegador: aceptar riesgo/excepción temporal (chrome: `Avanzado` → `Continuar`)

### Un backend está constantemente DOWN

```bash
# Ver logs del contenedor web1
docker logs caso1-web1

# Si tiene errores, reconstruir
docker compose down
docker compose up -d --build
```

### El balanceo no alterna entre web1 y web2

**Verificar healthcheck:**
```bash
curl http://localhost:8080/health
# Debe retornar {"status":"ok", ...}

# Si no, el backend estará DOWN
# Ver logs: docker logs caso1-web1
```

### Cambios en `haproxy.cfg` no se aplican

**Necesita recarga o reinicio:**
```bash
# Reinicio limpio
docker compose restart haproxy

# O recarga más suave (preserva conexiones activas)
docker kill -s HUP caso1-haproxy
```

---

## Métricas y Monitoreo

### Ver recursos consumidos

```bash
# Actualizado en tiempo real
docker stats

# Una sola vez
docker stats --no-stream
```

### Ver procesos dentro de un contenedor

```bash
# Ver procesos vistos desde el host
docker top caso1-web1

# Inspeccionar contenedor
docker inspect caso1-web1 | grep -E "Pid|Memory"
```

### Estadísticas de red

```bash
# Tráfico de red del contenedor
docker stats caso1-haproxy --no-stream | awk '{print $NF}'
```

---

## Limpieza y Reset

### Eliminar todo (contenedores, redes, volúmenes)

```bash
docker compose down -v

# Asegúrate de que no hay nada más
docker ps -a | grep caso1
docker images | grep caso1
```

### Reconstruir desde cero

```bash
docker compose down -v
docker system prune -a  # Elimina imágenes no usadas
docker compose build --no-cache
docker compose up -d
```

---

## Referencia de Comandos Docker

| Comando | Función |
|---------|---------|
| `docker compose up -d` | Iniciar stack en segundo plano |
| `docker compose down` | Detener y eliminar contenedores |
| `docker compose ps` | Listar servicios |
| `docker compose logs -f` | Ver logs en tiempo real |
| `docker compose exec web1 bash` | Entrar en la shell del contenedor |
| `docker compose restart web1` | Reiniciar un servicio |
| `docker pause caso1-web1` | Pausar (simula congelación) |
| `docker unpause caso1-web1` | Reanudar después de pausa |
| `docker stop caso1-web1` | Detener gracefully |
| `docker kill caso1-web1` | Forzar terminación |

---

## Recursos Útiles

- [Docker Documentation](https://docs.docker.com/)
- [HAProxy Configuration Manual](http://www.haproxy.org/#docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Linux Namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- [cgroups v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroups-v2.html)

---

## FAQ

**P: ¿Puedo correr esto en Windows/Mac?**
R: Sí, pero Docker Desktop debe estar corriendo primero. Los puertos serán
localhost:8080 en ambos casos.

**P: ¿Qué pasa si necesito más de 2 instancias web?**
R: Agrégalas en docker-compose.yml y haproxy.cfg (ver sección Configuración Avanzada).

**P: ¿Cómo hago backups de los datos?**
R: Actualmente no hay persistencia. Para activarla, monta volúmenes (ver ejemplo NFS
en ANALISIS_TECNICO.md).

**P: ¿Es esto production-ready?**
R: No. Para producción se necesita:
- Certificados Let's Encrypt (no auto-firmados)
- Persistencia de datos
- Logging centralizado
- Rate limiting y WAF
- Upgrade a Kubernetes (para > 10 instancias)

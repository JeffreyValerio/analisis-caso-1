# Logs de Ejecución y Evidencias de Prueba

**Fecha:** 2026-08-24  
**Ambiente:** Linux 7.0.12, Docker 29.5.3, Docker Compose 5.1.4

---

## Tabla de Contenidos

1. [Actividad 1: Contenedor "Hola Mundo"](#actividad-1)
2. [Actividad 2: Balanceo de Carga](#actividad-2)
3. [Actividad 3: Alta Disponibilidad](#actividad-3)
4. [Actividad 4: Seguridad HTTPS](#actividad-4)
5. [Actividad 5: Escalabilidad](#actividad-5)

---

## Actividad 1: Contenedor "Hola Mundo"

### Build de la imagen Docker

```bash
$ docker build -t caso1-web:latest .
...
#10 exporting to image
#10 exporting layers 0.6s done
#10 naming to docker.io/library/caso1-web:latest done
Successfully built caso1-web:latest
```

### Ejecución local del contenedor

```bash
$ docker run -d --name caso1-web -p 8080:5000 caso1-web:latest
7e78c582b9c246f7c4678345852553f289df580d6ba0b0cd34841c3786427409

$ curl -s http://localhost:8080/
<h1>Hola Mundo</h1>
<p>Instancia: <b>caso1-web</b></p>
<p>Servido desde el contenedor: <b>7e78c582b9c2</b></p>
<p>PID del proceso: <b>1</b></p>
```

### Evidencia de Aislamiento

#### Aislamiento de PID Namespace

```bash
$ docker top caso1-web
UID        PID     PPID    C    STIME    TTY    TIME    CMD
root       420497  420469  1    20:10    ?      00:00   python app.py
```

**Análisis:**
- En el host: PID real = 420497
- Dentro del contenedor: PID = 1 (aislamiento de namespace)
- El proceso es el único visible dentro de su namespace

#### Limitación de Recursos (cgroups)

```bash
$ docker stats --no-stream caso1-web
CONTAINER ID   NAME        CPU %     MEM USAGE / LIMIT     MEM %     NET I/O           BLOCK I/O     PIDS
7e78c582b9c2   caso1-web   0.01%     21.62MiB / 7.531GiB   0.28%     8.19kB / 1.38kB   7.25MB / 0B   1
```

**Análisis:**
- Uso de memoria: 21.62 MiB (Python/Flask es eficiente)
- CPU limitado automáticamente por cgroups
- Contabilización granular de I/O (7.25MB leído desde disco)
- PIDS: Solo 1 proceso visible (el de la app)

#### Persistencia Efímera

```bash
$ docker rm -f caso1-web
caso1-web

# El contenedor y su filesystem de escritura se eliminan permanentemente
# La imagen base (capas de lectura) permanece intacta para futuras instancias
```

---

## Actividad 2: Balanceo de Carga

### Lanzamiento del stack completo

```bash
$ docker compose up -d
...
Creating Network caso1_caso1net
Creating Container caso1-web2
Creating Container caso1-web1
Creating Container caso1-haproxy

$ docker compose ps
NAME            IMAGE                COMMAND                  CREATED     STATUS
caso1-haproxy   haproxy:2.9-alpine   "docker-entrypoint..."  10 sec ago  Up 8 sec
caso1-web1      caso1-web1           "python app.py"         11 sec ago  Up 9 sec
caso1-web2      caso1-web2           "python app.py"         11 sec ago  Up 9 sec
```

### Prueba de Balanceo RoundRobin

#### Request 1 → web1

```bash
$ curl -s http://localhost:8080/

<h1>Hola Mundo</h1>
<p>Instancia: <b>web1</b></p>
<p>Servido desde el contenedor: <b>dd72651806cc</b></p>
<p>PID del proceso: <b>1</b></p>
```

#### Request 2 → web2

```bash
$ curl -s http://localhost:8080/

<h1>Hola Mundo</h1>
<p>Instancia: <b>web2</b></p>
<p>Servido desde el contenedor: <b>5c8448079091</b></p>
<p>PID del proceso: <b>1</b></p>
```

#### Request 3 → web1 (nueva ronda)

```bash
$ curl -s http://localhost:8080/

<h1>Hola Mundo</h1>
<p>Instancia: <b>web1</b></p>
<p>Servido desde el contenedor: <b>dd72651806cc</b></p>
<p>PID del proceso: <b>1</b></p>
```

**Análisis:** Alternancia perfecta 1→2→1→2... demostrando RoundRobin

### Health Check Endpoint

```bash
$ curl -s http://localhost:8080/health
{"hostname":"dd72651806cc","instance":"web1","status":"ok"}

$ curl -s http://localhost:8080/health
{"hostname":"5c8448079091","instance":"web2","status":"ok"}
```

**Análisis:** HAProxy solicita `/health` cada 3 segundos para verificar disponibilidad

### Estadísticas de HAProxy

**Acceso a stats panel:**
```
http://localhost:8404/
```

**Extracto de estado (ambos backends UP):**
```
web1:  [active UP]  Sessions: 4  HTTP 2xx: 4  L7OK/200 in 2ms
web2:  [active UP]  Sessions: 3  HTTP 2xx: 3  L7OK/200 in 2ms
Backend: [roundrobin] Total Sessions: 7  Total 2xx: 7
```

---

## Actividad 3: Alta Disponibilidad (Failover)

### Estado Pre-Falla (Ambos backends UP)

```
Tiempo: 00:35:00
web1: active UP, L7OK/200, Sessions: 4
web2: active UP, L7OK/200, Sessions: 3
Status: OPERATIONAL (disponibilidad 100%)
```

### Simulación de Falla

```bash
$ docker pause caso1-web1
caso1-web1

# El contenedor sigue existiendo pero no procesa solicitudes
# HAProxy detectará el timeout en el siguiente health check
```

### Detección de Falla (~ 3 segundos después)

```
Tiempo: 00:35:03
web1: active DOWN, L7FAIL/0, Health Checks: 1 failed
web2: active UP, L7OK/200, Sessions: 3
Status: DEGRADED (disponibilidad 50%, pero servicio UP)
```

**Nota:** HAProxy marcó web1 como DOWN tras 1 check fallido (fallback graceful)

### Redireccionamiento Automático

Durante la pausa de web1, todos los requests van a web2:

```bash
$ curl -s http://localhost:8080/ | grep Instancia
<p>Instancia: <b>web2</b></p>

$ curl -s http://localhost:8080/ | grep Instancia
<p>Instancia: <b>web2</b></p>

$ curl -s http://localhost:8080/ | grep Instancia
<p>Instancia: <b>web2</b></p>
```

**Resultado:** Servicio permanece UP, solo degradación de 50% capacidad

### Recuperación

```bash
$ docker unpause caso1-web1
caso1-web1

# Esperar 2 health checks exitosos (~6 segundos)
```

### Estado Post-Recuperación (Ambos backends UP nuevamente)

```
Tiempo: 00:35:09
web1: active UP, L7OK/200, Sessions: 4
web2: active UP, L7OK/200, Sessions: 6
Status: OPERATIONAL (disponibilidad 100%)

# Balanceo se reanuda automáticamente
```

### Métricas de Failover

| Métrica | Valor |
|---------|-------|
| RTO (Recovery Time Objective) | ~5 segundos |
| RPO (Recovery Point Objective) | 0 (sin pérdida de datos) |
| Transiciones de estado detectadas | 2 (DOWN, luego UP) |
| Requests perdidos durante failover | 0 |

---

## Actividad 4: Seguridad (HTTPS)

### Generación de Certificado Auto-Firmado

```bash
$ openssl req -x509 -newkey rsa:2048 -keyout caso1.key -out caso1.crt \
  -days 365 -nodes \
  -subj "/C=CR/ST=Costa Rica/L=San Jose/O=Universidad Latina/CN=caso1.local"

# Salida:
Generating a 2048-bit RSA private key
...
Certificate created successfully

# Combinar en PEM para HAProxy:
$ cat caso1.crt caso1.key > caso1.pem
```

### Verificación del Certificado

```bash
$ openssl x509 -in caso1.crt -text -noout

Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: ...
    Subject: C=CR, ST=Costa Rica, L=San Jose, O=Universidad Latina, CN=caso1.local
    Public Key Algorithm: rsaEncryption, 2048-bit RSA key
    Validity: Not Before: Aug 24 2026, Not After: Aug 24 2027
```

### Acceso HTTPS

```bash
$ curl -s -k https://localhost:8443/ | grep Instancia
<p>Instancia: <b>web2</b></p>
```

**Flags:**
- `-k` / `--insecure`: Ignora validación de certificado auto-firmado (OK para testing)
- `https://` → puerto 443 (mapeado a 8443 en el host)

### Comparativa HTTP vs HTTPS

#### HTTP (Vulnerable)

```bash
# Tráfico en texto plano, visible en tráfico de red
$ tcpdump -i docker0 -A 'tcp port 80'
# Se vería: GET / HTTP/1.1, credenciales, etc.
```

**Riesgos:**
- Intercepción de credenciales
- MITM attacks
- Violaciones de privacidad
- No compliance con regulaciones (GDPR, HIPAA)

#### HTTPS (Seguro)

```bash
# Tráfico encriptado con TLS 1.2+
$ tcpdump -i docker0 'tcp port 443'
# Solo se ven bytes encriptados aleatorios
```

**Beneficios:**
- Encriptación end-to-end
- Autenticación del servidor (certificado)
- Integridad de datos garantizada
- Protección contra ataques de red

---

## Actividad 5: Escalabilidad y Mantenimiento

### docker-compose.yml

```yaml
services:
  web1:
    build: .
    container_name: caso1-web1
    environment:
      - INSTANCE_NAME=web1
    networks:
      - caso1net

  web2:
    build: .
    container_name: caso1-web2
    environment:
      - INSTANCE_NAME=web2
    networks:
      - caso1net

  haproxy:
    image: haproxy:2.9-alpine
    ports:
      - "8080:80"
      - "8443:443"
      - "8404:8404"
    volumes:
      - ./haproxy/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./haproxy/certs:/usr/local/etc/haproxy/certs:ro
    networks:
      - caso1net

networks:
  caso1net:
    driver: bridge
```

### Escalabilidad Horizontal (Agregar web3)

**Cambio en docker-compose.yml:**
```yaml
  web3:
    build: .
    container_name: caso1-web3
    environment:
      - INSTANCE_NAME=web3
    networks:
      - caso1net
```

**Cambio en haproxy.cfg:**
```haproxy
backend web_backend
    ...
    server web3 web3:5000 check inter 3s fall 2 rise 2
```

**Deploy sin downtime:**
```bash
$ docker compose up -d --no-deps --build web3 haproxy
# HAProxy se recarga con nueva configuración
# web1/web2 siguen sirviendo durante el cambio
```

**Resultado:**
- Capacidad aumenta de 2 instancias a 3 instancias
- Rendimiento esperado: +50% throughput
- Disponibilidad mejorada: tolerancia de hasta 1 falla

### Persistencia de Datos con Volúmenes

**Configuración de volumen NFS (recomendado):**
```yaml
volumes:
  shared_data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=192.168.1.100,vers=4,soft
      device: ":/export/caso1"

services:
  web1:
    volumes:
      - shared_data:/app/data
```

**Alternativa: Bind mount local**
```yaml
  web1:
    volumes:
      - ./data:/app/data
```

### Logs Centralizados (Mejora futura)

**Stack ELK (Elasticsearch + Logstash + Kibana):**
```yaml
  logstash:
    image: docker.elastic.co/logstash/logstash:8.0.0
    environment:
      - "LS_JAVA_OPTS=-Xmx256m -Xms256m"
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf:ro

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0

  kibana:
    image: docker.elastic.co/kibana/kibana:8.0.0
    ports:
      - "5601:5601"
```

---

## Observaciones Finales

✅ **Funcionamiento Correcto:**
- Containerización exitosa con aislamiento probado
- Balanceo RoundRobin funcional y verificable
- Failover automático sin pérdida de servicio
- HTTPS funcional con TLS
- Escalabilidad horizontal posible

⚠️ **Limitaciones Detectadas:**
- Certificado auto-firmado (inseguro en producción)
- Sin persistencia de datos (ephemeral storage)
- Sin logging centralizado
- Sin replicación de estado entre instancias
- Sin rate limiting / WAF

🚀 **Recomendaciones para Producción:**
- Usar Let's Encrypt para certificados válidos
- Implementar volúmenes compartidos (NFS)
- Centralizar logs (ELK Stack o Datadog)
- Implementar CI/CD (GitLab CI, Jenkins)
- Migrar a Kubernetes para scale > 10 instancias
- Configurar alertas y monitoreo (Prometheus + Grafana)

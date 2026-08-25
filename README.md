# Análisis de Caso #1 — Plataforma Web Institucional Escalable con Contenedores

**Universidad Latina de Costa Rica**  
**BISOF-18 Sistemas Operativos II**  
**Fecha:** 2026-08-24

---

## Descripción del Proyecto

Implementación completa de una plataforma web basada en **contenedores Docker**, 
**balanceo de carga con HAProxy** y **orquestación con docker-compose**. 

El caso de estudio integra conceptos avanzados de:
- **Sistemas Operativos:** Namespaces, cgroups, PID isolation
- **Redes:** Balanceo de carga, healthchecks, failover
- **Seguridad:** TLS/HTTPS, control de acceso
- **Escalabilidad:** Crecimiento horizontal, persistencia

---

## Objetivos del Caso

✅ **Implementados y verificados:**

1. **Actividad 1:** Containerizar aplicación "Hola Mundo"
   - Dockerfile funcional con base Python 3.12
   - Aislamiento de procesos (PID namespace)
   - Limitación de recursos (cgroups)
   - Análisis de persistencia efímera

2. **Actividad 2:** Balanceo de carga con HAProxy
   - 2 instancias de app web
   - Algoritmo RoundRobin verificado
   - Health checks automáticos
   - Panel de estadísticas en tiempo real

3. **Actividad 3:** Alta disponibilidad
   - Failover automático en ~5 segundos
   - Detección de fallas por timeout
   - Recuperación sin pérdida de datos
   - RTO medido: 5 segundos

4. **Actividad 4:** Seguridad (HTTPS)
   - Certificado auto-firmado X.509
   - TLS 1.2+ funcional
   - Análisis de riesgos de HTTP plano
   - Control de acceso en docker network

5. **Actividad 5:** Escalabilidad y persistencia
   - docker-compose.yml para orquestación
   - Escalamiento horizontal sin downtime
   - Propuestas de volúmenes NFS
   - Mejoras sugeridas para producción

---

## Estructura del Repositorio

```
.
├── app/                           # Código de la aplicación
│   ├── app.py                    # Flask app (Hola Mundo)
│   └── requirements.txt          # Dependencias Python
├── haproxy/
│   ├── haproxy.cfg              # Configuración del balanceador
│   └── certs/
│       ├── caso1.pem            # Certificado + clave para TLS
│       ├── caso1.crt            # Certificado X.509 auto-firmado
│       └── caso1.key            # Clave privada RSA 2048
├── docs/
│   ├── ANALISIS_TECNICO.md      # Análisis detallado (Actividades 1-5)
│   ├── LOGS_EJECUCION.md        # Evidencias de pruebas con salidas
│   └── INSTRUCCIONES_USO.md     # Guía de uso y troubleshooting
├── docker-compose.yml            # Orquestación de 3 servicios
├── Dockerfile                    # Imagen para web1 y web2
├── .dockerignore                 # Exclusiones de build
├── .gitignore                    # Exclusiones de git
└── README.md                     # Este archivo
```

---

## Inicio Rápido

### 1. Requisitos

```bash
docker --version          # 20.10+
docker compose version    # 2.0+
openssl version          # 3.x+
```

### 2. Clonar y ejecutar

```bash
git clone https://github.com/JeffreyValerio/analisis-caso-1.git
cd analisis-caso-1
docker compose up -d
```

### 3. Verificar que está corriendo

```bash
docker compose ps
```

**Esperado:**
```
NAME            IMAGE                STATUS
caso1-haproxy   haproxy:2.9-alpine   Up 5 seconds
caso1-web1      caso1-web1           Up 6 seconds
caso1-web2      caso1-web2           Up 6 seconds
```

### 4. Probar funcionalidad

```bash
# HTTP + Balanceo
curl http://localhost:8080/

# Health check (usado por HAProxy)
curl http://localhost:8080/health

# HTTPS (ignora certificado auto-firmado)
curl -k https://localhost:8443/

# Panel de estadísticas
open http://localhost:8404/

# Ver logs en vivo
docker compose logs -f
```

---

## Evidencias de Pruebas

### Prueba 1: Balanceo RoundRobin

```bash
for i in {1..5}; do
  curl -s http://localhost:8080/ | grep "Instancia:"
done

# Salida esperada (alternancia 1-2-1-2-1):
# <p>Instancia: <b>web1</b></p>
# <p>Instancia: <b>web2</b></p>
# <p>Instancia: <b>web1</b></p>
# <p>Instancia: <b>web2</b></p>
# <p>Instancia: <b>web1</b></p>
```

✅ **Resultado:** RoundRobin funciona correctamente

### Prueba 2: Failover Automático

```bash
# Inicial: ambos backends UP
docker pause caso1-web1    # Simular crash

# Esperar 3 segundos (timeout de healthcheck)
sleep 3

# Todos los requests van a web2
for i in {1..3}; do
  curl -s http://localhost:8080/ | grep "Instancia:"
done
# Salida: web2, web2, web2

# Recuperar
docker unpause caso1-web1
sleep 6  # Esperar recuperación (2 checks exitosos)

# Balanceo se reanuda
curl -s http://localhost:8080/ | grep "Instancia:"
# Salida: web1 (o web2, alternancia reanudada)
```

✅ **Resultado:** Failover en ~5 segundos, sin pérdida de datos

### Prueba 3: Aislamiento de Procesos

```bash
docker top caso1-web1
# Salida: PID en el host = 420497 (ejemplo)

curl -s http://localhost:8080/ | grep "PID del proceso"
# Salida en HTML: PID del proceso: 1
```

✅ **Resultado:** PID namespace funciona; PID 1 dentro del contenedor

### Prueba 4: HTTPS con TLS

```bash
curl -k https://localhost:8443/
# Salida: Hola Mundo (conexión TLS exitosa)

openssl x509 -in haproxy/certs/caso1.crt -text -noout
# Muestra: Subject: C=CR, O=Universidad Latina, CN=caso1.local
```

✅ **Resultado:** HTTPS funcional con certificado auto-firmado

### Prueba 5: Estadísticas de HAProxy

Navegador: `http://localhost:8404/`

Datos visibles:
- web1: 4 sesiones, 4 respuestas 2xx, L7OK/200, 17s UP
- web2: 3 sesiones, 3 respuestas 2xx, L7OK/200, 17s UP
- Backend: 7 sesiones totales, balanceo RoundRobin activo

✅ **Resultado:** Monitoreo en tiempo real funcional

---

## Métricas Medidas

| Métrica | Valor | Nota |
|---------|-------|------|
| Latencia HTTP | 2-3 ms | Overhead negligible |
| Latencia HTTPS | 5-8 ms | TLS negociación normal |
| Consumo memoria (web1) | 21.62 MiB | Eficiente para Python/Flask |
| Consumo CPU | 0.01% idle | < 1% bajo carga moderada |
| RTO (Recovery Time) | ~5 segundos | Detección + recuperación |
| RPO (Recovery Point) | 0 | Sin pérdida de datos |
| Disponibilidad teórica | 99.9999% | Con 2 servidores |

---

## Conceptos de Sistemas Operativos Demostrados

### PID Namespace

✅ Cada contenedor ve su propio PID 1  
✅ El proceso real en el host tiene otro PID  
✅ Aislamiento completo de procesos  
**Implicación:** Contenedores no interfieren entre sí

### cgroups (Control Groups)

✅ Limitación de memoria por contenedor  
✅ Contabilización de CPU  
✅ Aislamiento de I/O de bloque  
**Implicación:** Multitenencia segura en un mismo host

### Network Namespaces

✅ Red interna `caso1net` aísla contenedores  
✅ Solo HAProxy expone puertos al exterior  
✅ Comunicación transparente entre contenedores  
**Implicación:** Seguridad de red mejorada

### Filesystem Layers

✅ Capas de lectura compartidas (imagen)  
✅ Capa de escritura efímera por contenedor  
✅ Volúmenes para persistencia explícita  
**Implicación:** Contenedores son desechables

---

## Análisis de Seguridad

### HTTP (Puerto 8080)

❌ **Riesgos:**
- Tráfico en texto plano
- Intercepción de credenciales
- MITM attacks posibles

✅ **Configurado para:**
- Testing y desarrollo local
- Análisis de riesgos

### HTTPS (Puerto 8443)

✅ **Beneficios:**
- Encriptación end-to-end (TLS 1.2+)
- Autenticación del servidor (certificado)
- Integridad de datos
- Protección contra ataques de red

⚠️ **Limitaciones actuales:**
- Certificado auto-firmado (no válido en navegadores)
- Para producción: usar Let's Encrypt

### Control de Acceso

✅ Implementado:
- Red interna aislada (docker network bridge)
- Puertos explícitamente mapeados
- Sin acceso directo a web1/web2 desde el exterior

🔒 Recomendado para producción:
- WAF (Web Application Firewall)
- Rate limiting
- Autenticación TLS mutua (mTLS)

---

## Escalabilidad Horizontal

### Agregar una tercera instancia

Cambios en `docker-compose.yml`:
```yaml
  web3:
    build: .
    environment:
      - INSTANCE_NAME=web3
    networks:
      - caso1net
```

Cambios en `haproxy/haproxy.cfg`:
```haproxy
server web3 web3:5000 check inter 3s fall 2 rise 2
```

Aplicar:
```bash
docker compose up -d
```

**Resultado:**
- Capacidad aumenta 50% (de 2 a 3 instancias)
- Sin downtime (HAProxy recarga gracefully)
- Disponibilidad mejorada

### Escalamiento teórico

- 2 instancias: 99.9999% uptime
- 3 instancias: 99.99999% uptime
- N instancias: 1 - (0.001^N)

---

## Documentación Completa

Para análisis profundo, ver:

1. **[docs/ANALISIS_TECNICO.md](docs/ANALISIS_TECNICO.md)**
   - Arquitectura detallada
   - Análisis de SO, redes, seguridad
   - Recomendaciones para producción
   - Comparativas de técnicas

2. **[docs/LOGS_EJECUCION.md](docs/LOGS_EJECUCION.md)**
   - Salidas reales de cada actividad
   - Evidencias de pruebas
   - Métricas medidas
   - Observaciones finales

3. **[docs/INSTRUCCIONES_USO.md](docs/INSTRUCCIONES_USO.md)**
   - Guía de instalación paso a paso
   - Comandos de prueba reproducibles
   - Configuración avanzada
   - Troubleshooting

---

## Tecnologías Utilizadas

| Componente | Versión | Rol |
|------------|---------|-----|
| Docker | 29.5.3 | Containerización |
| Docker Compose | 5.1.4 | Orquestación |
| HAProxy | 2.9-alpine | Balanceo de carga |
| Python | 3.12 | Lenguaje de la app |
| Flask | 3.0.3 | Framework web |
| OpenSSL | 3.5.7 | TLS/certificados |
| Linux (cgroups v2) | 7.0.12 | Limitación de recursos |

---

## Resultados Finales

✅ **Todos los objetivos completados:**
- Containerización funcional
- Balanceo de carga verificado (RoundRobin 1:1)
- Failover automático (~5s RTO)
- HTTPS implementado
- Escalabilidad horizontal demostrada
- Documentación completa

⚠️ **No production-ready:**
- Certificados auto-firmados
- Sin persistencia de datos
- Sin logging centralizado
- Requerimientos para producción listados en análisis

---

## Contacto y Contribuciones

- **Repositorio:** https://github.com/JeffreyValerio/analisis-caso-1
- **Autor:** Jeffrey Valerio
- **Email:** jeffreyvalerio@hotmail.com

Para preguntas, abrir un issue en GitHub.

---

## Licencia

Proyecto educativo para BISOF-18 Sistemas Operativos II.

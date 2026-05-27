# Rate limiting privacy-first

Este documento diseña la estrategia de rate limiting y anti-abuse para urlbreve.
La Fase 1 ya está implementada sin IP, sin fingerprinting, sin modelos nuevos,
sin migraciones y sin dependencias nuevas.

## Problema

urlbreve evita guardar IPs, user-agent, referrer, geolocalización y tracking.
Esa decisión es central para el proyecto, pero hace que el control de abuso sea
menos directo que en sistemas que identifican visitantes por IP o fingerprint.

Superficies de abuso actuales o previstas:

- La creación anónima por `POST /api/shorten/` puede usarse para crear grandes
  volúmenes de URLs, spam o enlaces a destinos maliciosos.
- La creación autenticada con `X-API-Key` puede abusarse si una clave se filtra,
  se automatiza agresivamente o se usa para evadir moderación manual.
- `/report/` puede recibir spam de reportes falsos o ruido automatizado.
- El password gate puede recibir fuerza bruta contra enlaces protegidos.
- Las redirecciones públicas pueden ser hotlinked, usadas como salto masivo o
  consultadas de forma agresiva.
- Proteger usuarios anónimos sin guardar IP cruda es difícil: cuanto más fuerte
  es la defensa, más probable es que introduzca identificadores personales o
  persistentes.

## Principios

- No guardar IPs crudas en la base de datos.
- No guardar user-agent, referrer ni huellas de navegador.
- No añadir trackers ni captcha externo por defecto.
- Preferir límites asociados a entidades explícitas: usuario, API key, sesión o
  enlace.
- Usar datos efímeros y agregados cuando haga falta defensa temporal.
- Hacer que cualquier excepción basada en infraestructura sea explícita,
  documentada y fácil de apagar.
- Fallar de forma conservadora: si hay duda entre bloquear creación abusiva o
  recopilar más datos personales, primero limitar funcionalidad.

## Estrategia por capas

### Usuarios autenticados

Los flujos web autenticados pueden limitarse por `request.user.id`, que no añade
un identificador nuevo. Ejemplos:

- URLs creadas por día.
- Rotaciones de API key por día.
- Cambios de namespace por ventana de tiempo.

El contador puede vivir inicialmente en cache local de Django y, si hay varias
instancias, moverse a Redis o a un backend de cache compartido.

### API keys

Las peticiones con `X-API-Key` deben limitarse por una clave estable que no sea
la API key en claro. Hay dos opciones razonables:

- usar `UserProfile.id` tras verificar la key;
- usar un digest interno derivado de la key cruda solo en memoria durante la
  petición.

La opción recomendada es limitar por usuario asociado, porque la key ya se
verifica para resolver el owner y no se necesita guardar ni exponer hashes
adicionales. Revocar una key debe cortar también el uso futuro de esa identidad
API.

### Sesiones Django

Para flujos web públicos como `/report/` y el password gate, una cookie de
sesión puede dar límites suaves sin IP:

- reportes por sesión y por ventana de tiempo;
- intentos fallidos de contraseña por sesión;
- cooldown visual antes de permitir nuevos POST.

Esto no detiene clientes que descartan cookies, pero reduce abuso casual sin
crear identificadores opacos propios.

### Ruta y cache

Algunas acciones pueden limitarse por ruta o entidad:

- intentos de password gate por `ShortURL.id`;
- volumen de redirecciones por `ShortURL.id`;
- reportes repetidos por `reported_path` normalizado.

Estos límites no identifican visitantes. Sirven para proteger un recurso bajo
ataque, aunque pueden afectar a usuarios legítimos cuando un enlace se vuelve
popular.

### Honeypot

Los formularios públicos pueden añadir un campo honeypot oculto en HTML:

- si viene relleno, se rechaza o se acepta de forma silenciosa sin crear efecto;
- no requiere servicios externos;
- no identifica al visitante.

Es especialmente útil para `/report/`. Debe implementarse con cuidado para no
romper accesibilidad: el campo debe estar fuera del flujo normal de teclado y
tener nombre no obvio.

### Tamaños y validación estricta

Ya existe validación conservadora de slug, URL destino y detalles de reporte. La
estrategia debe mantener y reforzar:

- límites de tamaño de JSON y formularios;
- `destination_url` solo `http://` o `https://`;
- límites de longitud para `title`, `details`, `slug` y password;
- rechazo temprano de JSON inválido;
- respuestas genéricas que no ayuden a enumerar recursos privados.

### Moderación manual

La moderación con `is_disabled` y `AbuseReport` sigue siendo una capa central.
Rate limiting reduce volumen; no reemplaza revisión humana ni bloqueo de enlaces
abusivos.

Futuro posible:

- cola de reportes priorizada por número de reportes por `ShortURL`;
- acciones de admin para dominios repetidamente abusivos;
- lista de destinos bloqueados por dominio o patrón, con revisión manual.

### Dominios abusivos

Un bloqueo futuro por destino debe operar sobre dominio normalizado, no sobre
datos del visitante. Puede usarse para impedir creación de enlaces hacia
dominios marcados como phishing, malware o spam.

Decisiones pendientes para esa capa:

- si el bloqueo es manual o alimentado por listas externas;
- cómo auditar falsos positivos;
- si las listas externas introducen dependencias o filtrado opaco.

## Opciones para usuarios anónimos

### No limitar anónimos

Ventajas:

- privacidad máxima;
- implementación simple;
- cero identificadores nuevos.

Riesgos:

- la API anónima puede ser abusada a gran escala;
- más carga para moderación manual;
- potencial degradación del servicio.

Esta opción solo es razonable si la API anónima está desactivada o muy limitada
por defecto.

### Limitar por sesión o cookie

Ventajas:

- compatible con Django;
- no requiere IP;
- útil para formularios web y abuso casual.

Riesgos:

- no protege contra bots que descartan cookies;
- crea una cookie de sesión, aunque sea estándar y limitada;
- no encaja igual de bien con clientes API puros.

### Prueba de trabajo ligera

El servidor puede pedir una prueba computacional simple antes de aceptar ciertas
acciones anónimas.

Ventajas:

- no identifica al visitante;
- eleva el coste de automatizar abuso masivo;
- no depende de terceros.

Riesgos:

- complica clientes legítimos;
- puede perjudicar dispositivos lentos;
- necesita diseño cuidadoso para evitar DoS contra el propio servidor.

Puede explorarse más adelante para creación anónima por API, no como primera
fase.

### Captcha externo

Queda descartado inicialmente.

Motivos:

- introduce terceros en el flujo;
- puede añadir tracking o fingerprinting;
- perjudica accesibilidad y auditabilidad;
- no encaja con la filosofía privacy-first por defecto.

### Reverse proxy con IP temporal no persistente

Nginx u otro proxy puede limitar por IP en memoria sin escribir access logs
persistentes.

Ventajas:

- efectivo bajo ataques volumétricos;
- evita que Django tenga que almacenar IP;
- puede configurarse como defensa temporal.

Riesgos:

- sigue usando IP como señal, aunque sea efímera;
- puede afectar a NATs, redes compartidas o Tor/VPN;
- debe cuidarse que los logs no persistan IPs;
- la configuración real vive fuera del código Django.

Esta capa debe documentarse como modo de emergencia de infraestructura, no como
parte normal de producto.

### Hash HMAC temporal de IP

Otra opción es derivar buckets efímeros con HMAC:

```text
bucket = HMAC(secret_rotado, ip + ventana_temporal)
```

La IP cruda no se guarda y el secreto rota con frecuencia, por ejemplo cada hora
o cada día.

Ventajas:

- permite limitar anónimos con más precisión que una sesión;
- no persiste IP cruda;
- los buckets viejos dejan de ser correlacionables si se destruyen secretos
  antiguos.

Riesgos:

- sigue siendo tratamiento de datos personales derivado de IP;
- puede convertirse en tracking si la rotación es larga;
- requiere disciplina operacional sobre secretos y retención;
- aumenta el área de auditoría y debe ser opcional.

Recomendación: no implementarlo en la primera fase. Mantenerlo como mecanismo
opcional, sensible y documentado para escenarios donde el abuso no pueda
controlarse de otra manera.

## Decisión inicial recomendada

La primera implementación debería evitar IPs por completo:

- Añadir `URLBREVE_ANONYMOUS_API_ENABLED` para poder desactivar creación anónima
  por API en producción.
- Si la API anónima está activa, aplicar un límite muy bajo y documentado.
- Aplicar límites fuertes por usuario autenticado.
- Aplicar límites fuertes por usuario resuelto desde `X-API-Key`.
- Añadir honeypot en `/report/`.
- Limitar password gate por sesión y opcionalmente por enlace con cooldown.
- Mantener validación estricta de tamaños y destinos.
- Usar moderación manual con `AbuseReport` e `is_disabled`.
- Configurar nginx sin access logs persistentes en producción.
- Reservar protección temporal en memoria a nivel de infraestructura para
  ataques activos, con uso explícito y revisable.

## Fase 1 implementada

La Fase 1 usa Django cache con ventana diaria y `timezone.localdate()`. Las
claves de cache no contienen IP, user-agent, referrer ni API keys en claro.

Límites activos:

- `POST /api/shorten/` anónimo: por sesión Django. Si
  `URLBREVE_ANONYMOUS_API_ENABLED=False`, devuelve `403`.
- `POST /api/shorten/` con `X-API-Key`: por usuario resuelto desde la API key.
- `/links/new/`: por usuario autenticado.
- `/`: creación anónima web por sesión Django.
- `/report/`: por sesión Django.
- Password gate: por sesión Django y `ShortURL.id`.

Cuando se supera un límite, la API devuelve `429` JSON. Los formularios web
muestran error de formulario y no crean registros ni redirigen.

El password gate cuenta todos los POST válidos de contraseña, correctos o
incorrectos. Esta decisión reduce fuerza bruta sin revelar si una contraseña era
válida. Si se supera el límite, no se comprueba la contraseña, no se redirige y
no se incrementan estadísticas.

Limitaciones:

- La API anónima y la creación anónima web se limitan por sesión/cookie.
  Clientes que descartan cookies pueden evadir este límite.
- El cache local solo coordina límites dentro de una instancia. Varias
  instancias necesitarán cache compartida.
- No hay honeypot todavía.
- No hay defensa de infraestructura automatizada todavía.

## Settings

Estos settings se leen del entorno, igual que el resto de configuración del
proyecto:

- `URLBREVE_ANONYMOUS_API_ENABLED`: activa o desactiva creación anónima por API.
- `URLBREVE_RATE_LIMITING_ENABLED`: interruptor general de rate limiting.
- `URLBREVE_ANONYMOUS_DAILY_LIMIT`: límite diario para creación anónima cuando
  esté habilitada.
- `URLBREVE_AUTHENTICATED_DAILY_LIMIT`: límite diario para creación web de
  usuarios autenticados.
- `URLBREVE_API_KEY_DAILY_LIMIT`: límite diario para creación por API key.
- `URLBREVE_REPORT_SESSION_DAILY_LIMIT`: límite diario de reportes por sesión.
- `URLBREVE_PASSWORD_GATE_SESSION_LIMIT`: intentos por sesión antes de cooldown.

Los límites numéricos `<= 0` se tratan como ilimitados para esa capa concreta.

Settings propuestos para fases posteriores:

- `URLBREVE_REPORT_HONEYPOT_ENABLED`: activa honeypot en formularios públicos.
- `URLBREVE_PRIVACY_PRESERVING_IP_BUCKETS_ENABLED`: activaría buckets HMAC
  temporales basados en IP. Sigue siendo opcional, sensible y desactivado por
  defecto.

Valores iniciales sugeridos para producción pequeña:

- API anónima desactivada o límite muy bajo.
- API key: límite mayor, pero finito.
- Usuarios autenticados web: límite moderado por día.
- Password gate: límite bajo por sesión y cooldown corto por enlace.
- Reportes: honeypot activo y límites por sesión.

## Implementación futura por fases

### Fase 1: límites sin IP

Estado: implementada.

- Settings añadidos.
- Contadores en cache por usuario autenticado.
- Contadores en cache por usuario resuelto desde API key.
- Contadores por sesión para creación anónima web, `/report/` y password gate.
- `429 Too Many Requests` para API cuando corresponde.
- Tests de límites y bypass con `URLBREVE_RATE_LIMITING_ENABLED=False`.

### Fase 2: honeypot y cooldown por enlace

- Añadir campo honeypot a `/report/`.
- Añadir cooldown por `ShortURL.id` para intentos de password gate.
- Añadir límites por `reported_path` para reportes repetidos.
- Mantener respuestas genéricas y sin datos de visitante.

### Fase 3: cache compartida

- Revisar si cache local basta para una sola instancia.
- Si hay varias instancias, añadir Redis u otro backend compatible con Django
  cache.
- Mantener las claves de cache como identificadores de entidad, no de visitante.
- Documentar retención y expiración de claves.

### Fase 4: defensa temporal de infraestructura

- Configurar nginx sin access logs persistentes.
- Preparar reglas temporales en memoria para ataques activos.
- Evaluar buckets HMAC temporales solo si las fases anteriores no bastan.
- Documentar activación, duración, responsable y revisión posterior.

## No objetivos de la primera implementación

- No guardar IP cruda.
- No guardar user-agent ni referrer.
- No añadir captcha externo.
- No crear fingerprinting de navegador.
- No bloquear Tor/VPN por defecto.
- No depender de listas externas sin revisión.

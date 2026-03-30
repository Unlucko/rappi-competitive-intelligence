# Competitive Intelligence: Sistema de Scraping y Analisis Competitivo para Rappi

## Descripcion General

Este sistema recolecta automaticamente datos de precios, tarifas y tiempos de entrega de Rappi, Uber Eats y DiDi Food en Mexico, los compara de forma estructurada y genera un informe ejecutivo con insights accionables. El objetivo es que el equipo de Rappi pueda monitorear su posicion competitiva por ciudad, zona socioeconomica y producto de referencia, sin intervension manual.

El sistema tiene dos modos de uso: scraping en vivo mediante Playwright y un modo de datos de muestra para explorar el dashboard sin ejecutar el navegador.

---

## Arquitectura

```
competitive-intelligence/
├── run_scraper.py              # Orquestador principal: ejecuta scrapers y genera reportes
├── app.py                      # Dashboard interactivo Streamlit
├── config.py                   # Direcciones, productos, configuracion de plataformas y scraping
│
├── scrapers/
│   ├── base_scraper.py         # Clase base con logica comun y estructura ScrapingResult
│   ├── rappi_scraper.py        # Scraper especifico para rappi.com.mx
│   ├── ubereats_scraper.py     # Scraper especifico para ubereats.com
│   └── didifood_scraper.py     # Scraper especifico para didifoods.com
│
├── analysis/
│   ├── comparative_analyzer.py # Calculos de comparacion: precios, tarifas, tiempos, geografia
│   ├── insight_generator.py    # Generacion de los 5 insights accionables priorizados
│   └── report_builder.py       # Construccion del informe HTML, Markdown y graficos Plotly
│
├── utils/
│   ├── browser_manager.py      # Gestion del ciclo de vida del navegador Playwright
│   └── rate_limiter.py         # Control de velocidad, reintentos y backoff exponencial
│
└── output/
    ├── scraped_data.json        # Resultados del scraping en vivo
    ├── sample_data.json         # Datos de muestra para modo demo
    ├── screenshots/             # Capturas de pantalla ante errores
    └── scraper.log              # Log de ejecucion
```

### Modulo `scrapers/`

Cada scraper hereda de `BaseScraper` e implementa la logica especifica de navegacion para su plataforma. Devuelven objetos `ScrapingResult` con campos estandarizados que luego se serializan a diccionario.

### Modulo `analysis/`

`ComparativeAnalyzer` toma el DataFrame de resultados y produce tablas de comparacion por plataforma, ciudad, tipo de zona y producto. `InsightGenerator` consume esas tablas para producir exactamente 5 insights priorizados por impacto. `ReportBuilder` ensambla el informe final en HTML y Markdown, y exporta los graficos como archivos HTML independientes.

### Modulo `utils/`

`BrowserManager` gestiona la instancia de Playwright: arranque, rotacion de user-agents y cierre limpio. `RateLimiter` implementa delays aleatorios entre peticiones, reintentos con backoff exponencial y un maximo configurable de intentos por URL.

---

## Plataformas Scrapeadas

| Plataforma | URL base | Busqueda de restaurante |
|---|---|---|
| Rappi | rappi.com.mx | McDonald's |
| Uber Eats | ubereats.com | McDonald's |
| DiDi Food | didifoods.com | McDonald's |

Cada plataforma puede habilitarse o deshabilitarse de forma independiente en `config.py` mediante el campo `enabled` de `PlatformConfig`.

---

## Direcciones Seleccionadas y Justificacion

Se eligieron 25 direcciones distribuidas en 6 ciudades de Mexico para cubrir distintos perfiles socioeconomicos y geograficos:

| Ciudad | Zonas | Tipo |
|---|---|---|
| CDMX | Polanco, Condesa, Roma Norte, Santa Fe | Alta |
| CDMX | Coyoacan, Del Valle, Narvarte | Media |
| CDMX | Iztapalapa, Gustavo A. Madero, Tepito, Xochimilco | Popular |
| Monterrey | San Pedro Garza Garcia | Alta |
| Monterrey | Centro, Cumbres | Media |
| Monterrey | Apodaca | Popular |
| Guadalajara | Zapopan | Alta |
| Guadalajara | Centro | Media |
| Guadalajara | Tlaquepaque, Tonala | Popular |
| Puebla | Angelopolis | Alta |
| Puebla | Centro | Media |
| Merida | Norte, Centro | Media |
| Cancun | Zona Hotelera | Alta |
| Cancun | Centro | Media |

**Justificacion de la seleccion:** La distribucion intencional entre zonas alta, media y popular permite detectar si las plataformas aplican tarifas de envio diferenciales segun el nivel socioeconomico del codigo postal, una practica relevante para la estrategia de precios de Rappi. La inclusion de varias ciudades permite comparaciones inter-mercado.

---

## Productos de Referencia

Se usan cuatro productos de McDonald's como canasta estandarizada, ya que McDonald's esta disponible en las tres plataformas en todas las ciudades analizadas, lo que permite comparaciones directas sin sesgo de disponibilidad:

| ID | Producto | Categoria |
|---|---|---|
| `big_mac` | Big Mac | fast_food |
| `combo_mediano` | Combo Mediano McDonald's | fast_food |
| `mcnuggets_6` | McNuggets 6pc | fast_food |
| `coca_cola_500ml` | Coca-Cola 500ml | retail |

---

## Metricas Recolectadas

Por cada combinacion de plataforma, direccion y producto se registran:

| Campo | Descripcion |
|---|---|
| `product_price` | Precio del producto en la plataforma (MXN) |
| `delivery_fee` | Tarifa de envio cobrada al usuario |
| `service_fee` | Tarifa de servicio o comision de la plataforma |
| `total_price` | Suma: precio del producto + tarifa de envio + tarifa de servicio |
| `delivery_time_minutes` | Tiempo estimado de entrega en minutos |
| `has_promotion` | Si el producto o restaurante tiene algun descuento activo |
| `discount_amount` | Monto del descuento aplicado (si aplica) |
| `scrape_success` | Si la extraccion fue exitosa o fallo |
| `scraped_at` | Timestamp de la extraccion |

---

## Instrucciones de Ejecucion

### Requisitos

```bash
pip install playwright pandas plotly streamlit
playwright install chromium
```

### Modo de datos de muestra (sin scraping en vivo)

Este modo usa `output/sample_data.json` y no abre ningun navegador. Es la forma recomendada para explorar el dashboard sin dependencias externas:

```bash
python run_scraper.py --sample-only
```

### Modo scraping en vivo

Ejecuta el scraping real contra las tres plataformas. Por defecto usa 3 direcciones por plataforma. Se puede ampliar con el argumento `--max-addresses`:

```bash
python run_scraper.py
python run_scraper.py --max-addresses=10
```

Si el scraping en vivo no produce resultados exitosos, el sistema carga automaticamente los datos de muestra como fallback.

### Dashboard interactivo

Despues de ejecutar el scraper (o directamente con datos de muestra):

```bash
streamlit run app.py
```

La aplicacion se abre en `http://localhost:8501`.

---

## Como Funciona el Scraping

1. **Playwright headless**: El navegador Chromium se lanza en modo sin cabeza (`headless=True`). Cada scraper navega a la URL de la plataforma, ingresa la direccion de entrega, busca el restaurante McDonald's y extrae los precios y tarifas del DOM.
2. **Rotacion de user-agents**: En cada sesion se selecciona aleatoriamente uno de cuatro user-agents reales (Chrome en Mac, Chrome en Windows, Safari en Mac, Chrome en Linux) para reducir la probabilidad de deteccion.
3. **Rate limiting**: Entre cada peticion se espera un delay aleatorio de entre 2 y 5 segundos (`min_delay_seconds`, `max_delay_seconds`). Esto reduce la carga sobre los servidores y simula comportamiento humano.
4. **Reintentos con backoff exponencial**: Si una peticion falla, el sistema reintenta hasta 3 veces (`max_retries=3`) con un tiempo de espera que crece exponencialmente a partir de una base de 2 segundos (`backoff_base_seconds`).
5. **Capturas de pantalla ante errores**: Cuando una extraccion falla, Playwright toma una captura de pantalla y la guarda en `output/screenshots/` para facilitar el diagnostico.
6. **Fallback automatico**: Si ningun scraper produce resultados exitosos, el orquestador carga `output/sample_data.json` para garantizar que el informe siempre pueda generarse.

---

## Como Funciona el Informe

El informe se genera automaticamente al finalizar el scraping mediante `ReportBuilder`:

1. **5 insights accionables**: `InsightGenerator` analiza los resultados de `ComparativeAnalyzer` y produce exactamente 5 insights priorizados por nivel de impacto (alto, medio, bajo). Cada insight incluye: hallazgo, impacto para el negocio y recomendacion concreta.
2. **Visualizaciones Plotly**: Se generan graficos interactivos de barras agrupadas para precios por producto y plataforma, tarifas de envio y servicio, tiempos de entrega, comparacion geografica por ciudad y tarifa por tipo de zona socioeconomica. Tambien se incluye un mapa de calor de costo total por ciudad y plataforma.
3. **Dashboard Streamlit**: `app.py` expone todos los analisis en siete pestanas: Resumen Ejecutivo, Precios, Tarifas, Tiempos de Entrega, Analisis Geografico, Insights y Datos Crudos. El resumen ejecutivo muestra la posicion competitiva de Rappi mediante metricas clave con indicadores de delta frente a la competencia.
4. **Exportacion**: El informe se guarda en HTML y Markdown en `output/`. Los graficos se exportan como archivos HTML independientes. Los datos filtrados pueden descargarse desde el dashboard en CSV o JSON.

---

## Consideraciones Eticas

- **Rate limiting estricto**: Delays de 2-5 segundos entre peticiones para no generar carga indebida en los servidores de las plataformas.
- **Rotacion de user-agents**: Se usan cadenas de user-agent reales de navegadores comerciales; no se suplantan identidades.
- **Uso limitado**: El scraping se realiza con fines de investigacion competitiva interna. El volumen de peticiones es minimo (maximo 25 direcciones por plataforma en una ejecucion completa).
- **Sin almacenamiento de datos personales**: No se recolectan ni almacenan datos de usuarios, sesiones ni informacion personal de ninguna plataforma.
- **Respeto a robots.txt**: El sistema opera sobre las interfaces publicas de las aplicaciones web tal como lo haria un usuario humano.

---

## Decisiones Tecnicas

### Por que Playwright y no Requests/BeautifulSoup

Las tres plataformas renderizan su contenido dinamicamente mediante JavaScript (React o similares). Las peticiones HTTP directas devuelven HTML vacio o requieren replicar flujos de autenticacion y tokens anti-bot complejos. Playwright controla un navegador real, lo que permite interactuar con la interfaz exactamente como un usuario humano.

### Por que fallback con datos de muestra

Los sitios de delivery invierten en deteccion de bots y pueden bloquear IPs en entornos de desarrollo o CI. El fallback garantiza que el sistema sea demostrable en cualquier entorno sin depender de la disponibilidad de las plataformas externas en el momento de la evaluacion.

### Por que arquitectura modular (scrapers / analysis / utils)

La separacion en tres capas permite: (1) reemplazar o agregar un scraper nuevo sin modificar el analisis, (2) ejecutar el analisis sobre datos historicos sin volver a hacer scraping, y (3) testear cada componente de forma independiente. Esta estructura escala naturalmente a mas plataformas (Cornershop, Drizly, etc.).

---

## Limitaciones y Mejoras Futuras

**Limitaciones actuales:**

- Los scrapers dependen de la estructura del DOM de cada plataforma; un cambio de diseno puede romper la extraccion.
- No se maneja login; los precios para usuarios PRO o con suscripcion no son accesibles.
- El scraping en vivo puede ser lento (varios minutos para las 25 direcciones en 3 plataformas).
- No hay programacion automatica; el scraping debe lanzarse manualmente.

**Mejoras futuras:**

- Agregar monitoreo de precios en el tiempo (base de datos persistente) para detectar cambios dinamicos de precios por hora o dia de la semana.
- Implementar proxies rotativos para reducir la probabilidad de bloqueo.
- Extender la canasta de productos de referencia a otras cadenas disponibles en las tres plataformas.
- Programar ejecuciones periodicas con cron o GitHub Actions para generar series temporales.
- Agregar pruebas automatizadas para detectar roturas de scrapers ante cambios de DOM.

---

## Costo Estimado

**$0 USD**

El sistema utiliza exclusivamente herramientas de codigo abierto (Playwright, pandas, Plotly, Streamlit) y no requiere ninguna API de pago, servicio cloud ni infraestructura externa. Los datos se almacenan localmente en archivos JSON y CSV.

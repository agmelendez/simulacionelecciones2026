# 🗳️ Simulación Elecciones Presidenciales Costa Rica 2026

Landing page para compartir resultados de simulaciones y predicciones electorales basadas en modelos de Machine Learning desarrollados en Python.

## 🆕 Actualización - 21 de enero 2026 (Modelo v2.1)

**Última actualización del modelo:** 21 de enero 2026

### 📊 Indicadores Clave (Corte 21 enero 2026)
- **Probabilidad de Victoria en 1ra Ronda:** 62.45%
- **Media de Voto Válido (Laura Fernández):** 41.12%
- **Nivel de Indecisión:** 32%
- **Pool de Encuestas:** Incluye medición más reciente del CIEP-UCR

### 🛠️ Mejoras Técnicas del Modelo v2.1
1. **Ajuste de Logit-Normal Mejorado:** Matriz de covarianza que captura mejor la correlación entre candidatos del mismo bloque ideológico
2. **Nuevo Escenario de "Dispersión":** Parte de los indecisos migra a candidaturas minoritarias (RESTO), reflejando el fraccionamiento observado en encuestas recientes
3. **Decaimiento Temporal:** Las encuestas de octubre y noviembre de 2025 tienen peso significativamente menor comparado con las de enero de 2026
4. **Sensibilidad a Abstención Técnica:** Factor que impacta la distribución final de votos

### 📈 Top 3 Escenarios de Segunda Ronda
1. **Laura Fernández vs Álvaro Ramos:** 45%
2. **Laura Fernández vs Claudia Dobles:** 18%
3. **Laura Fernández vs Ariel Robles:** 12%

## 📋 Descripción

Este proyecto presenta un sitio web estático y seguro diseñado para publicar análisis predictivos de las elecciones presidenciales de Costa Rica 2026. El sitio implementa las mejores prácticas de seguridad web y ciberseguridad para proteger tanto el contenido como los usuarios.

El modelo utiliza **100,000 simulaciones Monte Carlo** con técnicas estadísticas avanzadas para proyectar posibles resultados electorales, considerando la incertidumbre inherente en las encuestas y el comportamiento de votantes indecisos.

## ✨ Características

### Funcionalidades
- 📊 Landing page moderno y responsivo
- 📈 Sección para publicar resultados de simulaciones
- 🔬 Documentación de metodología y tecnologías
- 📧 Formulario de contacto con validación
- 🎨 Diseño adaptable a todos los dispositivos

### Seguridad y Ciberseguridad
- 🔒 **Content Security Policy (CSP)** - Prevención de XSS
- 🛡️ **Sanitización de inputs** - Protección contra inyección de código
- 🚫 **X-Frame-Options** - Prevención de clickjacking
- 🔐 **HTTPS enforcement** - Forzado de conexiones seguras
- ⚡ **Rate limiting** - Protección contra spam y ataques de fuerza bruta
- 🎯 **CSRF tokens** - Protección contra falsificación de peticiones
- 🔍 **Input validation** - Validación exhaustiva de formularios
- 📝 **Security headers** - Headers HTTP de seguridad
- 🚷 **Protección de archivos sensibles**
- 🔄 **HSTS** - Strict Transport Security

## 🏗️ Estructura del Proyecto

```
simulacionelecciones2026/
│
├── index.html                              # Página principal
├── .htaccess                              # Configuración de seguridad Apache
├── README.md                              # Documentación
├── .gitignore                            # Archivos ignorados por Git
│
├── cr_presidential_mc_2026_updated.py     # Script de simulación v2.1 [NUEVO]
├── Modelo_de_Simulación_Elecciones.ipynb  # Jupyter Notebook con análisis
│
├── Articulo Modelo de Simulación Elecciones CR 2026.pdf  # Documento académico
├── DOCUMENTO_TECNICO_METODOLOGIA.txt (1).pdf             # Metodología técnica
│
├── resumen_mc_2026.json                   # Métricas clave del modelo [NUEVO]
├── figura_mc_2026.png                     # Visualización principal [NUEVO]
├── simulaciones_mc_2026.csv               # Dataset de simulaciones [NUEVO]
├── resumen_candidatos_mc_2026.csv         # Estadísticas por candidato [NUEVO]
├── escenarios_segunda_ronda_2026.csv      # Análisis de pares Top 2 [NUEVO]
│
├── resumen_candidatos_final.csv           # Datos históricos
├── top2_pairs_final.csv                   # Combinaciones históricas
├── Resultados del modelo.jpeg             # Visualización histórica
├── simulacion_final_integrada (1).png     # Gráfico histórico
│
├── css/
│   └── styles.css                         # Estilos del sitio
│
├── js/
│   ├── security.js                        # Módulo de seguridad
│   └── main.js                            # Lógica principal
│
└── config/
    └── security-headers.conf              # Configuración headers
```

## 🚀 Instalación y Despliegue

### Requisitos Previos
- Servidor web (Apache, Nginx, etc.)
- Certificado SSL/TLS para HTTPS
- Navegador web moderno

### Opción 1: Despliegue Local

```bash
# Clonar el repositorio
git clone https://github.com/tuusuario/simulacionelecciones2026.git
cd simulacionelecciones2026

# Abrir con un servidor local
# Opción Python
python -m http.server 8000

# Opción Node.js
npx http-server -p 8000

# Visitar: http://localhost:8000
```

### Opción 2: Despliegue en Apache

```bash
# Copiar archivos al directorio web
sudo cp -r * /var/www/html/simulacionelecciones2026/

# Asegurar que mod_rewrite y mod_headers estén habilitados
sudo a2enmod rewrite
sudo a2enmod headers
sudo systemctl restart apache2

# Configurar SSL (recomendado: Let's Encrypt)
sudo certbot --apache -d tudominio.com
```

### Opción 3: Despliegue en Nginx

```bash
# Copiar archivos
sudo cp -r * /usr/share/nginx/html/simulacionelecciones2026/

# Agregar configuración de seguridad en nginx.conf
# Ver config/security-headers.conf para ejemplos

sudo nginx -t
sudo systemctl restart nginx
```

### Opción 4: Despliegue en Plataformas Cloud

#### Netlify
```bash
# Instalar Netlify CLI
npm install -g netlify-cli

# Deploy
netlify deploy --prod
```

#### Vercel
```bash
# Instalar Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
```

#### GitHub Pages
```bash
# Push a GitHub
git push origin main

# Habilitar GitHub Pages en Settings > Pages
# Seleccionar branch main y carpeta root
```

## 🔧 Configuración

### Personalizar Content Security Policy

Editar en `index.html` (línea 9) o `.htaccess` según necesidades:

```html
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; ...">
```

### Configurar Formulario de Contacto

Por defecto, el formulario simula el envío. Para conectar con un backend:

1. Editar `js/main.js` en la función `submitForm()`
2. Reemplazar el código simulado con una llamada real:

```javascript
fetch('/api/contact', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': formData.csrfToken
    },
    body: JSON.stringify(formData)
})
.then(response => response.json())
.then(data => {
    showMessage('¡Mensaje enviado exitosamente!', 'success');
})
.catch(error => {
    showMessage('Error al enviar el mensaje', 'error');
});
```

### Ajustar Rate Limiting

Modificar en `js/security.js`:

```javascript
rateLimiter: {
    maxAttempts: 5,        // Número máximo de intentos
    timeWindow: 60000      // Ventana de tiempo en ms (1 minuto)
}
```

## 🔐 Características de Seguridad Implementadas

### 1. Content Security Policy (CSP)
Previene ataques XSS limitando las fuentes de contenido:
- Scripts solo desde el mismo origen
- Estilos solo desde el mismo origen
- Prevención de inline scripts maliciosos
- Frame-ancestors: none (previene clickjacking)

### 2. Sanitización de Inputs
Todas las entradas de usuario son sanitizadas:
- Escape de caracteres HTML especiales
- Validación de patrones
- Limitación de longitud
- Filtrado de caracteres de control

### 3. HTTPS Enforcement
- Redirección automática HTTP → HTTPS
- HSTS habilitado (31536000 segundos)
- Upgrade de conexiones inseguras

### 4. Rate Limiting
- Límite de 5 intentos por minuto en formulario
- Prevención de spam
- Limpieza automática de registros antiguos

### 5. CSRF Protection
- Generación de tokens únicos por sesión
- Validación de tokens en envíos
- Protección contra falsificación de peticiones

### 6. Headers de Seguridad
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), ...
```

## 🧪 Testing de Seguridad

### Verificar Headers de Seguridad

```bash
# Usando curl
curl -I https://tudominio.com

# Usando securityheaders.com
# Visitar: https://securityheaders.com/?q=tudominio.com

# Usando Mozilla Observatory
# Visitar: https://observatory.mozilla.org/
```

### Verificar CSP

```bash
# Usar CSP Evaluator de Google
# Visitar: https://csp-evaluator.withgoogle.com/
```

### Testing de Vulnerabilidades

```bash
# OWASP ZAP
zap-cli quick-scan https://tudominio.com

# Nikto
nikto -h https://tudominio.com

# SSL Labs
# Visitar: https://www.ssllabs.com/ssltest/
```

## 📊 Ejecutar el Modelo de Simulación

### Opción 1: Ejecutar el Script Python (v2.1)

```bash
# Instalar dependencias
pip install numpy pandas matplotlib seaborn scipy

# Ejecutar el script de simulación
python3 cr_presidential_mc_2026_updated.py
```

El script generará automáticamente:
- `resumen_mc_2026.json` - Métricas de probabilidad exactas
- `figura_mc_2026.png` - Histograma de distribución con barrera del 40%
- `simulaciones_mc_2026.csv` - Dataset completo (muestra de 10,000)
- `resumen_candidatos_mc_2026.csv` - Estadísticas por candidato
- `escenarios_segunda_ronda_2026.csv` - Análisis de pares Top 2

### Opción 2: Usar Jupyter Notebook

```bash
# Instalar Jupyter
pip install jupyter

# Abrir el notebook
jupyter notebook "Modelo_de_Simulación_Elecciones.ipynb"
```

### Características del Modelo v2.1

- **100,000 simulaciones Monte Carlo**
- **Distribución Logit-Normal** con matriz de covarianza mejorada
- **3 Escenarios de Indecisos:**
  - Balanceado (40%): Distribución proporcional
  - Polarizado (35%): Concentración en top 2
  - Dispersión (25%): Migración a candidaturas minoritarias [NUEVO]
- **Decaimiento temporal** en el peso de encuestas antiguas
- **Sensibilidad a abstención técnica**

## 🛠️ Tecnologías Utilizadas

### Frontend
- HTML5
- CSS3 (Variables CSS, Flexbox, Grid)
- JavaScript (ES6+)
- Responsive Design

### Seguridad
- Content Security Policy
- HTTPS/TLS
- Input Sanitization
- Rate Limiting
- CSRF Protection

### Backend (Modelo de Simulación)
- Python 3.8+
- **NumPy** - Cálculos numéricos y simulaciones Monte Carlo
- **Pandas** - Procesamiento y análisis de datos de encuestas
- **SciPy** - Distribuciones estadísticas (logit-normal)
- **Matplotlib** - Visualización de resultados
- **Seaborn** - Gráficos estadísticos avanzados

### Metodología Estadística
- **Monte Carlo Simulation** (100,000 iteraciones)
- **Distribución Logit-Normal** con covarianza
- **Pooling de encuestas** con decaimiento temporal
- **Análisis de correlación** entre bloques ideológicos
- **Modelado de indecisos** con múltiples escenarios

## 📝 To-Do

- [x] Agregar resultados de simulación (Actualizado 21 enero 2026)
- [x] Crear modelo de simulación v2.1 con mejoras técnicas
- [x] Documentar metodología y cambios técnicos
- [ ] Implementar gráficos interactivos con D3.js o Plotly
- [ ] Agregar sistema de autenticación para administradores
- [ ] Crear dashboard para actualización de contenido
- [ ] Implementar analytics
- [ ] Agregar blog/noticias
- [ ] Optimizar performance (lazy loading, minificación)
- [ ] Agregar tests automatizados
- [ ] Configurar CI/CD

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 👤 Autor

**Agustín Gómez Meléndez**
Centro de Investigación en Opinión y Datos (CIODD)
Universidad de Costa Rica

## 📞 Contacto

Para consultas o colaboraciones, usar el formulario de contacto en el sitio web.

## ⚠️ Disclaimer

Este es un proyecto de análisis estadístico con fines educativos e informativos. Los resultados presentados no constituyen predicciones oficiales y no deben ser utilizados como base única para toma de decisiones.

## 🔗 Enlaces Útiles

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Content Security Policy Reference](https://content-security-policy.com/)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [SecurityHeaders.com](https://securityheaders.com/)
- [SSL Labs](https://www.ssllabs.com/)

---

**🔒 Sitio seguro con protección HTTPS y CSP** | **Made with ❤️ for secure web**

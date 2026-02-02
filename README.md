# 🗳️ Simulación Elecciones Presidenciales 2026

Landing page para compartir resultados de simulaciones y predicciones electorales basadas en modelos de Machine Learning desarrollados en Python.

## 📋 Descripción

Este proyecto presenta un sitio web estático y seguro diseñado para publicar análisis predictivos de las elecciones presidenciales 2026. El sitio implementa las mejores prácticas de seguridad web y ciberseguridad para proteger tanto el contenido como los usuarios.

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
├── index.html              # Página principal
├── .htaccess              # Configuración de seguridad Apache
├── README.md              # Documentación
├── .gitignore            # Archivos ignorados por Git
│
├── css/
│   └── styles.css        # Estilos del sitio
│
├── js/
│   ├── security.js       # Módulo de seguridad
│   └── main.js           # Lógica principal
│
├── assets/
│   └── images/           # Imágenes del sitio
│
└── config/
    └── security-headers.conf  # Configuración headers para varios servidores
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

## 📊 Agregar Resultados de Simulación

Para publicar resultados del modelo de Python:

1. Crear visualizaciones en Python (matplotlib, seaborn, plotly)
2. Exportar como imágenes o HTML interactivo
3. Agregar al directorio `assets/images/`
4. Actualizar la sección `#results` en `index.html`

Ejemplo de código Python para generar gráficos:

```python
import matplotlib.pyplot as plt
import pandas as pd

# Tu modelo de simulación
results = tu_modelo.predict()

# Crear visualización
plt.figure(figsize=(12, 6))
plt.plot(results)
plt.title('Simulación Elecciones 2026')
plt.savefig('assets/images/simulation_results.png')
```

## 📄 Documento post-electoral generado (10 páginas)

**[Ver documento completo (PDF)](simulacion_cr2026_v3_3_postelectoral.pdf)**

### Contenido del análisis

**1. Resultados oficiales TSE**
- Laura Fernández: **48.33%** (1,156,735 votos)
- Álvaro Ramos: 33.42% (799,875 votos)
- Participación: 69.1%

**2. Evaluación del modelo v3.3**

| Aspecto | Calificación |
|---------|--------------|
| Predicción principal (victoria 1ª ronda) | ✅ **CORRECTA** |
| Calibración de incertidumbre | ✅ **CORRECTA** (resultado en IC 90%) |
| Proyección media Laura | ⚠️ Subestimó 4.2 pp |
| Predicción candidatos menores | ❌ Error masivo en Ramos |
| Módulo aprobación presidencial | ⚠️ Dirección correcta, magnitud insuficiente |

**3. Lecciones metodológicas**
- El modelo cumplió su objetivo de cuantificar probabilidad
- Las encuestas fallaron masivamente con Ramos (9% → 33%)
- El efecto Chaves fue mayor al modelado (+4.5 pp vs +2.5 pp)
- La "era de fragmentación" no aplicó: concentración bipartidista del 81.75%

**4. Contexto histórico**
- Primera victoria en 1ª ronda desde 2010 (16 años)
- Cuarto mejor resultado desde 1982
- Ruptura con patrón de fragmentación 2014-2022

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

### Backend (para modelo Python)
- Python 3.x
- Pandas
- NumPy
- Scikit-learn
- Matplotlib/Seaborn

## 📝 To-Do

- [ ] Conectar formulario con backend real
- [ ] Agregar resultados de simulación
- [ ] Implementar gráficos interactivos
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

**Equipo de Simulación Elecciones 2026**

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

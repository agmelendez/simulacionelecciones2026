# 🔒 Política de Seguridad

## Reporte de Vulnerabilidades

Si descubres una vulnerabilidad de seguridad en este proyecto, por favor repórtala de manera responsable.

### Cómo Reportar

1. **NO** abras un issue público
2. Envía un correo a: [security@tudominio.com] (reemplazar con email real)
3. Incluye:
   - Descripción detallada de la vulnerabilidad
   - Pasos para reproducir
   - Impacto potencial
   - Sugerencias de corrección (si las tienes)

### Tiempo de Respuesta

- Confirmación inicial: 48 horas
- Actualización de estado: 7 días
- Corrección según severidad:
  - Crítica: 24-48 horas
  - Alta: 7 días
  - Media: 30 días
  - Baja: 90 días

## Características de Seguridad Implementadas

### 1. Protección contra XSS (Cross-Site Scripting)

#### Content Security Policy
```
default-src 'self'
script-src 'self' 'unsafe-inline'
style-src 'self' 'unsafe-inline'
img-src 'self' data: https:
frame-ancestors 'none'
```

#### Sanitización de Inputs
- Escape de caracteres HTML especiales
- Validación de patrones
- Limitación de longitud de campos
- Filtrado de caracteres de control

**Archivo:** `js/security.js` líneas 15-47

### 2. Protección contra Clickjacking

#### X-Frame-Options
```
X-Frame-Options: DENY
```

#### Frame Ancestors en CSP
```
frame-ancestors 'none'
```

#### JavaScript Frame Busting
```javascript
if (window.top !== window.self) {
    window.top.location = window.self.location;
}
```

**Archivo:** `js/security.js` líneas 112-117

### 3. Protección contra CSRF (Cross-Site Request Forgery)

#### Token Generation
```javascript
generateCSRFToken() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte =>
        byte.toString(16).padStart(2, '0')
    ).join('');
}
```

**Archivo:** `js/security.js` líneas 125-131

### 4. Rate Limiting

#### Configuración
- Máximo 5 intentos por minuto
- Ventana deslizante de 60 segundos
- Limpieza automática de registros antiguos

```javascript
rateLimiter: {
    maxAttempts: 5,
    timeWindow: 60000
}
```

**Archivo:** `js/security.js` líneas 64-96

### 5. Validación de Inputs

#### Email
```javascript
validateEmail(email) {
    const re = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i;
    return re.test(String(email).toLowerCase());
}
```

#### Texto Seguro
```javascript
validateSafeText(text) {
    const re = /^[a-zA-Z0-9\s.,;:!?¿¡áéíóúÁÉÍÓÚñÑüÜ\-()]+$/;
    return re.test(text);
}
```

**Archivo:** `js/security.js` líneas 33-47

### 6. HTTPS Enforcement

#### Server-side (.htaccess)
```apache
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
```

#### Client-side (JavaScript)
```javascript
if (location.protocol !== 'https:' &&
    location.hostname !== 'localhost') {
    location.replace(`https:${location.href.substring(
        location.protocol.length
    )}`);
}
```

**Archivo:** `js/security.js` líneas 119-123

### 7. Strict Transport Security (HSTS)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Archivo:** `.htaccess` línea 35

### 8. Protección de Archivos Sensibles

#### Denegación de acceso
```apache
<FilesMatch "\.(git|gitignore|htaccess|env|config)$">
    Require all denied
</FilesMatch>
```

**Archivo:** `.htaccess` líneas 48-50

### 9. Headers de Seguridad

#### Implementados
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

**Archivo:** `.htaccess` líneas 15-38

### 10. Input Cleaning

```javascript
cleanInput(input, maxLength = 1000) {
    let cleaned = input.trim().slice(0, maxLength);
    cleaned = cleaned.replace(/[\x00-\x1F\x7F]/g, '');
    cleaned = this.escapeHTML(cleaned);
    return cleaned;
}
```

**Archivo:** `js/security.js` líneas 49-62

## Configuración de Seguridad Recomendada

### Servidor Web

#### Apache
1. Habilitar módulos necesarios:
```bash
a2enmod rewrite
a2enmod headers
a2enmod ssl
```

2. Configurar SSL con certificado válido
3. Usar el archivo `.htaccess` incluido

#### Nginx
Ver `config/security-headers.conf` para configuración completa

### Certificado SSL/TLS

#### Let's Encrypt (Recomendado)
```bash
sudo apt-get install certbot
sudo certbot --apache -d tudominio.com
```

#### Configuración TLS Recomendada
- TLS 1.2 o superior
- Deshabilitar TLS 1.0 y 1.1
- Cipher suites fuertes
- OCSP Stapling habilitado

### Firewall

#### UFW (Ubuntu/Debian)
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### firewalld (CentOS/RHEL)
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## Pruebas de Seguridad

### Herramientas Recomendadas

#### 1. SecurityHeaders.com
```
https://securityheaders.com/?q=tudominio.com
```
Objetivo: A+ rating

#### 2. SSL Labs
```
https://www.ssllabs.com/ssltest/analyze.html?d=tudominio.com
```
Objetivo: A+ rating

#### 3. Mozilla Observatory
```
https://observatory.mozilla.org/analyze/tudominio.com
```
Objetivo: 90+ score

#### 4. OWASP ZAP
```bash
zap-cli quick-scan --self-contained \
    --start-options '-config api.disablekey=true' \
    https://tudominio.com
```

#### 5. Nikto
```bash
nikto -h https://tudominio.com -ssl
```

### Testing Manual

#### XSS Testing
```javascript
// Intentar inyectar script en formulario
<script>alert('XSS')</script>
<img src=x onerror=alert('XSS')>
```
**Esperado:** Input sanitizado, script no ejecutado

#### CSRF Testing
```javascript
// Intentar enviar formulario sin token
fetch('/api/contact', {
    method: 'POST',
    body: JSON.stringify({name: 'test'})
})
```
**Esperado:** Solicitud rechazada

#### Clickjacking Testing
```html
<!-- Intentar cargar sitio en iframe -->
<iframe src="https://tudominio.com"></iframe>
```
**Esperado:** Frame bloqueado

## Actualizaciones de Seguridad

### Dependencias
- Revisar dependencias mensualmente
- Actualizar bibliotecas con vulnerabilidades conocidas
- Suscribirse a alertas de seguridad

### Monitoreo
- Revisar logs regularmente
- Configurar alertas para actividad sospechosa
- Realizar auditorías trimestrales

## Mejores Prácticas

### Para Desarrolladores

1. **Nunca confíes en el input del usuario**
   - Siempre validar y sanitizar
   - Usar whitelist en lugar de blacklist

2. **Principio de mínimo privilegio**
   - Dar solo los permisos necesarios
   - No ejecutar con privilegios elevados

3. **Defensa en profundidad**
   - Múltiples capas de seguridad
   - No depender de una sola medida

4. **Mantener actualizado**
   - Sistema operativo
   - Servidor web
   - Bibliotecas y dependencias

5. **Logging y monitoreo**
   - Registrar intentos de acceso
   - Monitorear patrones anormales
   - Revisar logs regularmente

### Para Administradores

1. **Backup regular**
   - Automatizar backups
   - Almacenar en ubicación segura
   - Probar restauración

2. **Firewall configurado**
   - Solo puertos necesarios abiertos
   - Reglas de filtrado apropiadas

3. **Actualizaciones de seguridad**
   - Aplicar parches prontamente
   - Probar en ambiente de staging

4. **Monitoreo activo**
   - Alertas configuradas
   - Revisión de logs
   - Detección de intrusiones

## Checklist de Seguridad

- [x] HTTPS habilitado
- [x] Certificado SSL válido
- [x] HSTS configurado
- [x] CSP implementado
- [x] X-Frame-Options configurado
- [x] X-Content-Type-Options configurado
- [x] X-XSS-Protection habilitado
- [x] Referrer-Policy configurado
- [x] Permissions-Policy configurado
- [x] Rate limiting implementado
- [x] Input validation implementada
- [x] Input sanitization implementada
- [x] CSRF protection implementada
- [x] Archivos sensibles protegidos
- [x] Directory listing deshabilitado
- [x] Error messages genéricos
- [x] Server information oculta

## Recursos Adicionales

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

## Contacto de Seguridad

Para reportes de seguridad: [security@tudominio.com]

PGP Key: [ID de clave PGP si aplica]

---

Última actualización: 2026-01-08

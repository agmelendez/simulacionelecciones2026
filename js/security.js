/**
 * Módulo de Seguridad
 * Implementa funciones de sanitización y protección contra ataques comunes
 */

const Security = {
    /**
     * Sanitiza texto para prevenir XSS
     * @param {string} str - String a sanitizar
     * @returns {string} - String sanitizado
     */
    sanitizeHTML(str) {
        if (typeof str !== 'string') return '';

        const temp = document.createElement('div');
        temp.textContent = str;
        return temp.innerHTML;
    },

    /**
     * Escapa caracteres especiales HTML
     * @param {string} text - Texto a escapar
     * @returns {string} - Texto escapado
     */
    escapeHTML(text) {
        if (typeof text !== 'string') return '';

        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;',
        };

        return text.replace(/[&<>"'/]/g, (char) => map[char]);
    },

    /**
     * Valida email
     * @param {string} email - Email a validar
     * @returns {boolean} - True si es válido
     */
    validateEmail(email) {
        const re = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i;
        return re.test(String(email).toLowerCase());
    },

    /**
     * Valida que el texto solo contenga caracteres seguros
     * @param {string} text - Texto a validar
     * @returns {boolean} - True si es válido
     */
    validateSafeText(text) {
        // Permite letras, números, espacios y puntuación común
        const re = /^[a-zA-Z0-9\s.,;:!?¿¡áéíóúÁÉÍÓÚñÑüÜ\-()]+$/;
        return re.test(text);
    },

    /**
     * Limpia y valida input de formulario
     * @param {string} input - Input a limpiar
     * @param {number} maxLength - Longitud máxima
     * @returns {string} - Input limpio
     */
    cleanInput(input, maxLength = 1000) {
        if (typeof input !== 'string') return '';

        // Trim y limitar longitud
        let cleaned = input.trim().slice(0, maxLength);

        // Remover caracteres de control
        cleaned = cleaned.replace(/[\x00-\x1F\x7F]/g, '');

        // Sanitizar HTML
        cleaned = this.escapeHTML(cleaned);

        return cleaned;
    },

    /**
     * Rate limiting simple por cliente
     */
    rateLimiter: {
        attempts: new Map(),
        maxAttempts: 5,
        timeWindow: 60000, // 1 minuto

        /**
         * Verifica si se puede realizar la acción
         * @param {string} key - Identificador único
         * @returns {boolean} - True si está permitido
         */
        canProceed(key) {
            const now = Date.now();
            const userAttempts = this.attempts.get(key) || [];

            // Filtrar intentos antiguos
            const recentAttempts = userAttempts.filter(
                timestamp => now - timestamp < this.timeWindow
            );

            if (recentAttempts.length >= this.maxAttempts) {
                return false;
            }

            recentAttempts.push(now);
            this.attempts.set(key, recentAttempts);

            return true;
        },

        /**
         * Limpia entradas antiguas
         */
        cleanup() {
            const now = Date.now();
            for (const [key, attempts] of this.attempts.entries()) {
                const recentAttempts = attempts.filter(
                    timestamp => now - timestamp < this.timeWindow
                );

                if (recentAttempts.length === 0) {
                    this.attempts.delete(key);
                } else {
                    this.attempts.set(key, recentAttempts);
                }
            }
        }
    },

    /**
     * Previene clickjacking verificando que la página no esté en iframe
     */
    preventFraming() {
        if (window.top !== window.self) {
            console.warn('Posible intento de clickjacking detectado');
            window.top.location = window.self.location;
        }
    },

    /**
     * Asegura que se use HTTPS
     */
    enforceHTTPS() {
        if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            console.warn('Redirigiendo a HTTPS para seguridad');
            location.replace(`https:${location.href.substring(location.protocol.length)}`);
        }
    },

    /**
     * Genera un token CSRF simple
     * @returns {string} - Token CSRF
     */
    generateCSRFToken() {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    },

    /**
     * Valida URL para prevenir open redirect
     * @param {string} url - URL a validar
     * @returns {boolean} - True si es segura
     */
    validateURL(url) {
        try {
            const parsed = new URL(url, window.location.origin);
            // Solo permitir URLs del mismo origen
            return parsed.origin === window.location.origin;
        } catch {
            return false;
        }
    },

    /**
     * Protección contra ataques de timing
     * @param {string} a - Primera string
     * @param {string} b - Segunda string
     * @returns {boolean} - True si son iguales
     */
    constantTimeCompare(a, b) {
        if (a.length !== b.length) return false;

        let result = 0;
        for (let i = 0; i < a.length; i++) {
            result |= a.charCodeAt(i) ^ b.charCodeAt(i);
        }

        return result === 0;
    },

    /**
     * Inicializa todas las medidas de seguridad
     */
    initialize() {
        console.log('🔒 Módulo de seguridad inicializado');

        // Prevenir framing
        this.preventFraming();

        // Forzar HTTPS
        this.enforceHTTPS();

        // Limpiar rate limiter periódicamente
        setInterval(() => {
            this.rateLimiter.cleanup();
        }, 60000);

        // Deshabilitar click derecho en producción (opcional)
        // document.addEventListener('contextmenu', (e) => e.preventDefault());

        // Deshabilitar algunas teclas de desarrollo (opcional)
        // document.addEventListener('keydown', (e) => {
        //     if (e.key === 'F12' || (e.ctrlKey && e.shiftKey && e.key === 'I')) {
        //         e.preventDefault();
        //     }
        // });
    }
};

// Auto-inicialización cuando el DOM está listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => Security.initialize());
} else {
    Security.initialize();
}

// Exportar para uso global
window.Security = Security;

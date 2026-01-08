/**
 * Script Principal
 * Maneja la interactividad del sitio con medidas de seguridad
 */

// Esperar a que el DOM y el módulo de seguridad estén listos
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Aplicación inicializada');

    // Inicializar componentes
    initSmoothScroll();
    initContactForm();
    initAnimations();

    /**
     * Smooth scroll para navegación
     */
    function initSmoothScroll() {
        const navLinks = document.querySelectorAll('.nav-menu a[href^="#"]');

        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();

                const targetId = this.getAttribute('href');
                if (!targetId || targetId === '#') return;

                const targetSection = document.querySelector(targetId);
                if (!targetSection) return;

                // Smooth scroll
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });

                // Actualizar URL sin recargar
                if (history.pushState) {
                    history.pushState(null, null, targetId);
                }
            });
        });
    }

    /**
     * Manejo del formulario de contacto con validación segura
     */
    function initContactForm() {
        const form = document.getElementById('contactForm');
        if (!form) return;

        form.addEventListener('submit', function(e) {
            e.preventDefault();

            // Rate limiting
            if (!Security.rateLimiter.canProceed('contact-form')) {
                showMessage('Has enviado demasiados mensajes. Por favor espera un momento.', 'warning');
                return;
            }

            // Validar y sanitizar inputs
            const formData = validateAndSanitizeForm(form);

            if (!formData) {
                showMessage('Por favor, corrige los errores en el formulario.', 'error');
                return;
            }

            // Simular envío (aquí iría la llamada al backend)
            submitForm(formData);
        });

        // Validación en tiempo real
        const inputs = form.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });

            input.addEventListener('input', function() {
                // Limpiar mensaje de error al escribir
                const errorMsg = this.parentElement.querySelector('.error-message');
                if (errorMsg) {
                    errorMsg.remove();
                }
            });
        });
    }

    /**
     * Valida y sanitiza todos los campos del formulario
     * @param {HTMLFormElement} form - Formulario a validar
     * @returns {Object|null} - Datos sanitizados o null si hay errores
     */
    function validateAndSanitizeForm(form) {
        const nameInput = form.querySelector('#name');
        const emailInput = form.querySelector('#email');
        const messageInput = form.querySelector('#message');

        let isValid = true;

        // Validar nombre
        const name = nameInput.value.trim();
        if (name.length < 2 || name.length > 100) {
            showFieldError(nameInput, 'El nombre debe tener entre 2 y 100 caracteres');
            isValid = false;
        } else if (!Security.validateSafeText(name)) {
            showFieldError(nameInput, 'El nombre contiene caracteres no permitidos');
            isValid = false;
        }

        // Validar email
        const email = emailInput.value.trim();
        if (!Security.validateEmail(email)) {
            showFieldError(emailInput, 'Por favor ingresa un email válido');
            isValid = false;
        }

        // Validar mensaje
        const message = messageInput.value.trim();
        if (message.length < 10 || message.length > 1000) {
            showFieldError(messageInput, 'El mensaje debe tener entre 10 y 1000 caracteres');
            isValid = false;
        }

        if (!isValid) return null;

        // Sanitizar y retornar datos
        return {
            name: Security.cleanInput(name, 100),
            email: Security.cleanInput(email, 100),
            message: Security.cleanInput(message, 1000),
            timestamp: new Date().toISOString(),
            csrfToken: Security.generateCSRFToken()
        };
    }

    /**
     * Valida un campo individual
     * @param {HTMLInputElement} field - Campo a validar
     * @returns {boolean} - True si es válido
     */
    function validateField(field) {
        const value = field.value.trim();

        // Limpiar errores previos
        const existingError = field.parentElement.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }

        // Validación según el tipo de campo
        if (field.hasAttribute('required') && !value) {
            showFieldError(field, 'Este campo es requerido');
            return false;
        }

        if (field.type === 'email' && value && !Security.validateEmail(value)) {
            showFieldError(field, 'Email inválido');
            return false;
        }

        if (field.maxLength > 0 && value.length > field.maxLength) {
            showFieldError(field, `Máximo ${field.maxLength} caracteres`);
            return false;
        }

        return true;
    }

    /**
     * Muestra error en un campo específico
     * @param {HTMLInputElement} field - Campo con error
     * @param {string} message - Mensaje de error
     */
    function showFieldError(field, message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.color = '#ef4444';
        errorDiv.style.fontSize = '0.875rem';
        errorDiv.style.marginTop = '0.25rem';
        errorDiv.textContent = message;

        field.parentElement.appendChild(errorDiv);
        field.style.borderColor = '#ef4444';
    }

    /**
     * Simula envío del formulario
     * @param {Object} formData - Datos del formulario
     */
    function submitForm(formData) {
        // Mostrar indicador de carga
        const submitBtn = document.querySelector('.contact-form button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Enviando...';
        submitBtn.disabled = true;

        // Simular llamada al servidor
        setTimeout(() => {
            console.log('Datos del formulario (sanitizados):', formData);

            // En producción, aquí iría:
            // fetch('/api/contact', {
            //     method: 'POST',
            //     headers: {
            //         'Content-Type': 'application/json',
            //         'X-CSRF-Token': formData.csrfToken
            //     },
            //     body: JSON.stringify(formData)
            // })
            // .then(response => response.json())
            // .then(data => { ... })

            // Mostrar mensaje de éxito
            showMessage('¡Mensaje enviado exitosamente! Te contactaremos pronto.', 'success');

            // Limpiar formulario
            document.getElementById('contactForm').reset();

            // Restaurar botón
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }, 1500);
    }

    /**
     * Muestra mensaje al usuario
     * @param {string} message - Mensaje a mostrar
     * @param {string} type - Tipo de mensaje (success, error, warning, info)
     */
    function showMessage(message, type = 'info') {
        // Sanitizar mensaje
        const safeMessage = Security.escapeHTML(message);

        // Crear elemento de alerta
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} fade-in`;
        alert.innerHTML = `<strong>${safeMessage}</strong>`;

        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };

        alert.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            padding: 1rem 1.5rem;
            background-color: white;
            border-left: 4px solid ${colors[type]};
            border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            z-index: 9999;
            max-width: 400px;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(alert);

        // Remover después de 5 segundos
        setTimeout(() => {
            alert.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    }

    /**
     * Inicializa animaciones al hacer scroll
     */
    function initAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Observar elementos para animar
        const elementsToAnimate = document.querySelectorAll('.feature-card, .alert, .results-placeholder');
        elementsToAnimate.forEach(el => observer.observe(el));
    }

    // Agregar estilos para animaciones
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }

        .error-message {
            animation: shake 0.3s ease-in-out;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-5px); }
            75% { transform: translateX(5px); }
        }
    `;
    document.head.appendChild(style);

    console.log('✅ Todos los componentes inicializados correctamente');
});

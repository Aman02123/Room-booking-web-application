// ==================== UTILITY FUNCTIONS ====================

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 0
    }).format(amount);
}

// Format date
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-IN', options);
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `flash-message flash-${type}`;
    notification.textContent = message;
    
    let container = document.querySelector('.flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// ==================== SMOOTH SCROLLING ====================

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// ==================== NAVBAR SCROLL EFFECT ====================

let lastScroll = 0;
const navbar = document.querySelector('.navbar');

if (navbar) {
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            navbar.style.boxShadow = '0 4px 20px rgba(0,0,0,0.2)';
        } else {
            navbar.style.boxShadow = '0 4px 16px rgba(0,0,0,0.12)';
        }
        
        lastScroll = currentScroll;
    });
}

// ==================== FORM VALIDATION ====================

// Email validation
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Phone validation
function validatePhone(phone) {
    const re = /^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$/;
    return re.test(phone);
}

// Password strength checker
function checkPasswordStrength(password) {
    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (password.match(/[a-z]+/)) strength++;
    if (password.match(/[A-Z]+/)) strength++;
    if (password.match(/[0-9]+/)) strength++;
    if (password.match(/[$@#&!]+/)) strength++;
    
    return strength;
}

// ==================== DATE PICKER CONSTRAINTS ====================

// Set minimum date for date inputs
function setMinimumDates() {
    const today = new Date().toISOString().split('T')[0];
    const dateInputs = document.querySelectorAll('input[type="date"]');
    
    dateInputs.forEach(input => {
        if (!input.hasAttribute('min')) {
            input.setAttribute('min', today);
        }
    });
}

// Call on page load
document.addEventListener('DOMContentLoaded', setMinimumDates);

// ==================== BOOKING FORM HANDLERS ====================

// Calculate nights and total price
function calculateBookingPrice(checkIn, checkOut, pricePerNight) {
    const date1 = new Date(checkIn);
    const date2 = new Date(checkOut);
    const nights = Math.ceil((date2 - date1) / (1000 * 60 * 60 * 24));
    
    if (nights <= 0) {
        return { nights: 0, total: 0, valid: false };
    }
    
    return {
        nights: nights,
        total: nights * pricePerNight,
        valid: true
    };
}

// ==================== PAYMENT METHOD HANDLERS ====================

// Handle credit card number formatting
function formatCardNumber(value) {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const matches = v.match(/\d{4,16}/g);
    const match = (matches && matches[0]) || '';
    const parts = [];
    
    for (let i = 0, len = match.length; i < len; i += 4) {
        parts.push(match.substring(i, i + 4));
    }
    
    if (parts.length) {
        return parts.join(' ');
    } else {
        return value;
    }
}

// Format expiry date
function formatExpiryDate(value) {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    
    if (v.length >= 2) {
        return v.substring(0, 2) + '/' + v.substring(2, 4);
    }
    
    return v;
}

// Add card formatting listeners if card form exists
const cardNumberInput = document.querySelector('input[placeholder*="1234"]');
if (cardNumberInput) {
    cardNumberInput.addEventListener('input', function(e) {
        this.value = formatCardNumber(this.value);
    });
}

const expiryInput = document.querySelector('input[placeholder*="MM/YY"]');
if (expiryInput) {
    expiryInput.addEventListener('input', function(e) {
        this.value = formatExpiryDate(this.value);
    });
}

// ==================== LOADING INDICATOR ====================

function showLoading() {
    if (!document.getElementById('loadingOverlay')) {
        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        `;
        
        const spinner = document.createElement('div');
        spinner.style.cssText = `
            width: 50px;
            height: 50px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #C9A962;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        `;
        
        overlay.appendChild(spinner);
        document.body.appendChild(overlay);
        
        // Add spin animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

// ==================== IMAGE LAZY LOADING ====================

if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    });
    
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
}

// ==================== ANIMATIONS ====================

// Fade in on scroll
function fadeInOnScroll() {
    const elements = document.querySelectorAll('.fade-in-on-scroll');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });
    
    elements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

document.addEventListener('DOMContentLoaded', fadeInOnScroll);

// ==================== LOCAL STORAGE ====================

// Save form data to local storage
function saveFormData(formId, data) {
    try {
        localStorage.setItem(formId, JSON.stringify(data));
    } catch (e) {
        console.error('Error saving form data:', e);
    }
}

// Load form data from local storage
function loadFormData(formId) {
    try {
        const data = localStorage.getItem(formId);
        return data ? JSON.parse(data) : null;
    } catch (e) {
        console.error('Error loading form data:', e);
        return null;
    }
}

// Clear form data from local storage
function clearFormData(formId) {
    try {
        localStorage.removeItem(formId);
    } catch (e) {
        console.error('Error clearing form data:', e);
    }
}

// ==================== KEYBOARD SHORTCUTS ====================

document.addEventListener('keydown', function(e) {
    // Close modal on Escape key
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (modal.style.display === 'flex') {
                modal.style.display = 'none';
            }
        });
    }
});

// ==================== PRINT BOOKING DETAILS ====================

function printBookingDetails() {
    window.print();
}

// ==================== COPY TO CLIPBOARD ====================

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy:', err);
            showNotification('Failed to copy to clipboard', 'error');
        });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            document.execCommand('copy');
            showNotification('Copied to clipboard!', 'success');
        } catch (err) {
            console.error('Failed to copy:', err);
            showNotification('Failed to copy to clipboard', 'error');
        }
        
        document.body.removeChild(textarea);
    }
}

// ==================== FORM AUTO-SAVE ====================

// Auto-save form data every 30 seconds
let autoSaveInterval;

function startAutoSave(formElement, formId) {
    if (autoSaveInterval) {
        clearInterval(autoSaveInterval);
    }
    
    autoSaveInterval = setInterval(() => {
        const formData = new FormData(formElement);
        const data = {};
        
        formData.forEach((value, key) => {
            data[key] = value;
        });
        
        saveFormData(formId, data);
    }, 30000); // 30 seconds
}

function stopAutoSave() {
    if (autoSaveInterval) {
        clearInterval(autoSaveInterval);
        autoSaveInterval = null;
    }
}

// ==================== ACCESSIBILITY ====================

// Add skip to main content link
function addSkipLink() {
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.textContent = 'Skip to main content';
    skipLink.className = 'skip-link';
    skipLink.style.cssText = `
        position: absolute;
        top: -40px;
        left: 0;
        background: #C9A962;
        color: #1A1D29;
        padding: 8px;
        text-decoration: none;
        z-index: 10000;
    `;
    
    skipLink.addEventListener('focus', function() {
        this.style.top = '0';
    });
    
    skipLink.addEventListener('blur', function() {
        this.style.top = '-40px';
    });
    
    document.body.insertBefore(skipLink, document.body.firstChild);
}

// Call on page load
document.addEventListener('DOMContentLoaded', addSkipLink);

// ==================== ERROR HANDLING ====================

window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
});

// ==================== CONSOLE MESSAGE ====================

console.log('%cHotel Luxe', 'font-size: 24px; font-weight: bold; color: #C9A962;');
console.log('%cBuilt with care for exceptional user experience', 'font-size: 14px; color: #666;');
console.log('%c© 2025 Hotel Luxe. All rights reserved.', 'font-size: 12px; color: #999;');
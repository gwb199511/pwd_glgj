export function showTooltip(message, targetElement, tooltipId) {
    const tooltip = document.getElementById(tooltipId);
    const tooltipMessage = tooltip.querySelector('.tooltip-message');
    tooltipMessage.textContent = message;
    
    const rect = targetElement.getBoundingClientRect();
    tooltip.style.left = `${rect.left}px`;
    tooltip.style.top = `${rect.bottom + window.scrollY + 5}px`;
    
    tooltip.style.display = 'flex';
    tooltip.style.animation = 'bounceInOutFade 5s ease-in-out';
    targetElement.classList.add('highlight');

    setTimeout(() => {
        hideTooltip(tooltipId);
    }, 5000);
}

export function hideTooltip(tooltipId) {
    const tooltip = document.getElementById(tooltipId);
    if (tooltip) {
        tooltip.style.animation = 'none';
        tooltip.style.display = 'none';
    }
    document.querySelectorAll('.highlight').forEach(el => el.classList.remove('highlight'));
}

export function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.textContent = message;
    alertDiv.className = `alert alert-${type}`;
    Object.assign(alertDiv.style, {
        position: 'fixed',
        top: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        padding: '10px 20px',
        borderRadius: '5px',
        backgroundColor: type === 'error' ? '#f8d7da' : '#d4edda',
        color: type === 'error' ? '#721c24' : '#155724',
        border: type === 'error' ? '1px solid #f5c6cb' : '1px solid #c3e6cb',
        zIndex: '1000',
        animation: 'fadeInOut 5s ease-in-out'
    });

    document.body.appendChild(alertDiv);

    setTimeout(() => alertDiv.remove(), 5000);
}

export function showPasswordModal() {
    const modal = document.getElementById('passwordModal');
    if (modal) {
        modal.style.display = 'block';
    } else {
        console.error('Password modal not found');
    }
}

export function hidePasswordModal() {
    const modal = document.getElementById('passwordModal');
    if (modal) {
        modal.style.display = 'none';
        document.getElementById('editPassword').value = ''; // 清空密码输入框
    }
    console.log("Password modal hidden");
}

export function showErrorNotification(message) {
    const notification = document.createElement('div');
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #ffcccc;
        color: #990000;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        z-index: 1000;
    `;
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.remove();
    }, 5000);
}
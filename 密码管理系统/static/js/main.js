import { initServerManagement, enterEditMode, exitEditMode, verifyPassword } from './serverManagement.js';
import { initHistoryManagement } from './historyManagement.js';
import { setupBackgroundChange } from './backgroundChange.js';
import { showErrorNotification, hidePasswordModal } from './uiInteractions.js';

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded');
    initServerManagement();
    initHistoryManagement();
    setupBackgroundChange();
    setupGlobalErrorHandler();
    setupEditModeButton();
});

function setupEditModeButton() {
    const editModeButton = document.getElementById('editModeButton');
    const exitEditModeButton = document.getElementById('exitEditModeButton');
    const confirmPasswordButton = document.getElementById('confirmPasswordButton');
    const cancelPasswordButton = document.getElementById('cancelPasswordButton');

    editModeButton?.addEventListener('click', enterEditMode);
    exitEditModeButton?.addEventListener('click', exitEditMode);
    confirmPasswordButton?.addEventListener('click', () => {
        const password = document.getElementById('editPassword').value;
        verifyPassword(password);
    });
    cancelPasswordButton?.addEventListener('click', hidePasswordModal);
}

function setupGlobalErrorHandler() {
    const handleError = (event) => {
        const isSSLError = event.message?.includes('SSL');
        console.warn(isSSLError ? 'SSL error occurred:' : 'Unhandled error:', event.message || event.reason);
        showErrorNotification('发生了一个错误，但不影响主要功能。');
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleError);
}
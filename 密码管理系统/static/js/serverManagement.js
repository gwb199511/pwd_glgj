import { showTooltip, hideTooltip, showAlert, showPasswordModal, hidePasswordModal } from './uiInteractions.js';

let currentPage = 1;
const itemsPerPage = 20;
let allServers = [];
let filteredServers = [];
let isSearchMode = false;

export function initServerManagement() {
    const addServerForm = document.getElementById('addServerForm');
    addServerForm.addEventListener('submit', handleServerSubmit);
    getServers();

    if (localStorage.getItem('editMode') === 'true') enableEditMode();

    document.querySelector('.generate-button').addEventListener('click', generatePasswordsForAll);
    document.querySelector('.confirm-button').addEventListener('click', confirmUpdates);
    setupSearch();

    const exitEditModeButton = document.getElementById('exitEditModeButton');
    exitEditModeButton?.addEventListener('click', exitEditMode);
}

export function getServers() {
    axios.get('/servers')
        .then(response => {
            allServers = response.data;
            isSearchMode ? performSearch() : displayServerList(allServers);
        })
        .catch(error => console.error('Error:', error));
}

function handleServerSubmit(e) {
    e.preventDefault();
    const ipInput = document.getElementById('ip');
    if (!ipInput.value.trim()) return showTooltip('请填写 IP 地址', ipInput, 'ipTooltip');
    if (!document.getElementById('username').value.trim()) return showTooltip('请填写用户名', document.getElementById('username'), 'usernameTooltip');
    if (!document.getElementById('password').value.trim()) return showTooltip('请填写密码', document.getElementById('password'), 'passwordTooltip');

    const serverData = {
        ip: ipInput.value,
        username: document.getElementById('username').value,
        password: document.getElementById('password').value,
        purpose: document.getElementById('purpose').value
    };

    axios.post('/servers', serverData)
        .then(response => {
            showAlert(response.data.message, 'success');
            getServers();
            e.target.reset();
            hideTooltip('ipTooltip');
        })
        .catch(error => {
            if (error.response?.status === 409) {
                showTooltip('该服务器地址已存在，无法重复添加。', ipInput, 'ipTooltip');
            } else {
                console.error('Error:', error);
                showAlert('添加服务器时发生错误', 'error');
            }
        });
}

export function enterEditMode() {
    localStorage.getItem('editMode') !== 'true' ? showPasswordModal() : enableEditMode();
}

export function exitEditMode() {
    localStorage.setItem('editMode', 'false');
    updateEditModeVisibility();
    showAlert('已退出编辑模式', 'success');
}

export function generatePasswordsForAll() {
    const selectedServers = document.querySelectorAll('#serverList tbody tr input.server-select:checked');
    if (selectedServers.length === 0) return showAlert('请选择至少一台服务器', 'error');

    selectedServers.forEach(checkbox => {
        const serverId = checkbox.id.split('-')[1];
        generatePasswordForServer(serverId);
    });
    showAlert('已为选中的服务器生成新密码，点击确认修改。', 'success');
}

function generatePasswordForServer(serverId) {
    axios.get('/generate_password')
        .then(response => {
            const newPasswordInput = document.getElementById(`new-password-${serverId}`);
            newPasswordInput.value = response.data.password;
            newPasswordInput.style.display = 'block';
            newPasswordInput.disabled = false;
            newPasswordInput.classList.add('password-flash');
            setTimeout(() => newPasswordInput.classList.remove('password-flash'), 6000);
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert(`为服务器 ${serverId} 生成密码时出错`, 'error');
        });
}

export function confirmUpdates() {
    const selectedServers = document.querySelectorAll('#serverList tbody tr input.server-select:checked');
    if (selectedServers.length === 0) return showAlert('请选择至少一台服务器进行修改', 'error');

    let hasNewPassword = false;
    let updatedServers = 0;
    const totalSelected = selectedServers.length;

    selectedServers.forEach(checkbox => {
        const row = checkbox.closest('tr');
        const serverId = row.querySelector('td:nth-child(2)').textContent;
        const newPassword = row.querySelector(`#new-password-${serverId}`).value;

        if (newPassword) {
            hasNewPassword = true;
            const serverData = {
                ip: row.querySelector(`#ip-${serverId}`).value,
                username: row.querySelector(`#username-${serverId}`).value,
                password: row.querySelector(`#password-${serverId}`).value,
                purpose: row.querySelector(`#purpose-${serverId}`).value,
                new_password: newPassword
            };

            axios.put(`/servers/${serverId}`, serverData)
                .then(response => {
                    updatedServers++;
                    const passwordInput = row.querySelector(`#password-${serverId}`);
                    passwordInput.value = newPassword;
                    passwordInput.classList.add('password-flash');
                    setTimeout(() => passwordInput.classList.remove('password-flash'), 6000);

                    const newPasswordInput = row.querySelector(`#new-password-${serverId}`);
                    newPasswordInput.value = '';
                    newPasswordInput.style.display = 'none';

                    if (updatedServers === totalSelected) showAlert(`成功更新 ${updatedServers} 台服务器的密码`, 'success');
                })
                .catch(error => {
                    console.error('Error:', error);
                    showAlert(`更新服务器 ${serverId} 失败，请检查输入并重试`, 'error');
                });
        }
    });

    if (!hasNewPassword) showAlert('请生成新的密码,再确认修改', 'error');
}

function updateEditModeVisibility() {
    const editMode = localStorage.getItem('editMode') === 'true';
    const editModeContent = document.getElementById('editModeContent');
    const editModeButtons = document.getElementById('editModeButtons');
    const exitEditModeButton = document.getElementById('exitEditModeButton');
    const editModeButton = document.getElementById('editModeButton');
    const exitEditModeContainer = document.getElementById('exitEditModeContainer');

    editModeContent.style.display = editMode ? 'block' : 'none';
    editModeButtons.style.display = editMode ? 'flex' : 'none';
    exitEditModeButton.style.display = editMode ? 'block' : 'none';
    editModeButton.style.display = editMode ? 'none' : 'block';
    exitEditModeContainer.style.display = editMode ? 'block' : 'none';

    document.querySelectorAll('#serverList input[type="text"]').forEach(input => {
        input.disabled = !editMode;
    });
}

export function verifyPassword(password) {
    axios.post('/verify_password', { password })
        .then(response => {
            if (response.data.message === "密码验证成功") {
                hidePasswordModal();
                enableEditMode();
                showAlert('已进入编辑模式', 'success');
            } else {
                showAlert("密码错误，请重试", 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert("验证过程中出现错误，请重试", 'error');
        });
}

function enableEditMode() {
    localStorage.setItem('editMode', 'true');
    updateEditModeVisibility();
    console.log("Entered edit mode");
}

function displayServerList(servers) {
    const serverList = document.querySelector('#serverList tbody');
    serverList.innerHTML = '';

    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageServers = servers.slice(startIndex, endIndex);

    const rows = pageServers.map(server => `
        <tr>
            <td><input type="checkbox" id="select-${server.id}" class="server-select"></td>
            <td>${server.id}</td>
            <td><input type="text" value="${server.ip}" id="ip-${server.id}" disabled></td>
            <td><input type="text" value="${server.username}" id="username-${server.id}" disabled></td>
            <td class="password-cell">
                <input type="text" value="${server.password}" id="password-${server.id}" disabled>
            </td>
            <td><input type="text" value="${server.purpose}" id="purpose-${server.id}" disabled></td>
            <td><input type="text" id="new-password-${server.id}" placeholder="新密码" class="new-password-input" style="display: none;"></td>
        </tr>
    `).join('');

    serverList.innerHTML = rows || '<tr><td colspan="7">没有找到匹配的服务器</td></tr>';

    updatePagination(servers.length);
    updateEditModeVisibility();
}

function updatePagination(totalItems) {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    const pagination = document.querySelector('.pagination-container');
    pagination.innerHTML = '';

    if (totalPages > 1) {
        const prevButton = document.createElement('button');
        prevButton.textContent = '上一页';
        prevButton.onclick = () => changePage(currentPage - 1);
        prevButton.disabled = currentPage === 1;

        const pageInfo = document.createElement('span');
        pageInfo.className = 'page-info';
        pageInfo.textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页`;

        const nextButton = document.createElement('button');
        nextButton.textContent = '下一页';
        nextButton.onclick = () => changePage(currentPage + 1);
        nextButton.disabled = currentPage === totalPages;

        pagination.appendChild(prevButton);
        pagination.appendChild(pageInfo);
        pagination.appendChild(nextButton);
    }
}

function changePage(newPage) {
    currentPage = newPage;
    isSearchMode ? displayServerList(filteredServers) : displayServerList(allServers);
}

function setupSearch() {
    const searchButton = document.getElementById('searchButton');
    const searchInput = document.getElementById('searchInput');

    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') performSearch();
    });

    searchInput.addEventListener('input', function(e) {
        if (e.target.value === '') {
            isSearchMode = false;
            currentPage = 1;
            displayServerList(allServers);
        }
    });
}

function performSearch() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    filteredServers = allServers.filter(server => 
        server.ip.toLowerCase().includes(searchTerm) ||
        server.username.toLowerCase().includes(searchTerm) ||
        server.purpose.toLowerCase().includes(searchTerm)
    );
    isSearchMode = searchTerm !== '';
    currentPage = 1;
    displayServerList(filteredServers);
}
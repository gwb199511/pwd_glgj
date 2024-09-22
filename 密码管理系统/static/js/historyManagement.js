export function initHistoryManagement() {
    const historyButton = document.getElementById('historyButton');
    const popup = document.getElementById('historyPopup');
    if (historyButton && popup) {
        historyButton.addEventListener('click', (event) => {
            event.stopPropagation();
            showHistoryPopup(event);
        });

        const closeButton = popup.querySelector('.close');
        closeButton?.addEventListener('click', hideHistoryPopup);

        document.addEventListener('click', (event) => {
            if (!popup.contains(event.target) && event.target !== historyButton) {
                hideHistoryPopup();
            }
        });
    } else {
        console.error('History button or popup not found');
    }
}

function showHistoryPopup(event) {
    const popup = document.getElementById('historyPopup');
    const button = event.target;
    const buttonRect = button.getBoundingClientRect();
    const windowHeight = window.innerHeight;
    const windowWidth = window.innerWidth;

    Object.assign(popup.style, {
        left: `${buttonRect.left}px`,
        top: `${buttonRect.top}px`,
        width: `${buttonRect.width}px`,
        height: `${buttonRect.height}px`,
        display: 'block'
    });

    popup.offsetHeight;

    const finalWidth = Math.min(windowWidth * 0.9, 1200);
    const finalHeight = Math.min(windowHeight * 0.99, 900);
    const finalLeft = Math.max(5, Math.min(buttonRect.left, windowWidth - finalWidth - 5));
    const finalTop = Math.max(2, Math.min(buttonRect.bottom + 2, windowHeight - finalHeight - 2));

    Object.assign(popup.style, {
        width: `${finalWidth}px`,
        height: `${finalHeight}px`,
        left: `${finalLeft}px`,
        top: `${finalTop}px`
    });

    requestAnimationFrame(() => popup.classList.add('show'));

    loadOperationLogs(1);
}

function hideHistoryPopup() {
    const popup = document.getElementById('historyPopup');
    const button = document.getElementById('historyButton');
    const buttonRect = button.getBoundingClientRect();

    popup.classList.remove('show');
    popup.style.transition = 'all 0.3s ease-in';

    requestAnimationFrame(() => {
        Object.assign(popup.style, {
            width: `${buttonRect.width}px`,
            height: `${buttonRect.height}px`,
            left: `${buttonRect.left}px`,
            top: `${buttonRect.top}px`
        });

        popup.addEventListener('transitionend', () => {
            popup.style.display = 'none';
            popup.style.transition = '';
        }, { once: true });
    });
}

function loadOperationLogs(page) {
    axios.get(`/operation_logs?page=${page}&per_page=20`)
        .then(response => {
            const logsContainer = document.getElementById('logsContainer');
            logsContainer.innerHTML = response.data.logs.length ? '' : '<tr><td colspan="3" style="text-align: center;">暂无操作记录</td></tr>';
            response.data.logs.forEach(log => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td style="text-align: left;">${log.timestamp}</td>
                    <td style="text-align: left;">${log.operation_type}</td>
                    <td style="text-align: left;">${log.details}</td>
                `;
                logsContainer.appendChild(row);
            });
            updatePagination(response.data.current_page, response.data.total_pages);
        })
        .catch(error => {
            console.error('Error loading logs:', error);
            alert('加载操作日志时出错，请稍后再试。');
        });
}

function updatePagination(currentPage, totalPages) {
    const paginationContainer = document.getElementById('pagination');
    paginationContainer.innerHTML = '';

    if (totalPages > 1) {
        const prevButton = document.createElement('button');
        prevButton.textContent = '上一页';
        prevButton.onclick = () => loadOperationLogs(currentPage - 1);
        prevButton.disabled = currentPage === 1;

        const nextButton = document.createElement('button');
        nextButton.textContent = '下一页';
        nextButton.onclick = () => loadOperationLogs(currentPage + 1);
        nextButton.disabled = currentPage === totalPages;

        const pageInfo = document.createElement('span');
        pageInfo.textContent = `第 ${currentPage} 页，共 ${totalPages} 页`;

        paginationContainer.appendChild(prevButton);
        paginationContainer.appendChild(pageInfo);
        paginationContainer.appendChild(nextButton);
    }
}

function handleHistoryClick(event) {
    const historyItem = event.target.closest('.history-item');
    if (!historyItem) return;

    const historyId = historyItem.dataset.id;
    // TODO: 实现加载历史记录的功能
}

document.addEventListener('DOMContentLoaded', () => {
    const historyContainer = document.querySelector('#history-container');
    historyContainer?.addEventListener('click', handleHistoryClick);
});
export function setupBackgroundChange() {
    changeBackground();
    setInterval(changeBackground, 120000);
}

function changeBackground() {
    const body = document.body;
    const img = new Image();
    img.onload = function() {
        body.style.backgroundImage = `linear-gradient(rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.5)), url(${img.src})`;
        body.style.backgroundSize = 'cover';
        body.style.backgroundPosition = 'center';
        body.style.backgroundAttachment = 'fixed';
    }
    img.src = '/random_background?' + new Date().getTime();
}
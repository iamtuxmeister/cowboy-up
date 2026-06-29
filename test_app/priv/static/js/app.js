// Test App — client JS
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".flash").forEach(el => {
        setTimeout(() => el.remove(), 5000);
    });
});

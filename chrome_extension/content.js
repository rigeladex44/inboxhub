// Content Script: Berjalan otomatis di halaman myaccount.google.com/apppasswords
(function() {
    const APP_NAME = "Dashboard Mail";

    // Toast Notifikasi
    function showNotification(message, bg = "#0f172a", textCol = "#38bdf8") {
        const toast = document.createElement("div");
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 99999999;
            background: ${bg};
            color: ${textCol};
            padding: 14px 22px;
            border-radius: 12px;
            box-shadow: 0 12px 35px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.1);
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.3s ease;
        `;
        toast.innerHTML = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }

    // Fungsi Utama: Cari input, isi nama aplikasi, dan klik 'Buat'
    function autoFillAndCreate() {
        const allInputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type]), input.whsOnd'));
        
        const targetInput = allInputs.find(input => {
            const label = (input.getAttribute("aria-label") || "").toLowerCase();
            const placeholder = (input.getAttribute("placeholder") || "").toLowerCase();
            const name = (input.getAttribute("name") || "").toLowerCase();
            return label.includes("nama") || label.includes("name") || label.includes("app") ||
                   placeholder.includes("nama") || placeholder.includes("name") ||
                   name.includes("app");
        }) || document.querySelector('input[type="text"]');

        if (targetInput) {
            targetInput.focus();
            targetInput.value = APP_NAME;

            // Trigger Google Reactive Events (MDC / Angular)
            targetInput.dispatchEvent(new Event("input", { bubbles: true }));
            targetInput.dispatchEvent(new Event("change", { bubbles: true }));

            targetInput.style.border = "2px solid #0284c7";
            targetInput.style.background = "#f0f9ff";

            // Cari tombol 'Buat' atau 'Create'
            const buttons = Array.from(document.querySelectorAll("button, div[role='button']"));
            const createButton = buttons.find(btn => {
                const text = btn.textContent.trim().toLowerCase();
                return text === "buat" || text === "create" || text.includes("buat") || text.includes("create");
            });

            if (createButton) {
                createButton.focus();
                createButton.style.outline = "3px solid #10b981";
                showNotification(`⚡ Mengisi nama: <b>${APP_NAME}</b> & otomatis menekan tombol Buat...`);
                
                setTimeout(() => {
                    createButton.click();
                    showNotification(`🎉 Sukses! Silakan salin 16 karakter Sandi Aplikasi di layar.`, "#064e3b", "#34d399");
                }, 400);
            } else {
                showNotification(`✅ Berhasil mengisi: <b>${APP_NAME}</b>! Silakan klik tombol Buat.`);
            }

            return true;
        }

        return false;
    }

    // Polling hingga elemen siap
    let attempts = 0;
    const interval = setInterval(() => {
        attempts++;
        const success = autoFillAndCreate();
        if (success || attempts > 25) {
            clearInterval(interval);
        }
    }, 250);
})();

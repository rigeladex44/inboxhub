/**
 * Bookmarklet Chrome: Pembuatan Sandi Aplikasi Google (Dashboard Mail)
 * 
 * Cara Penggunaan:
 * 1. Buat Bookmark baru di Google Chrome (tekan Ctrl+D atau Cmd+D).
 * 2. Beri nama: "⚡ Buat Sandi Gmail (Dashboard Mail)"
 * 3. Di kolom URL, paste kode Bookmarklet (javascript:...) di bawah ini.
 * 4. Simpan ke Bookmark Bar.
 * 
 * Cara Kerja:
 * - Jika diklik dari tab mana saja: Otomatis membuka https://myaccount.google.com/apppasswords
 * - Saat di halaman Sandi Aplikasi Google: Otomatis mengisi nama "Dashboard Mail",
 *   memicu event input (agar tombol aktif), dan menyorot/klik tombol "Buat" (Create).
 */

// ================= KODE BOOKMARKLET MINIFIED (COPY KODE INI KE KOLOM URL BOOKMARK) =================
// javascript:(function(){const n="Dashboard Mail",t="https://myaccount.google.com/apppasswords";function e(n,t="#0f172a",e="#38bdf8"){const o=document.createElement("div");o.style.cssText=`position:fixed;bottom:24px;right:24px;z-index:9999999;background:${t};color:${e};padding:14px 20px;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,0.6),0 0 0 1px rgba(255,255,255,0.1);font-family:system-ui,sans-serif;font-size:13px;font-weight:600;display:flex;align-items:center;gap:8px;`,o.innerHTML=n,document.body.appendChild(o),setTimeout(()=>o.remove(),4500)}function o(){const t=Array.from(document.querySelectorAll('input[type="text"], input:not([type]), input.whsOnd')).find(n=>{const t=(n.getAttribute("aria-label")||"").toLowerCase(),e=(n.getAttribute("placeholder")||"").toLowerCase(),o=(n.getAttribute("name")||"").toLowerCase();return t.includes("nama")||t.includes("name")||t.includes("app")||e.includes("nama")||e.includes("name")||o.includes("app")})||document.querySelector('input[type="text"]');if(t){t.focus(),t.value=n,t.dispatchEvent(new Event("input",{bubbles:!0})),t.dispatchEvent(new Event("change",{bubbles:!0})),t.style.border="2px solid #0284c7",t.style.background="#f0f9ff";const o=Array.from(document.querySelectorAll("button, div[role='button']")).find(n=>{const t=n.textContent.trim().toLowerCase();return"buat"===t||"create"===t||t.includes("buat")||t.includes("create")});return o?(o.focus(),o.style.outline="3px solid #10b981",e(`⚡ Mengisi <b>${n}</b> & menekan tombol Buat...`),setTimeout(()=>{o.click(),e(`🎉 Selesai! Silakan salin 16 karakter sandi kuning di atas.`,`#064e3b`,`#34d399`)},400)):e(`✅ Berhasil mengisi: <b>${n}</b>! Silakan klik Buat.`),!0}return!1}window.location.hostname.includes("google.com")&&window.location.pathname.includes("/apppasswords")?function(){let n=0;const t=setInterval(()=>{n++,(!o()&&n<=20)||clearInterval(t)},250)}():(e("🚀 Membuka halaman Sandi Aplikasi Google..."),setTimeout(()=>{window.location.href=t},400))})();


// ================= SOURCE CODE LENGKAP (READABLE) =================
(function() {
    const APP_NAME = "Dashboard Mail";
    const TARGET_URL = "https://myaccount.google.com/apppasswords";

    // Notifikasi Toast Mengambang
    function showNotification(message, bg = "#0f172a", textCol = "#38bdf8") {
        const toast = document.createElement("div");
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999999;
            background: ${bg};
            color: ${textCol};
            padding: 14px 20px;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.1);
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
        `;
        toast.innerHTML = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4500);
    }

    // Fungsi Utama: Mengisi Nama Aplikasi dan Otomatis Klik Tombol 'Buat'
    function autoFillAndCreateAppPassword() {
        const allInputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type]), input.whsOnd'));
        
        // Cari input berdasarkan atribut atau fallback ke text input pertama
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

            // Trigger Google Reactive Events (MDC / Angular) agar tombol 'Buat' aktif
            targetInput.dispatchEvent(new Event("input", { bubbles: true }));
            targetInput.dispatchEvent(new Event("change", { bubbles: true }));

            // Beri visual highlight pada input
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
                showNotification(`⚡ Mengisi <b>${APP_NAME}</b> & otomatis menekan tombol Buat...`);
                
                // Otomatis klik tombol Buat setelah input terdaftar
                setTimeout(() => {
                    createButton.click();
                    showNotification(`🎉 Selesai! Silakan salin 16 karakter sandi aplikasi di layar.`, "#064e3b", "#34d399");
                }, 400);
            } else {
                showNotification(`✅ Berhasil mengisi: <b>${APP_NAME}</b>! Silakan klik tombol Buat.`);
            }

            return true;
        }

        return false;
    }

    // Cek apakah browser sedang berada di halaman App Passwords Google
    const isAppPasswordsPage = window.location.hostname.includes("google.com") && 
                               window.location.pathname.includes("/apppasswords");

    if (isAppPasswordsPage) {
        // DI SINI: CUKUP 1X KLIK LANGSUNG JADI!
        let attempts = 0;
        const checkInterval = setInterval(() => {
            attempts++;
            const success = autoFillAndCreateAppPassword();
            if (success || attempts > 20) {
                clearInterval(checkInterval);
            }
        }, 250);
    } else {
        // Jika belum di halaman tersebut, alihkan langsung
        showNotification("🚀 Membuka halaman Sandi Aplikasi Google...");
        setTimeout(() => {
            window.location.href = TARGET_URL;
        }, 400);
    }
})();

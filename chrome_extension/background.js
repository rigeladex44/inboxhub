// Background Service Worker untuk Ekstensi Chrome
// Membuka tab Google App Passwords dan menginjeksi pengisi otomatis

chrome.action.onClicked.addListener(async (currentTab) => {
    const TARGET_URL = "https://myaccount.google.com/apppasswords";

    // 1. Buat tab baru langsung ke halaman Sandi Aplikasi Google
    const newTab = await chrome.tabs.create({
        url: TARGET_URL,
        active: true
    });

    // 2. Dengarkan saat tab selesai dimuat sempurna
    const tabUpdateListener = (tabId, changeInfo, tab) => {
        if (tabId === newTab.id && changeInfo.status === 'complete') {
            // Hapus listener setelah terpanggil
            chrome.tabs.onUpdated.removeListener(tabUpdateListener);

            // 3. Suntikkan content.js untuk mengisi nama dan klik 'Buat'
            setTimeout(() => {
                chrome.scripting.executeScript({
                    target: { tabId: newTab.id },
                    files: ["content.js"]
                }).catch(err => {
                    console.log("Eksekusi script:", err);
                });
            }, 500);
        }
    };

    chrome.tabs.onUpdated.addListener(tabUpdateListener);
});

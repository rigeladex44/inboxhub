# 📬 Panduan Penggunaan Personal Email Dashboard

Dashboard ini memantau email masuk secara real-time yang **khusus disaring hanya untuk pesan dari**:
- 🔴 **Google** (*Keamanan, Verifikasi Akun, Notifikasi*)
- 🔵 **Facebook / Meta** (*Keamanan Akun, Grup, Notifikasi Halaman*)
- 🔷 **Microsoft Account Team** (*Kode Masuk, Verifikasi 2FA, Info Keamanan*)

Pesan dari pengirim lain (newsletter, promo belanja, dsb.) secara otomatis dilewati (*skip*).

---

## 🚀 Cara Menjalankan

1. **Jalankan Backend Flask**:
   Buka terminal di folder ini dan jalankan:
   ```bash
   python3 app.py
   ```
2. **Buka di Browser**:
   Akses alamat:
   ```text
   http://127.0.0.1:5000
   ```

---

## 🔑 Konfigurasi Akun (`accounts.json`)

Akun dikonfigurasi pada file [`accounts.json`](file:///Volumes/Hengkyy/Dashboard%20Email/accounts.json):

1. **Akun Gmail**:
   - Membutuhkan **Sandi Aplikasi (App Password)** 16 digit dari [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) dengan Verifikasi 2 Langkah yang sudah aktif.
2. **Akun Hotmail / Outlook**:
   - Karena Microsoft menutup protokol *Basic Auth* per September 2024, email Hotmail dipantau menggunakan fitur **Auto-Forwarding**:
     - Buka **outlook.live.com** > **Settings** > **Mail** > **Forwarding**.
     - Aktifkan penerusan ke akun Gmail indukan Anda (`rigeladex@gmail.com`).
     - Seluruh email Hotmail akan otomatis mengalir dan terbaca di dashboard tanpa perlu mendaftarkan Hotmail langsung ke IMAP.

---

## 🛠️ Fitur Dashboard

- **Filter Platform 1-Klik:** Tab filter di bagian atas untuk melihat *Semua Target*, *Google*, *Facebook*, atau *Microsoft*.
- **Pencarian Cepat:** Cari berdasarkan kata kunci subjek, pengirim, maupun kutipan isi.
- **Baca Pesan Lengkap:** Klik kartu email untuk membuka modal pratinjau pesan lengkap (*format asli HTML & teks polos*).
- **Auto-Refresh:** Timer penyegaran otomatis (1m, 3m, 5m).

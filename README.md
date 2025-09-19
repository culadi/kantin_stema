# Stema Canteen

Sebuah aplikasi web berbasis **Flask** untuk mengelola klaim makanan harian karyawan. Sistem ini memungkinkan karyawan untuk mengambil jatah makan mereka dengan menggunakan ID unik, sementara admin dapat mengelola data karyawan, melacak klaim, dan melihat laporan.

## ✨ Fitur Utama

*   **Klaim Makanan**: Karyawan dapat mengambil makanan dengan memasukkan `ref_id`. Sistem akan mencegah klaim ganda pada hari yang sama.
*   **Feedback Suara (TTS)**: Memberikan umpan balik audio yang dipersonalisasi menggunakan Google Text-to-Speech (gTTS) untuk sukses atau gagal klaim.
*   **Dashboard Admin**: Melihat riwayat klaim, statistik harian/mingguan, dan daftar karyawan.
*   **Manajemen Karyawan**:
    *   CRUD (Buat, Baca, Perbarui, Hapus) data karyawan.
    * *   Impor data karyawan dari file Excel (.xlsx/.xls).
    *   Fitur Arsip: "Hapus" karyawan dengan mengarsipkannya daripada menghapus data secara permanen.
    *   Pulihkan karyawan yang telah diarsipkan.
*   **Autentikasi Admin**: Halaman admin dilindungi dengan login.
*   **Aktivitas Log**: Mencatat semua aktivitas penting (tambah, edit, arsip, impor karyawan, dll).
*   **Pembersihan Otomatis**: Menghapus file suara TTS custom yang berusia lebih dari 7 hari secara otomatis.

## 🛠️ Teknologi yang Digunakan

*   **Backend**: Python, Flask
*   **Database**: PostgreSQL (dengan SQLAlchemy ORM)
*   **Frontend**: HTML, CSS, JavaScript (dengan templat Jinja2)
*   **Lainnya**:
    *   `gTTS` untuk Text-to-Speech
    *   `pandas` untuk impor file Excel
    *   `APScheduler` untuk tugas latar belakang (pembersihan file)
    *   `python-dotenv` untuk mengelola environment variables
    *   `psycopg2` sebagai adapter PostgreSQL

## 📋 Prasyarat

Sebelum menjalankan aplikasi, pastikan Anda telah menginstal:

*   Python 3.7+
*   PostgreSQL Server
*   pip (Python package manager)

## 🚀 Panduan Instalasi

### 1. Clone Repository

```bash
git clone <your-gitlab-repo-url>
cd stema-canteen
```

### 2. Buat Environment Virtual (Virtual Environment)

```bash
python -m venv venv
source venv/bin/activate  # Untuk Linux/macOS
# atau
venv\Scripts\activate     # Untuk Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Database

1.  Buat database baru di PostgreSQL (e.g., `stema_canteen`).
2.  Sesuaikan koneksi database di file `.env`.

### 5. Konfigurasi Environment Variables

Buat file `.env` di root direktori project dan isi dengan konfigurasi Anda:

```env
# Kredensial Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stema_canteen
DB_USER=your_db_username
DB_PASSWORD=your_strong_password

# Flask Secret Key (Generate yang baru untuk production!)
SECRET_KEY=your-super-secret-key-here

# Optional: Konfigurasi lainnya
```

### 6. Inisialisasi Database

Jalankan perintah berikut di shell Python untuk membuat tabel-tabel yang diperlukan:

```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
...
>>> exit()
```

### 7. Jalankan Aplikasi

```bash
python app.py
```

Aplikasi akan berjalan di `http://localhost:5003`.

## 📁 Struktur Project

```
stema-canteen/
├── app.py                 # File aplikasi Flask utama
├── requirements.txt       Daftar dependencies Python
├── .env                  File environment variables (ignore di git)
├── .gitignore
├── README.md
│
├── static/
│   └── sounds/           # Direktori untuk file audio
│       ├── custom/       # File TTS yang digenerate otomatis
│       └── ...           # File suara default (e.g., sudah_diambil.mp3)
│
├── templates/            # Template HTML Flask
│   ├── index.html        # Halaman utama untuk klaim makanan
│   ├── admin.html        # Dashboard admin
│   ├── employee_list.html
│   ├── archive.html
│   └── register.html     # Halaman registrasi admin
│
├── users.json            # File penyimpanan kredensial admin (tergenerate)
└── activity_log.jsonl    # Log aktivitas sistem (tergenerate)
```

## 👨‍💻 Penggunaan

### 1. Klaim Makanan (Karyawan)

1.  Buka halaman utama (`/`).
2.  Masukkan `ref_id` yang terdaftar.
3.  Tekan enter atau tombol submit.
4.  Sistem akan memvalidasi dan memutar suara konfirmasi.

### 2. Login Admin

1.  **Daftar Admin Pertama Kali**: Buka `/register` untuk membuat akun admin baru.
2.  Akses `/admin` dan login dengan kredensial yang telah didaftarkan.

### 3. Mengelola Karyawan

*   **Lihat Daftar**: Pergi ke `Employee List` dari dashboard admin.
*   **Tambah Karyawan**: Gunakan form pada halaman `Employee List`.
*   **Edit/Hapus**: Gunakan tombol aksi pada tabel di `Employee List`.
*   **Impor dari Excel**: Gunakan fitur impor pada halaman `Employee List`. Format file Excel: Kolom pertama `ref_id`, Kolom kedua `nama`.

### 4. Melihat Arsip

Akses halaman `Archive` dari dashboard admin untuk melihat, memulihkan, atau menghapus permanen karyawan yang telah diarsipkan.

## 🔧 Skedul Tugas (Scheduler)

Aplikasi secara otomatis menjalankan tugas pembersihan file suara TTS lama setiap hari. Ini dikelola oleh `APScheduler` dan tidak memerlukan intervensi manual.

## ⚠️ Catatan Penting

*   File `.env` dan `users.json` mengandung informasi sensitif dan **tidak boleh** di-commit ke version control (sudah tercakup di `.gitignore` contoh).
*   Pastikan untuk mengubah `SECRET_KEY` di production.
*   Konfigurasi database dan path file suara harus disesuaikan untuk environment deployment (production).
*   Aplikasi ini dijalankan dengan `debug=True` yang **tidak boleh digunakan dalam environment production**.

## 📄 Lisensi

Proprietary - Dimiliki oleh STEMA.
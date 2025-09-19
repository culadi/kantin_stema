Stema Canteen
Sebuah aplikasi web berbasis Flask untuk mengelola klaim makanan harian karyawan. Sistem ini memungkinkan karyawan untuk mengambil jatah makan mereka dengan menggunakan ID unik, sementara admin dapat mengelola data karyawan, melacak klaim, dan melihat laporan.

✨ Fitur Utama
Klaim Makanan: Karyawan dapat mengambil makanan dengan memasukkan ref_id. Sistem akan mencegah klaim ganda pada hari yang sama.

Feedback Suara (TTS): Memberikan umpan balik audio yang dipersonalisasi menggunakan Google Text-to-Speech (gTTS) untuk sukses atau gagal klaim.

Dashboard Admin: Melihat riwayat klaim, statistik harian/mingguan, dan daftar karyawan.

Manajemen Karyawan:

CRUD (Buat, Baca, Perbarui, Hapus) data karyawan.

Impor data karyawan dari file Excel (.xlsx/.xls).

Fitur Arsip: "Hapus" karyawan dengan mengarsipkannya daripada menghapus data secara permanen.

Pulihkan karyawan yang telah diarsipkan.

Autentikasi Admin: Halaman admin dilindungi dengan login.

Aktivitas Log: Mencatat semua aktivitas penting (tambah, edit, arsip, impor karyawan, dll).

Pembersihan Otomatis: Menghapus file suara TTS custom yang berusia lebih dari 7 hari secara otomatis.

🛠️ Teknologi yang Digunakan
Backend: Python, Flask

Database: PostgreSQL (dengan SQLAlchemy ORM)

Frontend: HTML, CSS, JavaScript (dengan templat Jinja2)

Lainnya:

gTTS untuk Text-to-Speech

pandas untuk impor file Excel

APScheduler untuk tugas latar belakang (pembersihan file)

python-dotenv untuk mengelola environment variables

psycopg2 sebagai adapter PostgreSQL

📋 Prasyarat
Sebelum menjalankan aplikasi, pastikan Anda telah menginstal:

Python 3.7+

PostgreSQL Server

pip (Python package manager)

🚀 Panduan Instalasi
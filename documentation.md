# Repolution Workflow Documentation

Dokumen ini menjelaskan alur kerja pipeline Repolution, peran tiap agen, artefak yang dihasilkan, dan cara menjalankan sistem dari CLI maupun web UI.

## Ringkasan Sistem

Repolution adalah pipeline analisis codebase yang berjalan bertahap. Tujuannya adalah:

1. Membaca dan membungkus source code menjadi representasi flat.
2. Mengidentifikasi repo, route, endpoint, field, dan transaksi yang relevan.
3. Mengukur biaya eksekusi dan jejak karbon dari endpoint yang aktif.
4. Menganalisis fungsi yang paling layak dioptimasi.
5. Menyatukan refactor dan validasi hasilnya.
6. Menyusun laporan akhir yang bisa dibaca manusia.

Nama produk yang dipakai di UI dan narasi internal adalah **Repolution**.

## Alur Agen

Urutan agen yang dipakai di workflow saat ini:

1. **Agen-Repomix**
   - Membaca source code dari folder lokal atau Git URL.
   - Menghasilkan bundle flat seperti `flat_codebase.txt`.
   - Menjadi sumber input untuk analisis berikutnya.

2. **Agen-AnalysisRepo**
   - Memetakan struktur repo.
   - Menemukan route, controller, endpoint, dan area yang perlu dianalisis.
   - Menghasilkan konteks awal untuk pengukuran dan optimasi.

3. **Agen-Codecarbon**
   - Menjalankan request ke aplikasi target yang sedang aktif.
   - Mengukur waktu respons, energi, dan estimasi CO2 per request.
   - Menyimpan hasil pengukuran ke artefak carbon report.

4. **Agen-AnalysisFunc**
   - Menganalisis fungsi, relasi logika, dan area yang berpotensi dioptimasi.
   - Menentukan fokus refactor berdasarkan hasil repo analysis dan carbon profiling.

5. **Agen-RefactorValidator**
   - Menggabungkan proses refactor dan validasi hasil.
   - Memastikan perubahan yang diusulkan masih konsisten secara logika dan aman untuk dipakai.
   - Dalam demo UI, agen ini juga bisa memicu retry flow jika validasi awal gagal.

6. **Agen-Report**
   - Menyusun ringkasan akhir.
   - Menggabungkan temuan repo, hasil carbon, hasil analisis fungsi, dan status validasi.
   - Menghasilkan laporan markdown dan artefak pendukung lain.

## Graf Workflow

Graf hubungan agen yang dipakai sebagai acuan visual dan reasoning:

```text
Agen-Repomix -> Agen-AnalysisRepo
Agen-AnalysisRepo -> Agen-Codecarbon
Agen-Codecarbon -> Agen-AnalysisFunc
Agen-AnalysisFunc -> Agen-RefactorValidator
Agen-RefactorValidator -> Agen-Codecarbon
Agen-Codecarbon -> Agen-Report
```

Makna graf tersebut:

- Repomix menyiapkan data mentah.
- AnalysisRepo membaca konteks repo sebelum pengukuran.
- Codecarbon menjadi titik ukur utama untuk request live.
- AnalysisFunc melakukan penajaman analisis logika sebelum perbaikan.
- RefactorValidator mengunci kualitas hasil refactor sebelum finalisasi.
- Codecarbon dapat dipanggil lagi setelah validasi untuk memastikan perubahan tidak memperburuk beban eksekusi.
- Report menutup pipeline dengan output yang bisa dibagikan.

## Artefak Output

Output pipeline biasanya berada di folder berikut:

- `output/flat_codebase.txt` - hasil bundling repo oleh Repomix.
- `output/transactions.json` - hasil identifikasi transaksi dan endpoint.
- `output/ingestion_result.json` - metadata ingestion.
- `output/carbon_report.json` - hasil pengukuran energi dan CO2.
- `reports/code_carbon_report.md` - ringkasan laporan akhir.
- `reports/tests/` - test yang dihasilkan untuk verifikasi refactor.

Catatan: nama file dapat sedikit berbeda tergantung mode eksekusi dan implementasi agen yang dipakai.

## Cara Menjalankan

### 1. Web UI

Jalankan server backend dan buka dashboard web.

```bash
python server.py
```

Lalu buka:

```text
http://localhost:5000
```

Di web UI, masukkan path repo atau Git URL, lalu isi base URL aplikasi target yang sedang hidup. Setelah itu jalankan pipeline dari tombol yang tersedia.

### 2. Demo Static UI

Untuk demo lokal yang menampilkan alur visual pipeline:

```bash
python -m http.server 8000
```

Lalu buka:

```text
http://localhost:8000/demo_pipeline.html
```

### 3. CLI

Untuk menjalankan pipeline langsung dari terminal:

```bash
python pipeline.py --source C:\path\to\repo --base-url http://localhost:8000
```

Jika ingin melewati pengukuran carbon:

```bash
python pipeline.py --source C:\path\to\repo --skip-carbon
```

## Environment

Pastikan variabel dan dependensi berikut tersedia:

- `OPENROUTER_API_KEY` untuk analisis AI.
- `TARGET_BASE_URL` untuk endpoint aplikasi target.
- `repomix` terpasang global untuk ingestion repo.
- Python dependencies dari `requirements.txt` sudah terinstal.

Contoh `.env`:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
TARGET_BASE_URL=http://localhost:8000
REPOMIX_OUTPUT_DIR=./output
REPORT_OUTPUT_DIR=./reports
```

## Catatan UI

- UI memakai nama produk **Repolution**, bukan Green-Code.
- Log dan tampilan visual dijaga tanpa ikon ceklis, silang, atau badge simbolik yang berlebihan.
- Fokus tampilan adalah teks yang bersih, status yang jelas, dan alur yang mudah diikuti.

## Referensi File

- [pipeline.py](pipeline.py)
- [server.py](server.py)
- [demo_pipeline.html](demo_pipeline.html)
- [web_ui/index.html](web_ui/index.html)
- [implementation_summary.md](implementation_summary.md)
- [MULTI_AGENT_CODE_CARBON.md](MULTI_AGENT_CODE_CARBON.md)

---
name: skripsi-latex
description: Bantu penulisan, kompilasi, dan pengecekan konsistensi skripsi/tesis berbasis LaTeX mengikuti aturan PPKI. Gunakan saat bekerja di proyek skripsi LaTeX (mis. folder "Skripsi LaTeX"), menyerap aturan penulisan dari PPKI.md, membangun/merapikan struktur proyek, mengkompilasi ke PDF, atau menganalisis ketidaksinkronan antar-kalimat/bab. Trigger: "skripsi", "PPKI", "bab", "latex", "kompilasi", "konsistensi kalimat".
---

# Skripsi LaTeX Assistant

Skill ini di-scaffold dari pola nyata di log Claude Code (sesi "Draft Skripsi"
dengan ratusan operasi Bash/Read/Write/Edit di folder `Skripsi LaTeX`).
**Verifikasi dan sesuaikan** sebelum dipakai rutin.

## Prinsip

- Bahasa kerja: **Bahasa Indonesia**.
- Patuhi aturan penulisan dari **PPKI** (Pedoman Penulisan Karya Ilmiah).
  Jika ada `PPKI.md` atau PDF pedoman di repo, **baca dulu** dan jadikan acuan.
- Jangan mengarang isi; jangan mengubah substansi tanpa konfirmasi. Fokus pada
  struktur, konsistensi, dan kepatuhan format.

## Workflow

1. **Serap pedoman.** Baca `PPKI.md`/pedoman. Ringkas aturan kunci: margin,
   penomoran bab/sub-bab, gaya sitasi, format tabel/gambar, kutipan.
2. **Petakan proyek.** Temukan `main.tex`/root, daftar `\input`/`\include`,
   file bab, `.bib`, dan gambar. Laporkan struktur sebelum mengubah.
3. **Kompilasi aman.** Gunakan toolchain yang ada (`latexmk -pdf`, atau
   `pdflatex`+`biber`/`bibtex`). Jalankan dari root proyek; laporkan error log
   (baris pertama yang gagal), jangan hanya "gagal".
4. **Analisis konsistensi** (saat diminta):
   - Istilah: cek penggunaan istilah yang tidak konsisten antar-bab.
   - Klaim vs. bukti: tandai kalimat yang tidak didukung sitasi.
   - Alur: tandai lompatan logika/kalimat yang tidak nyambung antar-paragraf.
   - Sitasi: pastikan setiap `\cite` ada di `.bib` dan sebaliknya.
   Sajikan temuan sebagai tabel: lokasi (file:baris) → masalah → saran.
5. **Perubahan bertahap.** Edit kecil + kompilasi ulang untuk memastikan tidak
   merusak build. Jangan refactor besar tanpa persetujuan.

## Decision rules

- Tidak yakin aturan PPKI → tanyakan / tandai "perlu verifikasi", jangan menebak.
- Konflik antara gaya penulisan penulis dan PPKI → ikuti PPKI, beri catatan.
- File besar / banyak bab → gunakan `index` atau peta struktur dulu (hemat token).

## Output

- Ringkasan perubahan + hasil kompilasi (sukses/gagal + pesan error relevan).
- Untuk analisis: tabel temuan yang bisa langsung ditindaklanjuti.

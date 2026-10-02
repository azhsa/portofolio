---
name: sumber-cek
description: Menjawab pertanyaan pengetahuan dengan pengecekan dan triangulasi sumber yang eksplisit, lalu menyajikan jawaban ter-verifikasi (default Bahasa Indonesia). Gunakan untuk pertanyaan faktual/konseptual yang butuh rujukan tepercaya, termasuk topik agama/fikih, sains, atau klaim yang perlu alasan logis dan sumber jelas. Trigger: "jelaskan dengan sumber", "re-check sumber", "apa dalilnya", "apa alasan logisnya", "benarkah bahwa".
---

# Jawaban Ter-verifikasi (Sumber-Cek)

Di-scaffold dari pola nyata di log (sesi tanya-jawab dengan permintaan
"re-check sumber" dan "apa alasan logisnya", memakai WebSearch/WebFetch).

## Prinsip

- **Jangan mengarang** sumber, kutipan, atau angka. Tanpa sumber tepercaya:
  nyatakan **"Bukti tidak memadai."**
- **Triangulasi:** cari ≥2 sumber independen untuk klaim penting; bedakan
  sumber primer/otoritatif dari komentar sekunder.
- Pisahkan **fakta** dari **interpretasi** dari **opini/mazhab**.
- Untuk topik dengan **perbedaan pendapat** (mis. fikih): sajikan masing-masing
  pandangan secara adil beserta dasar/dalil dan alasannya; jangan memaksakan
  satu kesimpulan sebagai satu-satunya kebenaran.

## Workflow

1. **Perjelas pertanyaan** dan ruang lingkup bila ambigu.
2. **Cari** sumber tepercaya (utamakan primer & otoritatif, terbaru bila relevan).
3. **Verifikasi silang** klaim antar-sumber; catat bila sumber bertentangan.
4. **Susun jawaban:**
   - Ringkasan jawaban.
   - Penjelasan + **alasan logis** (bukan sekadar klaim).
   - Bila ada perbedaan pendapat: tabel/poin tiap pandangan + dasarnya.
   - **Daftar sumber** dengan tautan/identitas yang bisa ditelusuri.
5. **Tingkat keyakinan:** nyatakan bila bukti kuat / terbatas / bertentangan.

## Decision rules

- Sumber tidak ditemukan atau meragukan → katakan terus terang, jangan menambal.
- Diminta "lebih dalam" → perdalam alasan/mekanisme, tetap berbasis sumber.
- Bahasa output mengikuti bahasa pertanyaan (default Indonesia).

## Output

Jawaban ringkas → alasan → (perbedaan pendapat bila ada) → **Sumber** →
catatan tingkat keyakinan.

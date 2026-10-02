# Claude OS — Peta Navigasi Vault

> File ini adalah **peta** (bukan "graph RAG"). Tujuannya: memberi Claude Code
> jalur yang jelas untuk menemukan informasi di vault ini sehingga jawaban lebih
> cepat dan hemat token. Baca file ini lebih dulu, lalu ikuti `index.md` di tiap
> folder sebagai daftar isi.

## Struktur folder (pola Karpathy: raw → wiki → output)

```
Claude Code/
├── CLAUDE.md        ← file ini (peta + aturan navigasi)
├── index.md         ← master index / daftar isi utama
├── raw/             ← informasi mentah: sumber, kutipan, hasil riset belum diolah
│   └── index.md
├── wiki/            ← hasil sintesis: artikel gaya ensiklopedia dari data raw
│   └── index.md
├── output/          ← deliverable final: laporan, draft, slide, naskah
│   └── index.md
├── Sessions/        ← ekspor transkrip sesi Claude Code (otomatis via hook)
└── Memory/          ← salinan file CLAUDE.md global & per-proyek
```

## Aturan navigasi (wajib diikuti Claude)

1. **Mulai dari `index.md`.** Setiap folder punya `index.md` sebagai daftar isi.
   Jangan memindai seluruh folder; baca `index.md` dulu untuk tahu ke mana harus
   pergi. Ini yang membuat pencarian hemat token saat file sudah banyak.
2. **Alur informasi searah:** data masuk ke `raw/` → disintesis jadi artikel di
   `wiki/` → dijadikan deliverable di `output/`. Jangan menaruh deliverable di
   `raw/`, dan jangan menaruh sumber mentah di `output/`.
3. **Perbarui index saat menambah file.** Setiap kali membuat file baru di sebuah
   folder, tambahkan entri (link `[[nama-file]]`) di `index.md` folder tersebut.
4. **Satu topik = satu subfolder di `wiki/`.** Mis. `wiki/slr-metodologi/` dengan
   `index.md`-nya sendiri bila artikelnya banyak.
5. **Gunakan wikilink `[[...]]`** antar-catatan agar graf Obsidian terbentuk dan
   mudah ditelusuri manusia maupun Claude.

## Konteks pemilik vault

- Bahasa kerja utama: **Bahasa Indonesia** (gunakan ini kecuali diminta lain).
- Domain utama: **skripsi/tesis (LaTeX)** dan **Systematic Literature Review
  (SLR)** mengikuti PRISMA 2020, Cochrane, APA 7. Lihat skill terkait di
  `~/.claude/skills/` (`skripsi-latex`, `slr-review`, `sumber-cek`).
- Prinsip: jangan mengarang sumber/sitasi; bedakan fakta dari asumsi; jika bukti
  kurang, nyatakan "bukti tidak memadai".

## Cara menambah pengetahuan baru (contoh)

> "Riset X, simpan sumber ke `raw/`, sintesiskan ke `wiki/<topik>/`, lalu buat
> ringkasan deliverable di `output/`, dan update semua `index.md` terkait."

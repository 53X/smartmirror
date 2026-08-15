# Sari photo sources (demo and later training)

There is **no clean public dataset of pallu + border + body + blouse + hanging shots per SKU**. Cloakroom-style reconstruction data is something we have to capture in a store. What exists online is mostly classification photos (a woman wearing a sari, or a product thumbnail).

## Use now (demo catalog)

Wikimedia Commons, CC-licensed product/museum photos:

- [Category:Banarasi Sari](https://commons.wikimedia.org/wiki/Category:Banarasi_Sari)
- [Category:Saris](https://commons.wikimedia.org/wiki/Category:Saris)
- Seeded demos: Bandhani hanging sari (CC BY-SA 4.0, Kutch.artesania) and Odisha museum Nivi drape (CC BY-SA 3.0, Subhashish Panigrahi)

These are **one photo per sari**, not a five-shot SOP. Fine for proving try-on. Not fine as a SKU identity database.

## Request / download (research, check license before training)

- [IndoFashion](https://github.com/IndoFashion/IndoFashion) — 106K Indian ethnic images including **Saree**; access form required. MIT code, dataset via request. Mostly worn/product shots, not part maps.
- [Indo Fashion on Kaggle](https://www.kaggle.com/datasets/validmodel/indo-fashion-dataset) — same family; verify license on the page.
- [Saree-NIFT-Style](https://huggingface.co/datasets/shrimantasatpati/Saree-NIFT-Style) — Hugging Face, **CC BY-NC-SA 4.0** (non-commercial). Style/drape images, not SKU part shots.
- [BanglaDressNet](https://www.kaggle.com/datasets/musfiqurtuhin/bangladressnet) — includes a Saree class; classification, 224px, not VTO parts.
- Handloom patch sets (e.g. older GitHub handloom GAN repos) — cropped motifs, useless as hanging garments.

## Do not scrape

Myntra / Amazon / boutique Instagram catalogs are not a dataset we can dump into the repo.

## What we still need from a real store

Five photos **per SKU** on the SOP. That is the moat. Public sets will not replace it.

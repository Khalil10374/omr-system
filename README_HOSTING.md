# OMR Enterprise Barcode & QR Code Print System — Hosting Copy

এই ফোল্ডারটি Streamlit hosting-এর জন্য প্রস্তুত করা fresh copy। মূল portable
ফোল্ডারের generated PDF, temporary preview, cache এবং পুরোনো database এখানে
রাখা হয়নি। প্রথমবার চালু হলে `omr_system.db` নিজে থেকে তৈরি হবে।

## সবচেয়ে সহজ deploy: Streamlit Community Cloud

1. এই পুরো folder-টি একটি নতুন GitHub repository-তে upload করুন।
2. Streamlit Cloud-এ **New app** নির্বাচন করুন।
3. Repository, branch এবং main file হিসেবে `app.py` নির্বাচন করুন।
4. Deploy চাপুন। `requirements.txt` দেখে dependency নিজে install হবে।
5. App URL খুলে login করুন:

   - Username: `admin`
   - Password: `admin123`

6. Login করার পর **Settings → Username & Password** থেকে password বদলে দিন।

## Render/Railway-এর মতো service

- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT`
- `Procfile`-এ একই start command দেওয়া আছে।

## App details

- Framework: Streamlit (Python)
- Entry point: `app.py`
- Database: SQLite (`omr_system.db`, প্রথম run-এ তৈরি হয়)
- Required Python: 3.10+
- Main features: OMR barcode/QR PDF generation, full-sheet/overlay-only mode,
  roll range generation, alignment test sheet, visual calibrator, generation
  history, CSV export, barcode/QR tester, bilingual UI এবং logo settings।
- Included master template: `omr_template.pdf`
- Included branding/font assets: `default_logo.png`, login images,
  `AdorNoirrit.woff2`

## গুরুত্বপূর্ণ hosting note

এই সংস্করণে SQLite এবং generated files local filesystem-এ থাকে। অনেক free
hosting service restart বা redeploy-এর সময় local file মুছে দিতে পারে। তাই
production data/history স্থায়ীভাবে রাখতে হলে নিয়মিত **Settings → Database &
Maintenance** থেকে database backup download করুন, অথবা persistent disk/remote
database ব্যবহার করুন।

Generated PDF browser থেকেই download করতে হবে; server filesystem-এ এগুলো
স্থায়ী archive হিসেবে ধরে রাখা উচিত নয়।

## Local smoke test

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

তারপর browser-এ `http://localhost:8501` খুলুন।

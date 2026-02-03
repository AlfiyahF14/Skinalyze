import os
import uuid
import re
import json
import unicodedata
from pathlib import Path

import pandas as pd
from flask import (
    Flask, 
    render_template, 
    request, 
    jsonify, 
    url_for, 
    session
)
from werkzeug.middleware.proxy_fix import ProxyFix

from mapping import chatbot_logic, handle_chat
from mapping.chatbot.dataset_loader import load_chatbot_dataset

STATE_MEMORY = {}
USER_MEMORY = STATE_MEMORY

# joblib untuk load model .pkl
try:
    import joblib
except Exception:
    joblib = None

def get_bool_param(name):
    val = request.args.get(name, "").strip().lower()
    return val in ["true", "yes", "1", "on"]

def is_yes(val):
    return str(val).strip().lower() == "yes"

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"

MODEL_DIR_MAP = {
    "facialwash": "facialwash",
    "moisturizer": "moisturizer",
    "serum": "serum",
    "sunscreen": "sunscreen",
    "toner": "toner",
}

app = Flask(
    __name__,
    template_folder=BASE_DIR.joinpath("templates").as_posix(),
    static_folder=BASE_DIR.joinpath("static").as_posix(),
)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "7d8f9e0a1b2c3d4e5f6g7h8i9j0k1l2m")
app.wsgi_app = ProxyFix(
    app.wsgi_app, 
    x_for=1, 
    x_proto=1, 
    x_host=1, 
    x_port=1, 
    x_prefix=1
)

# -------------------------
# Util Dataset
# -------------------------
def normalize_key(name: str) -> str:
    return name.lower().replace(" ", "").replace("_", "")

def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # bersihkan nama kolom (strip) lalu rename beberapa variasi ke nama kolom standar
    cols = {c: c.strip() for c in df.columns}
    df = df.rename(columns=cols)

    # Lower-case map detection
    colmap = {}
    for c in df.columns:
        lc = c.lower()
        if "nama" in lc and "produk" in lc:
            colmap[c] = "Nama Produk"
        elif lc == "name" or lc == "nama":
            colmap[c] = "Nama Produk"
        elif "brand" in lc:
            colmap[c] = "Brand"
        elif "kandung" in lc or "kandungan" in lc:
            colmap[c] = "Kandungan Utama"
        elif "gambar" in lc or lc == "image" or lc == "images":
            colmap[c] = "Gambar"
        elif "jenis" in lc and "kulit" in lc:
            colmap[c] = "Jenis Kulit"
        elif "masalah" in lc:
            colmap[c] = "Masalah Kulit"
        elif "score" in lc:
            colmap[c] = "Score"
        elif "catat" in lc or "note" in lc:
            colmap[c] = "Catatan"
        elif "alcohol" in lc:
            colmap[c] = "Alcohol-Free"
        elif "fragrance" in lc or "parfum" in lc:
            colmap[c] = "Fragrance-Free"
        elif "comed" in lc or ("non" in lc and "comedo" in lc):
            colmap[c] = "Non-Comedogenic"

    if colmap:
        df = df.rename(columns=colmap)

    for must in ["Nama Produk", "Brand", "Kandungan Utama", "Gambar", "Kategori", "Jenis Kulit", "Masalah Kulit"]:
        if must not in df.columns:
            df[must] = ""

    for col in ["Alcohol-Free", "Fragrance-Free", "Non-Comedogenic"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower().isin(["yes", "true", "1"])
        else:
            df[col] = False

    return df

def load_all_datasets():
    DATASET.clear()
    if not DATASET_DIR.exists():
        print("[DATASET] Folder dataset tidak ditemukan:", DATASET_DIR)
        return
    for fp in DATASET_DIR.glob("*.xlsx"):
        if fp.name.startswith("~$"):  # skip temporary Excel file
            continue
        try:
            df = pd.read_excel(fp, engine="openpyxl")
            df.columns = df.columns.str.strip().str.lower()
            df = normalize_dataframe(df)
            key = normalize_key(fp.stem)

            if "facial" in key: key = "facialwash"
            elif "moist" in key: key = "moisturizer"
            elif "serum" in key: key = "serum"
            elif "sun" in key: key = "sunscreen"
            elif "toner" in key: key = "toner"

            df["Kategori"] = key
            DATASET[key] = df
            print(f"[DATASET] Muat: {fp.name} ({len(df)} baris) → key: {key}")
        except Exception as e:
            print(f"[DATASET] Gagal baca {fp.name}: {e}")

# -------------------------
# Load Dataset
# -------------------------
DATASET = {}
load_all_datasets()

CHATBOT_DATASET = load_chatbot_dataset()

# -------------------------
# Load Models
# -------------------------
MODELS = {}

def load_models():
    MODELS.clear()
    if joblib is None:
        print("[MODEL] joblib tidak tersedia. Lewati load model.")
        return
    if not MODELS_DIR.exists():
        return

    for key in DATASET.keys():
        folder = MODEL_DIR_MAP.get(key)
        if not folder:
            continue
        pkl_path = MODELS_DIR / folder / f"{key}_model.pkl"
        csv_path = MODELS_DIR / folder / f"{key}_meta.csv"

        if pkl_path.exists():
            try:
                MODELS[key] = {"model": joblib.load(pkl_path)}
                print(f"[MODEL] Muat: {pkl_path}")
            except Exception as e:
                print(f"[MODEL] Gagal muat {pkl_path}: {e}")
        else:
            print(f"[MODEL] Tidak ditemukan: {pkl_path}")

        if csv_path.exists():
            try:
                if key not in MODELS:
                    MODELS[key] = {}
                MODELS[key]["meta"] = pd.read_csv(csv_path)
                print(f"[MODEL] Muat metadata: {csv_path}")
            except Exception as e:
                print(f"[MODEL] Gagal muat metadata {csv_path}: {e}")

# -------------------------
# Flask init
# -------------------------
import re
def get_image_path(kategori: str = "", nama_produk: str = "", image_col: str = "") -> str:
    default_image = url_for("static", filename="images/default.png")

    if not kategori or not image_col or str(image_col).lower() == "nan":
        return default_image

    # 🔥 FIX PENTING DI SINI
    CATEGORY_FOLDER_MAP = {
        "facialwash": "facial_wash",
        "facial wash": "facial_wash",
        "toner": "toner",
        "serum": "serum",
        "moisturizer": "moisturizer",
        "sunscreen": "sunscreen",
    }

    kat_raw = str(kategori).strip().lower()
    kat_clean = CATEGORY_FOLDER_MAP.get(kat_raw, kat_raw.replace(" ", "_"))

    filename = str(image_col).strip().split("/")[-1]

    return url_for("static", filename=f"images/{kat_clean}/{filename}")

def apply_filters(df, q="", brand="", prefs=None):
    if q:
        q_lower = q.lower()
        # proteksi bila kolom kosong
        mask1 = df.get("Nama Produk", "").astype(str).str.lower().str.contains(q_lower, na=False)
        mask2 = df.get("Kandungan Utama", "").astype(str).str.lower().str.contains(q_lower, na=False)
        df = df[mask1 | mask2]
    if brand:
        df = df[df.get("Brand", "").astype(str).str.lower() == brand.lower()]
    if prefs:
        for key, val in prefs.items():
            if val and key in df.columns:
                df = df[df[key] == True]
    return df

import re
import unicodedata
import pandas as pd

def clean_text(s: str) -> str:
    if not isinstance(s, str): return ""
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokenize(s: str) -> set:
    return set(clean_text(s).split())

def match_problem(user_problem: str, dataset_problem: str, variants: list) -> bool:
    """
    Matching versi baru:
    - Clean text
    - Token-by-token matching
    - Tidak butuh regex
    """
    user_tokens = tokenize(user_problem)
    dataset_tokens = tokenize(dataset_problem)

    # Variant dibersihkan semua
    variant_tokens = [tokenize(v) for v in variants]

    # Jika dataset punya token yang ada di salah satu variant → match
    for vt in variant_tokens:
        for token in vt:
            if token in dataset_tokens:
                return True

    # fallback (jarang dipakai)
    for ut in user_tokens:
        if ut in dataset_tokens:
            return True

    return False


CATEGORY_MAP = {
    "facialwash": ["facial wash", "facialwash", "cleanser", "fw", "sabun muka"],
    "toner": ["toner"],
    "serum": ["serum"],
    "moisturizer": ["moisturizer", "pelembab", "moist"],
    "sunscreen": ["sunscreen", "sunblock", "spf"],
    "setlengkap": ["facial wash, toner, serum, moisturizer, sunscreen"]
}

def recommend(category, jenis_kulit, masalah_kulit, prefs, top_k=10):

    # --- Normalisasi kategori untuk mencocokkan key dataset ---
    cat = category.lower().strip()
    dataset_key = None

    for key, aliases in CATEGORY_MAP.items():
        if cat in aliases:
            dataset_key = key
            break

    if dataset_key is None:
        dataset_key = category  # fallback

    df = DATASET.get(dataset_key, pd.DataFrame()).copy()
    if df.empty:
        print("DATAFRAME KOSONG UNTUK:", dataset_key)
        return []

    # ======================
    # NORMALISASI JENIS KULIT
    # ======================
    if jenis_kulit:
        jk_clean = clean_text(jenis_kulit)
        df["__jenis_norm"] = df["Jenis Kulit"].astype(str).apply(clean_text)
        df = df[df["__jenis_norm"].str.contains(jk_clean, na=False)]
    
    # ======================
    # HARD FILTER KANDUNGAN (WAJIB ADA)
    # ======================
    if prefs and "ingredient" in prefs:
        ing = clean_text(prefs["ingredient"])

        df["__kandungan_norm"] = df["Kandungan Utama"].astype(str).apply(clean_text)

        df = df[df["__kandungan_norm"].str.contains(ing, na=False)]

        # kalau setelah hard filter kosong → langsung return
        if df.empty:
            return []
        
    # ======================
    # NORMALISASI MASALAH KULIT (BISA LIST / STRING)
    # ======================
    if isinstance(masalah_kulit, list):
        masalah_list = [clean_text(m) for m in masalah_kulit if m]
    else:
        masalah_list = [clean_text(masalah_kulit)] if masalah_kulit else []

    # ======================
    # MATCH MASALAH KULIT (MULTI - OR LOGIC)
    # ======================
    if masalah_list:
        df["__m_norm"] = df["Masalah Kulit"].astype(str).apply(clean_text)

        def cocok_dengan_salah_satu(dataset_problem):
            for user_problem in masalah_list:
                user_tokens = set(tokenize(user_problem))
                matched_master = None

                # TIPE A — exact alias
                for master, variants in SKIN_MAP.items():
                    if user_problem in [clean_text(v) for v in variants]:
                        matched_master = master
                        break

                # TIPE B — token matching
                if matched_master is None:
                    for master, variants in SKIN_MAP.items():
                        for v in variants:
                            if user_tokens & set(tokenize(v)):
                                matched_master = master
                                break
                        if matched_master:
                            break

                # FILTER
                if matched_master:
                    if match_problem(
                        user_problem=user_problem,
                        dataset_problem=dataset_problem,
                        variants=SKIN_MAP[matched_master]
                    ):
                        return True
                else:
                    if any(t in dataset_problem.split() for t in user_tokens):
                        return True

            return False

        df = df[df["__m_norm"].apply(cocok_dengan_salah_satu)]

        # fallback aman
        if df.empty:
            df = DATASET.get(dataset_key, pd.DataFrame()).copy()

    # ======================
    # FILTER TAMBAHAN (PREFS DARI USER)
    # ======================
    if prefs:
        df = apply_filters(df, prefs=prefs)

    # kalau kosong setelah filter prefs → keluar saja
    if df.empty:
        return []

    # ============================
    # FILTER KHUSUS JENIS KULIT
    # ============================
    if jenis_kulit == "sensitif":
        # Harus TRUE semua
        df = df[
            (df["Alcohol-Free"] == True) &
            (df["Fragrance-Free"] == True) &
            (df["Non-Comedogenic"] == True)
        ]

    else:
        # Selain sensitif → fragrance BOLEH
        df = df[
            (df["Alcohol-Free"] == True) &
            (df["Non-Comedogenic"] == True)
        ]

    # kalau hasil kosong → return []
    if df.empty:
        return []

    #======================
    # 1. HAPUS DUPLIKASI SEBELUM RETURN
    # ======================
    # Asumsi: 'Nama Produk' dan 'Brand' adalah penentu unik
    df = df.drop_duplicates(subset=["Nama Produk", "Brand"], keep="first")

    # ==========================================
    # 2. HITUNG SKOR KEAMANAN (Safety Score)
    # ==========================================
    # Produk yang bebas alkohol, fragrance, & non-comedogenic dapat skor tertinggi (3)
    def calculate_safety_score(row):
        score = 0
        if row.get("Alcohol-Free") is True: score += 1
        if row.get("Fragrance-Free") is True: score += 1
        if row.get("Non-Comedogenic") is True: score += 1
        return score

    df["safety_score"] = df.apply(calculate_safety_score, axis=1)

    # ==========================================
    # 3. PENGACAKAN & PENGURUTAN
    # ==========================================
    # Diacak dulu (agar urutan brand tidak membosankan), 
    # lalu diurutkan berdasarkan skor keamanan tertinggi ke terendah.
    df = df.sample(frac=1).sort_values(by="safety_score", ascending=False).reset_index(drop=True)

    # ==========================================
    # 4. FILTER MAKSIMAL 1 PRODUK PER BRAND
    # ==========================================
    results = []
    brand_counts = {}

    for _, r in df.iterrows():
        # Berhenti jika sudah mencapai jumlah yang diminta (misal 7)
        if len(results) >= top_k:
            break
            
        row = r.to_dict()
        brand_name = row.get("Brand", "Unknown")

        # LOGIKA INTI: Jika brand ini sudah ada di daftar, lewati cari brand lain
        if brand_counts.get(brand_name, 0) >= 1:
            continue

        # ---- PROSES NOTES (Peringatan Otomatis) ----
        notes = []
        if not bool(row.get("Fragrance-Free")):
            notes.append("Produk ini mengandung fragrance, sebaiknya dihindari jika kulit sangat sensitif.")
        if not bool(row.get("Alcohol-Free")):
            notes.append("Produk ini mengandung alkohol, perhatikan bila kulit mudah kering atau iritasi.")
        if not bool(row.get("Non-Comedogenic")):
            notes.append("Produk ini berpotensi comedogenic, kurang cocok jika mudah berjerawat.")
        
        # Tambahkan catatan manual dari dataset jika ada
        if row.get("Catatan") and str(row.get("Catatan")).lower() != "nan":
            notes.append(str(row.get("Catatan")).strip())

        results.append({
            "nama": row.get("Nama Produk", ""),
            "brand": row.get("Brand", ""),
            "kategori": row.get("Kategori", ""),
            "kandungan": row.get("Kandungan Utama", ""),
            "image_url": get_image_path(
                row.get("Kategori", "").strip(),
                row.get("Nama Produk", "").strip(),
                row.get("Gambar") or row.get("image") or ""
            ),
            "alcohol_free": bool(row.get("Alcohol-Free")),
            "fragrance_free": bool(row.get("Fragrance-Free")),
            "non_comedogenic": bool(row.get("Non-Comedogenic")),
            "note": notes
        })

        # Tandai bahwa brand ini sudah diambil
        brand_counts[brand_name] = 1

    return results

# -------------------------
# Load Skin Mapping JSON
# -------------------------
import json

SKIN_MAP = {}

def load_skin_mapping():
    global SKIN_MAP
    json_path = BASE_DIR / "static" / "skin_mapping.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                SKIN_MAP = json.load(f)
            print("[SKIN MAP] Berhasil load skin_mapping.json")
        except Exception as e:
            print("[SKIN MAP] Error saat membaca JSON:", e)
    else:
        print("[SKIN MAP] File skin_mapping.json belum ada.")

load_skin_mapping()

# -------------------------
# SESSION & COOKIE HANDLER
# -------------------------
@app.before_request
def init_session_id():

    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

@app.after_request
def add_chat_uid_cookie(response):
    if "chat_uid" not in request.cookies:
 
        response.set_cookie("chat_uid", str(uuid.uuid4()), max_age=30*24*3600)
    return response

@app.route("/api/chatbot/reset", methods=["POST"])
def reset_chatbot():
    user_id = session.get("user_id")
    if user_id in USER_MEMORY:
        del USER_MEMORY[user_id] # Hapus riwayat dari memori global


    # session.pop("user_id", None) 

    return jsonify({"status": "success", "message": "Percakapan telah direset."})

# -------------------------
# ROUTES
# -------------------------
@app.route("/")
def page_home():
    all_df = pd.concat(list(DATASET.values())) if DATASET else pd.DataFrame()
    brands = sorted(all_df["Brand"].dropna().unique().tolist()) if "Brand" in all_df.columns else []
    categories = sorted(all_df["Kategori"].dropna().unique().tolist()) if "Kategori" in all_df.columns else []

    # Ambil parameter filter
    search = request.args.get("search")
    selected_brands = request.args.getlist("brand")
    selected_categories = request.args.getlist("kategori")
    alcohol_free = request.args.get("alcohol_free") == "true"
    fragrance_free = request.args.get("fragrance_free") == "true"
    non_comedogenic = request.args.get("non_comedogenic") == "true"

    if "Brand" in all_df.columns:
        all_df["Brand"] = all_df["Brand"].astype(str).str.strip().str.upper()
        selected_brands = [b.upper() for b in selected_brands]


    # Apply filter
    df_filtered = filter_produk(
        all_df,
        search=search,
        brands=selected_brands,
        categories=selected_categories,
        alcohol_free=alcohol_free,
        fragrance_free=fragrance_free,
        non_comedogenic=non_comedogenic
    )

    # Hapus duplikat
    df_filtered = df_filtered.drop_duplicates(subset=["Nama Produk"])

    # Fallback: kalau filter kosong, ambil default 6 produk
    if df_filtered.empty:
        df_filtered = all_df.drop_duplicates(subset=["Nama Produk"]).head(6)

    # Ambil 6 produk pertama
    items = []
    for _, r in df_filtered.head(6).iterrows():
        items.append({
        "nama": r.get("Nama Produk", ""),
        "brand": r.get("Brand", ""),
        "kategori": r.get("Kategori", ""),
        "kandungan": r.get("Kandungan Utama", ""),
        "image_url": get_image_path(
            r.get("Kategori", ""),
            r.get("Nama Produk", ""),
            r.get("Gambar") or r.get("image", "")
        ),
        "manfaat": generate_product_benefits(
                r.get("Kandungan Utama", ""),
                r.get("Kategori", "")
        ),
        "alcohol_free": str(r.get("Alcohol-Free", "")).strip().lower() == "yes",
        "fragrance_free": str(r.get("Fragrance-Free", "")).strip().lower() == "yes",
        "non_comedogenic": str(r.get("Non-Comedogenic", "")).strip().lower() == "yes",
    })

    return render_template(
        "home.html",
        items=items,
        brands=brands,
        categories=categories,
        search=search,        
        selected_brands=selected_brands, 
        selected_categories=selected_categories, 
        alcohol_free=alcohol_free,
        fragrance_free=fragrance_free,
        non_comedogenic=non_comedogenic,
        request=request
)

@app.route("/produk")
@app.route("/produk/page/<int:page>")
def page_produk(page=1):
    all_df = pd.concat(list(DATASET.values())) if DATASET else pd.DataFrame()

    brands = sorted(all_df["Brand"].dropna().unique().tolist()) if "Brand" in all_df.columns else []
    categories = sorted(all_df["Kategori"].dropna().unique().tolist()) if "Kategori" in all_df.columns else []

    # =============================
    # Ambil filter dari query string
    # =============================
    search = request.args.get("search")
    selected_brands = request.args.getlist("brand")
    selected_categories = request.args.getlist("kategori")

    alcohol_free = request.args.get("alcohol_free") == "true"
    fragrance_free = request.args.get("fragrance_free") == "true"
    non_comedogenic = request.args.get("non_comedogenic") == "true"

    # Normalisasi brand
    if "Brand" in all_df.columns:
        all_df["Brand"] = all_df["Brand"].astype(str).str.strip().str.upper()
        selected_brands = [b.upper() for b in selected_brands]

    # =============================
    # Apply filter
    # =============================
    df_filtered = filter_produk(
        all_df,
        search=search,
        brands=selected_brands,
        categories=selected_categories,
        alcohol_free=alcohol_free,
        fragrance_free=fragrance_free,
        non_comedogenic=non_comedogenic
    )

    df_filtered = df_filtered.drop_duplicates(subset=["Nama Produk"]).reset_index(drop=True)

    # =============================
    # Pagination
    # =============================
    per_page = 12
    total = len(df_filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)

    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    df_page = df_filtered.iloc[start:end]

    # =============================
    # Build items
    # =============================
    items = []
    for _, r in df_page.iterrows():
        items.append({
            "nama": r.get("Nama Produk", ""),
            "brand": r.get("Brand", ""),
            "kategori": r.get("Kategori", ""),
            "kandungan": r.get("Kandungan Utama", ""),
            "image_url": get_image_path(
                r.get("Kategori", ""),
                r.get("Nama Produk", ""),
                r.get("Gambar") or r.get("image", "")
            ),
            "manfaat": generate_product_benefits(
                r.get("Kandungan Utama", ""),
                r.get("Kategori", "")
            ),
            "alcohol_free": bool(r.get("Alcohol-Free")),
            "fragrance_free": bool(r.get("Fragrance-Free")),
            "non_comedogenic": bool(r.get("Non-Comedogenic")),
        })

    return render_template(
        "produk.html",
        brands=brands,
        categories=categories,
        items=items,
        search=search,
        selected_brands=selected_brands,
        selected_categories=selected_categories,
        alcohol_free=alcohol_free,
        fragrance_free=fragrance_free,
        non_comedogenic=non_comedogenic,
        page=page,
        total_pages=total_pages,
        request=request
    )

def filter_produk(
    df,
    search=None,
    brands=None,
    categories=None,
    alcohol_free=False,
    fragrance_free=False,
    non_comedogenic=False
):
    df = df.copy()

    if search:
        s = search.lower()
        df = df[
            df["Nama Produk"].astype(str).str.lower().str.contains(s, na=False) |
            df["Kandungan Utama"].astype(str).str.lower().str.contains(s, na=False)
        ]

    if brands:
        df = df[df["Brand"].isin(brands)]

    if categories:
        df["Kategori"] = df["Kategori"].astype(str).str.lower().str.replace(" ", "")
        categories = [c.lower().replace(" ", "") for c in categories]
        df = df[df["Kategori"].isin(categories)]

    if alcohol_free:
        df = df[df["Alcohol-Free"] == True]

    if fragrance_free:
        df = df[df["Fragrance-Free"] == True]

    if non_comedogenic:
        df = df[df["Non-Comedogenic"] == True]

    return df

@app.route("/chatbot")
def page_chatbot():
    return render_template("chatbot.html")

@app.route("/tentang")
def page_tentang():
    return render_template("tentang.html")

@app.route("/rekomendasi")
def page_rekomendasi():
    return render_template("rekomendasi.html")


# -------------------------
# API: Produk
# -------------------------

PRODUCT_BENEFIT_RULES = {
    # =====================
    # BRIGHTENING & SPOT
    # =====================
    "niacinamide": ["membantu mencerahkan kulit", "menyamarkan bekas jerawat", "memperkuat skin barrier"],
    "vitamin c": ["membantu mencerahkan kulit", "meratakan warna kulit", "melindungi dari radikal bebas"],
    "ascorbic acid": ["membantu mencerahkan kulit", "meratakan warna kulit"],
    "alpha arbutin": ["membantu memudarkan flek hitam", "meratakan warna kulit"],
    "tranexamic acid": ["membantu memudarkan bekas jerawat", "meratakan warna kulit"],
    "licorice": ["membantu mencerahkan kulit", "menenangkan kulit"],
    "glutathione": ["membantu mencerahkan kulit"],
    "mulberry extract": ["membantu mencerahkan kulit", "menyamarkan flek hitam"],
    "bearberry": ["membantu mencerahkan kulit", "memudarkan flek hitam"],
    "phenylethyl resorcinol": ["membantu mencerahkan kulit", "memudarkan flek hitam"],
    "alpha arbutin 2%": ["membantu memudarkan flek hitam", "meratakan warna kulit"],
    "alpha arbutin 3%": ["membantu memudarkan flek hitam", "meratakan warna kulit"],
    "ferulic acid": ["sebagai antioksidan", "membantu mencerahkan kulit"],
    "bright berries": ["sebagai antioksidan", "membantu mencerahkan kulit"],
    "summer plum": ["membantu mencerahkan kulit", "sebagai antioksidan"],
    "vitamin b3": ["membantu mencerahkan kulit", "menyamarkan bekas jerawat"],
    "edelweiss extract": ["membantu mencerahkan kulit", "melindungi skin barrier"],
    "crystal-white active": ["membantu mencerahkan kulit hingga lapisan dalam"],
    "silver vine extract": ["membantu mencerahkan kulit", "meningkatkan skin translucency"],
    "niacinamide + sakura": ["membantu mencerahkan kulit", "memberikan efek glowing"],
    "advanced niacinamide": ["membantu mencerahkan kulit", "melindungi dari blue light"],
    "alpha arbutin + niacinamide": ["membantu mencerahkan kulit", "memudarkan flek hitam"],
    "vitamin b3 + licorice": ["membantu mencerahkan kulit", "menyamarkan bekas jerawat"],
    "kojic acid": ["membantu memudarkan flek hitam", "mencerahkan kulit"],
    "14x brightening booster": ["membantu mencerahkan kulit secara intensif", "menyamarkan noda hitam"],
    "sweet cherry extract": ["membantu mencerahkan kulit", "sebagai antioksidan"],
    "extract vit b3": ["membantu mencerahkan kulit", "mengecilkan pori-pori"],
    "vitamin beads": ["membantu menutrisi kulit", "mencerahkan kulit"],
    "silver vine": ["membantu mencerahkan kulit", "meningkatkan skin translucency"],
    "brightening peptide": ["membantu mencerahkan kulit", "meratakan warna kulit"],
    "4x berries bright": ["membantu mencerahkan kulit", "sebagai antioksidan"],
    "20x brightening booster": ["membantu mencerahkan kulit secara intensif"],
    "actiwhite™": ["membantu mencerahkan kulit", "menghambat pembentukan melanin"],
    "oxyresveratrol": ["membantu mencerahkan kulit dengan kuat", "sebagai antioksidan"],
    "starfish essence": ["membantu mencerahkan kulit", "mempercepat regenerasi kulit"],
    "bio-highlighter peptide": ["memberikan efek glowing", "menghaluskan tekstur kulit"],
    "alpha arbutin 5%": ["membantu mencerahkan kulit", "memudarkan flek hitam membandel"],
    "17x brightening booster": ["membantu mencerahkan kulit secara intensif", "meratakan warna kulit"],
    "alpha arbutin 1%": ["membantu mencerahkan kulit", "menyamarkan noda hitam"],
    "kombucha": ["sebagai antioksidan", "membantu meningkatkan kecerahan alami kulit"],
    "carrot": ["sebagai antioksidan", "membantu mencerahkan kulit kusam"],
    "raspberry": ["melindungi kulit dari radikal bebas", "menjaga kesehatan kulit"],
    "terminalia ferdinandiana": ["sebagai sumber vitamin C alami", "membantu mencerahkan wajah"],
    "pomegranate": ["membantu menutrisi kulit", "sebagai anti-aging alami"],
    "kale": ["sebagai superfood untuk nutrisi kulit", "membantu detoksifikasi"],

    # =====================
    # FIRMING & PLUMPING
    # =====================
    "collagen peptide": ["menjaga elastisitas kulit", "membuat kulit kenyal", "memberikan efek firming"],
    "oat extract": ["menenangkan kulit", "menjaga kelembapan"],
    "skin-plumping peptide": ["menjaga elastisitas kulit", "membuat kulit kenyal"],

    # =====================
    # ACNE & OIL CONTROL
    # =====================
    "salicylic acid": ["membantu mengatasi jerawat", "membersihkan pori-pori"],
    "azelaic acid": ["membantu mengatasi jerawat", "menyamarkan bekas jerawat"],
    "tea tree": ["membantu meredakan jerawat", "mengurangi minyak berlebih"],
    "zinc": ["membantu mengontrol minyak berlebih"],
    "niacinamide zinc": ["membantu mengontrol minyak", "mengatasi jerawat"],
    "benzoyl peroxide": ["membantu membunuh bakteri penyebab jerawat", "mengurangi inflamasi"],
    "niacinamide 10%": ["membantu mengontrol minyak", "menenangkan kulit", "menyamarkan bekas jerawat"],
    "salicylic acid 2%": ["membantu mengatasi jerawat", "membersihkan pori-pori"],
    "zinc gluconate": ["membantu mengontrol minyak", "mengurangi inflamasi jerawat"],
    "d-panthenol": ["menenangkan kulit", "menjaga kelembapan"],
    "witch hazel": ["membantu meringkas pori-pori", "mengontrol minyak berlebih"],
    "succinic acid": ["membantu mengatasi jerawat dengan lembut", "mengontrol produksi sebum"],
    "mild bha": ["membersihkan pori-pori", "mengangkat sel kulit mati tanpa iritasi"],
    "mineral powder": ["membantu menyerap minyak berlebih", "memberikan efek halus pada kulit"],
    "potassium azeloyl diglycinate": ["membantu mencerahkan bekas jerawat", "mengontrol minyak wajah"],
    "salix nigra bark extract": ["sebagai eksfoliator alami", "membantu merawat kulit berjerawat"],
    "cinnamon bark extract": ["membantu mengontrol minyak", "sebagai anti-bakteri alami"],

    # =====================
    # SOOTHING & SENSITIVE
    # =====================
    "centella": ["menenangkan kulit", "mengurangi kemerahan"],
    "cica": ["menenangkan kulit", "mengurangi kemerahan"],
    "panthenol": ["menenangkan kulit", "menjaga kelembapan"],
    "allantoin": ["menenangkan kulit yang iritasi", "menjaga kelembapan"],
    "green tea": ["menenangkan kulit", "melindungi dari radikal bebas"],
    "aloe vera": ["menenangkan kulit", "menjaga kelembapan"],
    "chamomile": ["menenangkan kulit"],
    "beta glucan": ["menenangkan kulit", "menjaga kelembapan"],
    "shea butter": ["melembapkan kulit", "menenangkan kulit"],
    "jojoba oil": ["menenangkan kulit", "melembapkan kulit"],
    "mugwort": ["menenangkan kulit", "mengurangi kemerahan"],
    "madecassoside": ["menenangkan kulit", "memperbaiki skin barrier"],
    "cicapro": ["menenangkan kulit", "memperbaiki skin barrier"],
    "centella asiatica": ["menenangkan kulit", "mengurangi kemerahan", "memperbaiki skin barrier"],
    "cica complex": ["menenangkan kulit", "mengurangi kemerahan"],
    "prebiotic": ["menenangkan kulit", "menyeimbangkan mikrobioma kulit"],
    "heartleaf": ["menenangkan kemerahan", "membantu detoksifikasi kulit"],
    "hpr": ["menyamarkan tanda penuaan dengan minim iritasi", "membantu meremajakan kulit"],
    "synchrolife": ["melindungi kulit dari efek blue light", "mengurangi tanda-tanda kulit lelah"],
    "polygonum cuspidatum": ["sebagai antioksidan kuat", "membantu menenangkan kulit"],
    "camellia sinensis": ["membantu menenangkan kulit", "sebagai antioksidan (Green Tea)"],
    "rosmarinus officinalis": ["membantu menenangkan kulit", "sebagai anti-inflamasi alami"],
    "seaweed": ["membantu menutrisi kulit", "menenangkan dan menghidrasi"],

    # =====================
    # HYDRATION & BARRIER
    # =====================
    "hyaluronic acid": ["menjaga kelembapan kulit", "menghidrasi lapisan kulit"],
    "sodium hyaluronate": ["menjaga kelembapan kulit"],
    "glycerin": ["menjaga kelembapan kulit", "melembutkan kulit"],
    "ceramide": ["memperbaiki skin barrier", "mengunci kelembapan"],
    "cholesterol": ["membantu memperbaiki skin barrier"],
    "squalane": ["menjaga kelembapan kulit", "melembutkan kulit"],
    "urea": ["menjaga kelembapan kulit"],
    "panthenol 5%": ["menjaga kelembapan kulit", "menenangkan kulit"],
    "quadruple hydration system": ["membantu menghidrasi kulit", "menjaga kelembapan"],
    "hyaluronic": ["menjaga kelembapan kulit", "menghidrasi lapisan kulit"],
    "squalane+": ["menjaga kelembapan kulit", "melembutkan kulit"],
    "oxybiome": ["menenangkan kulit", "menjaga keseimbangan mikrobioma kulit"],
    "moistprime tech": ["menjaga kelembapan kulit"],
    "aquaxyl": ["membantu menghidrasi kulit", "mengunci kelembapan"],
    "triple protection+": ["melindungi kulit", "menjaga kelembapan kulit"],
    "14x hyaluron": ["menghidrasi kulit secara mendalam", "mengunci kelembapan"],
    "pentavitin": ["menjaga kelembapan hingga 72 jam", "memperbaiki skin barrier"],
    "deep water restore": ["menghidrasi kulit", "menenangkan kulit"],
    "cica complex + panthenol": ["menenangkan kemerahan", "memperbaiki skin barrier"],
    "nmf amino": ["menjaga kelembapan alami kulit", "memperkuat skin barrier"],
    "72h hydration active": ["menghidrasi kulit secara mendalam", "mengunci kelembapan"],
    "triple hydrating": ["menghidrasi berbagai lapisan kulit", "menjaga kelembapan"],
    "smart micro-foam complex": ["melembapkan kulit", "membersihkan dengan lembut", "menenangkan kulit"],
    "17x amino acid complex": ["menutrisi kulit", "menjaga elastisitas dan barrier"],
    "moisture magnet agent": ["mengunci kelembapan", "mencegah kulit dehidrasi"],
    "bio-hyaluronic acid": ["menghidrasi kulit secara intensif"],
    "rosebay willowherb": ["menenangkan kulit", "mengurangi kemerahan"],
    "multi probiome": ["menyeimbangkan mikrobioma kulit", "memperkuat barrier"],
    "stress relief agent": ["menenangkan kulit yang lelah"],
    "aqua ceramide 2%": ["memperbaiki skin barrier", "menjaga kadar air"],
    "11x ha": ["menghidrasi di berbagai lapisan kulit"],
    "allantoin": ["membantu menenangkan kulit iritasi", "menjaga kelembapan kulit"],
    "bisabolol": ["menenangkan kemerahan", "melindungi kulit sensitif"],
    "d-panthenol": ["menenangkan kulit", "membantu proses pemulihan barrier kulit"],
    "pure rose water": ["membantu menenangkan kulit", "menghidrasi dan menyegarkan wajah"],
    "real rose petal": ["memberikan kelembapan ekstra", "sebagai antioksidan alami"],
    "pga": ["menghidrasi kulit secara mendalam", "menjaga elastisitas kulit"],
    "hyacross 2%": ["membentuk lapisan pelindung kelembapan", "menghidrasi kulit lebih lama"],
    "marine collagen 5%": ["menjaga kekenyalan kulit", "menghidrasi kulit secara intensif"],
    "vegan dna pentavitin": ["menjaga kelembapan hingga 72 jam", "membantu memperbaiki skin barrier"],
    "97% galactomyces ferment filtrate": ["membantu mencerahkan kulit", "mengecilkan pori-pori", "meratakan tekstur"],
    "galactomyces": ["membantu mencerahkan kulit", "meningkatkan kejernihan tekstur kulit"],
    "ice plant extract": ["memberikan sensasi dingin", "menenangkan dan menghidrasi kulit"],
    "betaine": ["menghidrasi kulit", "membantu mencegah iritasi"],
    "probiotics 9 complex": ["membantu menjaga keseimbangan mikrobioma kulit", "memperkuat skin barrier"],

    # =====================
    # ANTI AGING
    # =====================
    "retinol": ["menyamarkan tanda penuaan", "meratakan tekstur kulit"],
    "retinal": ["menyamarkan tanda penuaan"],
    "bakuchiol": ["menyamarkan tanda penuaan", "meratakan tekstur kulit"],
    "peptide": ["menjaga elastisitas kulit"],
    "adenosine": ["menyamarkan garis halus"],
    "collagen": ["menjaga elastisitas kulit"],
    "resveratrol": ["sebagai antioksidan", "melindungi kulit dari penuaan"],
    "matrixyl 3000": ["menyamarkan garis halus", "menjaga elastisitas kulit", "meningkatkan produksi kolagen"],
    "peptide complex": ["menjaga elastisitas kulit", "mengurangi tanda penuaan"],
    "retinolsome 0.5%": ["menyamarkan tanda penuaan", "meratakan tekstur kulit"],
    "multi peptide": ["menjaga elastisitas kulit", "mengurangi kerutan"],
    "gold-peptide crystals": ["membantu anti-aging", "meningkatkan elastisitas kulit"],
    "youth glow active": ["membantu anti-aging", "meningkatkan kecerahan kulit"],
    "argireline™ peptide": ["menyamarkan garis halus", "memberikan efek mirip botox"],
    "mosscelltec™ no.1": ["memperkuat ketahanan kulit", "membantu anti-aging"],
    "vegan retinalt booster": ["mempercepat regenerasi kulit", "anti-aging tanpa iritasi"],
    "biotech recombinant collagen": ["menjaga kekenyalan kulit", "memberikan efek firming"],
    "immortelle flower oil": ["membantu anti-aging", "merevitalisasi kulit"],
    "actosome retinol": ["menyamarkan tanda penuaan", "meratakan tekstur kulit"],

    # =====================
    # EXFOLIATION & TEXTURE
    # =====================
    "glycolic acid": ["mengangkat sel kulit mati", "meratakan tekstur kulit"],
    "lactic acid": ["mengangkat sel kulit mati", "menjaga kelembapan kulit"],
    "mandelic acid": ["mengangkat sel kulit mati"],
    "pha": ["mengangkat sel kulit mati dengan lembut"],
    "bha": ["mengangkat sel kulit mati", "membersihkan pori-pori"],
    "aha": ["mengangkat sel kulit mati", "meratakan tekstur kulit"],
    "pha 5%": ["mengangkat sel kulit mati dengan lembut"],
    "lactic acid 10%": ["mengangkat sel kulit mati", "menjaga kelembapan kulit"],
    "mandelic acid 5%": ["mengangkat sel kulit mati"],
    "clarifying mineral": ["membersihkan pori-pori", "menyegarkan kulit"],
    "carboactiv": ["membantu detoks kulit", "meningkatkan tekstur kulit"],

    # =====================
    # SUNSCREEN & PROTECTION
    # =====================
    "zinc oxide": ["melindungi kulit dari sinar UV", "mencegah kerusakan akibat UVA/UVB"],
    "titanium dioxide": ["melindungi kulit dari sinar UV"],
    "octinoxate": ["melindungi kulit dari sinar UV"],
    "tinosorb": ["melindungi kulit dari sinar UV"],
    "avobenzone": ["melindungi kulit dari sinar UVA", "mencegah kerusakan kulit"],
    "spf 15 pa++": ["melindungi kulit dari paparan sinar UV"],
    "spf 30 pa+++": ["melindungi kulit dari paparan sinar UV"],
    "spf 35 pa+++": ["melindungi kulit dari paparan sinar UV"],
    "spf 50 pa++++": ["melindungi kulit dari paparan sinar UV"],
    "broad spectrum protection": ["melindungi kulit dari paparan sinar UVA & UVB"],

    # =====================
    # VITAMINS & EXTRACTS
    # =====================
    "8x essential vitamins": ["sebagai antioksidan", "menjaga kesehatan kulit"],
    "5x peptides": ["meningkatkan elastisitas kulit", "membantu anti-aging"],
    "rose oil": ["menenangkan kulit", "menghidrasi kulit"],
    "rose water": ["menenangkan kulit", "melembapkan kulit"],
    "marigold extract": ["menenangkan kulit", "mengurangi kemerahan"],
    "vitamin e": ["sebagai antioksidan", "menjaga kelembapan kulit"],
    "caffeine": ["mengurangi bengkak", "menenangkan kulit"],
    "coenzyme q10": ["sebagai antioksidan", "mengurangi tanda penuaan"],
    "licorice root extract": ["membantu mencerahkan kulit", "menenangkan kulit"],
    "green tea extract": ["menenangkan kulit", "melindungi dari radikal bebas"],
    "calendula": ["menenangkan kulit", "mengurangi kemerahan"],
    "amino ectoin": ["menjaga kelembapan kulit", "melindungi dari stres lingkungan"],

    # =====================
    # SPECIFIC NIACINAMIDE
    # =====================
    "niacinamide 5%": ["membantu mencerahkan kulit", "menyamarkan bekas jerawat", "menenangkan kulit"],
    "niacinamide 7%": ["membantu mencerahkan kulit", "menyamarkan bekas jerawat", "menenangkan kulit"],
    "niacinamide 12%": ["membantu mencerahkan kulit", "menyamarkan bekas jerawat", "menenangkan kulit"],
    "niacinamide 2%": ["membantu mencerahkan kulit", "menyamarkan bekas jerawat"],
    "niacinamide b3": ["membantu mencerahkan kulit", "menyamarkan bekas jerawat", "menenangkan kulit"]
}


CATEGORY_BASE_BENEFITS = {
    "facialwash": [
        "Membantu membersihkan kulit dari kotoran, minyak, dan sisa makeup",
        "Membantu menjaga kebersihan pori-pori"
    ],
    "toner": [
        "Membantu menyegarkan kulit setelah membersihkan wajah",
        "Membantu mempersiapkan kulit sebelum tahap skincare selanjutnya"
    ],
    "serum": [
        "Membantu merawat permasalahan kulit secara lebih intensif",
        "Membantu memberikan nutrisi aktif ke dalam kulit"
    ],
    "moisturizer": [
        "Membantu menjaga kelembapan kulit",
        "Membantu memperkuat lapisan pelindung kulit"
    ],
    "sunscreen": [
        "Membantu melindungi kulit dari paparan sinar matahari",
        "Membantu mencegah kerusakan kulit akibat sinar UV"
    ]
}

@app.route("/api/produk", methods=["GET"])
def api_produk():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip().lower()
    brand = request.args.get("brand", "").strip()

    # Normalisasi kategori (sudah benar)
    catmap = {
        "facial wash": "facial_wash",
        "facialwash": "facial_wash",
        "facial_wash": "facial_wash",
        "moisturizer": "moisturizer",
        "serum": "serum",
        "sunscreen": "sunscreen",
        "toner": "toner"
    }
    category = catmap.get(category, category)

    # Ambil filter preferensi dari query string
    # Dibuat lebih aman dengan mengecek beberapa variasi input
    def is_true(val):
        return str(val).strip().upper() in ["YES", "TRUE", "1", "ON"]

    prefs = {
        "Alcohol-Free": is_true(request.args.get("alcohol_free", "")),
        "Fragrance-Free": is_true(request.args.get("fragrance_free", "")),
        "Non-Comedogenic": is_true(request.args.get("non_comedogenic", "")),
    }

    # Ambil dataframe berdasarkan kategori
    if category and category in DATASET:
        df = DATASET[category].copy()
    else:
        # Jika kategori tidak spesifik, gabungkan semua dataset yang ada
        df = pd.concat(list(DATASET.values())) if DATASET else pd.DataFrame()

    if df.empty:
        return jsonify({"items": [], "count": 0})

    # Terapkan filter (fungsi apply_filters yang kamu buat sebelumnya)
    df = apply_filters(df, q=q, brand=brand, prefs=prefs)
    
    # Ambil top 60 saja biar gak berat pas loading di browser
    df = df.head(60)

    items = []
    for _, r in df.iterrows():
        # Ambil path gambar (pake fungsi get_image_path yang kita bahas tadi)
        img_col = r.get("Gambar") or r.get("image") or ""
        
        items.append({
            "nama": r.get("Nama Produk", ""),
            "brand": r.get("Brand", ""),
            "kategori": r.get("Kategori", ""),
            "kandungan": r.get("Kandungan Utama", ""),
            # Konversi value ke boolean murni untuk frontend
            "alcohol_free": is_true(r.get("Alcohol-Free")),
            "fragrance_free": is_true(r.get("Fragrance-Free")),
            "non_comedogenic": is_true(r.get("Non-Comedogenic")),
            "image_url": get_image_path(
                r.get("Kategori", ""),
                r.get("Nama Produk", ""),
                img_col
            )
        })
    
    return jsonify({"items": items, "count": len(items)})

def generate_product_benefits(kandungan_text, kategori):
    manfaat = []

    if not isinstance(kandungan_text, str):
        kandungan_text = ""

    # 1️⃣ Manfaat dasar dari kategori produk
    kategori = str(kategori).lower()
    base_benefits = CATEGORY_BASE_BENEFITS.get(kategori, [])
    for b in base_benefits:
        if b not in manfaat:
            manfaat.append(b)

    # 2️⃣ Manfaat dari kandungan utama
    if kandungan_text and isinstance(kandungan_text, str):
        kandungan_text = kandungan_text.lower()
        for ingredient, benefits in PRODUCT_BENEFIT_RULES.items():
            if ingredient in kandungan_text:
                for b in benefits:
                    if b not in manfaat:
                        manfaat.append(b)

    if not manfaat:
        return "Membantu merawat dan menjaga kesehatan kulit."

    manfaat = manfaat[:4]

    if len(manfaat) == 1:
        return manfaat[0] + "."
    elif len(manfaat) == 2:
        return manfaat[0] + " dan " + manfaat[1].lower() + "."
    else:
        return (
            ", ".join(manfaat[:-1])
            + ", dan "
            + manfaat[-1].lower()
            + "."
        )

# -------------------------
# API: Rekomendasi
# -------------------------
@app.route("/api/rekomendasi", methods=["POST"])
def api_rekomendasi():
    data = request.get_json(silent=True) or {}

    category = (data.get("category") or "").lower()
    jenis_kulit = data.get("jenis_kulit") or ""
    masalah_kulit = data.get("masalah_kulit") or []

    prefs_input = data.get("preferences") or {}
    prefs = {
        "Alcohol-Free": prefs_input.get("alcohol_free", False),
        "Fragrance-Free": prefs_input.get("fragrance_free", False),
        "Non-Comedogenic": prefs_input.get("non_comedogenic", False),
    }

    raw_results = recommend(category, jenis_kulit, masalah_kulit, prefs, top_k=10)

    items = []
    for r in raw_results:
        img_col = r.get("Gambar") or r.get("image") or ""

        items.append({
            **r,
            "image_url": get_image_path(
                r.get("Kategori", ""),
                r.get("Nama Produk", ""),
                img_col
            )
        })

    return jsonify({"items": items})


# -------------------------
# API: Brands
# -------------------------
@app.route("/api/brands", methods=["GET"])
def api_brands():
    all_df = pd.concat(list(DATASET.values())) if DATASET else pd.DataFrame()
    brands = sorted(all_df["Brand"].dropna().unique().tolist()) if "Brand" in all_df.columns else []
    return jsonify({"brands": brands})


# ============================================================ 
# API CHATBOT 
# ============================================================

STATE_MEMORY = {}

def init_state():
    return {
        "skin_type": None,
        "problem": [],
        "ingredients": [],
        "brand": None,
        "requested_benefit": None,

        "current_category": None,
        "last_ingredient": None,

        "mode_info": False,
        "mode_rekomendasi": False,
        "context_followup": None,

        # >>> TAMBAHAN INI <<<
        "last_index": 0,
        "last_user_input": "",

        "dataset": CHATBOT_DATASET
    }

# =========================
# ROUTE CHATBOT
# =========================
@app.route("/api/chatbot", methods=["POST"])
def chatbot_api():
    data = request.json or {}
    # Ambil session_id yang dikirim frontend
    session_id = data.get("session_id")
    user_message_raw = (data.get("message") or "").strip()

    # Logika Session Lock
    if session_id and session_id in STATE_MEMORY:
        state = STATE_MEMORY[session_id]
        print(f"✅ Melanjutkan Session: {session_id}")
    else:
        session_id = session_id or str(uuid.uuid4())
        STATE_MEMORY[session_id] = init_state()
        state = STATE_MEMORY[session_id]
        print(f"🆕 Session Baru: {session_id}")

    # Reset Chat
    if any(k in user_message_raw.lower() for k in ["reset", "ulang"]):
        STATE_MEMORY[session_id] = init_state() # Reset isi state-nya saja, ID tetap
        return jsonify({
            "session_id": session_id,
            "reply": "Siapp ✨ Data sudah aku reset. Kamu mau cari produk apa hari ini?"
        })
    
    state["last_user_input"] = user_message_raw.lower()

    reply = chatbot_logic(user_message_raw, state)

    STATE_MEMORY[session_id] = state

    return jsonify({
        "session_id": session_id,
        "reply": reply
    })
# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)












# =====================================================
# CHATBOT LOGIC — FINAL SAFE & CONTEXT-AWARE
# =====================================================
import random
import re
import difflib

# =========================
# IMPORT MAPPING
# =========================
from mapping.problem_mapping import PROBLEM_KEYWORDS
from mapping.skin_mapping import SKIN_TYPES
from mapping.product_mapping import PRODUCT_MAP
from mapping.ingredient_mapping.ingredient_info import INGREDIENT_INFO
from mapping.ingredient_mapping.ingredient_synonyms import INGREDIENT_SYNONYMS
from mapping.ingredient_rules.ingredient_interactions import INGREDIENT_INTERACTIONS
from mapping.ingredient_rules.kandungan_dalam_produk import KANDUNGAN_DALAM_PRODUK
from mapping.ingredient_rules.ingredient_suggestion import INGREDIENT_SUGGESTION
from mapping.product.product_benefit_mapping import PRODUCT_BENEFIT_RULES, CATEGORY_BASE_BENEFITS

# =========================
# KONFIGURASI
# =========================
SUPPORTED_BRANDS = ["wardah", "emina", "avoskin", "azarine", "erha", "npure", "elsheskin"]

OPENING_VARIANTS = [
    "Oke, aku bantu ya ✨",
    "Siap, kita bahas pelan-pelan 😊",
    "Baik, aku jelaskan ya 👌",
    "Ini yang bisa aku rekomendasikan ✨"
]

PRODUCT_MAP = {
    "facialwash": ["facial wash", "sabun muka"],
    "toner": ["toner"],
    "serum": ["serum"],
    "moisturizer": ["moisturizer", "pelembab"],
    "sunscreen": ["sunscreen", "sunblock"]
}

CATEGORY_TEXT = {
    "facialwash": "Facial Wash",
    "toner": "Toner",
    "serum": "Serum",
    "moisturizer": "Moisturizer",
    "sunscreen": "Sunscreen"
}

# =====================================================
# UTIL TEKS
# =====================================================
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = "".join(c if c.isalnum() or c.isspace() else " " for c in text)
    return " ".join(text.split())

def detect_from_mapping(text, mapping):
    results = []
    for key, keywords in mapping.items():
        for kw in keywords:
            if kw in text:
                results.append(key)
                break
    return results

def map_problem_display(raw_text):
    raw = raw_text.lower()
    detected_displays = [] # Pakai list untuk menampung banyak masalah
    
    # Gunakan IF yang berdiri sendiri (jangan pakai ELIF agar semua dicek)
    if "bekas jerawat" in raw or "pih" in raw or "pie" in raw: 
        detected_displays.append("bekas jerawat")
    elif "jerawat" in raw or "acne" in raw: # Pakai elif di sini agar "bekas jerawat" tidak terhitung "jerawat" biasa
        detected_displays.append("jerawat")
        
    if "bruntusan" in raw or "beruntusan" in raw: 
        detected_displays.append("bruntusan")
    if "komedo" in raw: 
        detected_displays.append("komedo")
    if "flek" in raw or "noda hitam" in raw: 
        detected_displays.append("flek hitam")
    if "kusam" in raw: 
        detected_displays.append("kulit kusam")
    if "pori" in raw: 
        detected_displays.append("masalah pori-pori") 
    return detected_displays

def normalize_dataset_text(val):
    return str(val).lower().replace("-", " ").replace("_", " ")

def is_gibberish(text):
    text = clean_text(text).lower()
    if not text:
        return True

    # 1. Daftar kata/frasa yang HARUS diizinkan (Navigasi)
    nav_keywords = [
        "yang lain", "produk lainnya", "lagi", "tambah", 
        "berikutnya", "next", "mau", "dong"
    ]

    if any(k in text for k in nav_keywords):
        return False

    # 2. Daftar kata kunci skincare
    all_known_words = (
        list(SKIN_TYPES.keys()) +
        list(PROBLEM_KEYWORDS.keys()) +
        ["serum", "toner", "sunscreen", "facial", "wash", "moisturizer", 
         "pelembab", "manfaat", "fungsi", "sabun muka", "sunblock"]
    )

    for synonyms in INGREDIENT_SYNONYMS.values():
        all_known_words.extend([s.lower() for s in synonyms])

    words = text.split()
    
    # 3. Cek apakah ada kata yang dikenal
    # Kita pakai pengecekan substring agar lebih aman
    has_known_word = any(w in all_known_words for w in words)
    
    if len(words) <= 2 and not has_known_word:
        return True 

    return False

def extract_limit(text, default=3):
    match = re.search(r'\b(\d+)\b', text)
    if match:
        return int(match.group(1))
    return default

def fuzzy_match(text, choices, cutoff=0.8):
    words = text.split()
    for word in words:
        matches = difflib.get_close_matches(word, choices, n=1, cutoff=cutoff)
        if matches:
            return matches[0]
    return None

# =====================================================
# NORMALIZE SKIN TYPE
# =====================================================
def normalize_skin_type(text):
    if "kombinasi" in text:
        return ["berminyak", "kering"]
    if "normal berminyak" in text:
        return ["normal", "berminyak"]
    if "normal kering" in text:
        return ["normal", "kering"]
    return None

# =====================================================
# NORMALIZE PROBLEM BY CATEGORY (UV & SUNSCREEN)
# =====================================================
def normalize_problems_for_category(problems, category):
    # UV tidak dianggap sebagai masalah kulit untuk sunscreen
    if category == "sunscreen":
        return [p for p in problems if p != "uv"]
    return problems

# =====================================================
# DETECT INGREDIENTS
# =====================================================
def detect_ingredients(text: str):
    text = text.lower()
    found = set()

    for main_name, synonyms in INGREDIENT_SYNONYMS.items():
        for s in synonyms:
            pattern = r"\b" + re.escape(s.lower()) + r"\b"
            if re.search(pattern, text):
                found.add(main_name)
                break

    return list(found)

# =====================================================
# NORMALISASI INGREDIENT UNTUK BENEFIT
# =====================================================
def normalize_ingredient_for_benefit(name: str) -> str:
    """
    Normalisasi nama ingredient untuk dicocokkan ke PRODUCT_BENEFIT_RULES:
    - Lowercase
    - Trim spasi
    - Hapus angka dan simbol % di akhir (misal 'Niacinamide 10%' → 'niacinamide')
    """
    name = name.lower().strip()
    name = re.sub(r"[\d%]+", "", name).strip()
    return name

# =====================================================
# AMBIL BENEFIT PRODUK
# =====================================================
def get_product_benefits(product: dict):
    """
    Mengembalikan string manfaat singkat dari kandungan utama produk.
    Menggunakan:
    - PRODUCT_BENEFIT_RULES
    - INGREDIENT_SYNONYMS untuk cek sinonim
    - normalize_ingredient_for_benefit untuk hapus angka/% dan normalisasi
    """
    benefits = []
    ingredients = product.get("Kandungan Utama", "")
    
    if ingredients:
        for ing in [i.strip().lower() for i in ingredients.split(",")]:
            
            canonical_name = None
            for main_name, synonyms in INGREDIENT_SYNONYMS.items():
                if ing == main_name or ing in [s.lower() for s in synonyms]:
                    canonical_name = main_name
                    break
            
            normalized_ing = normalize_ingredient_for_benefit(canonical_name or ing)
            ing_benefits = PRODUCT_BENEFIT_RULES.get(normalized_ing)
            
            if ing_benefits:
                benefits.extend(ing_benefits)

    benefits = list(dict.fromkeys(benefits))
    return ", ".join(benefits) if benefits else "– manfaat singkat belum tersedia"

# =====================================================
# INTENT DETECTION
# =====================================================
def detect_intent(msg: str):
    msg = clean_text(msg)

    # RESET (Paling atas agar selalu bisa interupsi)
    if any(k in msg for k in ["reset", "ulang", "hapus", "mulai lagi"]):
        return "RESET"

    # INTERACTION & ROUTINE
    if any(k in msg for k in ["boleh digabung", "barengan", "gabung", "tumpuk", "campur"]):
        return "INGREDIENT_INTERACTION"

    if any(k in msg for k in ["urutan", "pagi", "malam"]):
        return "ROUTINE"

    # SAFETY & BENEFITS
    if "aman" in msg:
        return "INGREDIENT_SAFETY"

    if any(k in msg for k in ["fungsi", "manfaat", "buat apa", "gunanya"]):
        for _, synonyms in INGREDIENT_SYNONYMS.items():
            if any(syn in msg for syn in synonyms):
                return "INGREDIENT_INFO"
        return "PRODUCT_OR_INGREDIENT_INFO"

    # RECOMMEND BY INGREDIENT (Lebih spesifik)
    if any(k in msg for k in ["produk", "rekomendasi"]) and any(
        syn in msg for syns in INGREDIENT_SYNONYMS.values() for syn in syns
    ):
        return "RECOMMEND_BY_INGREDIENT"
    
    if any(k in msg for k in [
        "lainnya", "yang lain", "produk lain",
        "mau yang lain", "lagi", "tambah",
        "rekomendasi lainnya"
    ]):
        return "MORE_RECOMMEND"

    # RECOMMEND UMUM (Paling bawah sebagai jaring terakhir)
    product_categories = ["serum", "facial wash", "sabun muka", "toner", "moisturizer", "sunscreen", "pelembab"]
    if (
        any(cat in msg for cat in product_categories) or
        any(sk in msg for sk in SKIN_TYPES) or
        any(p in msg for keys in PROBLEM_KEYWORDS.values() for p in keys) or
        any(k in msg for k in ["rekomendasi", "saran", "pakai apa", "dong"])
    ):
        return "RECOMMEND"

    # KANDUNGAN SAJA
    for _, synonyms in INGREDIENT_SYNONYMS.items():
        if any(syn in msg for syn in synonyms):
            return "INGREDIENT_INFO"

    return "UNKNOWN"

# =====================================================
# EXTRACT ENTITIES & UPDATE STATE
# =====================================================
def extract_entities(msg: str, state: dict):
    msg = clean_text(msg)
    prev_category = state.get("current_category")
    detected_skin = []

    # === INIT STATE (WAJIB) ===
    state.setdefault("problem", [])
    state.setdefault("ingredients", [])
    state.setdefault("problem_display", [])
    state.setdefault("current_category", None)
    state.setdefault("skin_type", None)
    state.setdefault("brand", None)

    for cat, kws in PRODUCT_MAP.items():
        if any(kw in msg for kw in kws):
            state["current_category"] = cat
            break

    if prev_category and state.get("current_category") != prev_category:
        state["last_reco_index"] = 0


    if not state["current_category"]:
        all_cat_keywords = [kw for sublist in PRODUCT_MAP.values() for kw in sublist]
        matched_cat = fuzzy_match(msg, all_cat_keywords)

        if matched_cat:
            for cat, kws in PRODUCT_MAP.items():
                if matched_cat in kws:
                    state["current_category"] = cat
                    break

    # === 2. SKIN TYPE ===
    normalized_combo = normalize_skin_type(msg)
    prev_skin_type = state.get("skin_type")
    detected_skin = []

    # 1. Cek normalized_combo dulu (misal "sensitif + berminyak")
    if normalized_combo:
        state["skin_type"] = normalized_combo
    else:
        # 2. Cari skin type dari kata kunci
        for sk, keywords in SKIN_TYPES.items():
            if any(kw in msg for kw in keywords):
                detected_skin.append(sk)
        
        # 3. Set state["skin_type"] jika ada hasil detected_skin
        if detected_skin:
            state["skin_type"] = detected_skin if len(detected_skin) > 1 else detected_skin[0]
        else:
            # 4. Kalau ga ada yang terdeteksi, biarkan tetap prev_skin_type atau None
            state["skin_type"] = prev_skin_type

    # 5. Reset last_reco_index kalau skin type berubah
    if prev_skin_type != state.get("skin_type"):
        state["last_reco_index"] = 0
        state["last_index"] = 0

    # === 3. PROBLEM (UNTUK FILTER DATASET) ===
    detected_problems = detect_from_mapping(msg, PROBLEM_KEYWORDS)
    pure_skin_types = ["sensitif", "normal", "kombinasi", "kering", "minyak", "berminyak"]

    for prob in detected_problems:
        if prob not in pure_skin_types and prob not in state["problem"]:
            state["problem"].append(prob)

    new_displays = map_problem_display(msg)

    for display in new_displays:
        if display not in state["problem_display"]:
            state["problem_display"].append(display)

    # === IMPLISIT BRIGHTENING ===
    if "cerah" in msg or "mencerahkan" in msg or "brightening" in msg:
        if "kusam" not in state["problem"]:
            state["problem"].append("kusam")
        if "kulit kusam" not in state["problem_display"]:
            state["problem_display"].append("kulit kusam")

    # === 4. PROBLEM DISPLAY (UNTUK OUTPUT USER) ===
    new_displays = map_problem_display(msg)
    for display in new_displays:
        if display not in state["problem_display"]:
            state["problem_display"].append(display)

    # === 5. BRAND ===
    for b in SUPPORTED_BRANDS:
        if b in msg:
            state["brand"] = b
            break

    # === 6. INGREDIENT ===
    new_ingredients = detect_ingredients(msg)
    if new_ingredients:
        state["ingredients"] = list(set(state["ingredients"] + new_ingredients))

# =====================================================
# RESPONSE — INGREDIENT
# =====================================================
def ingredient_info_response(found_ingredients, state, user_input=""):
    if not found_ingredients:
        return "Boleh sebutkan nama kandungannya lebih spesifik? 😊"

    raw_input = found_ingredients[0]
    user_input = user_input.lower()
    
    # 1. Cari Nama Canonical
    canonical_name = None
    for main_name, synonyms in INGREDIENT_SYNONYMS.items():
        if raw_input.lower() in [s.lower() for s in synonyms]:
            canonical_name = main_name
            break
    
    if not canonical_name or canonical_name not in INGREDIENT_INFO:
        return f"Aku belum punya info detail tentang **{raw_input}**."

    info = INGREDIENT_INFO[canonical_name]
    display_name = canonical_name if raw_input.lower() == canonical_name.lower() else f"{canonical_name} ({raw_input.capitalize()})"
    
    # ==========================================================
    # LOGIKA REKOMENDASI PRODUK BERDASARKAN KANDUNGAN
    # ==========================================================
    if any(k in user_input for k in ["produk", "apa saja", "rekomendasi", "mau", "cari", "pakai", "serum", "moisturizer", "toner", "facial wash"]):
        
        # 1. Deteksi semua kategori yang ada di input user saat ini
        requested_cats = []
        for cat_key, synonyms in PRODUCT_MAP.items():
            if any(s in user_input.lower() for s in synonyms):
                requested_cats.append(cat_key)
        
        # 2. Jika user tidak menyebutkan kategori di input baru, pakai yang ada di state
        if not requested_cats and state.get("current_category"):
            requested_cats = [state.get("current_category")]

        # 3. JIKA MASIH KOSONG: Tanya kategori berdasarkan KANDUNGAN_DALAM_PRODUK
        if not requested_cats:
            available_cats = KANDUNGAN_DALAM_PRODUK.get(canonical_name.lower(), [])
            if available_cats:
                pretty_cats = [CATEGORY_TEXT.get(c, c.capitalize()) for c in available_cats]
                return (f"**{display_name}** biasanya tersedia dalam bentuk: **{', '.join(pretty_cats)}**.\n\n"
                        f"Kamu lagi cari {display_name} dalam kategori apa? 😊")
        
        # 4. PROSES PENCARIAN (Bisa Multi-Kategori)
        final_segments = []
        limit_match = re.search(r'\b(\d+)\b', user_input)
        limit = int(limit_match.group(1)) if limit_match else 3
        
        user_skin = state.get("skin_type")  # contoh: "berminyak"

        for target_cat in requested_cats:
            all_matches = []
            prods = state.get("dataset", {}).get(target_cat, [])
            
            for p in prods:
                kandungan = str(p.get("Kandungan Utama", "")).lower()
                jenis_kulit = str(p.get("Jenis Kulit", "")).lower()
                nama_produk = str(p.get("Nama Produk", "")).lower()

                if canonical_name.lower() in kandungan:
                    if user_skin and user_skin not in jenis_kulit:
                        continue

                    if user_skin == "kering" and "jerawat" not in state.get("problem", []):
                        if "acne" in nama_produk or "pimple" in nama_produk:
                            continue

                    all_matches.append(p)
            if not all_matches and user_skin:
                return (
                    f"Ada produk dengan **{display_name}**, tapi belum ada yang cocok "
                    f"untuk kulit **{user_skin}** 😢\n"
                    f"Mau aku tampilkan tanpa filter jenis kulit?"
                )

            if all_matches:
                random.shuffle(all_matches)

                offset = state.get("last_index", 0) if len(requested_cats) == 1 else 0
                if any(k in user_input for k in ["lagi", "lainnya", "tambah"]):
                    offset += limit

                selected_prods = all_matches[offset : offset + limit]

                if selected_prods:
                    res_list = [
                        f"- **{p.get('Brand')} {p.get('Nama Produk')}** "
                        f"(Cocok untuk: {p.get('Jenis Kulit')})"
                        for p in selected_prods
                    ]

                    cat_label = CATEGORY_TEXT.get(target_cat, target_cat.capitalize())
                    final_segments.append(
                        f"📍 **{cat_label}**:\n" + "\n".join(res_list)
                    )

                    if len(requested_cats) == 1:
                        state["last_index"] = offset

        
        # 5. KEMBALIKAN HASIL
        if final_segments:
            header = f"Ini beberapa pilihan produk dengan **{display_name}** ✨"
            return (
                f"{header}\n\n"
                + "\n\n".join(final_segments)
                + "\n\nMau lihat kategori lainnya? 😊"
            )
        return (
            f"Maaf, aku belum menemukan produk **{display_name}** "
            f"yang sesuai dengan kriteria kamu 😢\n"
            f"Kamu bisa coba:\n"
            f"- Ganti kategori produk\n"
            f"- Atau ketik *tanpa filter jenis kulit*"
        )
    # ==========================================================
    # LOGIKA INFO MANFAAT (DEFAULT)
    # ==========================================================
    res = f"**{display_name}** adalah kandungan yang multifungsi ✨\n\n"
    res += f"**Manfaat utamanya:** {info['fungsi']}\n"

    if any(k in user_input for k in ["cocok", "untuk kulit apa", "siapa"]):
        res += f"**Cocok untuk:** {info['cocok_untuk']}\n"
    else:
        # Default tampilkan keduanya jika user hanya tanya "apa itu X"
        res += f"**Cocok untuk:** {info['cocok_untuk']}"     
    return res

def ingredient_safety_response(ingredients):
    """Hanya untuk pertanyaan keamanan kulit sensitif"""
    res_list = []
    for ing in ingredients:
        data = INGREDIENT_INFO.get(ing, {})
        aman = data.get("aman_untuk_sensitif")
        if aman in [True, "Sangat aman pada konsentrasi rendah (2–4%)"]:
            res_list.append(f"**{ing}** relatif aman untuk kulit sensitif 🌱")
        elif aman is False:
            res_list.append(f"**{ing}** sebaiknya dihindari untuk kulit sensitif ⚠️")
        else:
            res_list.append(f"Data keamanan **{ing}** belum lengkap.")
    return "\n".join(res_list)


def ingredient_interaction_response(ingredients, info_type="keamanan"):
    if len(ingredients) < 2:
        return "Sebutkan minimal dua kandungan ya 😊"
        
    pair = tuple(sorted(ingredients[:2]))
    info = INGREDIENT_INTERACTIONS.get(pair)
    
    if not info:
        return "Kombinasi ini belum ada di dataku, tapi amannya sebaiknya dipakai bergantian (pagi/malam) ya 😊"
    
    # Header yang sama untuk kedua info_type
    header = f"✨ **Kombinasi: {pair[0].capitalize()} + {pair[1].capitalize()}** ✨\n"
    keamanan = f"⚠️ **Status:** {info.get('keamanan')}"

    if info_type == "keamanan":
        return f"{header}{keamanan}"
        
    elif info_type == "full":
        # Menggunakan bullet points agar scannable (mudah dibaca sekilas)
        detail = (
            f"{header}{keamanan}\n"
            f"💡 **Fungsi:** {info.get('fungsi')}\n"
            f"📅 **Cara Pakai:** {info.get('carapakai')}\n"
            f"🚫 **Peringatan:** {info.get('peringatan')}"
        )
        return detail
    else:
        return "Info kombinasi belum tersedia."

# =====================================================
# RESPONSE — ROUTINE
# =====================================================
def routine_response(user_input=""):
    user_input = user_input.lower()
    # 1. Definisi Teks Rutinitas
    pagi_txt = (
        "Urutan skincare pagi ☀️\n"
        "1. Facial Wash\n"
        "2. Toner\n"
        "3. Serum\n"
        "4. Moisturizer\n"
        "5. Sunscreen"
    )
    malam_txt = (
        "Urutan skincare malam 🌙\n"
        "1. Facial Wash\n"
        "2. Toner\n"
        "3. Serum\n"
        "4. Moisturizer\n\n"
        "💡 Malam hari tidak perlu sunscreen ya 😊"
    )

    # 2. LOGIKA PENGECEKAN
    # Cek jika user minta KEDUANYA
    if ("pagi" in user_input or "day" in user_input) and ("malam" in user_input or "night" in user_input):
        return f"{pagi_txt}\n\n---\n\n{malam_txt}"
    
    # Cek jika hanya MALAM
    if "malam" in user_input or "night" in user_input:
        return malam_txt
    
    # Cek jika hanya PAGI
    if "pagi" in user_input or "day" in user_input:
        return pagi_txt

    # DEFAULT: Jika user cuma tanya "urutan skincare" tanpa sebut waktu
    return f"Kamu mau tahu urutan yang mana? 😊\n\n{pagi_txt}\n\n---\n\n{malam_txt}"

# =====================================================
# RESPONSE — REKOMENDASI (FINAL VERSION)
# =====================================================
def get_recommendation_response(state: dict):
    skin = state.get("skin_type")
    if skin == []:
        skin = None
        state["skin_type"] = None
    problems = state.get("problem", [])
    brand = state.get("brand")
    cat = state.get("current_category")
    user_ings = state.get("ingredients", [])
    original_problems = state.get("problem", [])

    problems = normalize_problems_for_category(original_problems, cat)
    if not problems and original_problems:
        problems = original_problems

    # ====== Jika category belum ada (Dynamic Check) ====== 
    if not cat and user_ings:
        available_categories = []
        # Cek ke seluruh dataset kategori apa saja yang punya kandungan tersebut
        for category_name, product_list in state.get("dataset", {}).items():
            # Cek apakah ada satu saja produk yang mengandung user_ings
            for p in product_list:
                product_ing = str(p.get("Kandungan Utama", "")).lower()
                if any(ing.lower() in product_ing for ing in user_ings):
                    available_categories.append(category_name)
                    break # Ketemu satu di kategori ini, lanjut kategori lain
        
        if available_categories:
            # Ubah nama kategori jadi lebih rapi (Capitalize)
            unique_cats = list(set(available_categories))
            cat_options = ", ".join([c.replace("_", " ").capitalize() for c in unique_cats])
            
            return (
                f"Aku nemu produk dengan kandungan **{', '.join(state['ingredients']).title()}** "
                f"dalam bentuk **{cat_options}**. \n\n"
                f"Kamu mau cari yang mana? 😊"
            )

    # ====== FIXED: Jika skin_type ada tapi problem kosong ======
    # (HANYA jalan kalau category BELUM ada)
    if skin and not problems and not cat:
        opening = random.choice(OPENING_VARIANTS)
        skin_text = skin if isinstance(skin, str) else " dan ".join(skin)

        response = (
            f"{opening} Oke, aku catat kulit kamu {skin_text} 🌿\n\n"
            "Supaya rekomendasinya lebih akurat, kamu punya masalah kulit apa?\n"
            "Contoh: jerawat, bruntusan, kusam, flek.\n\n"
            "Kamu juga bisa sekalian bilang mau cari produk apa "
            "(facial wash, toner, serum, moisturizer, atau sunscreen) 😊"
        )
        return response

    # Fallback kalau user tidak sebut kandungan
    if not cat:
        return (
            "Kamu mau cari produk kategori apa? 😊\n"
            "Pilihan: Facial Wash, Toner, Serum, Moisturizer, atau Sunscreen."
        )

    # ====== STRATEGY NARRATIVE (CATEGORY AWARE) ======
    strat_list = []
    strategy = ""

    # BASE SKIN TYPE (AMAN UNTUK SEMUA KATEGORI)
    if skin == "sensitif":
        strat_list.append("minim alkohol dan fragrance")
    if skin == "berminyak":
        strat_list.append("non-comedogenic")

    # ======================================
    # STRATEGY BERDASARKAN KATEGORI PRODUK
    # ======================================

    if cat == "facial wash":
        if any(p in problems for p in ["jerawat", "beruntusan"]):
            strat_list.append("membersihkan pori tanpa bikin iritasi")
        if any(p in problems for p in ["kusam", "flek", "bekas jerawat"]):
            strat_list.append("kandungan pencerah ringan dan soothing")

    elif cat == "sunscreen":
        strat_list.append("perlindungan UV yang aman untuk kulit sensitif")
        if any(p in problems for p in ["kusam", "flek", "bekas jerawat"]):
            strat_list.append("membantu mencegah noda makin gelap")

    elif cat == "serum":
        if any(p in problems for p in ["kusam", "flek", "bekas jerawat"]):
            strat_list.append("kandungan aktif pencerah dan antioksidan")
        if any(p in problems for p in ["jerawat", "beruntusan"]):
            strat_list.append("kandungan yang menenangkan dan memperbaiki skin barrier")

    elif cat == "moisturizer":
        strat_list.append("menjaga skin barrier dan kelembapan")
        if any(p in problems for p in ["bekas jerawat", "kusam"]):
            strat_list.append("kandungan pencerah yang aman untuk pemakaian harian")

    elif cat == "toner":
        strat_list.append("menyeimbangkan kondisi kulit tanpa iritasi")

    if strat_list:
        if len(strat_list) > 1:
            strategy = "aku pilihkan produk yang " + ", ".join(strat_list[:-1]) + " serta " + strat_list[-1] + ". "
        else:
            strategy = "aku pilihkan produk yang " + strat_list[0] + ". "

    # ====== DATA FILTERING ======
    products = state.get("dataset", {}).get(cat, [])

    # === PATCH: jika masih DataFrame, konversi ke list of dict ===
    if hasattr(products, "to_dict"):
        products = products.fillna("").to_dict(orient="records")

    filtered = []

    for p in products:
        product_skin = normalize_dataset_text(p.get("Jenis Kulit", ""))
        product_problem = normalize_dataset_text(p.get("Masalah Kulit", ""))
        product_brand = normalize_dataset_text(p.get("Brand", ""))
        product_ing = normalize_dataset_text(p.get("Kandungan Utama", ""))

        p_benefits_list = get_product_benefits(p)
        p_benefits_string = " ".join(p_benefits_list).lower()

        product_info_full = (product_problem + " " + " ".join(p_benefits_list) + " " + product_ing).lower()

        if user_ings:
            if not any(ing.lower() in product_ing for ing in user_ings):
                continue

        # Brand filter
        if brand and brand.lower() not in product_brand:
            continue

        # Skin type filter
        if skin:
            skin_list = skin if isinstance(skin, list) else [skin]
            if not any(s.lower() in product_skin for s in skin_list):
                continue

        # SAFETY GUARD (sensitif / kering)
        if skin == "sensitif":
            avoid_ings = INGREDIENT_SUGGESTION.get("sensitif", {}).get("avoid", [])
            if any(a.lower() in product_ing for a in avoid_ings):
                continue
            
        if problems:
            product_info_full = f"{product_problem} {product_ing}"
            match_found = any(prob.lower() in product_info_full for prob in problems)
            if not match_found:
                continue
        
        if user_ings:
            if not any(ing.lower() in product_ing for ing in user_ings):
                continue

        # ================================
        # INGREDIENT PRIORITY 
        # ================================
        if problems:
            ingredient_match = False
            has_priority_rule = False

            for prob in problems:
                if prob in INGREDIENT_SUGGESTION:
                    recommended_ings = INGREDIENT_SUGGESTION[prob].get("recommended", [])

                    if not recommended_ings:
                        continue

                    has_priority_rule = True

                    priority_source = (
                        product_ing + " " +
                        product_problem + " " +
                        product_info_full
                    ).lower()

                    if any(r.lower() in priority_source for r in recommended_ings):
                        ingredient_match = True
                        break

            if has_priority_rule and not ingredient_match:
                continue

        filtered.append(p)

    # ====== FALLBACK ======
    if not filtered:
        if brand:
            return (
                f"Aku belum menemukan produk {cat} dari brand "
                f"{brand.capitalize()} dengan kriteria ini di dataset 😔"
            )
        return f"Aku belum menemukan produk {cat} yang sesuai dengan kriteria ini di dataset 😔"

    # ====== RESPONSE BUILDER ======
    opening = random.choice(OPENING_VARIANTS)
    if isinstance(skin, list):
        skin_text = " dan ".join(skin)
    else:
        skin_text = skin if skin else "kamu"

    # 2. Ambil dari problem_display agar yang muncul kata asli user (misal: bruntusan)
    all_probs = state.get("problem_display", [])
    
    if not all_probs:
        all_probs = [p.replace("_", " ") for p in state.get("problem", [])]

    # Mulai susun kalimat
    response = f"{opening} Untuk kulit {skin_text}.\n"
    header_ing = f" dengan kandungan **{', '.join(user_ings).capitalize()}**" if user_ings else ""
    response = f"{opening} Untuk kulit {skin_text}{header_ing}.\n"
    
    if all_probs:
        unique_probs = list(dict.fromkeys(all_probs)) # Hapus duplikat
        if len(unique_probs) > 1:
            problems_text = ", ".join(unique_probs[:-1]) + " dan " + unique_probs[-1]
        else:
            problems_text = unique_probs[0]
        response += f" Dengan masalah {problems_text}, {strategy}\n\n"

    # 3. List Produk
    response += f"Rekomendasi {CATEGORY_TEXT.get(cat, cat.capitalize())} yang cocok:\n" 
        # ====== PAGING & LIMIT ======
    limit = extract_limit(state.get("last_user_input", ""), default=3)

    start_index = state.get("last_reco_index", 0)
    end_index = start_index + limit

    selected_products = filtered[start_index:end_index]

    if not selected_products and start_index == 0:
        return "Maaf, aku belum menemukan produk yang sesuai kriteria 😔"
    elif not selected_products:
        state["last_reco_index"] = 0
        return "Produk sudah habis ditampilkan 😊 Kamu mau ganti kategori atau kriteria?"


    state["last_reco_index"] = end_index

    # ====== RESPONSE BUILDER ======
    seen_recommendations = set()

    for p in selected_products:
        brand_name = str(p.get('Brand', '')).strip()
        prod_name = str(p.get('Nama Produk', '')).strip()
        nama_full = f"{brand_name} {prod_name}"

        if nama_full not in seen_recommendations:
            response += f"- **{nama_full}**\n"
            seen_recommendations.add(nama_full)

    response += (
        "\nKetik **'produk lainnya'** atau **'yang lain'** "
        "untuk melihat rekomendasi berikutnya 😊"
    ) 

    response += (
        "\nKalau mau lanjut ke kategori lain seperti facial wash, toner, serum, moisturizer "
        "atau sunscreen, tinggal bilang aja ya 😊"
    )
    return response

# =====================================================

def handle_educational_request(state, user_input):
    brand = state.get("brand")
    dataset = state.get("dataset", {})
    
    found_prod = None
    best_match_score = 0

    # 1. Cari produknya di dataset
    for cat, prods in dataset.items():
        for p in prods:
            brand_p = str(p.get('Brand', '')).lower()
            nama_p = str(p.get('Nama Produk', '')).lower()
            full_name_p = f"{brand_p} {nama_p}"
            
            if brand and brand.lower() in brand_p:
                match_count = sum(1 for word in user_input.split() if word in full_name_p)
                if match_count > best_match_score:
                    best_match_score = match_count
                    found_prod = p

    if found_prod:
        nama_prod = f"{found_prod.get('Brand')} {found_prod.get('Nama Produk')}"
        kandungan_utama_produk = str(found_prod.get("Kandungan Utama", "")).lower()
        manfaat_dari_rules = []
        
        # 2. LOGIKA PERBAIKAN: Cek apakah itu List atau String
        for ing_key, benefit_val in PRODUCT_BENEFIT_RULES.items():
            if ing_key.lower() in kandungan_utama_produk:
                # Jika isinya list [..], gabungkan pakai koma
                if isinstance(benefit_val, list):
                    benefit_str = ", ".join(benefit_val).lower()
                else:
                    benefit_str = str(benefit_val).lower()
                
                manfaat_dari_rules.append(benefit_str)

        if manfaat_dari_rules:
            # Gabungkan semua manfaat yang ketemu
            final_benefit = ", ".join(dict.fromkeys(manfaat_dari_rules))
            return f"Manfaat utama dari **{nama_prod}** adalah untuk {final_benefit} ✨"
        else:
            manfaat_fallback = found_prod.get("Manfaat", "merawat kulit")
            return f"Manfaat utama dari **{nama_prod}** adalah {manfaat_fallback.lower()} ✨"
    
    return "Boleh tahu nama produk lengkapnya? 😊"

# =====================================================
# MAIN LOGIC
# =====================================================
def chatbot_logic(user_input: str, state: dict):
    state.setdefault("ingredients", [])
    state.setdefault("problem", [])
    state.setdefault("skin_type", None)
    state.setdefault("brand", None)
    state.setdefault("current_category", None)
    state.setdefault("last_reco_index", 0)
    state["last_user_input"] = user_input.lower()


    if "dataset" not in state or not isinstance(state["dataset"], dict):
        raise ValueError("Dataset chatbot belum ter-load ke state")

    extract_entities(user_input, state)
    user_lower = user_input.lower()

    # =========================
    # DETEKSI INTENT MANFAAT (TARUH PALING ATAS)
    # =========================
    edu_keywords = ["manfaat", "fungsi", "kegunaan", "apa itu", "bagus buat apa", "efek"]
    is_asking_benefits = any(k in user_lower for k in edu_keywords)

    if is_asking_benefits:
        # JIKA ADA BRAND: Tanya manfaat produk spesifik
        if state.get("brand"):
            return handle_educational_request(state, user_lower)
        
        # JIKA HANYA ADA INGREDIENT: Pakai info detail dari ingredient_info_response
        if state.get("ingredients"):
            return ingredient_info_response(state["ingredients"], state, user_lower)
    
    # =========================
    # AUTO INGREDIENT RECO AFTER SKIN TYPE
    # =========================
    if (
        state.get("ingredients")
        and state.get("skin_type")
        and state.get("current_category")
        and not any(k in user_lower for k in ["lagi", "lainnya", "tambah"])
        and not is_asking_benefits
    ):
     
        if any(ing.lower() in user_lower for ing in state.get("ingredients", [])):
             pass # Masih bahas yang sama
        else:
             state["last_index"] = 0
             state["last_reco_index"] = 0

        state["last_reco_index"] = 0
        forced_input = f"rekomendasi {state['current_category']}"
        return ingredient_info_response(state["ingredients"], state, forced_input)
    
    intent = detect_intent(user_input)
    if intent == "RESET":
        dataset_backup = state.get("dataset", {})
        state.clear()
        state.update({
            "ingredients": [],
            "problem": [],
            "skin_type": None,
            "brand": None,
            "current_category": None,
            "dataset": dataset_backup
        })
        return "Siap ✨ semua data sudah aku reset. Kita mulai dari awal ya 😊"
    
    if is_gibberish(user_input):
        return (
            f"Maaf, aku kurang paham maksud dari '**{user_input}**' 😅\n"
            "Coba ketik dengan ejaan yang benar ya, misalnya: 'Retinol', 'Niacinamide', atau 'Serum'."
        )
    
    if state.get("ingredients") and not state.get("current_category"):
        all_cat_keywords = [kw for sublist in PRODUCT_MAP.values() for kw in sublist]
        if any(kw in user_lower for kw in all_cat_keywords):
            return ingredient_info_response(state["ingredients"], state, user_input)
    
    # =====================================================
    # PRIORITAS 2: INFO KANDUNGAN & KEAMANAN (Direct Info)
    # =====================================================
    # Cek interaksi dulu jika ada 2+ kandungan
    if intent == "INGREDIENT_INTERACTION" and len(state["ingredients"]) >= 2:
        user_lower = clean_text(user_input)
        info_type = "keamanan" if any(k in user_lower for k in ["boleh digabung", "barengan"]) else "full"
        return ingredient_interaction_response(state["ingredients"], info_type=info_type)

    # Cek keamanan kulit sensitif
    if intent == "INGREDIENT_SAFETY" and state["ingredients"]:
        return ingredient_safety_response(state["ingredients"])

    # Cek informasi manfaat kandungan
    if intent == "INGREDIENT_INFO" and state["ingredients"]:
        return ingredient_info_response(state["ingredients"], state, user_input)

    # =====================================================
    # PRIORITAS 3: INFO PRODUK SPESIFIK (Brand/Fungsi)
    # =====================================================
    if intent == "PRODUCT_OR_INGREDIENT_INFO":
        if state.get("brand"):
            found_prods = []
            target_cat = state.get("current_category")
            
            for cat, prods in state.get("dataset", {}).items():
                if target_cat and cat.lower() != target_cat.lower():
                    continue
                for p in prods:
                    if state["brand"].lower() in str(p.get("Brand", "")).lower():
                        found_prods.append(p)

            if found_prods:
                # Jika user nanya manfaat/fungsi
                if any(k in user_input.lower() for k in ["manfaat", "fungsi", "buat apa"]) or not any(k in user_input.lower() for k in ["produk", "apa saja"]):
                    p = found_prods[0]
                    nama_prod = f"{p.get('Brand')} {p.get('Nama Produk')}"
                    manfaat_txt = p.get("Manfaat") or get_product_benefits(p)
                    return f"Manfaat utama dari **{nama_prod}** adalah {manfaat_txt.lower()} ✨"
                # Jika user nanya daftar produk dari brand tersebut
                else:
                    seen_names = set()
                    list_nama = []
                    for p in found_prods:
                        nama_full = f"{p.get('Brand')} {p.get('Nama Produk')}"
                        if nama_full not in seen_names:
                            list_nama.append(f"**{nama_full}**")
                            seen_names.add(nama_full)
                        if len(list_nama) >= 3: break
                    return f"Berikut beberapa produk dari **{state['brand'].capitalize()}**:\n- " + "\n- ".join(list_nama)
        
        # Jika tidak ada brand tapi ada ingredients, arahkan ke info ingredient
        if state.get("ingredients"):
            return ingredient_info_response(state["ingredients"], state, user_input)   
        return "Boleh tahu nama produk atau kandungan apa yang ingin kamu tanyakan manfaatnya? 😊"

    # =====================================================
    # PRIORITAS 4: REKOMENDASI & ROUTINE
    # =====================================================
    if intent == "MORE_RECOMMEND":
        if not state.get("current_category"):
            return "Kamu mau produk kategori apa dulu? 😊"
        return get_recommendation_response(state)

    if intent == "ROUTINE":
        return routine_response(user_input)

    # Logika Rekomendasi (Berdasarkan Ingredient atau Umum)
    if intent in ["RECOMMEND", "RECOMMEND_BY_INGREDIENT"] or (intent == "UNKNOWN" and (state.get("skin_type") or state.get("problem"))):
    
        # Ganti extract_ingredients menjadi detect_ingredients
        current_ings = detect_ingredients(user_input) 
        
        if current_ings:
            # TIMPA (Overwrite) kandungan lama dengan yang baru disebut
            state["ingredients"] = current_ings
            # Reset index karena ini pencarian baru
            state["last_reco_index"] = 0
        # ============================

        # 1. Validasi Jenis Kulit
        if not state.get("skin_type"):
            target_list = []
            # Gunakan ingredients sebagai target jika ada (misal: "produk retinol")
            if state.get("ingredients"):
                target_list.extend(state["ingredients"])
            
            problems = state.get("problem_display", [])
            if isinstance(problems, list) and problems:
                target_list.extend(problems)
            
            target = " & ".join(target_list) if target_list else "skincare"

            return (
                f"Oke, aku bantu cari **{target}** yang pas ya 🔍\n"
                "Tapi aku perlu tahu dulu, jenis kulit kamu: "
                "**Normal, Berminyak, Kering, Kombinasi, atau Sensitif**? ✨"
            )
        
        # 2. Jika sudah lengkap atau semi-lengkap, panggil recommendation engine
        return get_recommendation_response(state)

    # === AUTO CONTINUE JIKA DATA TIBA-TIBA LENGKAP ===
    if state.get("skin_type") and state.get("problem") and state.get("current_category"):
        return get_recommendation_response(state)

    # =====================================================
    # FALLBACK 
    # =====================================================
    return (
        "Aku siap bantu ✨\n"
        "Kamu bisa sebutin jenis kulit, masalah kulit, atau tanya fungsi kandungan skincare kamu 😊"
    )

# =====================================================
# PUBLIC API
# =====================================================
def handle_chat(user_input, state):
    return chatbot_logic(user_input, state)

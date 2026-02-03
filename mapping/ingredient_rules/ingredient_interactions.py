INGREDIENT_INTERACTIONS = {
    # 1. KOMBINASI EKSFOLIASI & RETINOID (HIGH RISK)
    ('AHA', 'Retinol'): {
        'keamanan': "Sangat Hati-Hati/Tidak Disarankan. Kombinasi ini sangat berpotensi menyebabkan iritasi, kemerahan, dan kerusakan *skin barrier* karena keduanya adalah eksfoliator kuat.",
        'fungsi': "Meningkatkan eksfoliasi dan regenerasi, namun risiko iritasinya sangat tinggi. Hindari mencari efek ganda dengan cara ini.",
        'carapakai': "Gunakan secara terpisah di malam hari yang berbeda (misal: AHA Senin malam, Retinol Rabu malam). **Jangan pernah digunakan bersamaan** dalam rutinitas yang sama.",
        'peringatan': "BAHAYA: Hindari penggunaan bersamaan."
    },
    ('BHA', 'Retinol'): {
        'keamanan': "Sangat Hati-Hati/Tidak Disarankan. Mirip dengan AHA, kombinasi ini dapat menyebabkan kulit kering berlebihan dan iritasi parah.",
        'fungsi': "BHA membersihkan pori, Retinol meregenerasi. Terlalu kuat jika digabungkan.",
        'carapakai': "Gunakan secara terpisah di malam yang berbeda. Jika kulit kuat, BHA di pagi hari (wajib sunscreen kuat) dan Retinol di malam hari, tetapi ini berisiko.",
        'peringatan': "BAHAYA: Hindari penggunaan bersamaan."
    },
    ('AHA', 'BHA'): {
        'keamanan': "Hati-hati. Umumnya aman jika konsentrasi rendah, namun berisiko tinggi iritasi jika konsentrasi tinggi (seperti *peeling* serum).",
        'fungsi': "AHA eksfoliasi permukaan (mencerahkan), BHA eksfoliasi ke dalam pori (mengatasi komedo/jerawat). Sangat efektif untuk tekstur dan jerawat.",
        'carapakai': "Gunakan 1-2 kali seminggu saja (di malam hari). Untuk penggunaan harian, gunakan di waktu yang berbeda (AHA pagi, BHA malam, atau selang-seling hari).",
        'peringatan': "Hati-hati, berpotensi iritasi pada penggunaan berlebihan."
    },
    
    # 2. KOMBINASI WHITENING & RETINOID (SAFE / SYNERGISTIC)
    ('Niacinamide', 'Retinol'): {
        'keamanan': "Aman digunakan bersama. Niacinamide justru membantu menenangkan kulit dan mengurangi potensi iritasi dari Retinol.",
        'fungsi': "Retinol fokus pada regenerasi/anti-penuaan, Niacinamide memperbaiki *barrier* dan mengontrol minyak. Sinergis dan efektif.",
        'carapakai': "Dapat di-**layer** bersamaan di malam hari. Gunakan Niacinamide dulu → Retinol → Moisturizer (Metode *sandwich*).",
        'peringatan': "Aman dan Direkomendasikan."
    },
    ('Retinol', 'Vitamin C'): {
        'keamanan': "Bukan Konflik Kuat, namun Hati-Hati. Retinol dan Vitamin C aktif di pH berbeda dan dapat meningkatkan sensitivitas. (Lebih baik dipisah)",
        'fungsi': "Vitamin C (pagi) antioksidan dan mencerahkan. Retinol (malam) anti-penuaan. Efek ganda untuk peremajaan.",
        'carapakai': "Gunakan **terpisah** di waktu yang berbeda. Vitamin C di pagi hari (wajib sunscreen), Retinol di malam hari.",
        'peringatan': "Pisahkan waktu pakai untuk hasil optimal."
    },

    # 3. KOMBINASI WHITENING & WHITENING (SAFE / SYNERGISTIC)
    ('Alpha Arbutin', 'Niacinamide'): {
        'keamanan': "Sangat Aman. Kombinasi ini sangat efektif untuk flek hitam dan PIH.",
        'fungsi': "Keduanya adalah pencerah yang bekerja dengan mekanisme berbeda. Hasilnya efektif untuk meratakan warna kulit.",
        'carapakai': "Dapat di-**layer** bersamaan (pagi dan malam). Alpha Arbutin biasanya berbentuk serum cair, gunakan lebih dulu.",
        'peringatan': "Sangat Aman dan Sinergis."
    },
    ('Alpha Arbutin', 'Vitamin C'): {
        'keamanan': "Sangat Aman. Kombinasi pencerah yang sangat stabil dan efektif.",
        'fungsi': "Keduanya bekerja sama untuk menghambat produksi melanin dan melawan radikal bebas (antioksidan).",
        'carapakai': "Dapat di-**layer** bersamaan (pagi atau malam). Ideal di pagi hari sebelum sunscreen.",
        'peringatan': "Sangat Aman dan Sinergis."
    },
    ('Niacinamide', 'Vitamin C'): {
        'keamanan': "Aman digunakan bersama (mitos konflik pH sudah dipatahkan). Sangat efektif untuk mencerahkan.",
        'fungsi': "Meningkatkan efek antioksidan, mencerahkan, dan mengurangi kusam secara signifikan.",
        'carapakai': "Dapat di-**layer** bersamaan (pagi atau malam). Ideal di pagi hari sebelum sunscreen.",
        'peringatan': "Aman, tidak ada konflik."
    },
    
    # 4. KOMBINASI EKSFOLIASI & PENCERAH/CALMING (SAFE / SYNERGISTIC)
    ('AHA', 'Niacinamide'): {
        'keamanan': "Aman. Niacinamide membantu menenangkan kulit dari efek eksfoliasi AHA.",
        'fungsi': "AHA eksfoliasi permukaan (mencerahkan), Niacinamide memperbaiki *barrier*. Kombinasi yang baik untuk kulit kusam dan tekstur.",
        'carapakai': "Dapat di-**layer** bersamaan di malam hari. Aplikasikan AHA dulu.",
        'peringatan': "Tidak ada peringatan serius."
    },
    ('BHA', 'Niacinamide'): {
        'keamanan': "Sangat Aman. Kombinasi yang ideal untuk kulit berminyak dan berjerawat.",
        'fungsi': "BHA membersihkan pori dan mengatasi komedo, Niacinamide mengontrol sebum dan memudarkan bekas jerawat.",
        'carapakai': "Dapat di-**layer** bersamaan (pagi atau malam). BHA dapat digunakan setiap hari atau selang-seling.",
        'peringatan': "Sangat Aman dan Sinergis."
    },
    ('AHA', 'Centella'): {
        'keamanan': "Aman. Centella berfungsi sebagai *buffer* yang menenangkan setelah eksfoliasi AHA.",
        'fungsi': "AHA eksfoliasi, Centella mempercepat penyembuhan dan mengurangi kemerahan akibat eksfoliasi.",
        'carapakai': "Aplikasikan Centella (serum/moisturizer) setelah menggunakan AHA.",
        'peringatan': "Sangat Aman dan Sinergis."
    },
    
    # 5. KOMBINASI HIDRASI/BARRIER & AKTIF LAIN (SANGAT AMAN)
    ('Ceramide', 'Retinol'): {
        'keamanan': "Sangat Aman. Ceramide sangat dianjurkan untuk mendampingi Retinol.",
        'fungsi': "Retinol regenerasi (bisa mengeringkan), Ceramide memperkuat *barrier* kulit dan menjaga kelembapan. Sinergis untuk mengurangi efek samping Retinol.",
        'carapakai': "Gunakan Ceramide dalam *step* moisturizer setelah Retinol, atau gunakan metode *sandwich* (Ceramide → Retinol → Ceramide lagi).",
        'peringatan': "Sangat Aman dan Direkomendasikan."
    },
     ('Hyaluronic Acid', 'Retinol'): {
        'keamanan': "Sangat Aman. Hyaluronic Acid adalah penetral efek samping Retinol yang paling umum.",
        'fungsi': "Retinol meregenerasi, Hyaluronic Acid memberikan hidrasi instan untuk melawan kekeringan yang disebabkan Retinol.",
        'carapakai': "Dapat di-**layer** bersamaan. Hyaluronic Acid setelah mencuci muka → Retinol → Moisturizer.",
        'peringatan': "Sangat Aman."
    },
}
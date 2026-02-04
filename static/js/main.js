document.addEventListener("DOMContentLoaded", function () {
    console.log("Main.js loaded");

    /* ================================
       UTILITY FUNCTION
    ================================ */
    function potongKandungan(text, limit = 4) {
        if (!text) return "";
        const arr = text.split(',').map(i => i.trim());
        if (arr.length <= limit) return arr.join(', ');
        return arr.slice(0, limit).join(', ') + ', …';
    }
    
    /* ================================
       PRODUK & HOME PAGE
    ================================ */
    const produkGrid = document.getElementById("produkGrid");
    const loaderProduk = document.getElementById("loaderProduk");
    const btnFilter = document.getElementById("btnFilter");

    function renderProduk(items) {
        if (!produkGrid) return;
        produkGrid.innerHTML = "";
        if (!items || items.length === 0) {
            produkGrid.innerHTML = "<p class='fade-in'>Tidak ada produk ditemukan.</p>";
            return;
        }
        items.forEach(p => {
            const card = document.createElement("div");
            card.className = "produk-card fade-in";
            const imgSrc = (p.image_url && p.image_url.trim() !== "") ? p.image_url : "/static/Images/default.jpg";
            card.innerHTML = `
                <img src="${imgSrc}" alt="${p.nama}" class="produk-img">
                <h3>${p.nama}</h3>
                <p><strong>Brand:</strong> ${p.brand}</p>
                <p><strong>Kategori:</strong> ${p.kategori}</p>
                <p><strong>Kandungan Utama:</strong> ${potongKandungan(p.kandungan)}</p>
                <div class="label-box">
                    ${p.alcohol_free ? "<span>Alcohol-Free</span>" : ""}
                    ${p.fragrance_free ? "<span>Fragrance-Free</span>" : ""}
                    ${p.non_comedogenic ? "<span>Non-Comedogenic</span>" : ""}
                </div>
            `;
            produkGrid.appendChild(card);
        });
    }

    function loadProduk(initialLimit = null) {
        if (loaderProduk) loaderProduk.style.display = "block";
        if (produkGrid) produkGrid.innerHTML = "";

        const urlParams = new URLSearchParams(window.location.search);
        let kategoriURL = (urlParams.get("category") || "").trim();
        if (kategoriURL) kategoriURL = kategoriURL.toLowerCase().replace(/\s+/g, "");

        const q = document.getElementById("searchText")?.value.trim() || "";
        const categoryInput = document.getElementById("filterCategory")?.value || "";
        const category = categoryInput ? categoryInput : kategoriURL;
        const brand = document.getElementById("filterBrand")?.value || "";
        const alcoholFree = document.getElementById("prefAlcoholFree")?.checked || false;
        const fragranceFree = document.getElementById("prefFragranceFree")?.checked || false;
        const nonComedogenic = document.getElementById("prefNonComedogenic")?.checked || false;

        fetch(`/api/produk?q=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}&brand=${encodeURIComponent(brand)}&alcohol_free=${alcoholFree}&fragrance_free=${fragranceFree}&non_comedogenic=${nonComedogenic}`)
            .then(res => res.json())
            .then(data => {
                if (loaderProduk) loaderProduk.style.display = "none";
                let items = data.items || [];
                if (initialLimit && items.length > initialLimit) items = items.slice(0, initialLimit);
                renderProduk(items);
            })
            .catch(() => {
                if (loaderProduk) loaderProduk.style.display = "none";
                if (produkGrid) produkGrid.innerHTML = "<p class='fade-in'>Error memuat produk.</p>";
            });
    }

    if (btnFilter) btnFilter.addEventListener("click", () => loadProduk());

    if (produkGrid) {
        if (document.body.classList.contains("page-home")) loadProduk(6);
        else if (document.body.classList.contains("page-produk")) loadProduk();
    }

    /* ================================
       HAMBURGER MENU MOBILE
    ================================ */
    const hamburgerBtn = document.getElementById("hamburgerBtn");
    const mobileMenu = document.getElementById("mobileMenu");

    if (hamburgerBtn && mobileMenu) {
        mobileMenu.classList.add("hidden");

        hamburgerBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            mobileMenu.classList.toggle("hidden");
        });

        document.addEventListener("click", (e) => {
            if (!mobileMenu.contains(e.target) && !hamburgerBtn.contains(e.target)) {
                mobileMenu.classList.add("hidden");
            }
        });
    }

    /* ================================
       FILTER SIDEBAR MOBILE
    ================================ */
    const btnOpenFilter = document.getElementById("btnOpenFilter");
    const sidebar = document.querySelector(".filter-sidebar");
    const overlay = document.getElementById("mobileFilterOverlay");

    if (btnOpenFilter && sidebar && overlay) {
        btnOpenFilter.addEventListener("click", () => {
            if (window.innerWidth < 768) {
                sidebar.classList.add("show");
                overlay.classList.remove("hidden");
            }
        });
        overlay.addEventListener("click", () => {
            sidebar.classList.remove("show");
            overlay.classList.add("hidden");
        });
    }

    /* ================================
       REKOMENDASI PAGE
    ================================ */
    const kategoriMap = {
        facialwash: "Facial Wash",
        toner: "Toner",
        serum: "Serum",
        moisturizer: "Moisturizer",
        sunscreen: "Sunscreen"
    };

    const recommendForm = document.getElementById("recommendForm");
    const resultBox = document.getElementById("resultBox");
    const loaderRekom = document.getElementById("loader");

    function generateNotes(item) {
        const notes = [];
        if (item.alcohol_free === false) notes.push("Produk ini mengandung alcohol. Sebaiknya dihindari jika kulitmu mudah iritasi atau sangat sensitif.");
        if (item.fragrance_free === false) notes.push("Produk ini mengandung fragrance. Jika kulitmu sangat sensitif, lebih baik berhati-hati.");
        if (item.non_comedogenic === false) notes.push("Produk ini berpotensi menyumbat pori-pori (comedogenic). Tidak disarankan untuk kulit berminyak atau acne-prone.");
        return notes;
    }

    if (recommendForm) {
        recommendForm.addEventListener("submit", function (e) {
            e.preventDefault();
            if (loaderRekom) loaderRekom.style.display = "block";
            if (resultBox) {
                resultBox.style.display = "none";
                resultBox.innerHTML = "";
            }

            const formData = new FormData(recommendForm);
            const data = {
                category: formData.get("category"),
                jenis_kulit: formData.get("jenis_kulit"),
                masalah_kulit: formData.get("masalah_kulit"),
                preferences: {
                    alcohol_free: formData.get("prefAlcoholFree") ? true : false,
                    fragrance_free: formData.get("prefFragranceFree") ? true : false,
                    non_comedogenic: formData.get("prefNonComedogenic") ? true : false
                }
            };

            fetch("/api/rekomendasi", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(result => {
                if (loaderRekom) loaderRekom.style.display = "none";
                if (!resultBox) return;
                resultBox.style.display = "block";

                if (result.items && result.items.length > 0) {
                    result.items.forEach(item => {
                        const div = document.createElement("div");
                        div.className = "recommend-card fade-in";
                        const imgSrc = (item.image_url && item.image_url.trim() !== "") ? item.image_url : "/static/Images/default.jpg";
                        const autoNotes = generateNotes(item);

                        let notesHtml = "";
                        if (autoNotes.length > 0) notesHtml = "<ul>" + autoNotes.map(n => `<li>${n}</li>`).join("") + "</ul>";

                        div.innerHTML = `
                            <div class="card-content">
                                <img src="${imgSrc}" alt="${item.nama}" class="produk-img">
                                <h3>${item.nama}</h3>
                                <div class="card-details">
                                    <p class="detail-row"><strong>Brand:</strong> ${item.brand}</p>
                                    <p class="detail-row"><strong>Kategori:</strong> ${kategoriMap[item.kategori] || item.kategori}</p>
                                    <p class="ingredient-label"><strong>Kandungan Utama:</strong></p>
                                    <p class="ingredient-content">${potongKandungan(item.kandungan)}</p>
                                </div>
                                <div class="label-box flex flex-wrap gap-2 justify-start mt-3">
                                    ${item.alcohol_free ? `<span class="px-2 py-1 bg-blue-100 text-blue-700 rounded-full">🚫 Alcohol-Free</span>` : ""}
                                    ${item.fragrance_free ? `<span class="px-2 py-1 bg-pink-100 text-pink-600 rounded-full">🌸 Fragrance-Free</span>` : ""}
                                    ${item.non_comedogenic ? `<span class="px-2 py-1 bg-green-100 text-green-700 rounded-full">✅ Non-Comedogenic</span>` : ""}
                                </div>
                            </div>
                            ${autoNotes.length > 0 ? `<div class="note-alert mt-3"><span class="note-icon">⚠️</span><div><strong>Peringatan:</strong><br>${autoNotes.join("<br>")}</div></div>` : ""}
                        `;
                        resultBox.appendChild(div);
                    });
                } else {
                    resultBox.innerHTML = "<p class='fade-in'>Tidak ada rekomendasi ditemukan.</p>";
                }
            })
            .catch(() => {
                if (loaderRekom) loaderRekom.style.display = "none";
                if (resultBox) {
                    resultBox.style.display = "block";
                    resultBox.innerHTML = "<p class='fade-in'>Error memuat rekomendasi.</p>";
                }
            });
        });
    }

    /* ================================
       CHATBOT PAGE
    ================================ */
    localStorage.removeItem("chat_session_id");
    let sessionId = crypto.randomUUID();
    localStorage.setItem("chat_session_id", sessionId);

    const chatbotForm = document.getElementById("chatForm");
    const chatbotInput = document.getElementById("chatInput");
    const chatbotMessages = document.getElementById("chatMessages");
    const chatbotQuick = document.getElementById("chatQuick");

    function formatText(text) {
        if (!text) return "";
        return text.replace(/\n/g, "<br>").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    }

    function appendMessage(text, sender = "bot") {
        const div = document.createElement("div");
        div.classList.add(sender === "user" ? "user-message" : "bot-message");
        div.innerHTML = formatText(text);
        chatbotMessages.appendChild(div);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }

    function showTyping() {
        const bubble = document.createElement("div");
        bubble.className = "bot-message typing-bubble";
        bubble.textContent = "•••";
        chatbotMessages.appendChild(bubble);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        return bubble;
    }

    async function sendChat(userText) {
        appendMessage(userText, "user");
        chatbotInput.value = "";
        const typingBubble = showTyping();

        const res = await fetch("/api/chatbot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, message: userText })
        });

        const data = await res.json();
        typingBubble.remove();
        appendMessage(data.reply || "Maaf, saya belum menemukan jawabannya.", "bot");
    }

    if (chatbotForm) {
        chatbotForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const text = chatbotInput.value.trim();
            if (text) sendChat(text);
        });
    }

    if (chatbotQuick) {
        chatbotQuick.querySelectorAll("button").forEach(btn => {
            btn.addEventListener("click", () => {
                sendChat(btn.textContent.trim());
            });
        });
    }
});


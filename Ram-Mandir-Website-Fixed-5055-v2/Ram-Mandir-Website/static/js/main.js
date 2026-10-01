/* =============================================================
   Ram Mandir Visitor Portal — frontend logic
   ============================================================= */

(function () {
    "use strict";

    const $  = (sel, root = document) => root.querySelector(sel);
    const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

    let currentUser = null;
    let slotCache   = [];


    /* ---------------------------------------------------------- api --- */

    async function api(path, options = {}) {
        const res = await fetch(path, {
            headers: { "Content-Type": "application/json" },
            ...options,
            body: options.body ? JSON.stringify(options.body) : undefined,
        });
        let data;
        try {
            data = await res.json();
        } catch {
            throw new Error("The server sent an unexpected response.");
        }
        if (!res.ok) throw new Error(data.error || "Something went wrong.");
        return data;
    }


    /* -------------------------------------------------------- toasts --- */

    const ICONS = {
        success: "fa-circle-check",
        error:   "fa-circle-exclamation",
        info:    "fa-circle-info",
    };

    function toast(message, type = "success") {
        const el = document.createElement("div");
        el.className = `toast ${type}`;
        el.innerHTML = `<i class="fa-solid ${ICONS[type]}"></i><span></span>`;
        $("span", el).textContent = message;
        $("#toastStack").appendChild(el);

        setTimeout(() => {
            el.classList.add("hide");
            el.addEventListener("animationend", () => el.remove(), { once: true });
        }, 4200);
    }

    function showError(box, message) {
        box.classList.add("show");
        $("span", box).textContent = message;
    }

    function clearError(box) {
        box.classList.remove("show");
    }


    /* -------------------------------------------------------- modals --- */

    function openModal(id) {
        $(`#${id}`).classList.add("open");
        document.body.classList.add("no-scroll");
    }

    function closeModal(el) {
        el.classList.remove("open");
        if (!$(".modal-overlay.open")) document.body.classList.remove("no-scroll");
    }

    $$(".modal-overlay").forEach(overlay => {
        // Backdrop click closes, clicks inside the dialog do not.
        overlay.addEventListener("click", e => {
            if (e.target === overlay) closeModal(overlay);
        });
        $$("[data-close]", overlay).forEach(btn =>
            btn.addEventListener("click", () => closeModal(overlay)));
    });

    document.addEventListener("keydown", e => {
        if (e.key !== "Escape") return;
        const open = $(".modal-overlay.open");
        if (open) closeModal(open);
        if ($("#lightbox").classList.contains("open")) closeLightbox();
        $("#navLinks").classList.remove("open");
    });


    /* ------------------------------------------------- navbar / menu --- */

    const navbar    = $("#navbar");
    const navLinks  = $("#navLinks");
    const navToggle = $("#navToggle");

    navToggle.addEventListener("click", () => {
        const open = navLinks.classList.toggle("open");
        navToggle.setAttribute("aria-expanded", String(open));
        $("i", navToggle).className = open ? "fa-solid fa-xmark" : "fa-solid fa-bars";
    });

    // Close the mobile drawer after tapping a link.
    $$("#navLinks a").forEach(a => a.addEventListener("click", () => {
        navLinks.classList.remove("open");
        navToggle.setAttribute("aria-expanded", "false");
        $("i", navToggle).className = "fa-solid fa-bars";
    }));

    const toTop = $("#toTop");

    window.addEventListener("scroll", () => {
        navbar.classList.toggle("scrolled", window.scrollY > 20);
        toTop.classList.toggle("show", window.scrollY > 600);
    }, { passive: true });

    toTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

    // Highlight the nav link for whichever section is in view.
    const sections = $$("section[id], div[id='quick']");
    const navMap = new Map(
        $$("#navLinks a").map(a => [a.getAttribute("href").slice(1), a]));

    const spy = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            const link = navMap.get(entry.target.id);
            if (!link) return;
            $$("#navLinks a").forEach(a => a.classList.remove("active"));
            link.classList.add("active");
        });
    }, { rootMargin: "-45% 0px -50% 0px" });

    sections.forEach(s => spy.observe(s));


    /* ------------------------------------------------ scroll reveal --- */

    const revealer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add("visible");
            obs.unobserve(entry.target);
        });
    }, { threshold: 0.12, rootMargin: "0px 0px -60px 0px" });

    function observeReveals(root = document) {
        $$(".reveal:not(.visible)", root).forEach(el => revealer.observe(el));
    }
    observeReveals();


    /* --------------------------------------------- animated counters --- */

    const counters = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            const el     = entry.target;
            const target = Number(el.dataset.count);
            const suffix = el.dataset.suffix || "";
            const start  = performance.now();
            const DURATION = 1600;

            function tick(now) {
                const p = Math.min((now - start) / DURATION, 1);
                // easeOutExpo for a natural deceleration
                const eased = p === 1 ? 1 : 1 - Math.pow(2, -10 * p);
                el.textContent = Math.round(target * eased).toLocaleString("en-IN") + suffix;
                if (p < 1) requestAnimationFrame(tick);
            }
            requestAnimationFrame(tick);
            obs.unobserve(el);
        });
    }, { threshold: 0.5 });

    $$("[data-count]").forEach(el => counters.observe(el));


    /* ------------------------------------------- text size + language --- */

    const savedSize = localStorage.getItem("fontScale");
    if (savedSize) applyFontScale(savedSize);

    function applyFontScale(scale) {
        document.documentElement.style.setProperty("--font-scale", scale);
        $$(".text-size button").forEach(b =>
            b.classList.toggle("active", b.dataset.size === scale));
        localStorage.setItem("fontScale", scale);
    }

    $$(".text-size button").forEach(btn =>
        btn.addEventListener("click", () => applyFontScale(btn.dataset.size)));

    let lang = localStorage.getItem("lang") || "en";
    if (lang === "hi") applyLang("hi");

    function applyLang(next) {
        lang = next;
        $$("[data-en]").forEach(el => {
            const text = el.dataset[next];
            if (text) el.textContent = text;
        });
        $("#langLabel").textContent = next === "hi" ? "English" : "हिंदी";
        document.documentElement.lang = next;
        localStorage.setItem("lang", next);
    }

    $("#langToggle").addEventListener("click", () => {
        applyLang(lang === "en" ? "hi" : "en");
        toast(lang === "hi" ? "भाषा हिंदी में बदली गई" : "Language switched to English", "info");
    });


    /* --------------------------------------------------------- auth --- */

    const authBtn = $("#authBtn");

    function renderAuthButton() {
        const adminBtn = $("#adminPanelBtn");
        if (adminBtn) adminBtn.hidden = !(currentUser && currentUser.role === "admin");
        if (currentUser) {
            const initials = currentUser.name.trim().split(/\s+/)
                .slice(0, 2).map(w => w[0]).join("").toUpperCase();
            authBtn.className = "user-chip";
            authBtn.innerHTML =
                `<span class="user-avatar">${initials}</span>` +
                `<span>${currentUser.name.split(" ")[0]}</span>`;
        } else {
            authBtn.className = "btn btn-primary btn-sm";
            authBtn.innerHTML = `<i class="fa-solid fa-user"></i><span>${
                lang === "hi" ? "लॉगिन" : "Login"}</span>`;
        }
    }

    authBtn.addEventListener("click", () => {
        if (currentUser) {
            loadBookings();
            openModal("accountModal");
        } else {
            openModal("authModal");
        }
    });

    // Tab switching inside the auth modal
    $$("#authModal .tabs button").forEach(btn =>
        btn.addEventListener("click", () => switchAuthTab(btn.dataset.tab)));

    $$("#authModal [data-goto]").forEach(btn =>
        btn.addEventListener("click", () => switchAuthTab(btn.dataset.goto)));

    function switchAuthTab(tab) {
        $$("#authModal .tabs button").forEach(b =>
            b.classList.toggle("active", b.dataset.tab === tab));
        $("#loginForm").hidden    = tab !== "login";
        $("#registerForm").hidden = tab !== "register";
        $("#authTitle").textContent = tab === "login" ? "Welcome Back" : "Create Account";
        clearError($("#authError"));
    }

    $("#loginForm").addEventListener("submit", async e => {
        e.preventDefault();
        clearError($("#authError"));
        const btn = $("button[type=submit]", e.target);
        btn.disabled = true;

        try {
            const data = await api("/api/auth/login", {
                method: "POST",
                body: { email: $("#lEmail").value, password: $("#lPass").value },
            });
            currentUser = data.user;
            renderAuthButton();
            closeModal($("#authModal"));
            e.target.reset();
            toast(`Welcome back, ${currentUser.name.split(" ")[0]}!`);
        } catch (err) {
            showError($("#authError"), err.message);
        } finally {
            btn.disabled = false;
        }
    });

    $("#registerForm").addEventListener("submit", async e => {
        e.preventDefault();
        clearError($("#authError"));
        const btn = $("button[type=submit]", e.target);
        btn.disabled = true;

        try {
            const data = await api("/api/auth/register", {
                method: "POST",
                body: {
                    name:     $("#rName").value,
                    email:    $("#rEmail").value,
                    phone:    $("#rPhone").value,
                    password: $("#rPass").value,
                },
            });
            currentUser = data.user;
            renderAuthButton();
            closeModal($("#authModal"));
            e.target.reset();
            toast(`Account created. Jai Shree Ram, ${currentUser.name.split(" ")[0]}!`);
        } catch (err) {
            showError($("#authError"), err.message);
        } finally {
            btn.disabled = false;
        }
    });

    $("#logoutBtn").addEventListener("click", async () => {
        await api("/api/auth/logout", { method: "POST" });
        currentUser = null;
        renderAuthButton();
        closeModal($("#accountModal"));
        toast("You have been logged out.", "info");
    });


    /* ------------------------------------------------ my bookings --- */

    async function loadBookings() {
        const list = $("#bookingList");
        list.innerHTML = `<div class="skeleton" style="min-height:80px"></div>`;

        try {
            const { bookings } = await api("/api/bookings");
            $("#accSub").textContent = currentUser
                ? `${currentUser.name} · ${currentUser.email}` : "";

            if (!bookings.length) {
                list.innerHTML = `
                    <div class="empty-state">
                        <i class="fa-regular fa-calendar"></i>
                        <p>You have no darshan bookings yet.</p>
                    </div>`;
                return;
            }

            list.innerHTML = "";
            bookings.forEach(b => {
                const d = new Date(b.date + "T00:00:00");
                const row = document.createElement("div");
                row.className = "booking-row" + (b.status === "cancelled" ? " cancelled" : "");
                row.innerHTML = `
                    <div class="b-date">
                        <strong>${d.getDate()}</strong>
                        <span>${d.toLocaleString("en-IN", { month: "short" })}</span>
                    </div>
                    <div class="b-main">
                        <strong></strong>
                        <span></span><br>
                        <span class="b-ref"></span>
                    </div>`;

                $(".b-main strong", row).textContent = b.slot;
                $(".b-main span", row).textContent =
                    `${b.time} · ${b.people} ${b.people > 1 ? "devotees" : "devotee"}`;
                $(".b-ref", row).textContent = b.reference;

                if (b.status === "confirmed" && !b.past) {
                    const ticket = document.createElement("a");
                    ticket.className = "btn-ticket";
                    ticket.href = b.ticket_url;
                    ticket.target = "_blank";
                    ticket.rel = "noopener";
                    ticket.innerHTML = '<i class="fa-solid fa-qrcode"></i> Ticket';
                    row.appendChild(ticket);

                    const cancel = document.createElement("button");
                    cancel.className = "btn-cancel";
                    cancel.textContent = "Cancel";
                    cancel.addEventListener("click", () => cancelBooking(b.id));
                    row.appendChild(cancel);
                } else {
                    const tag = document.createElement("span");
                    tag.className = "b-ref";
                    tag.textContent = b.status === "cancelled" ? "Cancelled" : "Completed";
                    row.appendChild(tag);
                }
                list.appendChild(row);
            });
        } catch (err) {
            list.innerHTML = `<div class="empty-state"><p>${err.message}</p></div>`;
        }
    }

    async function cancelBooking(id) {
        if (!confirm("Cancel this darshan booking?")) return;
        try {
            await api(`/api/bookings/${id}`, { method: "DELETE" });
            toast("Booking cancelled.", "info");
            loadBookings();
            loadSlots($("#bookDate").value);
        } catch (err) {
            toast(err.message, "error");
        }
    }


    /* ------------------------------------------------ timings/slots --- */

    function to12h(hhmm) {
        const [h, m] = hhmm.split(":").map(Number);
        const period = h >= 12 ? "PM" : "AM";
        const hour = h % 12 || 12;
        return `${hour}:${String(m).padStart(2, "0")} ${period}`;
    }

    async function loadSlots(dateStr) {
        const grid = $("#timingGrid");
        try {
            const data = await api(`/api/slots?date=${encodeURIComponent(dateStr)}`);
            slotCache = data.slots;

            // --- timing cards ---
            grid.innerHTML = "";
            data.slots.forEach(s => {
                const used = Math.round((s.booked / s.capacity) * 100);
                const card = document.createElement("div");
                card.className = "timing-card reveal" + (s.kind === "aarti" ? " is-aarti" : "");
                card.innerHTML = `
                    <span class="kind"></span>
                    <h4></h4>
                    <p class="clock"></p>
                    <div class="capacity-bar"><div class="capacity-fill"></div></div>
                    <p class="avail"></p>`;

                $(".kind", card).textContent = s.kind === "aarti" ? "Aarti" : "Darshan";
                $("h4", card).textContent = s.label;
                $(".clock", card).textContent = `${to12h(s.start)} – ${to12h(s.end)}`;
                $(".capacity-fill", card).style.width = `${Math.min(used, 100)}%`;
                $(".avail", card).textContent = s.full
                    ? "Fully booked"
                    : `${s.available.toLocaleString("en-IN")} places available`;

                grid.appendChild(card);
            });
            observeReveals(grid);

            // --- booking dropdown ---
            const select = $("#bookSlot");
            select.innerHTML = `<option value="">Choose a slot</option>`;
            data.slots.forEach(s => {
                const opt = document.createElement("option");
                opt.value = s.id;
                opt.textContent = `${s.label} (${to12h(s.start)} – ${to12h(s.end)})` +
                    (s.full ? " — full" : "");
                opt.disabled = s.full;
                select.appendChild(opt);
            });
        } catch (err) {
            grid.innerHTML = `<div class="empty-state"><p>${err.message}</p></div>`;
        }
    }


    /* ------------------------------------------------- live status --- */

    const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 52;   // r = 52 in the SVG

    async function loadStatus() {
        try {
            const { status } = await api("/api/visitors/status");

            // Hero pill
            $("#heroLive").textContent =
                `${status.label} · ${status.inside.toLocaleString("en-IN")} devotees inside`;
            $("#heroDot").className = `pulse-dot ${status.level}`;

            // Gauge
            const fill = $("#gaugeFill");
            fill.style.strokeDasharray = GAUGE_CIRCUMFERENCE;
            fill.style.strokeDashoffset =
                GAUGE_CIRCUMFERENCE * (1 - status.percent / 100);
            fill.className.baseVal = `gauge-fill ${status.level}`;

            $("#gaugePct").textContent   = `${status.percent}%`;
            $("#crowdLabel").textContent = status.label;
            $("#crowdAdvice").textContent = status.advice;

            $("#mInside").textContent  = status.inside.toLocaleString("en-IN");
            $("#mWait").textContent    = `~${status.wait_minutes} min`;
            $("#mSlot").textContent    = status.current_slot;
            $("#mBest").textContent    = to12h(status.best_time);
            $("#mUpdated").textContent = status.updated;

            const badge = $("#openBadge");
            badge.textContent = status.is_open ? "Open now" : "Closed";
            badge.classList.toggle("closed", !status.is_open);
        } catch (err) {
            $("#heroLive").textContent = "Live status unavailable";
            console.error(err);
        }
    }

    $("#refreshStatus").addEventListener("click", e => {
        const icon = $("i", e.currentTarget);
        icon.style.transition = "transform .6s";
        icon.style.transform = "rotate(360deg)";
        setTimeout(() => { icon.style.transition = ""; icon.style.transform = ""; }, 620);
        loadStatus();
        toast("Visitor status refreshed.", "info");
    });

    setInterval(loadStatus, 60000);   // auto-refresh every minute


    /* ---------------------------------------------------- bookings --- */

    const dateInput = $("#bookDate");
    const today = new Date();
    const iso = d => d.toISOString().slice(0, 10);

    dateInput.min   = iso(today);
    dateInput.max   = iso(new Date(today.getTime() + 60 * 864e5));
    dateInput.value = iso(today);

    dateInput.addEventListener("change", () => {
        if (dateInput.value) loadSlots(dateInput.value);
    });

    $("#bookingForm").addEventListener("submit", async e => {
        e.preventDefault();
        const errBox = $("#bookingError");
        clearError(errBox);

        if (!currentUser) {
            openModal("authModal");
            toast("Please login to book a darshan slot.", "info");
            return;
        }
        if (!$("#bookSlot").value) {
            showError(errBox, "Please choose a darshan slot.");
            return;
        }

        const btn = $("#bookSubmit");
        btn.disabled = true;

        try {
            const { booking } = await api("/api/bookings", {
                method: "POST",
                body: {
                    slot_id: Number($("#bookSlot").value),
                    date:    dateInput.value,
                    people:  Number($("#bookPeople").value),
                },
            });

            $("#rcRef").textContent  = booking.reference;
            $("#rcDate").textContent = new Date(booking.date + "T00:00:00")
                .toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
            $("#rcSlot").textContent   = booking.slot;
            $("#rcTime").textContent   = booking.time.split(" - ").map(to12h).join(" – ");
            $("#rcPeople").textContent = booking.people;
            $("#rcQr").src = booking.qr_url;
            $("#rcTicket").href = booking.ticket_url;

            openModal("receiptModal");
            loadSlots(dateInput.value);
            loadStatus();
        } catch (err) {
            showError(errBox, err.message);
        } finally {
            btn.disabled = false;
        }
    });


    /* ------------------------------------------------------ nearby --- */

    const CATEGORY_LABEL = {
        temple: "Temple", ghat: "Riverside Ghat", food: "Food", shopping: "Shopping",
    };
    const CATEGORY_ICON = {
        temple: "fa-place-of-worship", ghat: "fa-water",
        food: "fa-utensils", shopping: "fa-bag-shopping",
    };

    async function loadPlaces(category = "all") {
        const grid = $("#nearbyGrid");
        grid.innerHTML = `<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>`;

        try {
            const { places } = await api(`/api/places?category=${category}`);
            grid.innerHTML = "";

            if (!places.length) {
                grid.innerHTML = `<div class="empty-state"><i class="fa-solid fa-map"></i>
                                  <p>No places in this category yet.</p></div>`;
                return;
            }

            places.forEach(p => {
                const card = document.createElement("article");
                card.className = "place-card reveal";

                const media = p.image
                    ? `<img src="/static/images/${p.image}" alt="" loading="lazy">`
                    : `<i class="fa-solid ${CATEGORY_ICON[p.category]} placeholder-icon"></i>`;

                card.innerHTML = `
                    <div class="place-media">
                        ${media}
                        <span class="place-dist">${p.distance_km} km</span>
                    </div>
                    <div class="place-body">
                        <span class="place-cat"></span>
                        <h3></h3>
                        <p></p>
                        <a class="map-link" target="_blank" rel="noopener noreferrer">
                            <i class="fa-solid fa-location-arrow"></i> Open in Maps
                        </a>
                    </div>`;

                $(".place-cat", card).textContent = CATEGORY_LABEL[p.category] || p.category;
                $("h3", card).textContent = p.name;
                $(".place-body p", card).textContent = p.description;
                $(".map-link", card).href =
                    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(p.maps_query)}`;
                if (p.image) $("img", card).alt = p.name;

                grid.appendChild(card);
            });
            observeReveals(grid);
        } catch (err) {
            grid.innerHTML = `<div class="empty-state"><p>${err.message}</p></div>`;
        }
    }

    $$("#placeFilters .chip").forEach(chip =>
        chip.addEventListener("click", () => {
            $$("#placeFilters .chip").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            loadPlaces(chip.dataset.cat);
        }));


    /* --------------------------------------------------- festivals --- */

    async function loadFestivals() {
        const grid = $("#festivalGrid");
        try {
            const { festivals } = await api("/api/festivals");
            grid.innerHTML = "";

            festivals.forEach(f => {
                const card = document.createElement("article");
                card.className = "festival-card reveal" + (f.past ? " is-past" : "");
                card.innerHTML = `
                    <div class="fest-top">
                        <div class="fest-icon"><i class="fa-solid ${f.icon}"></i></div>
                        <div class="countdown">
                            <strong></strong>
                            <span></span>
                        </div>
                    </div>
                    <h3></h3>
                    <p class="fest-hi"></p>
                    <span class="fest-date"><i class="fa-regular fa-calendar"></i></span>
                    <p class="fest-desc"></p>`;

                const days = Math.abs(f.days_away);
                $(".countdown strong", card).textContent = f.past ? "—" : days;
                $(".countdown span", card).textContent = f.past
                    ? "Past" : (days === 1 ? "day to go" : "days to go");

                $("h3", card).textContent = f.name;
                $(".fest-hi", card).textContent = f.name_hi || "";
                $(".fest-date", card).append(" " + f.date);
                $(".fest-desc", card).textContent = f.description;

                grid.appendChild(card);
            });
            observeReveals(grid);
        } catch (err) {
            grid.innerHTML = `<div class="empty-state"><p>${err.message}</p></div>`;
        }
    }


    /* --------------------------------------------------- emergency --- */

    async function loadContacts() {
        const grid = $("#emergencyGrid");
        try {
            const { contacts } = await api("/api/contacts");
            grid.innerHTML = "";

            contacts.forEach(c => {
                const card = document.createElement("article");
                card.className = "contact-card reveal";
                card.innerHTML = `
                    <div class="contact-icon"><i class="fa-solid ${c.icon}"></i></div>
                    <div class="contact-body">
                        <h3></h3>
                        <p></p>
                        <a class="contact-num"><i class="fa-solid fa-phone"></i></a>
                    </div>`;

                $("h3", card).textContent = c.service;
                $(".contact-body p", card).textContent = c.detail;
                const link = $(".contact-num", card);
                link.href = `tel:${c.number.replace(/[^0-9+]/g, "")}`;
                link.append(" " + c.number);

                grid.appendChild(card);
            });
            observeReveals(grid);
        } catch (err) {
            grid.innerHTML = `<div class="empty-state"><p>${err.message}</p></div>`;
        }
    }


    /* -------------------------------------------------- help form --- */

    $("#helpForm").addEventListener("submit", async e => {
        e.preventDefault();
        const errBox = $("#helpError");
        clearError(errBox);

        const btn = $("#helpSubmit");
        btn.disabled = true;

        try {
            const data = await api("/api/messages", {
                method: "POST",
                body: {
                    name:    $("#hName").value,
                    email:   $("#hEmail").value,
                    subject: $("#hSubject").value,
                    message: $("#hMessage").value,
                },
            });
            e.target.reset();
            toast(data.message);
        } catch (err) {
            showError(errBox, err.message);
        } finally {
            btn.disabled = false;
        }
    });


    /* ---------------------------------------------------- lightbox --- */

    const lightbox = $("#lightbox");
    const lbImg    = $("#lightboxImg");
    const lbCap    = $("#lightboxCaption");
    let lbIndex    = 0;

    const galleryFigures = $$("#galleryGrid .gallery-item");

    galleryFigures.forEach((fig, i) =>
        fig.addEventListener("click", () => openLightbox(i)));

    function openLightbox(i) {
        lbIndex = (i + galleryFigures.length) % galleryFigures.length;
        const fig = galleryFigures[lbIndex];
        lbImg.src = $("img", fig).src;
        lbImg.alt = $("img", fig).alt;
        lbCap.textContent = $("figcaption", fig).textContent;
        lightbox.classList.add("open");
        document.body.classList.add("no-scroll");
    }

    function closeLightbox() {
        lightbox.classList.remove("open");
        if (!$(".modal-overlay.open")) document.body.classList.remove("no-scroll");
    }

    $(".lightbox-close", lightbox).addEventListener("click", closeLightbox);
    $(".prev", lightbox).addEventListener("click", () => openLightbox(lbIndex - 1));
    $(".next", lightbox).addEventListener("click", () => openLightbox(lbIndex + 1));

    lightbox.addEventListener("click", e => {
        if (e.target === lightbox) closeLightbox();
    });

    document.addEventListener("keydown", e => {
        if (!lightbox.classList.contains("open")) return;
        if (e.key === "ArrowLeft")  openLightbox(lbIndex - 1);
        if (e.key === "ArrowRight") openLightbox(lbIndex + 1);
    });


    /* -------------------------------------------------------- boot --- */

    async function init() {
        try {
            const { user } = await api("/api/auth/me");
            currentUser = user;
        } catch { /* not logged in — the UI already reflects this */ }

        renderAuthButton();
        loadStatus();
        loadSlots(dateInput.value);
        loadPlaces();
        loadFestivals();
        loadContacts();
    }

    init();

    /* ------------------------------------------------ announcements --- */
    async function loadAnnouncements() {
        try {
            const data = await api("/api/announcements");
            const a = data.announcements && data.announcements[0];
            if (!a) return;
            $("#announcementTitle").textContent = a.title + " —";
            $("#announcementText").textContent = " " + a.body;
            const bar = $("#announcementBar");
            bar.style.display = "block";
            if (a.type === "warning") bar.style.background = "#fff0ee";
            if (a.type === "success") bar.style.background = "#eefaf3";
        } catch (_) {}
    }
    loadAnnouncements();

})();

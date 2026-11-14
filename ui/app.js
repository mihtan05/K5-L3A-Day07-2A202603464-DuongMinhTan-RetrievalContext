(() => {
  "use strict";

  const state = {
    overview: null,
    activeCorpus: "bonus",
    questionsByCorpus: { bonus: [], core: [] },
    assetsById: new Map(),
    bonusTracesCache: new Map(),
    coreTracesCache: new Map(),
    isAsking: false,
  };

  const QUICK_PROMPTS = {
    bonus: [
      {
        label: "Biểu đồ: Tỷ lệ rác nhựa (Fig 5)",
        text: "Theo Figure 5 trong báo cáo World Bank 2022, nhựa chiếm bao nhiêu phần trăm tổng số rác thải được khảo sát?",
      },
      {
        label: "Bảng số liệu: Nhựa tiêu dùng chính",
        text: "Các loại nhựa tiêu dùng chính (dominant plastic polymers) và khối lượng phát sinh tại Việt Nam được thống kê như thế nào?",
      },
      {
        label: "Sơ đồ: Quy trình EPR",
        text: "Sơ đồ quy trình thực hiện Trách nhiệm mở rộng của nhà sản xuất (EPR) hoạt động qua các bước nào?",
      },
      {
        label: "Ngoài tài liệu (Kiểm tra Abstain)",
        text: "Báo cáo có thống kê doanh thu ngành thép Việt Nam năm 2024 đạt bao nhiêu tỷ USD không?",
      },
    ],
    core: [
      {
        label: "Hội nghị Liên Hợp Quốc về Nhựa",
        text: "Các mục tiêu chính liên quan đến đàm phán thỏa thuận toàn cầu về ô nhiễm nhựa được đề cập trong tài liệu là gì?",
      },
      {
        label: "Vấn đề vi nhựa & tái chế",
        text: "Tài liệu nêu những thách thức chính nào đối với việc thu gom và tái chế rác thải nhựa?",
      },
      {
        label: "Ngoài tài liệu (Kiểm tra Abstain)",
        text: "Tài liệu có quy định mức thuế carbon cho hàng không châu Âu năm 2030 không?",
      },
    ],
  };

  // ---------- DOM Utilities (XSS-safe) ----------
  const $ = (id) => document.getElementById(id);

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "className") {
        node.className = v;
      } else if (k === "textContent") {
        node.textContent = v;
      } else if (k === "dataset") {
        for (const [dk, dv] of Object.entries(v)) {
          node.dataset[dk] = String(dv);
        }
      } else if (k === "hidden") {
        node.hidden = true;
      } else {
        node.setAttribute(k, String(v));
      }
    }
    for (const child of Array.isArray(children) ? children : [children]) {
      if (child === null || child === undefined) continue;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    }
    return node;
  }

  function clearNode(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function fmtPct(rate) {
    if (rate === null || rate === undefined || Number.isNaN(Number(rate))) return "—";
    return `${(Number(rate) * 100).toFixed(1)}%`;
  }

  function fmtNum(val, digits = 2) {
    if (val === null || val === undefined || Number.isNaN(Number(val))) return "—";
    return Number(val).toFixed(digits);
  }

  function fmtFraction(obj) {
    if (!obj || typeof obj !== "object") return "—";
    const num = obj.n ?? obj.valid;
    const den = obj.N ?? obj.total;
    if (num === undefined || den === undefined) return "—";
    const pct = den > 0 ? ((num / den) * 100).toFixed(0) : "0";
    return `${num}/${den} (${pct}%)`;
  }

  // ---------- 1. Light/Dark 2-State Theme Toggle ----------
  function getEffectiveScheme() {
    const meta = document.querySelector('meta[name="color-scheme"]');
    const content = meta ? meta.getAttribute("content") : "light dark";
    if (content === "dark" || content === "light") return content;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function syncThemeUI(scheme) {
    const toggle = $("theme-toggle");
    const label = $("theme-label");
    const sun = $("theme-icon-sun");
    const moon = $("theme-icon-moon");
    const isDark = scheme === "dark";
    if (toggle) toggle.setAttribute("aria-pressed", String(isDark));
    if (label) label.textContent = isDark ? "Giao diện sáng" : "Giao diện tối";
    if (sun) sun.hidden = !isDark;
    if (moon) moon.hidden = isDark;
  }

  function applyScheme(scheme, persist = true) {
    const meta = document.querySelector('meta[name="color-scheme"]');
    if (meta) meta.setAttribute("content", scheme);
    if (persist) {
      try {
        localStorage.setItem("color-scheme", scheme);
      } catch (_) {}
    }
    syncThemeUI(scheme);
  }

  function initTheme() {
    syncThemeUI(getEffectiveScheme());
    const toggle = $("theme-toggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const next = getEffectiveScheme() === "dark" ? "light" : "dark";
        applyScheme(next, true);
      });
    }
    window.addEventListener("storage", (e) => {
      if (e.key === "color-scheme" && (e.newValue === "dark" || e.newValue === "light")) {
        applyScheme(e.newValue, false);
      }
    });
  }

  // ---------- 2. Accessible Tabs ----------
  const TAB_IDS = ["tab-playground", "tab-bonus-eval", "tab-core-eval", "tab-gallery"];

  function activateTab(tabId, focusTab = false) {
    for (const id of TAB_IDS) {
      const btn = $(id);
      if (!btn) continue;
      const selected = id === tabId;
      btn.setAttribute("aria-selected", String(selected));
      btn.setAttribute("tabindex", selected ? "0" : "-1");
      const panelId = btn.getAttribute("aria-controls");
      const panel = panelId ? $(panelId) : null;
      if (panel) panel.hidden = !selected;
      if (selected && focusTab) btn.focus();
    }
  }

  function initTabs() {
    const tablist = document.querySelector('[role="tablist"]');
    if (!tablist) return;

    for (const id of TAB_IDS) {
      const btn = $(id);
      if (btn) {
        btn.addEventListener("click", () => activateTab(id, false));
      }
    }

    tablist.addEventListener("keydown", (event) => {
      const currentIdx = TAB_IDS.indexOf(document.activeElement?.id || "");
      if (currentIdx === -1) return;
      let nextIdx = null;
      if (event.key === "ArrowRight") nextIdx = (currentIdx + 1) % TAB_IDS.length;
      else if (event.key === "ArrowLeft") nextIdx = (currentIdx - 1 + TAB_IDS.length) % TAB_IDS.length;
      else if (event.key === "Home") nextIdx = 0;
      else if (event.key === "End") nextIdx = TAB_IDS.length - 1;

      if (nextIdx !== null) {
        event.preventDefault();
        activateTab(TAB_IDS[nextIdx], true);
      }
    });
  }

  // ---------- 3. Light-Dismiss Modal Dialog ----------
  function openChunkModal(chunk) {
    const dialog = $("asset-dialog");
    if (!dialog) return;

    const cid = chunk.id || chunk.chunk_id || "Chunk";
    const mod = chunk.modality || "text";
    const page = chunk.page ? `Trang ${chunk.page}` : "Trang ?";
    const badge = $("dialog-badge");
    badge.textContent = mod;
    badge.className = `badge ${mod === "chart" || mod === "diagram" || mod === "image_diagram" ? "badge-warn" : mod === "table" ? "badge-info" : "badge-success"}`;

    $("dialog-title").textContent = chunk.title || cid;
    const parts = [cid, chunk.source_id, page, chunk.section].filter(Boolean);
    $("dialog-caption").textContent = parts.join(" · ");

    const figWrap = $("dialog-figure-wrap");
    const img = $("dialog-img");
    if (chunk.crop_url) {
      img.src = chunk.crop_url;
      figWrap.hidden = false;
    } else {
      img.removeAttribute("src");
      figWrap.hidden = true;
    }

    $("dialog-text").textContent = chunk.text || "(Không có nội dung văn bản chi tiết)";
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
  }

  function initDialog() {
    const dialog = $("asset-dialog");
    const closeBtn = $("dialog-close-btn");
    if (!dialog) return;

    if (closeBtn) {
      closeBtn.addEventListener("click", () => dialog.close());
    }

    // Fallback light-dismiss when clicking backdrop outside .modal-card
    dialog.addEventListener("click", (event) => {
      if (event.target !== dialog) return;
      const card = dialog.querySelector(".modal-card");
      if (!card) {
        dialog.close();
        return;
      }
      const rect = card.getBoundingClientRect();
      const inside =
        event.clientX >= rect.left &&
        event.clientX <= rect.right &&
        event.clientY >= rect.top &&
        event.clientY <= rect.bottom;
      if (!inside) dialog.close();
    });
  }

  // ---------- 4. Q&A Rendering (XSS-safe DOM tokens) ----------
  function buildChunkLookup(trace, retrievalComparison) {
    const map = new Map(state.assetsById);
    const register = (item) => {
      if (!item) return;
      const id = item.id || item.chunk_id;
      if (id) map.set(id, { ...map.get(id), ...item, id });
    };
    (trace?.cited_chunks || []).forEach(register);
    (trace?.context_chunks || []).forEach(register);
    if (retrievalComparison && typeof retrievalComparison === "object") {
      for (const comp of Object.values(retrievalComparison)) {
        (comp?.hits || []).forEach(register);
      }
    }
    return map;
  }

  function renderAnswerWithCitations(container, text, chunkMap) {
    clearNode(container);
    const raw = String(text || "").trim();
    if (!raw) {
      container.appendChild(el("span", { className: "abstain-note", textContent: "(Không có nội dung câu trả lời)" }));
      return;
    }

    const tokenRe = /\[([A-Za-z0-9_.:-]+)\]/g;
    let lastIndex = 0;
    let match;
    while ((match = tokenRe.exec(raw)) !== null) {
      if (match.index > lastIndex) {
        container.appendChild(document.createTextNode(raw.slice(lastIndex, match.index)));
      }
      const cid = match[1];
      const meta = chunkMap.get(cid);
      if (meta) {
        const citeBtn = el("button", {
          type: "button",
          className: "inline-cite-btn",
          title: `Xem chi tiết trích dẫn ${cid}`,
          textContent: `[${cid}]`,
        });
        citeBtn.addEventListener("click", () => openChunkModal(meta));
        container.appendChild(citeBtn);
      } else {
        container.appendChild(document.createTextNode(match[0]));
      }
      lastIndex = tokenRe.lastIndex;
    }
    if (lastIndex < raw.length) {
      container.appendChild(document.createTextNode(raw.slice(lastIndex)));
    }
  }

  function createAssistantCard({ trace, retrievalComparison, label }) {
    const status = String(trace?.status || "answered").toLowerCase();
    const isAbstain = status === "abstain";
    const chunkMap = buildChunkLookup(trace, retrievalComparison);

    const badges = [
      el("span", {
        className: `badge ${isAbstain ? "badge-warn" : "badge-success"}`,
        textContent: isAbstain ? "Từ chối trả lời (Abstain)" : "Đã trả lời",
      }),
    ];
    if (label) {
      badges.push(el("span", { className: "badge badge-info", textContent: label }));
    }
    if (trace?.review && typeof trace.review.passed === "boolean") {
      badges.push(
        el("span", {
          className: `badge ${trace.review.passed ? "badge-success" : "badge-danger"}`,
          textContent: trace.review.passed ? "Audit: Pass" : "Audit: Fail",
        })
      );
    }

    const metricParts = [];
    if (trace?.latency_s !== undefined && trace?.latency_s !== null) {
      metricParts.push(`${Number(trace.latency_s).toFixed(2)}s`);
    }
    if (trace?.num_searches !== undefined && trace?.num_searches !== null) {
      metricParts.push(`${trace.num_searches} search`);
    }
    if (trace?.usage?.total_tokens) {
      metricParts.push(`${trace.usage.total_tokens} tok`);
    }

    const header = el("div", { className: "assistant-card-header" }, [
      el("div", { className: "assistant-badges" }, badges),
      el("span", { className: "assistant-metrics", textContent: metricParts.join(" · ") }),
    ]);

    const answerBody = el("div", { className: "answer-body" });
    renderAnswerWithCitations(answerBody, trace?.answer || "", chunkMap);

    const children = [header, answerBody];

    if (trace?.expected_answer) {
      children.push(
        el("div", { className: "expected-box" }, [
          el("strong", { textContent: "Đáp án chuẩn tham khảo: " }),
          document.createTextNode(trace.expected_answer),
        ])
      );
    }

    // Cited Evidence Strip
    const citedChunks = trace?.cited_chunks || [];
    const evidenceStrip = el("div", { className: "evidence-strip" }, [
      el("div", { className: "evidence-title", textContent: `Nguồn trích dẫn (${citedChunks.length})` }),
    ]);

    if (citedChunks.length > 0) {
      const chipWrap = el("div", { className: "evidence-chips" });
      for (const c of citedChunks) {
        const cid = c.id || c.chunk_id;
        const pageStr = c.page ? `p.${c.page}` : "";
        const modStr = c.modality || "text";
        const metaTxt = [modStr, pageStr, c.title].filter(Boolean).join(" · ");
        const chip = el("button", { type: "button", className: "cite-chip" }, [
          el("code", { textContent: cid }),
          el("span", { className: "cite-chip-meta", textContent: metaTxt }),
        ]);
        chip.addEventListener("click", () => openChunkModal(c));
        chipWrap.appendChild(chip);
      }
      evidenceStrip.appendChild(chipWrap);
    } else {
      evidenceStrip.appendChild(
        el("p", {
          className: "abstain-note",
          textContent: isAbstain
            ? "Agent từ chối trả lời vì tài liệu không chứa bằng chứng đủ rõ — không bịa nguồn trích dẫn."
            : "Không có chunk trích dẫn cụ thể được đính kèm.",
        })
      );
    }
    children.push(evidenceStrip);

    // Collapsible technical details (progressive disclosure so Q&A stays uncluttered)
    const techGroup = el("div", { className: "tech-details-group" });
    const events = trace?.events || [];
    if (events.length > 0) {
      const list = el("ul", { className: "events-list" });
      events.forEach((ev, idx) => {
        const toolName = ev.tool_name || ev.type || "step";
        const argText = ev.arguments ? JSON.stringify(ev.arguments) : ev.message || "";
        const resultHint = ev.returned_ids ? ` -> [${ev.returned_ids.join(", ")}]` : "";
        list.appendChild(
          el("li", { className: "event-row" }, [
            el("span", { className: "event-tool", textContent: `${idx + 1}. ${toolName}` }),
            el("div", { className: "event-detail", textContent: `${argText}${resultHint}` }),
          ])
        );
      });
      techGroup.appendChild(
        el("details", { className: "tech-details" }, [
          el("summary", { textContent: `Hành trình gọi Tool của Agent (${events.length} bước)` }),
          list,
        ])
      );
    }

    if (retrievalComparison && Object.keys(retrievalComparison).length > 0) {
      const compGrid = el("div", { className: "comparison-grid" });
      for (const [method, info] of Object.entries(retrievalComparison)) {
        const col = el("div", { className: "comparison-col" }, [
          el("div", { className: "comparison-col-head" }, [
            el("span", { textContent: method.toUpperCase() }),
            el("span", { className: "mono", textContent: `${info.latency_ms} ms` }),
          ]),
        ]);
        const hits = info.hits || [];
        if (hits.length === 0) {
          col.appendChild(el("span", { className: "abstain-note", textContent: "Không có kết quả" }));
        } else {
          for (const h of hits) {
            const btn = el("button", { type: "button", className: "comparison-hit" }, [
              el("span", { className: "comparison-hit-id", textContent: `#${h.rank} · ${h.id} (score ${Number(h.score || 0).toFixed(3)})` }),
              el("span", { textContent: (h.title || h.text || "").slice(0, 95) }),
            ]);
            btn.addEventListener("click", () => openChunkModal(h));
            col.appendChild(btn);
          }
        }
        compGrid.appendChild(col);
      }
      techGroup.appendChild(
        el("details", { className: "tech-details" }, [
          el("summary", { textContent: "So sánh top-3 Retrieval (Dense vs BM25 vs Hybrid)" }),
          compGrid,
        ])
      );
    }

    if (techGroup.children.length > 0) {
      children.push(techGroup);
    }

    return el("div", { className: "assistant-card" }, children);
  }

  function removeEmptyState() {
    const empty = $("qa-empty-state");
    if (empty) empty.remove();
    const clearBtn = $("btn-clear-thread");
    if (clearBtn) clearBtn.hidden = false;
  }

  function restoreEmptyState() {
    const thread = $("qa-thread");
    clearNode(thread);
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.7");
    const circle = document.createElementNS(svgNS, "circle");
    circle.setAttribute("cx", "11");
    circle.setAttribute("cy", "11");
    circle.setAttribute("r", "8");
    const path = document.createElementNS(svgNS, "path");
    path.setAttribute("d", "m21 21-4.3-4.3");
    svg.appendChild(circle);
    svg.appendChild(path);

    const iconWrap = el("div", { className: "empty-icon", "aria-hidden": "true" }, [svg]);
    const p = el("p", {}, [
      "Nhập câu hỏi phía trên hoặc bấm một chip gợi ý để nhận câu trả lời kèm ",
      el("code", { textContent: "[chunk_id]" }),
      " có thể click xem nguyên văn trang PDF.",
    ]);
    thread.appendChild(
      el("div", { id: "qa-empty-state", className: "empty-state-card" }, [
        iconWrap,
        el("h3", { textContent: "Sẵn sàng tra cứu tài liệu" }),
        p,
      ])
    );
    const clearBtn = $("btn-clear-thread");
    if (clearBtn) clearBtn.hidden = true;
  }

  function appendConversationTurn({ question, corpus, metaLabel, trace, retrievalComparison }) {
    const thread = $("qa-thread");
    removeEmptyState();
    const userBubble = el("div", { className: "user-bubble" }, [
      el("div", { className: "bubble-meta" }, [
        el("span", { textContent: corpus === "bonus" ? "Bonus 138p" : "Core 94p" }),
        metaLabel ? el("span", { textContent: `· ${metaLabel}` }) : null,
      ]),
      el("p", { className: "user-question-text", textContent: question }),
    ]);

    const assistantCard = createAssistantCard({ trace, retrievalComparison, label: metaLabel });
    const turn = el("article", { className: "qa-turn" }, [userBubble, assistantCard]);
    thread.prepend(turn);
  }

  // ---------- 5. Corpus Controls, Quick Prompts & Ask Form ----------
  function renderQuickPrompts() {
    const container = $("quick-chips");
    if (!container) return;
    clearNode(container);
    const prompts = QUICK_PROMPTS[state.activeCorpus] || [];
    for (const item of prompts) {
      const btn = el("button", {
        type: "button",
        className: "chip-btn",
        textContent: item.label,
        title: item.text,
      });
      btn.addEventListener("click", () => {
        const input = $("question-input");
        const err = $("question-error");
        if (err) err.hidden = true;
        if (input) {
          input.value = item.text;
          input.focus();
        }
        const status = $("live-status");
        if (status) status.textContent = "Đã điền câu hỏi gợi ý — nhấn Enter hoặc Gửi câu hỏi";
      });
      container.appendChild(btn);
    }
  }

  async function populateSampleSelect(corpus) {
    const sel = $("sample-select");
    if (!sel) return;
    let items = state.questionsByCorpus[corpus];
    if (!items || items.length === 0) {
      const res = await fetch(`/api/questions?corpus=${encodeURIComponent(corpus)}&split=all`);
      if (res.ok) {
        items = await res.json();
        state.questionsByCorpus[corpus] = items;
      } else {
        items = [];
      }
    }

    clearNode(sel);
    sel.appendChild(
      el("option", {
        value: "",
        textContent: `Hoặc chọn từ bộ Benchmark (${items.length} câu)...`,
      })
    );
    for (const q of items) {
      const cat = q.category || (q.answerable === false ? "unanswerable" : "answerable");
      sel.appendChild(
        el("option", {
          value: q.question,
          textContent: `[${q.split}/${cat}] ${q.id}: ${q.question.slice(0, 68)}`,
        })
      );
    }
  }

  function initComposer() {
    const radios = document.querySelectorAll('input[name="corpus"]');
    radios.forEach((radio) => {
      radio.addEventListener("change", () => {
        if (!radio.checked) return;
        state.activeCorpus = radio.value;
        renderQuickPrompts();
        populateSampleSelect(state.activeCorpus);
      });
    });

    const sampleSel = $("sample-select");
    if (sampleSel) {
      sampleSel.addEventListener("change", () => {
        if (!sampleSel.value) return;
        const input = $("question-input");
        const err = $("question-error");
        if (err) err.hidden = true;
        if (input) {
          input.value = sampleSel.value;
          input.focus();
        }
      });
    }

    const input = $("question-input");
    const askForm = $("ask-form");
    const errEl = $("question-error");

    if (input) {
      input.addEventListener("input", () => {
        if (errEl && !errEl.hidden && input.value.trim()) {
          errEl.hidden = true;
        }
      });
      // IME-safe Enter to submit (Shift+Enter inserts newline)
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          if (event.isComposing || event.keyCode === 229) return;
          event.preventDefault();
          askForm.requestSubmit();
        }
      });
    }

    if (askForm) {
      askForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (state.isAsking) return;

        const question = (input?.value || "").trim();
        if (!question) {
          if (errEl) {
            errEl.textContent = "Vui lòng nhập câu hỏi hoặc chọn một gợi ý trước khi gửi.";
            errEl.hidden = false;
          }
          input?.focus();
          return;
        }
        if (errEl) errEl.hidden = true;

        const configMode = $("select-config")?.value || "improved";
        const method = $("select-method")?.value || "hybrid";
        const corpus = state.activeCorpus;

        state.isAsking = true;
        const btn = $("btn-run-query");
        const btnLabel = $("btn-run-label");
        const status = $("live-status");
        if (btn) btn.disabled = true;
        if (btnLabel) btnLabel.textContent = "Đang tìm kiếm...";
        if (status) status.textContent = "Đang truy vấn pgvector + BM25...";

        removeEmptyState();
        const thread = $("qa-thread");
        const userBubble = el("div", { className: "user-bubble" }, [
          el("div", { className: "bubble-meta" }, [
            el("span", { textContent: corpus === "bonus" ? "Bonus 138p" : "Core 94p" }),
            el("span", { textContent: `· ${method} · ${configMode}` }),
          ]),
          el("p", { className: "user-question-text", textContent: question }),
        ]);

        const dots = el("span", { className: "typing-dots", "aria-hidden": "true" }, [
          el("span"),
          el("span"),
          el("span"),
        ]);
        const loadingCard = el("div", { className: "assistant-card loading-card" }, [
          dots,
          el("span", { textContent: "Agent đang tìm đoạn văn bản/bảng biểu phù hợp và tổng hợp câu trả lời..." }),
        ]);
        const turn = el("article", { className: "qa-turn" }, [userBubble, loadingCard]);
        thread.prepend(turn);
        turn.scrollIntoView({ behavior: "smooth", block: "nearest" });

        try {
          const res = await fetch("/api/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              corpus,
              config_mode: configMode,
              retrieval_method: method,
              question,
            }),
          });
          const data = await res.json();
          if (!res.ok || data.error) {
            throw new Error(data.error || `HTTP ${res.status}`);
          }

          const answerCard = createAssistantCard({
            trace: data.trace,
            retrievalComparison: data.retrieval_comparison,
            label: `${method} · ${configMode}`,
          });
          turn.replaceChild(answerCard, loadingCard);
          if (status) {
            status.textContent = `Hoàn tất trong ${Number(data.trace?.latency_s || 0).toFixed(2)}s`;
          }
          if (input) input.value = "";
        } catch (err) {
          const errorCard = el("div", { className: "assistant-card" }, [
            el("span", { className: "badge badge-danger", textContent: "Lỗi truy vấn" }),
            el("p", {
              className: "answer-body",
              textContent: `Không thể hoàn tất câu hỏi: ${err.message}. Kiểm tra lại PostgreSQL/pgvector hoặc biến môi trường LLM.`,
            }),
          ]);
          turn.replaceChild(errorCard, loadingCard);
          if (status) status.textContent = "Truy vấn gặp lỗi";
        } finally {
          state.isAsking = false;
          if (btn) btn.disabled = false;
          if (btnLabel) btnLabel.textContent = "Gửi câu hỏi";
        }
      });
    }

    const clearBtn = $("btn-clear-thread");
    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        restoreEmptyState();
        const status = $("live-status");
        if (status) status.textContent = "";
      });
    }
  }

  // ---------- 6. Bonus Report Rendering ----------
  function renderBonusKPIs() {
    const grid = $("bonus-kpi-grid");
    if (!grid || !state.overview) return;
    clearNode(grid);

    const bTest = state.overview.bonus_runs?.["test-selected"] || {};
    const bDevImp = state.overview.bonus_runs?.["dev-improved"] || {};
    const bDevBase = state.overview.bonus_runs?.["dev-baseline"] || {};
    const bMan = state.overview.bonus_manifest || {};

    const cards = [
      {
        label: "Bonus Test Pass Rate",
        value: bTest.overall_pass_rate_pct !== undefined ? `${bTest.overall_pass_rate_pct}%` : "—",
        sub: `${bTest.total_passed ?? "—"}/${bTest.total_questions ?? "—"} câu đạt (Ngưỡng >=90%)`,
      },
      {
        label: "Dev Improved vs Baseline",
        value: `${bDevImp.overall_pass_rate_pct ?? "—"}% vs ${bDevBase.overall_pass_rate_pct ?? "—"}%`,
        sub: "Cải thiện nhờ Hybrid + Visual Metadata",
      },
      {
        label: "Citation Validity (Test)",
        value: fmtPct(bTest.citation_validity?.rate),
        sub: `${bTest.citation_validity?.valid ?? "—"}/${bTest.citation_validity?.total ?? "—"} trích dẫn hợp lệ`,
      },
      {
        label: "Quy mô Bonus Corpus",
        value: `${bMan.document?.total_pages ?? bMan.total_pages ?? 138} trang`,
        sub: `${bMan.total_chunks ?? 458} chunks · 80 bảng/biểu đồ`,
      },
    ];

    for (const c of cards) {
      grid.appendChild(
        el("div", { className: "kpi-card" }, [
          el("div", { className: "kpi-label", textContent: c.label }),
          el("div", { className: "kpi-value", textContent: c.value }),
          el("div", { className: "kpi-sub", textContent: c.sub }),
        ])
      );
    }
  }

  async function loadBonusReport() {
    const run = $("bonus-run-select")?.value || "test-selected";
    const catFilter = $("bonus-cat-filter")?.value || "all";

    let payload = state.bonusTracesCache.get(run);
    if (!payload) {
      const res = await fetch(`/api/traces?corpus=bonus&run=${encodeURIComponent(run)}`);
      if (!res.ok) return;
      payload = await res.json();
      state.bonusTracesCache.set(run, payload);
    }

    const catTbody = $("bonus-category-tbody");
    if (catTbody) {
      clearNode(catTbody);
      const byCat = payload.summary?.by_category || {};
      for (const [cat, stats] of Object.entries(byCat)) {
        const pct = Number(stats.rate_pct ?? stats.pass_rate_pct ?? 0);
        const catLabel = stats.label_vi ? `${stats.label_vi} (${cat})` : cat;
        catTbody.appendChild(
          el("tr", {}, [
            el("td", { className: "mono", textContent: catLabel }),
            el("td", { textContent: `${stats.passed} / ${stats.total}` }),
            el("td", {}, [
              el("span", {
                className: `badge ${pct >= 90 ? "badge-success" : pct >= 70 ? "badge-warn" : "badge-danger"}`,
                textContent: `${pct.toFixed(1)}%`,
              }),
            ]),
          ])
        );
      }
    }

    const tracesTbody = $("bonus-traces-tbody");
    if (tracesTbody) {
      clearNode(tracesTbody);
      const rows = (payload.traces || []).filter(
        (t) => catFilter === "all" || t.category === catFilter
      );
      for (const t of rows) {
        const passed = t.review?.passed;
        const tr = el("tr", { className: "clickable-row" }, [
          el("td", { className: "mono", textContent: t.query_id }),
          el("td", { className: "mono", textContent: t.category || "—" }),
          el("td", { textContent: t.question || "" }),
          el("td", { textContent: t.status || "—" }),
          el("td", {}, [
            el("span", {
              className: `badge ${passed ? "badge-success" : "badge-danger"}`,
              textContent: passed === true ? "PASS" : passed === false ? "FAIL" : "—",
            }),
          ]),
        ]);
        tr.addEventListener("click", () => {
          appendConversationTurn({
            question: t.question || t.query_id,
            corpus: "bonus",
            metaLabel: `Bonus ${run} · ${t.query_id}`,
            trace: t,
          });
          activateTab("tab-playground", false);
          window.scrollTo({ top: 0, behavior: "smooth" });
        });
        tracesTbody.appendChild(tr);
      }
    }
  }

  // ---------- 7. Core Report Rendering ----------
  function renderCoreKPIs() {
    const grid = $("core-kpi-grid");
    if (!grid || !state.overview) return;
    clearNode(grid);

    const cMan = state.overview.core_manifest || {};
    const cTestHybrid = state.overview.retrieval_runs?.["test-selected"]?.methods?.hybrid || {};
    const cTestImp = state.overview.core_agent_runs?.["test-improved"] || {};
    const cTestBase = state.overview.core_agent_runs?.["test-baseline"] || {};

    const cards = [
      {
        label: "Core Hybrid Test Hit@1",
        value: fmtPct(cTestHybrid.hit_at_1_rate),
        sub: `MRR@5: ${fmtNum(cTestHybrid.mrr_at_5 ?? cTestHybrid.mrr_at_3, 3)} · Cov: ${fmtPct(cTestHybrid.context_evidence_rate)}`,
      },
      {
        label: "Core Improved Grounded",
        value: fmtNum(cTestImp.grounded_answer?.mean, 3),
        sub: `Baseline Test: ${fmtNum(cTestBase.grounded_answer?.mean, 3)}`,
      },
      {
        label: "Core Citation Validity",
        value: fmtFraction(cTestImp.citation_validity),
        sub: `Abstention: ${fmtFraction(cTestImp.abstention)}`,
      },
      {
        label: "Quy mô Core Corpus",
        value: `${cMan.pages ?? cMan.total_pages ?? 94} trang`,
        sub: `${cMan.chunks ?? cMan.total_chunks ?? 407} chunks (2 tài liệu)`,
      },
    ];

    for (const c of cards) {
      grid.appendChild(
        el("div", { className: "kpi-card" }, [
          el("div", { className: "kpi-label", textContent: c.label }),
          el("div", { className: "kpi-value", textContent: c.value }),
          el("div", { className: "kpi-sub", textContent: c.sub }),
        ])
      );
    }
  }

  function renderCoreSummaryTables() {
    const runs = state.overview?.retrieval_runs || {};
    const sel = $("core-run-select");
    if (sel && sel.options.length === 0) {
      for (const name of Object.keys(runs)) {
        sel.appendChild(el("option", { value: name, textContent: name }));
      }
      if (runs["test-selected"]) sel.value = "test-selected";
    }

    const selectedRun = sel?.value || Object.keys(runs)[0];
    const retTbody = $("core-retrieval-tbody");
    if (retTbody && selectedRun && runs[selectedRun]) {
      clearNode(retTbody);
      const methods = runs[selectedRun].methods || {};
      for (const [m, stats] of Object.entries(methods)) {
        const mrr = stats.mrr_at_5 ?? stats.mrr_at_3;
        retTbody.appendChild(
          el("tr", {}, [
            el("td", { className: "mono", textContent: m }),
            el("td", { textContent: fmtPct(stats.hit_at_1_rate) }),
            el("td", { textContent: fmtPct(stats.evidence_hit_at_3_rate) }),
            el("td", { textContent: fmtNum(mrr, 3) }),
            el("td", { textContent: fmtPct(stats.context_evidence_rate) }),
            el("td", { textContent: `${fmtNum(stats.avg_latency_s, 3)}s` }),
          ])
        );
      }
    }

    const agentTbody = $("core-agent-summary-tbody");
    const agentRuns = state.overview?.core_agent_runs || {};
    if (agentTbody) {
      clearNode(agentTbody);
      for (const [runName, s] of Object.entries(agentRuns)) {
        agentTbody.appendChild(
          el("tr", {}, [
            el("td", { className: "mono", textContent: runName }),
            el("td", { textContent: s.split || "—" }),
            el("td", { textContent: fmtNum(s.grounded_answer?.mean, 3) }),
            el("td", { textContent: fmtFraction(s.citation_validity) }),
            el("td", { textContent: fmtFraction(s.abstention) }),
            el("td", { textContent: fmtFraction(s.false_abstention) }),
          ])
        );
      }
    }
  }

  async function loadCoreTraces() {
    const run = $("core-agent-trace-select")?.value || "test-improved";
    let payload = state.coreTracesCache.get(run);
    if (!payload) {
      const res = await fetch(`/api/traces?corpus=core&run=${encodeURIComponent(run)}`);
      if (!res.ok) return;
      payload = await res.json();
      state.coreTracesCache.set(run, payload);
    }

    const tbody = $("core-traces-tbody");
    if (!tbody) return;
    clearNode(tbody);
    for (const t of payload.traces || []) {
      const isAbstain = t.status === "abstain";
      const tr = el("tr", { className: "clickable-row" }, [
        el("td", { className: "mono", textContent: t.query_id }),
        el("td", { className: "mono", textContent: t.answerable === false ? "unanswerable" : "answerable" }),
        el("td", { textContent: t.question || "" }),
        el("td", {}, [
          el("span", {
            className: `badge ${isAbstain ? "badge-warn" : "badge-success"}`,
            textContent: t.status || "—",
          }),
        ]),
        el("td", { className: "mono", textContent: String((t.citations || []).length) }),
      ]);
      tr.addEventListener("click", () => {
        appendConversationTurn({
          question: t.question || t.query_id,
          corpus: "core",
          metaLabel: `Core ${run} · ${t.query_id}`,
          trace: t,
        });
        activateTab("tab-playground", false);
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      tbody.appendChild(tr);
    }
  }

  // ---------- 8. Visual Asset Gallery ----------
  function renderGallery() {
    const grid = $("asset-gallery-grid");
    if (!grid || !state.overview) return;
    clearNode(grid);

    const modFilter = $("gallery-mod-filter")?.value || "all";
    const query = ($("gallery-search")?.value || "").trim().toLowerCase();
    const assets = (state.overview.visual_assets || []).filter((a) => {
      if (modFilter !== "all" && a.modality !== modFilter) return false;
      if (!query) return true;
      const hay = `${a.chunk_id} ${a.title} ${a.section} ${a.text} p.${a.page}`.toLowerCase();
      return hay.includes(query);
    });

    if (assets.length === 0) {
      grid.appendChild(
        el("p", { className: "abstain-note", textContent: "Không tìm thấy bảng hoặc biểu đồ phù hợp bộ lọc." })
      );
      return;
    }

    for (const a of assets) {
      const badgeCls = a.modality === "table" ? "badge-info" : "badge-warn";
      const card = el("button", { type: "button", className: "asset-card" }, [
        el("div", { className: "asset-card-head" }, [
          el("span", { className: `badge ${badgeCls}`, textContent: a.modality || "asset" }),
          el("span", { className: "asset-page", textContent: `p.${a.page || "?"}` }),
        ]),
        el("h3", { className: "asset-title", textContent: a.title || a.chunk_id }),
        el("p", { className: "asset-excerpt", textContent: (a.text || "").slice(0, 180) }),
      ]);
      card.addEventListener("click", () => openChunkModal({ ...a, id: a.chunk_id }));
      grid.appendChild(card);
    }
  }

  // ---------- 9. App Initialization ----------
  async function init() {
    initTheme();
    initTabs();
    initDialog();
    initComposer();
    renderQuickPrompts();

    try {
      const [overviewRes] = await Promise.all([
        fetch("/api/overview"),
        populateSampleSelect("bonus"),
      ]);
      if (!overviewRes.ok) throw new Error(`HTTP ${overviewRes.status}`);
      state.overview = await overviewRes.json();

      for (const a of state.overview.visual_assets || []) {
        if (a.chunk_id) state.assetsById.set(a.chunk_id, { ...a, id: a.chunk_id });
      }

      const bTest = state.overview.bonus_runs?.["test-selected"];
      const assetCount = (state.overview.visual_assets || []).length;
      const pill = $("header-status-pill");
      if (pill && bTest) {
        pill.textContent = `Bonus Test ${bTest.overall_pass_rate_pct}% · ${assetCount} Visual Assets`;
      } else if (pill) {
        pill.textContent = `${assetCount} Visual Assets sẵn sàng`;
      }

      renderBonusKPIs();
      renderCoreKPIs();
      renderCoreSummaryTables();
      renderGallery();

      await Promise.all([loadBonusReport(), loadCoreTraces()]);

      $("bonus-run-select")?.addEventListener("change", loadBonusReport);
      $("bonus-cat-filter")?.addEventListener("change", loadBonusReport);
      $("core-run-select")?.addEventListener("change", renderCoreSummaryTables);
      $("core-agent-trace-select")?.addEventListener("change", loadCoreTraces);
      $("gallery-mod-filter")?.addEventListener("change", renderGallery);
      $("gallery-search")?.addEventListener("input", renderGallery);
    } catch (err) {
      const pill = $("header-status-pill");
      if (pill) pill.textContent = `Lỗi kết nối API (${err.message})`;
    }
  }

  init();
})();

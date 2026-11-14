# Báo cáo Day 7

**Sinh viên:** Dương Minh Tân · **MSSV:** `2A202603464` · **Lớp:** `K5-L3A`

## Dữ liệu và benchmark

- Nguồn, quyền sử dụng, số trang và số chunk: 2 báo cáo World Bank *Taking Stock* (`wb_taking_stock_aug2024`, `wb_taking_stock_mar2025`, giấy phép `CC BY-NC 3.0 IGO` / Public Disclosure Authorized), **94 trang** → **407 chunk** tách bằng `by_paragraph(max_size=800)` (chiến lược `B` từ Day 6; metadata `year`, `section`, `source_id`, `page`), lưu tại [chunks.json](../../data/chunks.json) và [index_manifest.json](../../data/index_manifest.json) (`embed=159.63s`, `total=238.46s`, `chunks_sha256`: `e349e3a9...346aa1`).
- Vector store, embedding model, phiên bản và số chiều: **PostgreSQL 18.6** + **pgvector 0.8.1** (`127.0.0.1:55433/day6_lab`, `psycopg 3.3.8`, exact cosine similarity, `407` rows); embedding **`BAAI/bge-base-en-v1.5`** (**768 chiều**, `sentence-transformers 6.3.0`, `torch 2.15.0+cpu`) nối qua [day6.py](../../rag/day6.py); lexical `rank_bm25` (`BM25Okapi`) và reranker `BAAI/bge-reranker-base`.
- Agent model, cách chạy và phân chia dev/test: **`gemini-2.5-flash-lite`** (`provider=gemini`, `temperature=0.0`, `max_tokens=1024`) qua [agent.py](../../rag/agent.py); chạy bằng `python -m rag.eval_retrieval` và `rag.eval_agent` (chỉ truyền `id`, `question`). Benchmark [questions.json](../../data/benchmark/questions.json) gồm **24 câu**: `dev` **17 câu** (`q01`–`q15` có đáp án + `u01`–`u02` thiếu bằng chứng) và `test` **7 câu** (`q16`–`q20` có đáp án + `u03`–`u04` thiếu bằng chứng).
- Cách xác định câu có/thiếu evidence và tiêu chí chấm: *Retrieval* dùng `is_hit` đối chiếu `source_id`, `page`, `gold.evidence` (`Hit@1`, `Evidence Hit@3`, `MRR@k`, `Context Evidence Rate`) và chấm tay context trên `test` thang `0/1/2` tại [test_context_manual_audit.json](../../results/retrieval/test_context_manual_audit.json). *Agent* đọc và chấm tay từng câu trong `reviews.json`, tổng hợp qua [agent_metrics.py](../../starter/agent_metrics.py): điểm `2` khi đủ số liệu/điều kiện/đơn vị và mọi `[chunk_id]` trích dẫn đều thực sự ủng hộ; `abstain` nhầm chấm `0`; câu thiếu bằng chứng phải từ chối đúng mà không suy đoán.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline | `dense`, top-3, no filter, FIFO, 2400 chars | Đường cơ sở Day 6 nguyên bản | dev | 10/15 (0.6667) | 14/15 (0.9333) | 14/15 (0.9333) | 0.2791s/câu · `$0` |
| Dense + filter | `dense`, top-3, user filter, FIFO, 2400 chars | Bật filter `year`/`section` tránh nhiễu khác ấn bản | dev | 11/15 (0.7333) | 14/15 (0.9333) | 14/15 (0.9333) | 0.3351s/câu · `$0` |
| Phương pháp 2 | `bm25`, top-3, user filter, FIFO, 2400 chars | Khớp từ khóa chính xác cho con số/thuật ngữ | dev | 12/15 (0.8000) | 13/15 (0.8667) | 13/15 (0.8667) | 0.0043s/câu · `$0` |
| Phương pháp 3 / Cải thiện 1 | `hybrid` (RRF `k=60`, pool=20), top-3, user filter, FIFO, 2400 | Hợp nhất ngữ nghĩa + từ khóa vào top-3 | dev | 11/15 (0.7333) | 15/15 (1.0000) | 15/15 (1.0000) | 0.6259s/câu · `$0` |
| Phương pháp 4 | `hybrid_rerank` (`bge-reranker-base`), top-3, filter, FIFO, 2400 | Cross-encoder chấm lại cặp `(query, chunk)` | dev | 11/15 (0.7333) | 15/15 (1.0000) | 15/15 (1.0000) | 12.3725s/câu · `$0` |
| Ablation budget hẹp | `hybrid`, top-3, user filter, FIFO, **1200** chars | Kiểm chứng tác động khi siết context budget | dev | 11/15 (0.7333) | 15/15 (1.0000) | 11/15 (0.7333) | 0.2862s/câu · `$0` |
| Cải thiện 2 | `hybrid`, top-5, user filter, `score_dedup`, 3200 chars | Tăng `top-k=5` + budget 3200 tránh rơi bằng chứng hạng 2–4 | dev | 11/15 (0.7333) | 15/15 (1.0000) | 15/15 (1.0000) | 0.3143s/câu · `$0` |
| So sánh PP4 mở rộng | `hybrid_rerank`, top-5, user filter, `score_dedup`, 3200 chars | Kiểm tra reranker ở cấu hình mở rộng `top-k=5, 3200` | dev | 11/15 (0.7333) | 15/15 (1.0000) | 15/15 (1.0000) | 10.0423s/câu · `$0` |
| Cấu hình đã chọn | `hybrid`, top-5, user filter, `score_dedup`, 3200 chars | Đánh giá độc lập trên `test` (`MRR@5 = 1.0000`) | test | 5/5 (1.0000) | 5/5 (1.0000) | 5/5 (1.0000) | 0.2547s/câu · `$0` |
| Baseline | `dense`, top-3, no filter, FIFO, 2400 chars | Đối chiếu trực tiếp Baseline trên `test` (`MRR@3 = 0.9000`) | test | 4/5 (0.8000) | 5/5 (1.0000) | 5/5 (1.0000) | 0.2441s/câu · `$0` |

Trên `dev`, `hybrid` RRF đồng thời là Phương pháp 3 và Cải thiện 1; toàn bộ embedding/BM25/reranker chạy cục bộ (`$0`). Chấm tay context trên `test` ([test_context_manual_audit.json](../../results/retrieval/test_context_manual_audit.json)) đều đạt `2.0/2.0`, nhưng Baseline không filter để lọt chunk dự báo 8/2024 (`aug2024__p033__c002`) vào hạng 2 ở `q19` và xếp footnote `p053__c003` trước `p053__c000` ở `q18`, còn cấu hình đã chọn đạt `Hit@1 = 5/5`. Hai lỗi điển hình trên `dev` và lý do chốt cấu hình:
- **Lỗi `q13` (va chạm hai ấn bản):** Hỏi dự báo GDP bản *August 2024*, nhưng `dense` không filter xếp bản 3/2025 (`mar2025__p037__c002`, score `0.773754`) lên hạng 1 trước bản đúng 8/2024 (`aug2024__p016__c000`, `0.773563`); bật metadata filter nâng `Hit@1` của `dense` từ `10/15 → 11/15`.
- **Lỗi `q10` & ablation budget (`1200` vs `3200`):** `dense` nhầm *"fiscal account surplus 1.8% GDP"* sang *"current account surplus"* (rơi `mar2025__p014__c000` khỏi top-3 → `14/15`), còn `bm25` trượt câu diễn đạt lại `q02`, `q08` (`13/15`); `hybrid` RRF đưa `mar2025__p014__c000` lên hạng 2 và giữ đủ phủ ngữ nghĩa (`15/15`). Khi siết `budget=1200` (`dev-b1200`), `Context Evidence Rate` tụt xuống `11/15`; vì `hybrid` ở `top_k=5, budget=3200, score_dedup` đạt cùng điểm tuyệt đối với `hybrid_rerank` nhưng nhanh hơn ~32× (`0.3143s` vs `10.0423s`), tôi chốt cấu hình này.

## Agent và đánh giá

- Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi: *Baseline* dùng 1 tool `search_documents` (`dense`, `top_k=3`, `budget=1600`, `fifo`, `max_searches=2`); *Improved* dùng 3 tool (`search_documents` `hybrid`, `keyword_search` `bm25`, `get_adjacent_chunks`), `top_k=5`, `budget=3200`, `score_dedup`, `max_searches=4`, tự suy luận filter `year`/`section` qua `_sanitize_filter` (tìm lại không filter nếu rỗng). Kết quả nhiều lượt được chuẩn hóa bằng `pack_score = 1 / (10 + rank)` (chunk kề nhận `0.9 × parent_ps`) rồi đưa qua `pack_context`; `_validate_citations` buộc mọi `[chunk_id]` phải nằm trong context trước khi chấp nhận `submit_answer`. Dừng khi gọi hợp lệ `submit_answer`/`abstain` (cấm gọi khi chưa search) hoặc quá `max_turns`; lỗi DB (`RetrievalError`) và lỗi API sau 6 lần retry (`ProviderError`) ghi `status="error"` vào trace, không nuốt lỗi.

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| Baseline / `dev` | 17/17 | TB `1.65` (1 lượt: 6, 2 lượt: 11; 28 `search_documents`) | `0`: 4, `1`: 1, `2`: 10 · TB **`1.40`** (`N=15`) | 14/14 | 11/11 | 2/2 | 4/15 |
| Improved / `dev` | 17/17 | TB `1.76` (1 lượt: 7, 2 lượt: 7, 3 lượt: 3; 21 search, 6 adj, 3 kw) | `0`: 0, `1`: 0, `2`: 15 · TB **`2.00`** (`N=15`) | 23/23 | 15/15 | 2/2 | 0/15 |
| Baseline / `test` | 7/7 | TB `1.71` (1 lượt: 2, 2 lượt: 5; 12 `search_documents`) | `0`: 1, `1`: 0, `2`: 4 · TB **`1.60`** (`N=5`) | 4/4 | 4/4 | 2/2 | 1/5 |
| Improved / `test` | 7/7 | TB `1.86` (1 lượt: 4, 2 lượt: 1, 3 lượt: 1, 4 lượt: 1; 10 search, 1 adj, 2 kw) | `0`: 0, `1`: 0, `2`: 5 · TB **`2.00`** (`N=5`) | 6/6 | 5/5 | 2/2 | 0/5 |

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| `q16` (`test`) | `truc_tiep` | `test-improved`: 1× `search_documents` → top-1 `aug2024__p052__c001` | VND 786T (US\$31B), 8% GDP, nhà đầu tư tổ chức trong nước lớn thứ 2 `[B__wb_taking_stock_aug2024__p052__c001]`. | **Grade 2** · Cite `[True]`. Đủ số liệu, quy mô GDP, xếp hạng. |
| `q17` (`test`) | `dien_dat_lai` | `test-improved`: 1× `search_documents` → top-1 `aug2024__p040__c001` | Kỳ hạn TPDN ~4 năm (< nửa TB khu vực); 2019–23: CP 37T, TPCP 271T, TPDN 403T VND `[B__wb_taking_stock_aug2024__p040__c001]`. | **Grade 2** · Cite `[True]`. Đối chiếu đúng cả 2 vế. |
| `q18` (`test`) | `dieu_kien_ngoai_le` | **Baseline:** FIFO 1600 cắt `p053__c000/c001`. **Improved:** `search(section='special_focus_emobility')` + `get_adjacent_chunks` | **Baseline:** `abstain`. **Improved:** 2030 xe máy điện (`5.3 MtCO2eq` SPS); sau 2030–35 ô tô, xe tải, buýt `226`/`249 MtCO2eq` `[...mar2025__p053__c000]`, `[...p053__c001]`. | **Baseline 0 → Improved 2**, Cites `[True, True]`. Vá đủ đoạn liền kề. |
| `q19` (`test`) | `metadata_filter` | `test-improved`: 1× `search_documents` → top-1 `mar2025__p037__c002` | GDP dự báo 6.8% (2025), 6.5% (2026); xuất khẩu giảm do Mỹ, Trung Quốc chậm lại & bất định thương mại `[B__wb_taking_stock_mar2025__p037__c002]`. | **Grade 2** · Cite `[True]`. Đúng ấn bản 2025. |
| `q20` (`test`) | `metadata_filter` | `test-improved`: tự lọc `year=2024` → `aug2024__p032__c001`, `p015__c004` | Thặng dư ngân sách H1-2024 đạt 4.2% GDP so với 1.5% GDP H1-2023 `[B__wb_taking_stock_aug2024__p015__c004]`. | **Grade 2** · Cite `[True]`. Tự lọc đúng năm 2024. |
| `u03` (`test`) | `unanswerable` | `test-improved`: `search_documents` + `keyword_search('VinFast')` (3 lượt) | `abstain`: báo cáo nêu chung 37+ hãng xe máy điện, không có doanh số VinFast 2024. | **Abstention đúng (`True`)**. |
| `u04` (`test`) | `unanswerable` | `test-improved`: 3× `search_documents` + `keyword_search('minimum wage')` (4 lượt) | `abstain`: chỉ nêu tăng lương công chức/hưu trí từ 1/7/2024, không có % lương tối thiểu vùng tư nhân. | **Abstention đúng (`True`)**. |
| `q03` (`dev` sửa lỗi) | `dien_dat_lai` | **Baseline:** FIFO 1600 cắt `p050__c001` → **Improved:** `keyword_search('pre-funding')` | **Baseline:** `abstain` → **Improved:** yêu cầu ký quỹ trước giao dịch cản trở dòng vốn ngoại và nâng hạng `[...aug2024__p050__c001]`. | **Grade 0 → 2**, Cite `[True]`. |
| `q05` (`dev` sửa lỗi) | `truc_tiep` | **Baseline:** thiếu `p051__c001` → **Improved:** `get_adjacent_chunks` giữ `p045__c003` + `p051__c001` | **Baseline:** thiếu Luật BHXH → **Improved:** nêu ràng buộc Law on Social Insurance & khẩu vị kỳ hạn dài `[...p051__c001]`, `[...p045__c003]`. | **Grade 1 → 2**, Cites `[True, True]`. |
| `q10`, `q13` (`dev` sửa lỗi) | `dieu_kien` & `filter` | `q10`: Baseline lạc *current account* → Improved `hybrid` lấy `p014__c000`; `q13`: tự lọc `year=2024` | `q10`: đầu tư công thấp (4.6% GDP) & giảm chi thường xuyên; `q13`: 6.1% (2024), 6.5% (2025–26). | **Grade 0 → 2** trên cả hai câu. |

- Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí:
  - Retrieval: [dev summary](../../results/retrieval/dev/summary.json), [dev-k5-b3200 summary](../../results/retrieval/dev-k5-b3200/summary.json), [test-selected summary](../../results/retrieval/test-selected/summary.json), [test_context_manual_audit.json](../../results/retrieval/test_context_manual_audit.json).
  - Agent (`$0.00`, `0` lỗi): `dev-baseline` (`264.94s`, `58,705` tok — [traces](../../results/agent/dev-baseline/traces.json)/[reviews](../../results/agent/dev-baseline/reviews.json)/[summary](../../results/agent/dev-baseline/summary.json)); `dev-improved` (`401.64s`, `167,927` tok — [traces](../../results/agent/dev-improved/traces.json)/[reviews](../../results/agent/dev-improved/reviews.json)/[summary](../../results/agent/dev-improved/summary.json)); `test-baseline` (`76.42s`, `23,095` tok — [traces](../../results/agent/test-baseline/traces.json)/[reviews](../../results/agent/test-baseline/reviews.json)/[summary](../../results/agent/test-baseline/summary.json)); `test-improved` (`107.24s`, `53,964` tok — [traces](../../results/agent/test-improved/traces.json)/[reviews](../../results/agent/test-improved/reviews.json)/[summary](../../results/agent/test-improved/summary.json)).
  - Lệnh chạy tiêu biểu (cài `.venv` từ [requirements.txt](../../requirements.txt) và bật PostgreSQL `127.0.0.1:55433`):
    ```powershell
    $py = ".\.venv\Scripts\python.exe"
    & $py -m rag.eval_retrieval --split dev --methods dense,hybrid,hybrid_rerank --top-k 5 --budget 3200 --pack-mode score_dedup --tag k5-b3200
    & $py -m rag.eval_retrieval --split test --methods hybrid --top-k 5 --budget 3200 --pack-mode score_dedup --tag selected
    & $py -u -m rag.eval_agent --split dev --config improved --method hybrid --top-k 5 --budget 3200 --max-searches 4 --pack-mode score_dedup --tag improved --sleep 1.5
    & $py -u -m rag.eval_agent --split test --config improved --method hybrid --top-k 5 --budget 3200 --max-searches 4 --pack-mode score_dedup --tag improved --sleep 1.5
    & $py starter/agent_metrics.py --cases results/agent/test-improved/cases.json --traces results/agent/test-improved/traces.json --reviews results/agent/test-improved/reviews.json --split test --output results/agent/test-improved/summary.json
    ```
- Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:
  - Baseline → Improved loại bỏ hoàn toàn từ chối nhầm (`4/15 → 0/15` dev, `1/5 → 0/5` test), nâng Grounded mean từ `1.40 → 2.00` (dev) và `1.60 → 2.00` (test), giữ `100%` citation hợp lệ và abstention đúng (sửa các ca `q18`, `q03`, `q05`, `q10`, `q13`).
  - Đánh đổi & giới hạn: budget gấp đôi (`1600 → 3200`) và multi-tool tăng tổng token ~`2.86×` (dev) / ~`2.34×` (test) và độ trễ ~`+40–52%` (chủ yếu ở câu `unanswerable` như `u03`, `u04`). Giới hạn: tự suy luận filter phụ thuộc LLM (`q19` model không truyền `year=2025`), và với dữ liệu lớn hơn cần thay exact cosine bằng HNSW/IVFFlat.

## Thử thách nâng cao (nếu thực hiện)

- Tài liệu, nguồn, quyền sử dụng, số trang và phiên bản: *Vietnam: Plastic Pollution Diagnostics* (World Bank Group, Report No. `P167307`, `2022-06-28`, giấy phép `CC BY 3.0 IGO`, [link PDF công khai](http://documents.worldbank.org/curated/en/099731406282241639/pdf/P1673071d02f2c0be180741356b6b0e3deb.pdf)), **138 trang** (`processed_text_pages = 135`, index trên **129 trang**) → **458 chunk** nạp vào `pgvector` với `strategy = "BONUS"` (`BAAI/bge-base-en-v1.5`, 768 chiều; `embed=380.79s`, `total=432.99s`, SHA256 `42b9e358...3da2`) bằng [bonus_ingest.py](../../rag/bonus_ingest.py).
- Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index và phần chưa xử lý: Tách 458 chunk gồm **`378` text** (`by_paragraph`), **`26` table** (`table_01`–`26`), **`16` image_diagram**, **`38` chart** (**80 tài sản** bảng/hình kèm tọa độ `bbox` và mô tả có cấu trúc); bổ sung tool `lookup_visual_asset` tra trực tiếp theo `asset_id`/`page`. **9 trang không sinh chunk** (`12, 13, 24, 25, 91, 94, 95, 101, 138`: trang 24 trắng hoàn toàn `0` ký tự/`0` ảnh, các trang khác là bìa/phân chương và ảnh nền Shutterstock thuần trang trí — ghi rõ trong [index_manifest.json](../../data/bonus/index_manifest.json)). Giới hạn hiện tại dùng `bbox` + mô tả cấu trúc lúc ingest, chưa tách PNG rời hay gọi VLM live trên từng pixel.
- Cách chia benchmark, schema evidence, model và cấu hình đã chốt trên dev: Benchmark **48 câu** đối chiếu `0` lỗi với PDF gốc ([build_bonus_benchmark.py](../../rag/build_bonus_benchmark.py) → [questions.json](../../data/bonus/questions.json)), khóa `test` trước khi chạy: `dev` **18 câu** (3 câu × 6 nhóm) và `test` **30 câu** (`6` bảng, `5` ảnh/sơ đồ, `5` biểu đồ, `4` multi-hop, `4` text, `6` thiếu bằng chứng); schema `gold` lưu `{source_id, page, asset_id, modality, bbox, evidence}` (không truyền cho agent). Chạy trên `gemini-3.5-flash-lite` (xoay model khi chạm RPM/quota trong [agent.py](../../rag/agent.py)): `dev-baseline` (`dense`, `top_k=3`, `budget=1600`, `max_searches=2`, FIFO) đạt **`11/18` (`61.11%`)**; cấu hình đã chốt **`dev-improved`** (`hybrid`, `top_k=5`, `budget=4800`, `max_searches=5`, `score_dedup`, `lookup_visual_asset`) đạt **`18/18` (`100.0%`)**, `26/26` citations hợp lệ.

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---|---|---|
| Bảng | 6 / 6 | 100,00% | `bt_q01`–`bt_q06` đọc đúng số liệu, đơn vị (VND/kg, m/s, CCI) & bảng ghép (`Table 6, 11, 13, 17, 21, 26`). |
| Ảnh, sơ đồ | 5 / 5 | 100,00% | `bt_q07`–`bt_q11` trích đúng nhãn bản đồ, vùng bay UAV, khung lưới và `APLASTIC-Q` (`Figure 4, 26, 47, 48, 49`). |
| Biểu đồ | 5 / 5 | 100,00% | `bt_q12`–`bt_q16` đọc đúng giá trị cột/tròn/đường (`Figure 2, 7, 15, 23, 29`), phân biệt đúng đỉnh theo giờ hai camera. |
| Multi-hop | 4 / 4 | 100,00% | `bt_q17`–`bt_q20` tổng hợp chính xác 2–3 bảng/biểu đồ khác trang. |
| Text | 3 / 4 | 75,00% | Đạt `bt_q22`–`bt_q24`; chấm chặt không đạt `bt_q21` do budget `4800` lấp trước `p092__t02` nên thiếu danh sách 5 món đồ mang đi mục tiêu. |
| Thiếu bằng chứng | 6 / 6 | 100,00% | `bt_u01`–`bt_u06` đều từ chối chính xác và giải thích đúng phạm vi dữ liệu tài liệu. |
| **Toàn bộ** | **29 / 30** | **96,67%** | Vượt ngưỡng $\ge 90\%$ trên 30 câu `test` độc lập; `44 / 44` (`100%`) citations hợp lệ. |

- Trace, nhãn và evidence từng câu; thời gian, chi phí, lỗi hệ thống: Bộ dữ liệu [questions.json](../../data/bonus/questions.json), [chunks.json](../../data/bonus/chunks.json), [index_manifest.json](../../data/bonus/index_manifest.json). `dev-baseline`: [traces](../../results/bonus/dev-baseline/traces.json), [reviews](../../results/bonus/dev-baseline/reviews.json), [summary](../../results/bonus/dev-baseline/summary.json) (`440.02s`, `74,861` tok, `$0.002018`, `0` lỗi); `dev-improved`: [traces](../../results/bonus/dev-improved/traces.json), [reviews](../../results/bonus/dev-improved/reviews.json), [summary](../../results/bonus/dev-improved/summary.json) (`76.33s`, `135,135` tok, `$0.0`, `0` lỗi); `test-selected`: [traces](../../results/bonus/test-selected/traces.json), [reviews](../../results/bonus/test-selected/reviews.json), [summary](../../results/bonus/test-selected/summary.json) (`248.31s` = `8.28s/câu`, `57` search, `74` API calls, `260,631` tok, `$0.0`, `0` provider error trong kết quả lưu sau khi resume 1 lượt cho `bt_u06` vì chạm RPM tạm thời ở 29/30).
- Giới hạn, cách tái lập và đường dẫn benchmark:
  - Giới hạn: khi truy vấn kéo nhiều trang cùng lúc (`bt_q21`), budget `4800` vẫn có thể đẩy mất đoạn văn kề nếu không gọi thêm `get_adjacent_chunks`; phần trực quan phụ thuộc mô tả cấu trúc lúc ingest. Benchmark tại `data/bonus/questions.json`; kèm Web Demo UI 4 tab (*Hỏi & Đáp RAG*, *Báo cáo Bonus (+15đ)*, *Báo cáo Core (85đ)*, *Kho Bảng & Biểu đồ*) qua [server.py](../../rag/server.py) và [index.html](../../ui/index.html) tại `http://127.0.0.1:8765` (API payload đã kiểm thử trong [test_rag_day7.py](../../tests/test_rag_day7.py); kiểm thử tự động Chrome DevTools MCP chưa chạy do Chrome máy chưa bật `chrome://inspect/#remote-debugging`).
  ```powershell
  $py = ".\.venv\Scripts\python.exe"
  & $py -m rag.bonus_ingest
  & $py -m rag.build_bonus_benchmark
  & $py -u -m rag.eval_bonus --run dev-baseline
  & $py -u -m rag.eval_bonus --run dev-improved
  & $py -u -m rag.eval_bonus --run test-selected
  & $py -m rag.server --port 8765
  ```

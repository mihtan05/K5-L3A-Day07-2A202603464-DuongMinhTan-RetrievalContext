# Day 7 — Agentic RAG

**Bài cá nhân · Python 3.11+ · tiếp nối Day 6**

Dùng embedding và vector store từ Day 6 để xây một agent biết tìm bằng chứng, trả lời có nguồn và nhận biết khi không đủ thông tin. Bạn tự chọn kiến trúc, số tool và cách tổ chức retrieval.

> **Tùy chọn:** [Gợi ý dùng AI để lập trình](AGENT_SETUP.md) giúp bạn làm lab; phần này không bắt buộc và không tính điểm.

## Bài cần làm

![Agent tìm tài liệu trong kho Day 6 và trả lời có nguồn](assets/retrieval-pipeline.svg)

1. Kết nối dữ liệu, embedding và vector store Day 6.
2. Xây agent dùng model thật và ít nhất một khả năng truy xuất dữ liệu. Agent có thể dùng nhiều tool và nhiều lượt gọi.
3. Thử **ít nhất 3 phương pháp retrieval khác nhau**, trong đó có dense retrieval dùng vector store Day 6. Tự chọn các phương pháp còn lại; xem [gợi ý](GUIDE.md#2-thử-các-phương-pháp-retrieval).
4. Thử nhiều cấu hình, benchmark, phân tích lỗi và chọn cấu hình tốt trên **dev**; sau đó đánh giá trên **test**.

Benchmark tối thiểu có **24 câu**: dev gồm 15 câu có đáp án và 2 câu thiếu bằng chứng; test gồm 5 câu có đáp án và 2 câu thiếu bằng chứng. Xem [benchmark](BENCHMARK.md) và [rubric](RUBRIC.md).

## Thử thách nâng cao · +15 điểm

Index một tài liệu thực tế từ **100 trang** có bảng, ảnh và biểu đồ; xây agent truy xuất và trả lời các câu hỏi về nội dung đó. Hoàn thành [thử thách nâng cao](ADVANCED.md) và đạt **ít nhất 90% benchmark test** để nhận 15 điểm bonus. Phần cơ bản tối đa 85 điểm; toàn bài tối đa 100 điểm.

## Bắt đầu

1. Đọc [hướng dẫn](GUIDE.md), [rubric](RUBRIC.md) và [quy tắc](RULES.md).
2. Tạo repo cá nhân theo [cách nộp bài](SUBMISSION.md), chuẩn bị đầu ra Day 6 và model hỗ trợ tool calling.
3. Dùng hoặc thay thế [starter](starter/README.md); bạn cần kết nối model và vector store thật.
4. Chạy `python -m unittest discover -s tests -v`. Test mock chỉ kiểm tra code, không phải benchmark agent thật.

![Các bước thử nghiệm trên dev và đánh giá trên test](assets/experiment-loop.svg)

Nộp code, cách chạy, cấu hình, benchmark, trace và [báo cáo cá nhân](report/individual/2A202603464_DuongMinhTan.md). Thời gian ở [checkpoints](CHECKPOINTS.md) là gợi ý, có thể điều chỉnh theo lớp và phạm vi thử nghiệm.

## Triển khai cá nhân & Hướng dẫn tái lập

### 1. Kiến trúc mã nguồn (`rag/`)

- [`rag/day6.py`](rag/day6.py): Cầu nối dùng lại module chuẩn hóa PDF, chunker chiến lược `B` (`by_paragraph`, `max_size=800`), embedder (`BAAI/bge-base-en-v1.5`, 768 chiều) và `PgVectorStore` từ repo Day 6 (`DAY6_STARTER`).
- [`rag/ingest.py`](rag/ingest.py): Re-index 94 trang → 407 chunk từ 2 báo cáo World Bank (*Taking Stock* 08/2024 & 03/2025) vào `pgvector`, đồng bộ [`data/chunks.json`](data/chunks.json) và [`data/index_manifest.json`](data/index_manifest.json).
- [`rag/retrieval.py`](rag/retrieval.py): 4 phương pháp truy xuất (`dense`, `bm25`, `hybrid` RRF, `hybrid_rerank` CrossEncoder) cùng context packing (`fifo`, `score_dedup`, `neighbor_expand`) có hỗ trợ `pack_score` liên tool.
- [`rag/eval_retrieval.py`](rag/eval_retrieval.py): Benchmark retrieval (`Hit@1`, `Evidence Hit@3`, `MRR@k`, `Context Evidence Rate`) trên `dev`/`test` có/không filter và kiểm soát budget.
- [`rag/agent.py`](rag/agent.py): Agent dùng model thật (`gemini-2.5-flash-lite`) với tool-calling (`search_documents`, `keyword_search`, `get_adjacent_chunks`, `submit_answer`, `abstain`), tự suy luận filter `year`/`section` (`_sanitize_filter`), kiểm tra citation nội dòng (`_validate_citations`), giới hạn `max_searches`, retry backoff và log trace tương thích [`starter/agent_metrics.py`](starter/agent_metrics.py).
- [`rag/eval_agent.py`](rag/eval_agent.py): Runner chạy benchmark `baseline` vs `improved` trên `dev`/`test` (tuyệt đối không truyền `gold`, `expected_answer`, `absence_reason`, hay ground-truth `filter` vào agent).

### 2. Thiết lập môi trường & Khởi động Vector Store

1. Tạo file `.env` từ [`.env.example`](.env.example) và điền `GEMINI_API_KEY` (hoặc `OPENROUTER_API_KEY` / `OPENAI_API_KEY`); chỉnh `DAY6_STARTER` nếu repo Day 6 không nằm ở thư mục ngang hàng:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Tạo môi trường ảo Python tại repo Day 7 từ [`requirements.txt`](requirements.txt) (hoặc trỏ tới `.venv` của Day 6):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\pip install -r requirements.txt
   ```
3. Khởi động PostgreSQL + `pgvector` của Day 6 (trên Windows/WSL2 Ubuntu giữ phiên nền để dịch vụ không tự tắt):
   ```powershell
   wsl -d Ubuntu -u root -- bash -c "service postgresql start && exec sleep infinity"
   ```
4. Kiểm tra lại dữ liệu Day 6 nếu cần re-ingest:
   ```powershell
   $py = ".\.venv\Scripts\python.exe"
   & $py -m rag.ingest
   ```

### 3. Lệnh chạy lại benchmark, tổng hợp metrics và unit test

```powershell
$py = ".\.venv\Scripts\python.exe"

# 1. Benchmark retrieval trên dev (baseline, 4 phương pháp, ablations) và chốt hybrid -> test
& $py -m rag.eval_retrieval --split dev --methods dense --top-k 3 --budget 2400 --no-filter --tag baseline-dense-nofilter
& $py -m rag.eval_retrieval --split dev --top-k 3 --budget 2400
& $py -m rag.eval_retrieval --split dev --methods dense,hybrid,hybrid_rerank --top-k 3 --budget 1200 --tag b1200
& $py -m rag.eval_retrieval --split dev --methods dense,hybrid,hybrid_rerank --top-k 5 --budget 3200 --pack-mode score_dedup --tag k5-b3200
& $py -m rag.eval_retrieval --split test --methods dense --top-k 3 --budget 2400 --no-filter --tag baseline-dense-nofilter
& $py -m rag.eval_retrieval --split test --methods hybrid --top-k 5 --budget 3200 --pack-mode score_dedup --tag selected

# 2. Chạy Agentic RAG thật (baseline vs improved) trên dev và test
& $py -u -m rag.eval_agent --split dev --config baseline --tag baseline --sleep 1.5
& $py -u -m rag.eval_agent --split dev --config improved --method hybrid --top-k 5 --budget 3200 --max-searches 4 --pack-mode score_dedup --tag improved --sleep 1.5
& $py -u -m rag.eval_agent --split test --config baseline --tag baseline --sleep 1.5
& $py -u -m rag.eval_agent --split test --config improved --method hybrid --top-k 5 --budget 3200 --max-searches 4 --pack-mode score_dedup --tag improved --sleep 1.5

# 3. Tổng hợp metrics từ reviews.json (sau khi chấm tay từng câu)
& $py starter/agent_metrics.py --cases results/agent/dev-improved/cases.json --traces results/agent/dev-improved/traces.json --reviews results/agent/dev-improved/reviews.json --split dev --output results/agent/dev-improved/summary.json
& $py starter/agent_metrics.py --cases results/agent/test-improved/cases.json --traces results/agent/test-improved/traces.json --reviews results/agent/test-improved/reviews.json --split test --output results/agent/test-improved/summary.json

# 4. Chạy toàn bộ unit tests (starter + Day 7 + Bonus + Server)
& $py -m unittest discover -s tests -v
```

### 4. Thử thách nâng cao (+15 điểm) & Giao diện Web Demo (`http://127.0.0.1:8765`)

- [`rag/bonus_ingest.py`](rag/bonus_ingest.py): Ingest tài liệu 138 trang (*Vietnam: Plastic Pollution Diagnostics*, World Bank 2022) thành **458 chunk** đa phương thức (`378` text, `26` table, `16` image_diagram, `38` chart) với **80 tài sản bảng/hình/biểu đồ kèm tọa độ `bbox`** và nạp vào `pgvector` với `strategy="BONUS"`.
- [`rag/build_bonus_benchmark.py`](rag/build_bonus_benchmark.py): Sinh benchmark **48 câu** tại [`data/bonus/questions.json`](data/bonus/questions.json) (`18` `dev` + `30` `test`, phủ đủ 6 nhóm: `table`, `image_diagram`, `chart`, `multi_hop`, `text`, `unanswerable`).
- [`rag/eval_bonus.py`](rag/eval_bonus.py): Runner chạy `dev-baseline` (`11/18 = 61.11%`), `dev-improved` (`18/18 = 100.0%`), và `test-selected` (`29/30 = 96.67%`).
- [`rag/server.py`](rag/server.py) & [`ui/index.html`](ui/index.html): Web Demo UI 4 tab (*Hỏi & Đáp RAG*, *Báo cáo Bonus (+15đ)*, *Báo cáo Core (85đ)*, *Kho Bảng & Biểu đồ*), hỗ trợ hỏi-đáp trực tiếp kèm trích dẫn `[chunk_id]` bấm mở `<dialog id="asset-dialog" closedby="any">` xem nguyên văn PDF.

```powershell
$py = ".\.venv\Scripts\python.exe"

# Ingest 138 trang + sinh 48 câu benchmark Bonus
& $py -m rag.bonus_ingest
& $py -m rag.build_bonus_benchmark

# Chạy thực nghiệm dev-baseline, dev-improved và test-selected
& $py -u -m rag.eval_bonus --run dev-baseline
& $py -u -m rag.eval_bonus --run dev-improved
& $py -u -m rag.eval_bonus --run test-selected

# Khởi chạy Interactive Web Demo UI
& $py -m rag.server --port 8765
```

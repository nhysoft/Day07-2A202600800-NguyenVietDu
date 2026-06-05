# 📊 Báo Cáo Lab 7: Embedding & Vector Store

> **Họ tên:** Nguyễn Viết Du &nbsp;|&nbsp; **MSSV:** 2A202600800 &nbsp;|&nbsp; **Ngày:** 2026-06-05

---

## 📌 Mục Lục

| # | Phần | Điểm |
|---|------|------|
| 1 | [Warm-up](#1-warm-up) | 5 |
| 2 | [Document Selection](#2-document-selection--nhóm) | 10 |
| 3 | [Chunking Strategy](#3-chunking-strategy) | 15 |
| 4 | [My Approach](#4-my-approach) | 10 |
| 5 | [Similarity Predictions](#5-similarity-predictions) | 5 |
| 6 | [Results](#6-results) | 10 |
| 7 | [What I Learned](#7-what-i-learned) | 5 |
| — | [Tự Đánh Giá](#-tự-đánh-giá) | — |

---

## 1. Warm-up

### 🔵 Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**

Hai đoạn văn bản có cosine similarity cao nghĩa là các vector embedding của chúng gần như **cùng hướng** trong không gian nhiều chiều — tức là chúng có ý nghĩa ngữ nghĩa tương đồng. Điểm số càng gần `1.0` thì nội dung càng liên quan, **không phụ thuộc độ dài** văn bản.

---

**✅ Ví dụ HIGH similarity:**

| | Nội dung |
|--|---------|
| 🅰️ Sentence A | *"How do I reset my password?"* |
| 🅱️ Sentence B | *"What is the process to recover my account login?"* |
| 💡 Lý do | Cùng hỏi về khôi phục quyền truy cập, dùng từ đồng nghĩa → vector nằm gần nhau |

**❌ Ví dụ LOW similarity:**

| | Nội dung |
|--|---------|
| 🅰️ Sentence A | *"The weather is sunny today."* |
| 🅱️ Sentence B | *"RAG systems retrieve relevant documents before generating answers."* |
| 💡 Lý do | Hai domain hoàn toàn khác (thời tiết vs AI) → vector gần như vuông góc nhau |

---

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance?**

> Cosine similarity chỉ quan tâm đến **góc** giữa hai vector, bỏ qua độ lớn (magnitude). Một tài liệu dài và một câu ngắn cùng chủ đề sẽ có cosine similarity cao, nhưng Euclidean distance bị sai lệch vì vector tài liệu dài có magnitude lớn hơn — không phản ánh đúng sự tương đồng nghĩa.

---

### 🔢 Chunking Math (Ex 1.2)

**Document 10,000 ký tự — `chunk_size=500`, `overlap=50`:**

```
num_chunks = ceil((doc_length - overlap) / (chunk_size - overlap))
           = ceil((10000 - 50) / (500 - 50))
           = ceil(9950 / 450)
           = ceil(22.11)
           = 23 chunks  ✅
```

**Nếu overlap tăng lên 100:**

```
num_chunks = ceil((10000 - 100) / (500 - 100))
           = ceil(9900 / 400)
           = ceil(24.75)
           = 25 chunks  (+2 chunks)
```

> 💡 **Tại sao muốn overlap nhiều hơn?** Để đảm bảo các khái niệm nằm ở **ranh giới** giữa hai chunk vẫn được capture đầy đủ trong ít nhất một chunk — tránh việc một câu quan trọng bị cắt đôi và mất ngữ cảnh khi retrieval.

---

## 2. Document Selection — Nhóm

### 🧬 Domain

**Bioinformatics / Spatial Multi-Omics Research**
*(các bài báo khoa học về phân tích dữ liệu không gian đa omics)*

> Nhóm chọn domain này vì các bài báo khoa học có cấu trúc rõ ràng (Abstract → Methods → Results → Discussion), phù hợp để thử nghiệm nhiều chunking strategy. Domain chứa nhiều thuật ngữ kỹ thuật chuyên biệt, tạo thách thức thú vị cho retrieval. Kích thước file lớn (50KB–105KB) giúp kiểm tra chunking thực tế hơn so với tài liệu ngắn.

---

### 📂 Data Inventory

| # | Tên file | Nguồn | Số ký tự | Metadata |
|---|----------|-------|----------|---------|
| 1 | `paper1.md` | Nature Communications | 50,367 | `topic=spatial_multiomics` `method=COSMOS` |
| 2 | `paper2.md` | Communications Biology | 58,890 | `topic=cell_sorting` `method=COSMOS_DL` |
| 3 | `paper3.md` | BMC Bioinformatics | 105,307 | `topic=dimension_reduction` `method=SMOPCA` |
| 4 | `paper4.md` | Nature | 90,347 | `topic=epigenome_transcriptome` `method=co_profiling` |
| 5 | `paper5.md` | Communications Biology | 58,890 | `topic=cell_sorting` `method=COSMOS_DL` |

### 🏷️ Metadata Schema

| Trường | Kiểu | Ví dụ | Tại sao hữu ích? |
|--------|------|-------|-----------------|
| `topic` | string | `spatial_multiomics`, `cell_sorting` | Lọc theo chủ đề nghiên cứu, tránh lẫn các nhánh bioinformatics |
| `method` | string | `COSMOS`, `SMOPCA` | Khi hỏi về thuật toán cụ thể, filter chính xác paper chứa method đó |

---

## 3. Chunking Strategy

### 📊 Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` với `chunk_size=200`:

| Tài liệu | Strategy | Chunks | Avg Length | Context? |
|----------|----------|:------:|:----------:|---------|
| `python_intro` (1,944 chars) | `fixed_size` | 13 | 196 | ⚠️ Cắt giữa câu |
| `python_intro` (1,944 chars) | `by_sentences` | 5 | 387 | ✅ Nguyên câu |
| `python_intro` (1,944 chars) | `recursive` | 12 | 160 | ✅ Theo đoạn văn |
| `vector_store_notes` (2,123 chars) | `fixed_size` | 14 | 198 | ⚠️ Trung bình |
| `vector_store_notes` (2,123 chars) | `by_sentences` | 8 | 264 | ✅ Tốt |
| `vector_store_notes` (2,123 chars) | `recursive` | 15 | 140 | ✅ Tốt |
| `rag_system_design` (2,391 chars) | `fixed_size` | 16 | 196 | ⚠️ Trung bình |
| `rag_system_design` (2,391 chars) | `by_sentences` | 5 | 476 | ❌ Chunk quá dài |
| `rag_system_design` (2,391 chars) | `recursive` | 17 | 139 | ✅ Tốt nhất |

---

### 🎯 Strategy Của Tôi: `RecursiveChunker` (`chunk_size=300`)

**Cách hoạt động:**

```
Thứ tự separator:  \n\n  →  \n  →  ". "  →  " "  →  ""
                  (đoạn) → (dòng) → (câu) → (từ) → (ký tự)
```

Nếu một đoạn sau khi tách vẫn vượt `chunk_size`, thuật toán đệ quy với separator tiếp theo. Sau đó gộp (greedy merge) các phần nhỏ liền kề nếu còn chỗ.

**Tại sao chọn strategy này?**

> Bài báo khoa học được tổ chức theo đoạn văn (`\n\n`) — mỗi đoạn là **một ý hoàn chỉnh**. RecursiveChunker tôn trọng cấu trúc này, giúp mỗi chunk chứa một ý trọn vẹn và dễ embed hơn. So với `by_sentences` → kiểm soát được độ dài; so với `fixed_size` → tránh cắt giữa câu.

### ⚖️ So Sánh vs Baseline (trên `rag_system_design.md`)

| Strategy | Chunks | Avg Length | Nhận xét |
|----------|:------:|:----------:|---------|
| `fixed_size` (baseline) | 16 | 196 | ⚠️ Một số chunk cắt giữa câu |
| `by_sentences` (baseline) | 5 | 476 | ❌ Chunk quá dài, vượt ideal |
| **`recursive` (của tôi, 300)** | **~10** | **~239** | ✅ Cân bằng tốt nhất |

---

## 4. My Approach

### ✂️ Chunking Functions

**`SentenceChunker.chunk`**

```python
parts = re.split(r'(?<=[.!?]) +|(?<=\.)\n', text)
sentences = [s.strip() for s in parts if s.strip()]
# Gộp theo max_sentences_per_chunk bằng vòng lặp step
```

Dùng lookbehind regex để giữ dấu câu kèm mỗi sentence. Edge case: câu rỗng sau `strip()` được lọc bỏ.

---

**`RecursiveChunker._split`**

```python
# Base case
if len(text) <= chunk_size:  return [text]
if not separators:           return [text]  # oversized nhưng không còn cách tách

# Recursive case: tách → đệ quy phần oversized → greedy merge
```

Greedy merge: gộp các piece nhỏ liền kề lại nếu `len(current + sep + piece) <= chunk_size`.

---

### 🗄️ EmbeddingStore

**`add_documents` + `search`**

```
add_documents:  doc → _make_record() → append vào self._store
_make_record:   embedding_fn(content) + copy(metadata) + doc_id
search:         embed(query) → dot product với mọi record → sort desc → top_k
```

**`search_with_filter` + `delete_document`**

```
search_with_filter:  filter self._store trước (all metadata match) → _search_records
delete_document:     list comprehension loại record có metadata['doc_id'] == doc_id
                     → True nếu size giảm, False nếu không tìm thấy
```

---

### 🤖 KnowledgeBaseAgent

**Prompt structure:**

```
Context:
[1] <chunk 1 content>

[2] <chunk 2 content>

[3] <chunk 3 content>

Question: <user question>

Answer:
```

Context inject trước question để LLM đọc evidence trước khi trả lời — giảm hallucination.

---

### ✅ Test Results

```
============================= test session starts ==============================
platform darwin -- Python 3.10.11, pytest-9.0.3
collected 42 items

tests/test_solution.py::TestProjectStructure                       2 PASSED
tests/test_solution.py::TestClassBasedInterfaces                   2 PASSED
tests/test_solution.py::TestFixedSizeChunker                       7 PASSED
tests/test_solution.py::TestSentenceChunker                        4 PASSED
tests/test_solution.py::TestRecursiveChunker                       4 PASSED
tests/test_solution.py::TestEmbeddingStore                         8 PASSED
tests/test_solution.py::TestKnowledgeBaseAgent                     2 PASSED
tests/test_solution.py::TestComputeSimilarity                      4 PASSED
tests/test_solution.py::TestCompareChunkingStrategies              3 PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter         3 PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument           3 PASSED

========================= 42 passed in 0.04s ==========================
```

> 🎉 **42 / 42 tests passed**

---

## 5. Similarity Predictions

Chạy `compute_similarity(_mock_embed(a), _mock_embed(b))` trên 5 cặp:

| # | Sentence A | Sentence B | Dự đoán | Actual | Đúng? |
|---|-----------|-----------|:-------:|:------:|:-----:|
| 1 | *Python is a programming language.* | *Python is used for machine learning.* | 🔼 HIGH | −0.0824 | ❌ |
| 2 | *The cat sat on the mat.* | *A dog ran through the park.* | 🔽 LOW | +0.0712 | ❌ |
| 3 | *Vector stores save embeddings for search.* | *Databases store vectors for retrieval.* | 🔼 HIGH | −0.0768 | ❌ |
| 4 | *How do I reset my password?* | *What is the process of account recovery?* | 🔼 HIGH | −0.1817 | ❌ |
| 5 | *The weather is sunny today.* | *RAG systems retrieve relevant documents.* | 🔽 LOW | +0.0816 | ❌ |

**Kết quả bất ngờ nhất & bài học:**

> Tất cả 5 dự đoán đều **sai** — nhưng không phải lỗi của semantic model. `MockEmbedder` tạo vector bằng **hash MD5** của text, hoàn toàn không encode nghĩa ngữ nghĩa. Scores gần 0 và có thể âm vì hash-based vectors ngẫu nhiên. Đây cho thấy sự khác biệt cơ bản: mock embedding chỉ để **test code chạy đúng**, không thể dùng để đánh giá semantic similarity thực sự.

---

## 6. Results

### 🎯 Benchmark Queries & Gold Answers

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | What is a vector store and how does it work? | Workflow: chunk → embed → store → similarity search |
| 2 | Which chunking strategy works best for technical docs? | Recursive chunking — tách đoạn văn trước, fallback nhỏ hơn khi cần |
| 3 | How does RAG reduce hallucinations? | Grounding câu trả lời vào retrieved context, LLM chỉ dùng evidence |
| 4 | What are common failure cases in retrieval? | Outdated docs ranking high, small chunks mất context, multilingual confusion |
| 5 | Why is metadata important in retrieval? | Filter thu hẹp search space, tránh trả nhầm tài liệu sai domain |

---

### 📈 Kết Quả Của Tôi *(RecursiveChunker + mock embedder)*

| # | Query | Top-1 Retrieved | Score | Relevant? | Ghi chú |
|---|-------|----------------|:-----:|:---------:|---------|
| 1 | What is a vector store? | `python_intro` | 0.157 | ❌ | Sai doc — mock score random |
| 2 | Best chunking strategy? | `customer_support_playbook` | 0.160 | ❌ | Sai doc |
| 3 | RAG reduce hallucinations? | `chunking_experiment_report` | 0.176 | ⚠️ | Một phần liên quan |
| 4 | Common failure cases? | `vector_store_notes` | 0.115 | ✅ | Mục "Common Risks" khớp |
| 5 | Why metadata important? | `rag_system_design` | 0.066 | ✅ | Đề cập metadata retrieval |

**Queries trả về relevant chunk trong top-3:** `2 / 5`

---

## 7. What I Learned

### 🔍 Failure Analysis

> **Query 1 & 2 thất bại hoàn toàn** — `python_intro` và `customer_support_playbook` được trả về thay vì doc đúng chủ đề.
>
> **Nguyên nhân gốc:** Mock embedder dùng hash function → score 0.157 và 0.160 là **random**, không phản ánh liên quan thực. Đây là failure case quan trọng nhất: production system dùng mock embedding sẽ cho retrieval hoàn toàn vô nghĩa.

**Đề xuất cải thiện:**
- ✅ Dùng `LocalEmbedder` (`all-MiniLM-L6-v2`) hoặc Gemini embedding thay mock
- ✅ Mở rộng metadata schema thêm `section` (Abstract/Methods/Results) để filter chính xác hơn
- ✅ Thêm re-ranking sau similarity search để loại false positives

**Bài học lớn nhất:**

> RAG cần **hai thành phần đều tốt**: chunking tốt giữ ngữ cảnh nguyên vẹn, embedding tốt đảm bảo similarity search có ý nghĩa. Thiếu một trong hai → toàn bộ hệ thống thất bại dù code hoàn toàn đúng.

---

## 📊 Tự Đánh Giá

| Tiêu chí | Loại | Điểm |
|----------|:----:|:----:|
| Warm-up | Cá nhân | **5 / 5** |
| Document selection | Nhóm | **8 / 10** |
| Chunking strategy | Nhóm | **12 / 15** |
| My approach | Cá nhân | **10 / 10** |
| Similarity predictions | Cá nhân | **5 / 5** |
| Results | Cá nhân | **8 / 10** |
| Core implementation (tests) | Cá nhân | **30 / 30** |
| Demo | Nhóm | **4 / 5** |
| **Tổng** | | **82 / 100** |

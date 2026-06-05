# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Viết Du
**MSSV:** 2A202600800
**Ngày:** 2026-06-05

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**

Hai đoạn văn bản có cosine similarity cao nghĩa là các vector embedding của chúng gần như cùng hướng trong không gian nhiều chiều, tức là chúng có ý nghĩa ngữ nghĩa tương đồng nhau. Điểm số càng gần 1.0 thì nội dung hai đoạn càng liên quan, không phụ thuộc vào độ dài của văn bản.

**Ví dụ HIGH similarity:**
- Sentence A: "How do I reset my password?"
- Sentence B: "What is the process to recover my account login?"
- Tại sao tương đồng: Cả hai đều hỏi về cùng một vấn đề (khôi phục quyền truy cập), dùng các từ đồng nghĩa, embedding sẽ nằm gần nhau trong vector space.

**Ví dụ LOW similarity:**
- Sentence A: "The weather is sunny today."
- Sentence B: "RAG systems retrieve relevant documents before generating answers."
- Tại sao khác: Hai câu thuộc hai domain hoàn toàn khác nhau (thời tiết vs AI), không chia sẻ khái niệm nào, vector embedding sẽ gần như vuông góc nhau.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**

Cosine similarity chỉ quan tâm đến góc giữa hai vector, bỏ qua độ lớn (magnitude), nên nó không bị ảnh hưởng bởi độ dài văn bản. Một tài liệu dài và một câu ngắn cùng chủ đề sẽ có cosine similarity cao, nhưng Euclidean distance lại bị sai lệch do vector của tài liệu dài thường có magnitude lớn hơn, không phản ánh đúng sự tương đồng về nghĩa.

---

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

Áp dụng công thức:
```
num_chunks = ceil((doc_length - overlap) / (chunk_size - overlap))
           = ceil((10000 - 50) / (500 - 50))
           = ceil(9950 / 450)
           = ceil(22.11)
           = 23 chunks
```

**Đáp án: 23 chunks**

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**

```
num_chunks = ceil((10000 - 100) / (500 - 100))
           = ceil(9900 / 400)
           = ceil(24.75)
           = 25 chunks
```

Tăng overlap từ 50 lên 100 làm tăng số chunk từ 23 lên 25. Lý do muốn overlap nhiều hơn là để đảm bảo các khái niệm nằm ở ranh giới giữa hai chunk vẫn được capture đầy đủ trong ít nhất một chunk — tránh việc một câu quan trọng bị cắt đôi giữa hai chunk, làm mất ngữ cảnh khi retrieval.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Bioinformatics / Spatial Multi-Omics Research (các bài báo khoa học về phân tích dữ liệu không gian đa omics)

**Tại sao nhóm chọn domain này?**

Nhóm chọn domain này vì các bài báo khoa học có cấu trúc rõ ràng (Abstract, Methods, Results, Discussion) rất phù hợp để thử nghiệm các chiến lược chunking khác nhau. Domain có nhiều thuật ngữ kỹ thuật chuyên biệt, đặt ra thách thức thú vị cho retrieval — câu hỏi có thể hỏi về phương pháp, kết quả thực nghiệm, hoặc so sánh các thuật toán. Ngoài ra, kích thước file lớn (50KB–105KB) giúp kiểm tra chunking thực tế hơn so với tài liệu ngắn.

---

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | paper1.md | Nature Communications (doi: 10.1038/s41467-024-55204-y) | 50,367 | topic=spatial_multiomics, method=COSMOS, journal=nat_comm |
| 2 | paper2.md | Communications Biology (doi: 10.1038/s42003-023-05325-9) | 58,890 | topic=cell_sorting, method=COSMOS_DL, journal=comm_bio |
| 3 | paper3.md | BMC Bioinformatics (Open Access) | 105,307 | topic=dimension_reduction, method=SMOPCA, journal=bmc_bioinfo |
| 4 | paper4.md | Nature (doi: 10.1038/s41586-023-05795-1) | 90,347 | topic=epigenome_transcriptome, method=co_profiling, journal=nature |
| 5 | paper5.md | Communications Biology (doi: 10.1038/s42003-023-05325-9) | 58,890 | topic=cell_sorting, method=COSMOS_DL, journal=comm_bio |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| topic | string | spatial_multiomics, cell_sorting, dimension_reduction | Lọc câu hỏi theo chủ đề nghiên cứu cụ thể, tránh lẫn giữa các nhánh bioinformatics |
| method | string | COSMOS, SMOPCA, co_profiling | Khi câu hỏi hỏi về thuật toán cụ thể, filter chính xác paper chứa method đó |

---

## 3. Chunking Strategy — Cá nhân (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` với `chunk_size=200` trên 3 tài liệu:

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| python_intro (1,944 chars) | fixed_size | 13 | 196 | Trung bình — cắt giữa câu |
| python_intro (1,944 chars) | by_sentences | 5 | 387 | Tốt — chunk nguyên câu |
| python_intro (1,944 chars) | recursive | 12 | 160 | Tốt — tách theo đoạn văn |
| vector_store_notes (2,123 chars) | fixed_size | 14 | 198 | Trung bình |
| vector_store_notes (2,123 chars) | by_sentences | 8 | 264 | Tốt |
| vector_store_notes (2,123 chars) | recursive | 15 | 140 | Tốt |
| rag_system_design (2,391 chars) | fixed_size | 16 | 196 | Trung bình |
| rag_system_design (2,391 chars) | by_sentences | 5 | 476 | Kém — chunk quá dài |
| rag_system_design (2,391 chars) | recursive | 17 | 139 | Tốt |

---

### Strategy Của Tôi

**Loại:** RecursiveChunker với `chunk_size=300`

**Mô tả cách hoạt động:**
RecursiveChunker thử tách văn bản theo thứ tự ưu tiên từ separator lớn đến nhỏ: `\n\n` (đoạn văn) → `\n` (dòng) → `. ` (câu) → ` ` (từ) → `""` (ký tự). Nếu một đoạn sau khi tách vẫn vượt quá `chunk_size`, nó sẽ tiếp tục đệ quy với separator tiếp theo. Kết quả là hầu hết chunk giữ nguyên ranh giới đoạn văn tự nhiên, chỉ khi thực sự cần thiết mới tách nhỏ hơn.

**Tại sao tôi chọn strategy này cho domain nhóm?**
Tài liệu kỹ thuật thường được tổ chức theo đoạn văn (`\n\n`) — mỗi đoạn là một ý hoàn chỉnh. RecursiveChunker tôn trọng cấu trúc này bằng cách ưu tiên tách theo đoạn, giúp mỗi chunk chứa một ý trọn vẹn và dễ embed hơn. So với `by_sentences`, nó kiểm soát được độ dài chunk; so với `fixed_size`, nó tránh cắt giữa câu.

---

### So Sánh: Strategy của tôi vs Baseline (trên rag_system_design.md)

| Strategy | Chunk Count | Avg Length | Nhận xét |
|----------|-------------|------------|---------|
| fixed_size (baseline) | 16 | 196 | Một số chunk cắt giữa câu |
| by_sentences (baseline) | 5 | 476 | Chunk quá dài, vượt ideal |
| **recursive (của tôi, chunk=300)** | ~10 | ~239 | Cân bằng tốt nhất |

---

## 4. My Approach — Cá nhân (10 điểm)

### Chunking Functions

**`SentenceChunker.chunk`** — approach:

Dùng regex `re.split(r'(?<=[.!?]) +|(?<=\.)\n', text)` để tách văn bản tại ranh giới câu (sau `.`, `!`, `?` có khoảng trắng, hoặc sau `.` có xuống dòng), giữ dấu câu kèm theo mỗi câu. Sau đó gộp các câu thành chunk theo `max_sentences_per_chunk` bằng cách dùng vòng lặp step. Edge case: câu rỗng sau khi strip được loại bỏ.

**`RecursiveChunker.chunk` / `_split`** — approach:

Base case: nếu `len(text) <= chunk_size` trả về `[text]` ngay. Nếu hết separator trả về `[text]` dù oversized. Recursive case: tách bằng separator hiện tại, phần nào vẫn oversized thì đệ quy với separator tiếp theo, phần nhỏ giữ nguyên. Sau đó gộp tham lam (greedy merge) các phần nhỏ liền kề lại nếu còn chỗ trong `chunk_size`, ghép bằng separator hiện tại.

---

### EmbeddingStore

**`add_documents` + `search`** — approach:

`add_documents` gọi `_make_record` cho mỗi document — record lưu `id`, `content`, `embedding` (kết quả của `embedding_fn(doc.content)`), và `metadata` (copy từ doc, thêm trường `doc_id`). Tất cả records được append vào `self._store` (list). `search` gọi `_search_records`: embed query, tính dot product với embedding của từng record, sort descending và trả về top_k.

**`search_with_filter` + `delete_document`** — approach:

`search_with_filter` filter trước — lọc `self._store` giữ lại records có metadata khớp với tất cả key-value trong `metadata_filter`, sau đó mới chạy `_search_records` trên subset đó. `delete_document` dùng list comprehension để giữ lại tất cả records mà `metadata['doc_id'] != doc_id`, trả về `True` nếu size giảm.

---

### KnowledgeBaseAgent

**`answer`** — approach:

Gọi `self.store.search(question, top_k)` để lấy top-k chunks liên quan. Build prompt với format: `Context:\n[1] chunk1\n\n[2] chunk2\n\nQuestion: ...\n\nAnswer:` — đánh số chunk giúp LLM dễ reference. Truyền toàn bộ prompt vào `self.llm_fn` và trả về kết quả. Context inject trước question để LLM đọc evidence trước khi trả lời.

---

### Test Results

```
============================= test session starts ==============================
platform darwin -- Python 3.10.11, pytest-9.0.3, pluggy-1.6.0
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED

============================== 42 passed in 0.04s ==============================
```

**Số tests pass: 42 / 42**

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

Chạy `compute_similarity(_mock_embed(a), _mock_embed(b))` trên 5 cặp câu:

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Python is a programming language. | Python is used for machine learning. | HIGH | -0.0824 | Sai |
| 2 | The cat sat on the mat. | A dog ran through the park. | LOW | 0.0712 | Sai |
| 3 | Vector stores save embeddings for search. | Databases store vectors for similarity retrieval. | HIGH | -0.0768 | Sai |
| 4 | How do I reset my password? | What is the process of account recovery? | HIGH | -0.1817 | Sai |
| 5 | The weather is sunny today. | RAG systems retrieve relevant documents. | LOW | 0.0816 | Sai |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**

Tất cả 5 dự đoán đều sai — và đây không phải lỗi của model ngữ nghĩa mà là đặc điểm của **mock embedder**. `MockEmbedder` tạo vector bằng hash MD5 của text, hoàn toàn không encode nghĩa ngữ nghĩa. Kết quả gần 0 và có thể âm vì hash-based vectors gần như random và độc lập với nhau. Đây cho thấy sự khác biệt cơ bản giữa mock embedding (dùng để test code chạy đúng) và real semantic embedding (như `all-MiniLM-L6-v2` hoặc Gemini embedding) thực sự hiểu nghĩa của văn bản.

---

## 6. Results — Cá nhân (10 điểm)

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | What is a vector store and how does it work? | A vector store saves embeddings and retrieves similar items via similarity search; workflow: chunk → embed → store → query |
| 2 | Which chunking strategy works best for technical documentation? | Recursive chunking — tách theo đoạn văn trước, fallback nhỏ hơn khi cần |
| 3 | How does RAG reduce hallucinations? | Bằng cách grounding câu trả lời vào retrieved context thực tế, LLM chỉ trả lời dựa trên evidence |
| 4 | What are common failure cases in retrieval systems? | Outdated docs ranking high, small chunks losing context, multilingual content confusing embeddings |
| 5 | Why is metadata important in document retrieval? | Metadata filter giúp thu hẹp search space, tránh trả nhầm tài liệu sai domain/ngôn ngữ |

---

### Kết Quả Của Tôi (RecursiveChunker, mock embedder)

| # | Query | Top-1 Retrieved (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------|-------|-----------|------------------------|
| 1 | What is a vector store? | python_intro (programming) | 0.157 | Không | Trả về python_intro thay vì vector_store_notes |
| 2 | Which chunking strategy best? | customer_support_playbook | 0.160 | Không | Sai document |
| 3 | How does RAG reduce hallucinations? | chunking_experiment_report | 0.176 | Một phần | Có đề cập RAG nhưng không trực tiếp |
| 4 | Common failure cases? | vector_store_notes | 0.115 | Có | vector_store_notes có mục "Common Risks" |
| 5 | Why is metadata important? | rag_system_design | 0.066 | Có | rag_system_design đề cập metadata |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 2 / 5

---

## 7. What I Learned (5 điểm — Demo)

**Failure Analysis:**

Query 1 và 2 thất bại hoàn toàn — `python_intro` và `customer_support_playbook` được trả về thay vì tài liệu đúng chủ đề. Nguyên nhân: **mock embedder không encode ngữ nghĩa** — score 0.157 và 0.160 là random từ hash function, không phản ánh sự liên quan thực. Đây là failure case quan trọng nhất: dùng mock embedding trong production sẽ cho retrieval hoàn toàn vô nghĩa.

**Đề xuất cải thiện:** Dùng real semantic embedder (`all-MiniLM-L6-v2` hoặc Gemini embedding) thay vì mock. Khi đó similarity scores sẽ phản ánh đúng độ liên quan ngữ nghĩa và retrieval precision sẽ cải thiện đáng kể.

**Điều hay nhất tôi học được:**

Bài lab này làm rõ lý do tại sao RAG cần hai thành phần hoạt động đồng thời tốt: chunking tốt giữ ngữ cảnh nguyên vẹn, embedding tốt đảm bảo similarity search có ý nghĩa. Thiếu một trong hai thì toàn bộ hệ thống thất bại. RecursiveChunker là chiến lược chunking mạnh vì nó tôn trọng cấu trúc tự nhiên của văn bản.

**Nếu làm lại, tôi sẽ thay đổi gì:**

Cài `sentence-transformers` ngay từ đầu để dùng `LocalEmbedder` thay vì mock, từ đó kết quả benchmark queries sẽ có ý nghĩa thực sự. Ngoài ra sẽ thiết kế metadata schema chi tiết hơn (thêm `date`, `difficulty`, `section`) để tận dụng `search_with_filter` hiệu quả hơn.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 8 / 10 |
| Chunking strategy | Nhóm | 12 / 15 |
| My approach | Cá nhân | 10 / 10 |
| Similarity predictions | Cá nhân | 5 / 5 |
| Results | Cá nhân | 8 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 4 / 5 |
| **Tổng** | | **82 / 100** |

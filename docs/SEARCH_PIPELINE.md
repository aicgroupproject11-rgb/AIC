# Pipeline tìm kiếm video AIC

Tài liệu này là nguồn hướng dẫn chính để chuẩn bị dữ liệu, dựng index và chạy hệ thống. Dataset được lấy từ [Google Sheet do đề bài cung cấp](https://docs.google.com/spreadsheets/d/1rfn1fieTThS_Ki3SIoJ6uXOx2AhMq7wGCak6W4jZyZM/edit?gid=0#gid=0).

## 1. Thiết kế tổng thể

```text
Google Sheet / ZIP
        │
        ▼
download → extract → scan/validate → manifest.csv
                                      │
             ┌────────────────────────┼──────────────────────┐
             ▼                        ▼                      ▼
     clip-features-32            objects/*.json       domain taxonomy
             │                        │                      │
       normalize + PCA       object BoW + normalized IDF  domain prototypes
             └────────────────────────┼──────────────────────┘
                                      ▼
                 global / collection / domain R-trees
                                      │
query → normalize VI/EN + n-gram/typo/Telex → domain router → R-tree candidates
                                      │
                                      ▼
                  exact CLIP + object BoW + domain rerank
                                      │
                                      ▼
                       keyframe + video + timestamp
```

Hệ thống không huấn luyện lại CLIP. Nó dùng `clip-features-32` do ban tổ chức cung cấp, học phép PCA trên chính tập vector này, sau đó dựng các cây tìm kiếm. OpenCLIP chỉ encode câu query và các domain prompt; vì vậy model phải là `ViT-B-32` / `openai` để cùng không gian 512 chiều với feature có sẵn.

## 2. Đã kế thừa gì từ bốn nhánh

| Nhánh | Phần được giữ và hoàn thiện |
|---|---|
| `main` | Khung Django/React/Docker và hợp đồng API |
| `data-processing` | Ý tưởng scan, manifest, collection; viết lại thành CLI có schema tường minh và kiểm tra chéo |
| `feature/kis-api` | Search endpoint, lọc `#Lxx`, URL keyframe/video, UI kết quả |
| `search-engine` | CLIP + PCA + R-tree + exact rerank; mở rộng thành cây theo domain/collection và BoW |

### Phần tái sử dụng từ `code/be_stem`

`code/be_stem` không có KIS/video retrieval hoàn chỉnh, nhưng có một số thuật toán thuần hữu ích. Các ý tưởng sau đã được port và viết lại vào `BE/search_engine`, nên runtime mới **không import** nested project này:

| Mã tham khảo trong `code/be_stem` | Phần đưa vào pipeline KIS mới |
|---|---|
| `app/services/search/text_normalizer.py` | lowercase, bỏ dấu tiếng Việt, chuẩn hóa `đ → d` |
| `app/services/search/keyword_extractor.py` | giữ full query, sinh trigram/bigram/unigram, loại stopword |
| `app/services/search/topic_bag_keyword_matcher.py` | exact/phrase/fuzzy match có ngưỡng để typo nhẹ không làm match sai từ ngắn |
| `app/services/search/public_search_index_service.py` | công thức smoothed IDF, áp dụng vào object bag-of-words |
| `app/services/search/r_tree_domain_router.py` | ý tưởng routing trace/stats cho endpoint inspect |

Query analyzer mới còn xử lý một số lỗi gõ phổ biến: ký tự cuối bị lặp (`dapp → dap`), hậu tố số và Telex chưa hoàn tất (`nguowif ddi xe ddapj → nguoi di xe dap`). Tất cả biến thể chỉ dùng để match alias/object/domain; câu gốc vẫn được giữ khi encode CLIP.

Không tái sử dụng MongoDB, Neo4j, FastAPI, E5 full-text hay R-tree Python in-memory của `be_stem`: chúng không phù hợp với hàng triệu keyframe và stack Django hiện tại. Hệ thống KIS dùng `libspatialindex` persistent R-tree; E5 chỉ là hướng thử nghiệm cho domain routing, không được trộn với vector frame CLIP.

## 3. Dữ liệu đầu vào

Google Sheet hiện liệt kê các gói cho collection `L21` đến `L30`:

- `Keyframes_*.zip`: ảnh đại diện đã trích từ video, bắt buộc.
- `map-keyframes-aic25-b1.zip`: ánh xạ keyframe sang frame gốc và thời gian, bắt buộc.
- `clip-features-32-aic25-b1.zip`: vector CLIP theo đúng thứ tự keyframe, bắt buộc.
- `objects-aic25-b1.zip`: object detector output, dùng cho BoW và route domain, bắt buộc cho hybrid search đầy đủ.
- `media-info-aic25-b1.zip`: metadata video, dùng để kiểm tra độ nhất quán.
- `Videos_*.zip`: video gốc, không cần khi build/search index nhưng cần để phát video từ giao diện.

Sau khi giải nén, `data-root` phải có cấu trúc:

```text
data_processing/
├── keyframes/
│   └── L21_V001/
│       ├── 001.jpg
│       └── 002.jpg
├── map-keyframes/
│   └── L21_V001.csv
├── media-info/
│   └── L21_V001.json
├── objects/
│   └── L21_V001/
│       ├── 001.json
│       └── 002.json
├── clip-features-32/
│   └── L21_V001.npy
└── videos/                  # optional cho search, cần cho playback
    └── L21_V001.mp4
```

### Schema từng loại

`map-keyframes/L21_V001.csv` tối thiểu có:

| Cột | Ý nghĩa |
|---|---|
| `n` | Số thứ tự keyframe, trùng tên `001.jpg`, `002.jpg`, ... |
| `frame_idx` | Frame thật trong video gốc |
| `pts_time` | Thời điểm theo giây |

`clip-features-32/L21_V001.npy` là ma trận `[số_keyframe, 512]`. Dòng thứ 0 ứng với dòng đầu của map và `n=1`; pipeline ghi quan hệ này thành `clip_vector_index`, không nhầm `n` với `frame_idx`.

`objects/L21_V001/001.json` của dataset chính thức chứa bốn mảng song song:

- `detection_scores`;
- `detection_class_names` (Open Images MID);
- `detection_class_entities` (tên như `Man`, `Bicycle`, `Traffic light`);
- `detection_boxes`.

BoW dùng `detection_class_entities` có score từ `0.25` trở lên. Cùng một entity chỉ giữ score cao nhất, tối đa 20 entity/keyframe để giảm nhiễu.

Khi build, pipeline tính document frequency trên toàn bộ keyframe và lưu normalized IDF cho từng entity. Nhãn phổ biến ở nhiều frame như `person` vì thế ảnh hưởng ít hơn nhãn phân biệt như `bicycle` hoặc `traffic light`.

`manifest.csv` chuẩn do pipeline tạo có các cột:

| Cột | Ý nghĩa |
|---|---|
| `keyframe_id` | ID duy nhất, ví dụ `L21_V001_000001` |
| `collection_id` | `L21` ... `L30` |
| `video_id` | Ví dụ `L21_V001` |
| `keyframe_number` | Giá trị `n`, dùng tìm ảnh/object JSON |
| `clip_vector_index` | Dòng tương ứng trong `.npy`, bắt đầu từ 0 |
| `frame_number` | `frame_idx` trong video gốc |
| `timestamp_ms` | `pts_time × 1000` |
| `image_path` | Đường dẫn tương đối từ data-root |
| `video_path` | Đường dẫn video nếu có |

## 4. Chạy pipeline local

Yêu cầu Python 3.12. Từ thư mục repository:

```bash
cd BE
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Liệt kê package từ Sheet mà chưa tải file:

```bash
python -m data_processing.download_dataset --list
```

Tải và giải nén các gói cần để search (dữ liệu rất lớn, cần kiểm tra dung lượng trước):

```bash
python -m data_processing.download_dataset --extract
```

Muốn có video playback, thêm group `videos`:

```bash
python -m data_processing.download_dataset \
  --groups keyframes,map-keyframes,media-info,objects,clip-features-32,videos \
  --extract
```

Script hỗ trợ resume qua file `.part`, bỏ qua ZIP đã tải xong, kiểm tra zip-slip trước khi extract. Có thể tải thủ công từ Sheet; miễn cấu trúc sau giải nén đúng mục 3.

Kiểm tra sâu và sinh `manifest.csv`, `collection.json`:

```bash
python -m data_processing.cli prepare --data-root data_processing
```

Kết quả `valid: true` là điều kiện để build index. Sau đó:

```bash
python -m search_engine.cli build-index \
  --data-root data_processing \
  --index-dir search_engine/data/search_index \
  --pca-dim 24
```

Lần đầu OpenCLIP sẽ cần tải model weight. Có thể smoke test không qua web:

```bash
python -m search_engine.cli inspect-index
python -m search_engine.cli search "người phụ nữ đi xe đạp" --collection L21 --top-k 10
```

Chạy API/UI:

```bash
python manage.py migrate
python manage.py runserver
```

Ở terminal khác:

```bash
cd FE
npm install
npm run dev
```

API search:

```bash
curl -X POST http://localhost:8000/api/kis/search/ \
  -H 'Content-Type: application/json' \
  -d '{"query":"a woman riding a bicycle #L21","top_k":20}'
```

Debug một query mà không trả toàn bộ kết quả:

```bash
curl -X POST http://localhost:8000/api/kis/search/inspect/ \
  -H 'Content-Type: application/json' \
  -d '{"query":"nguowif ddi xe ddapj #L21","top_k":20}'
```

Response cho biết query đã chuẩn hóa, các n-gram/alias/object match, điểm của từng domain, danh sách domain được chọn và từng R-tree đã đọc (`tree_key`, vai trò routed/fallback, số entry, số ứng viên trả về/mới). Endpoint này dùng cùng query parser và candidate budget với search thật, phù hợp để học sinh debug recall.

## 5. Chạy bằng Docker

Chuẩn bị dữ liệu/index ở host trước, hoặc build index bằng one-shot container:

```bash
cp .env.example .env
docker compose build backend
docker compose run --rm backend python -m data_processing.cli prepare --data-root /data/aic
docker compose run --rm backend python manage.py build_kis_index
docker compose up
```

Hai biến host mount quan trọng:

```dotenv
KIS_DATA_ROOT_HOST=./BE/data_processing
KIS_INDEX_ROOT_HOST=./BE/search_engine/data/search_index
```

Raw dataset và index đều đã được `.gitignore`; không commit các ZIP, ảnh, video, `.npy`, file R-tree `.dat/.idx`.
Docker dùng `requirements.docker.txt` với PyTorch CPU để không tải CUDA runtime nhiều GB. Cài local vẫn dùng `requirements.txt` để PyTorch tự chọn wheel phù hợp hệ điều hành.

## 6. Luồng search và công thức điểm

1. Bỏ collection tag `#L21`, giữ nó làm filter.
2. Chuẩn hóa lowercase/bỏ dấu, sinh n-gram, sửa typo/Telex có kiểm soát và mở rộng alias (`xe đạp → bicycle`, `phụ nữ → woman`).
3. Domain router trộn lexical BoW và cosine với domain prototype; lấy tối đa ba domain có điểm ít nhất 60% domain tốt nhất.
4. Query R-tree theo `collection + domain`. Nếu không filter collection, dùng domain tree toàn cục.
5. Luôn lấy thêm ứng viên từ collection/global fallback tree để một lần route sai không làm mất kết quả đúng.
6. R-tree chạy trên PCA 24 chiều để tránh dùng R-tree trực tiếp ở 512 chiều. Top ứng viên được tính lại cosine trên vector gốc 512 chiều.
7. Điểm cuối mặc định:

```text
score = 0.82 × exact_CLIP + 0.12 × object_BoW + 0.06 × domain_match
```

Với một object trùng query, đóng góp BoW cơ sở là:

```text
object_term = detector_confidence × normalized_IDF × query_match_score
```

`query_match_score` bằng 1 cho exact match và thấp hơn cho fuzzy match. Tổng object score được chặn ở 1 để một frame có quá nhiều detection không lấn át CLIP.

API trả thêm `domains`, `routed_domains`, `matched_objects` và `score_components`, giúp học sinh giải thích vì sao một keyframe được chọn.

## 7. Các file cần chỉnh khi thử nghiệm

- `BE/search_engine/domain_taxonomy.json`: vocabulary/alias/domain prompt.
- `BE/search_engine/indexer.py`: candidate budget và trọng số rerank.
- `BE/search_engine/builder.py`: PCA dimension, object threshold, số domain/keyframe.
- `BE/apps/kis/serializers.py`: API contract.

Index hiện dùng `format_version = 2` vì có thêm `bow_idf.npy` và thống kê `tree_counts`. Index v1 cũ sẽ chủ động báo không tương thích; chạy lại `build-index`. Sau khi đổi taxonomy, CLIP model, PCA hoặc object threshold cũng phải build lại index. Không cần build lại khi chỉ đổi giao diện.

## 8. Kiểm thử và tiêu chí đánh giá

```bash
cd BE
python manage.py test
```

Với tập query có ground truth, nên đo riêng:

- `Recall@candidate_k`: R-tree/domain routing có đưa keyframe đúng vào candidate pool không;
- `Recall@K` hoặc `mAP@K`: chất lượng rerank cuối;
- latency p50/p95;
- ablation: CLIP-only so với CLIP + domain, và CLIP + domain + object BoW.

Nếu recall candidate thấp, tăng `candidate_k` hoặc `domains_per_frame` trước khi thay trọng số. Nếu candidate recall tốt nhưng top đầu sai, tinh chỉnh object/domain vocabulary và trọng số rerank.

## 9. Lỗi thường gặp

- `Chưa có search index`: chạy `build-index`, kiểm tra `KIS_INDEX_ROOT`.
- `Search index khác phiên bản code`: xóa/thay thư mục index cũ bằng kết quả `build-index` v2; không dùng lẫn file của hai lần build.
- `Query vector ... index cần ...`: model query khác model tạo `clip-features-32`.
- `Thiếu CLIP feature` hoặc count lệch: chạy `data_processing.cli scan --deep` và giải nén lại package tương ứng.
- UI thấy ảnh nhưng video 404: chưa tải/giải nén nhóm `videos`.
- Docker không thấy dữ liệu: kiểm tra `KIS_DATA_ROOT_HOST` và `KIS_INDEX_ROOT_HOST` trong `.env`.
- Lần đầu query chậm hoặc lỗi model: tải/cache OpenCLIP trước khi vào phòng thi; tránh để hệ thống phụ thuộc mạng tại thời điểm thi.

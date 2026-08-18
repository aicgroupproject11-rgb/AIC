# AIC Data Processing

## Thêm collection mới

### 1. Thêm keyframes

Tạo thư mục `keyframes` và giải nén dữ liệu vào:

keyframes/L31_V001/
keyframes/L31_V002/

### 2. Thêm mapping

Tạo thư mục `map-keyframes` và giải nén dữ liệu vào:

map-keyframes/L31_V001.csv
map-keyframes/L31_V002.csv

### 3. Thêm metadata

Tạo thư mục `media-info` và giải nén dữ liệu vào:

media-info/L31_V001.json
media-info/L31_V002.json

### 4. Thêm objects

Tạo thư mục `objects` và giải nén dữ liệu vào:

objects/L31_V001/
objects/L31_V002/

### 5. Thêm CLIP

Tạo thư mục `clip-features-32` và giải nén dữ liệu vào:

clip-features-32/L31_V001.npy
clip-features-32/L31_V002.npy

### 6. Thêm videos

Tạo thư mục `videos` và giải nén dữ liệu vào:

videos/L31_V001.mp4
videos/L31_V002.mp4

### 7. Chạy kiểm tra

python scan_aic.py

### 8. Tạo manifest

python build_manifest.py 
Kết quả tạo ra một file theo đường dẫn trong terminal

### 9. Kiểm tra manifest

python validate_manifest.py

Kết quả cuối phải là:

MANIFEST VALIDATION: PASS

### 10. Tạo collection

python build_collection.py 
Kết quả tạo ra một file theo đường dẫn trong terminal

### 11. Kiểm tra collection mapping

python validate_collection.py

Kết quả cuối phải là:

COLLECTION VALIDATION: PASS
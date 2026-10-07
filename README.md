# Mori — Tìm kiếm sản phẩm đa phương thức

Project bài tập xây dựng ứng dụng tìm kiếm trên catalog sản phẩm bằng **văn bản, giọng nói và hình ảnh**. Backend Python dùng chung các service cho CLI và web; giao diện web được phục vụ bởi FastAPI.

Catalog minh họa có 40 sản phẩm: giày, túi/balo, áo và bình nước. Tên, giá, tồn kho và mô tả là dữ liệu giả định phục vụ bài tập. Giá không quy định đơn vị tiền tệ.

## Tính năng

- Tìm kiếm văn bản tiếng Việt có dấu, không dấu và tiếng Anh bằng bộ từ vựng song ngữ hữu hạn.
- Nhận dạng giọng nói qua Web Speech API của trình duyệt; backend nhận transcript để tìm kiếm.
- Tìm kiếm ảnh upload hoặc ảnh mẫu bằng model CLIP ViT-B/32 ONNX chạy cục bộ trên CPU.
- Xem catalog, chi tiết sản phẩm, thứ hạng, điểm và thông tin xử lý truy vấn.
- API có kiểm tra đầu vào và giới hạn ảnh upload 8 MB.

## Yêu cầu

- Python 3.10 trở lên.
- Web: cài các gói trong `requirements-web.txt` (bao gồm dependencies của CLI).
- Microphone: trình duyệt hỗ trợ `SpeechRecognition`/`webkitSpeechRecognition`; quyền microphone và Internet có thể cần thiết. Tính năng này nhận diện bằng dịch vụ của trình duyệt, không phải mô hình speech-to-text chạy trong backend.

Model `models/clip-vit-base-patch32-vision-int8.onnx` và dữ liệu catalog đã có trong repository. Không cần API key, Node build hay tải model khi chạy ứng dụng.

## Khởi động web

Trên Windows PowerShell:

```powershell
# Tạo môi trường (chỉ thực hiện lần đầu)
py -3 -m venv .venv-web
.\.venv-web\Scripts\python.exe -m pip install -r requirements-web.txt

# Chạy ứng dụng
.\.venv-web\Scripts\python.exe -m uvicorn web.app:app --host 127.0.0.1 --port 8011
```

Mở [http://127.0.0.1:8011](http://127.0.0.1:8011). Dừng server bằng `Ctrl+C`. Có thể đổi port nếu `8011` đang được sử dụng. Dùng localhost hoặc HTTPS để trình duyệt cho phép truy cập microphone; nếu trình duyệt nhúng không hỗ trợ Web Speech API, hãy mở URL bằng Chrome hoặc trình duyệt tương thích.

## Sử dụng

- **Văn bản:** nhập truy vấn rồi nhấn Enter hoặc nút tìm kiếm. Ví dụ: `giày đen`, `giay den`, `black shoes`, `balo xanh lá`, `white shirt`, `bình nước đỏ`.
- **Giọng nói:** chọn tiếng Việt hoặc English, nhấn microphone và cấp quyền khi trình duyệt yêu cầu. Transcript được đưa vào ô tìm kiếm và tự tìm khi nhận diện kết thúc. Có thể sửa transcript trước khi tìm lại. Trình duyệt có thể gửi âm thanh tới dịch vụ nhận diện của nhà cung cấp; ứng dụng không lưu bản thu.
- **Hình ảnh:** tải JPEG, PNG hoặc WebP tối đa 8 MB, hoặc chọn ảnh mẫu. Ảnh upload được xử lý trong bộ nhớ và không ghi ra đĩa.
- Chọn số kết quả 3, 5, 12 hoặc 40. Chọn **Xem tất cả** để trở lại catalog.

Trước khi tìm kiếm, giao diện hiển thị catalog mà không gán điểm. Điểm tìm kiếm văn bản và điểm cosine của ảnh có thang đo khác nhau, không phải xác suất và không nên so trực tiếp.

## Chạy CLI

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe main.py --demo --top-k 3
```

CLI tương tác hỗ trợ truy vấn văn bản; demo chạy truy vấn văn bản, transcript mẫu và ảnh `datasets/images/query_a.png`.

## API

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `GET` | `/api/health` | Trạng thái ứng dụng và phương thức tìm kiếm |
| `GET` | `/api/catalog` | Catalog sản phẩm |
| `GET` | `/api/products/{product_id}` | Chi tiết sản phẩm |
| `GET` | `/api/image-samples` | Ảnh mẫu có sẵn |
| `POST` | `/api/search/text` | JSON `{ "text": "giày đen", "top_k": 5 }` |
| `POST` | `/api/search/voice` | JSON `{ "transcript": "black shoes", "top_k": 5 }` |
| `POST` | `/api/search/image` | Multipart với trường `image` và `top_k`, hoặc `sample_id`; JSON `{ "sample_id": "sample-1", "top_k": 5 }` cũng được hỗ trợ |

Phản hồi tìm kiếm gồm `mode`, `input`, `query`, `top_k`, `results` và `diagnostics`. Lỗi đầu vào trả 422; ảnh mẫu hoặc sản phẩm không tồn tại trả 404; ảnh không hỗ trợ trả 415.

## Cấu trúc project

```text
application/   Service truy vấn, tìm kiếm, xếp hạng, ảnh và giọng nói
data/          Repository sản phẩm, lưu trữ ảnh và bộ mã hóa CLIP
datasets/      Catalog JSON, ảnh sản phẩm, ảnh mẫu và dữ liệu đánh giá
models/        Model ONNX và ghi chú nguồn model
presentation/  Giao diện CLI
web/           FastAPI, schema API và giao diện tĩnh
scripts/       Tiện ích tạo dữ liệu, đánh giá và kiểm tra web
tests/         Kiểm thử unit và API
bootstrap.py   Composition root dùng chung
main.py        Điểm vào CLI
```

## Thiết kế tìm kiếm

**Văn bản và transcript:** chuẩn hóa chữ thường, bỏ dấu Unicode và thay một tập cụm tiếng Việt bằng từ khóa tiếng Anh. Sau đó hệ thống khớp các token khác nhau với tên, loại, màu và mô tả sản phẩm. Đây là từ điển hữu hạn cho catalog, không phải dịch máy hay tìm kiếm ngữ nghĩa. Không phải mọi từ đồng nghĩa hoặc cách diễn đạt tự nhiên đều được hỗ trợ.

**Hình ảnh:** ảnh được center-crop và đổi kích thước về 224×224, chuẩn hóa theo CLIP rồi mã hóa thành vector 512 chiều. Vector ảnh truy vấn được so với vector của ảnh catalog bằng cosine similarity. Model pretrained chưa được fine-tune riêng cho catalog này; kết quả phụ thuộc vào nội dung và độ rõ của ảnh.

**Xếp hạng:** điểm giảm dần; nếu bằng điểm thì ID sản phẩm tăng dần. Kết quả được giới hạn theo `top_k`.

## Giới hạn prototype

- Catalog nhỏ, chỉ gồm 40 sản phẩm minh họa; thông tin giá, tồn kho và mô tả là dữ liệu giả định, không phải catalog thương mại được cập nhật.
- Tìm kiếm văn bản dựa trên từ vựng ánh xạ Việt–Anh và khớp token, nên không hiểu mọi câu tự nhiên, từ đồng nghĩa hoặc lỗi chính tả.
- Tìm kiếm ảnh dùng CLIP pretrained, chưa fine-tune cho catalog này. Kết quả có thể kém với ảnh mờ, vật thể nhỏ, nhiều vật thể hoặc nội dung khác xa ảnh sản phẩm.
- Nhận dạng giọng nói phụ thuộc hỗ trợ và dịch vụ Web Speech API của trình duyệt; độ chính xác, khả năng dùng ngoại tuyến và quyền riêng tư âm thanh do trình duyệt/nhà cung cấp quyết định.
- Đây là prototype chạy cục bộ, chưa có tài khoản người dùng, phân quyền, cơ sở dữ liệu giao dịch, quản trị catalog hoặc triển khai production.
- Ảnh upload chỉ xử lý trong bộ nhớ trong phiên tìm kiếm; ứng dụng không lưu ảnh upload để tra cứu lại.

## Dữ liệu và nguồn ảnh

Ảnh sản phẩm và thông tin nguồn được lưu trong `datasets/` và `datasets/photo_sources.json`; trang `/static/photo-credits.html` liệt kê ghi công. Ảnh chỉ minh họa loại hoặc màu sản phẩm và không xác nhận thông tin thương mại của sản phẩm giả định. Model và nguồn tham khảo model được ghi trong [`models/README.md`](models/README.md).

Một số script chuẩn bị dữ liệu có thể tải ảnh từ Internet và cần dependencies riêng. `scripts/generate_dataset.py --overwrite-with-synthetic` ghi đè dữ liệu/ảnh bằng dữ liệu tổng hợp; chỉ dùng khi chủ ý phục hồi dataset hình học.

## Kiểm thử và tiện ích

```powershell
.\.venv-web\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-web\Scripts\python.exe scripts/verify_web.py
```

Các script khác gồm `scripts/evaluate.py`, `scripts/evaluate_image_models.py`, `scripts/check_catalog_photos.py`, `scripts/smoke_web.py` và `scripts/check_unified_web.cjs`. Một số tiện ích kiểm tra ảnh cần Pillow; kiểm thử trình duyệt CJS cần Node, Playwright và Edge. Xem nội dung từng script để biết tham số và dependencies cụ thể.

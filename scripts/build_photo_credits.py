from pathlib import Path
import json, html
root = Path(__file__).resolve().parents[1]
sources = json.loads((root/'datasets/photo_sources.json').read_text(encoding='utf-8'))
links = []
for s in sources:
    links.append(f'<li>Product {s["product_id"]}: <a href="{html.escape(s["source"])}">Source photo</a> — {html.escape(s.get("author", "See source page"))} — <a href="{html.escape(s["license"])}">License</a></li>')
(root/'web/static/photo-credits.html').write_text('''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nguồn ảnh — mori</title><link rel="stylesheet" href="/static/styles.css"></head><body><main style="padding-top:40px"><a href="/">← Trở về tìm kiếm</a><h1>Nguồn ảnh</h1><p>Catalog dùng 40 ảnh sản phẩm tách nền riêng biệt từ PNGimg. Ảnh được đổi sang màu của sản phẩm, căn giữa trên nền trung tính và lưu ở kích thước 900 × 900. Không ảnh nào chứa người hoặc đạo cụ khác. Ảnh query là bản sao ảnh sản phẩm 1, 5, 9.</p><p>Nguồn được cấp phép CC BY-NC 4.0; từng liên kết bên dưới trỏ tới trang ảnh tương ứng.</p><ul>''' + ''.join(links) + '</ul></main></body></html>',encoding='utf-8')

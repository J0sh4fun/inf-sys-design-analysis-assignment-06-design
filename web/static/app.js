"use strict";
const $ = id => document.getElementById(id);
const categories = {shoes:"Giày", bags:"Túi & balo", clothing:"Áo", drinkware:"Bình nước"};
const sampleNames = ["Giày đen", "Balo xanh lá", "Bình nước đỏ"];
let mode = "text", selectedImage = null, previewUrl = null, searchVersion = 0, searchController, detailVersion = 0, detailController;
function el(tag, text, cls) { const node = document.createElement(tag); if(text !== undefined) node.textContent = text; if(cls) node.className = cls; return node; }
async function api(path, options = {}) {
  let response;
  try { response = await fetch(path, options); } catch(e) { if(e.name === "AbortError") throw e; throw Error("Không kết nối được máy chủ. Vui lòng thử lại."); }
  const body = await response.json();
  if(!response.ok) throw Error(typeof body.detail === "string" ? body.detail : "Yêu cầu chưa hợp lệ.");
  return body;
}
function status(text, error = false) { $("status").textContent = text; $("status").classList.toggle("error", error); }
function pending(value) { $("search-button").disabled = value; $("search-button").textContent = value ? "Đang tìm…" : "Tìm kiếm ↗"; $("results").setAttribute("aria-busy", String(value)); }
function cancelSearch() { searchVersion++; searchController?.abort(); pending(false); }
function setMode(next) {
  microphone.cancel();
  cancelSearch(); mode = next;
  $("voice-note").hidden = mode !== "voice";
  $("mode-help").textContent = mode === "voice" ? "Voice search · Nói vào microphone; có thể sửa câu đã nhận diện." : "Text search · Nhập tiếng Việt có dấu, không dấu hoặc English.";
  $("search-input").placeholder = mode === "voice" ? "Hãy nói: tìm cho tôi giày chạy bộ" : "Bạn đang tìm gì? Try “black shoes”";
  $("search-input").focus();
}
let beforeVoice = "";
const microphone = new window.MicrophoneSearch({
  state: state => {
    const active = state !== "idle";
    $("voice-button").setAttribute("aria-pressed", String(active));
    $("voice-button").setAttribute("aria-label", active ? "Dừng microphone" : "Tìm bằng microphone");
    $("voice-button").title = active ? "Dừng microphone" : "Tìm bằng microphone";
    $("voice-button").classList.toggle("recording", active);
    $("voice-language").disabled = active;
    $("search-input").readOnly = active;
    $("search-button").disabled = active;
    if (state === "starting") status("Đang mở microphone… Hãy cho phép truy cập khi trình duyệt yêu cầu.");
    if (state === "listening") status("Đang nghe… Nói tên sản phẩm. Nhấn mic lần nữa để dừng.");
    if (state === "stopping") status("Đã dừng nghe. Đang hoàn tất nhận diện…");
  },
  preview: text => { $("search-input").value = text; },
  cancel: () => { $("search-input").value = beforeVoice; },
  error: message => status(message, true),
  final: text => { $("search-input").value = text; runSearch("voice"); },
});
$("voice-button").onclick = () => {
  if (microphone.active) { microphone.stop(); return; }
  setMode("voice"); beforeVoice = $("search-input").value;
  microphone.start($("voice-language").value);
};
$("text-mode").onclick = () => setMode("text");
window.addEventListener("pagehide", () => microphone.cancel());
document.addEventListener("visibilitychange", () => {
  if (document.hidden && microphone.active) { microphone.cancel(); status("Đã tắt microphone khi rời trang."); }
});
document.querySelectorAll("[data-query]").forEach(button => button.onclick = () => { setMode("text"); $("search-input").value = button.dataset.query; $("search-form").requestSubmit(); });
$("image-button").onclick = () => { setMode("text"); $("image-dialog").showModal(); };
$("close-images").onclick = () => $("image-dialog").close();
$("image-search").onclick = () => { $("image-dialog").close(); runSearch("image"); };
$("image-upload").onchange = () => {
  const file = $("image-upload").files[0];
  if(!file) return;
  if(previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file); selectedImage = {kind:"upload", file};
  $("upload-preview-image").src = previewUrl; $("upload-name").textContent = file.name; $("upload-preview").hidden = false;
  document.querySelectorAll(".sample").forEach(button => button.setAttribute("aria-pressed", "false"));
  $("image-search").disabled = false; $("sample-status").textContent = `Đã chọn ảnh: ${file.name}`;
};
async function loadSamples() {
  $("retry-samples").hidden = true;
  try {
    const body = await api("/api/image-samples"); $("sample-gallery").replaceChildren();
    body.samples.forEach((sample, i) => {
      const button = el("button", undefined, "sample"); button.type = "button"; button.setAttribute("aria-pressed", "false");
      const img = el("img"); img.src = sample.image_url; img.alt = sampleNames[i] || sample.name;
      button.append(img, el("span", sampleNames[i] || sample.name));
      button.onclick = () => { selectedImage = {kind:"sample", sample}; $("image-upload").value = ""; $("upload-preview").hidden = true; document.querySelectorAll(".sample").forEach(b => b.setAttribute("aria-pressed", String(b === button))); $("image-search").disabled = false; $("sample-status").textContent = `Đã chọn: ${sampleNames[i] || sample.name}`; };
      $("sample-gallery").append(button);
    });
    $("sample-status").textContent = "Chọn một ảnh để tiếp tục.";
  } catch(e) { $("sample-status").textContent = e.message; $("retry-samples").hidden = false; }
}
$("retry-samples").onclick = loadSamples;
function empty(title, text) { const box = el("div", undefined, "empty"); box.append(el("h3", title), el("p", text)); $("results").replaceChildren(box); }
function renderProducts(items, ranked) {
  $("results").replaceChildren(); $("result-count").textContent = `${items.length} sản phẩm`;
  if(!items.length) empty("Chưa tìm thấy sản phẩm", "Thử tên sản phẩm hoặc màu khác, ví dụ: giày đen / black shoes.");
  items.forEach((item, index) => {
    const p = item.product, card = el("article", undefined, "card"), visual = el("div", undefined, "card-image"), img = el("img");
    img.src = item.image_url; img.alt = p.name_vi || p.name; img.loading = "lazy";
    visual.append(img); if(ranked) visual.append(el("span", `#${index+1}`, "rank"));
    const content = el("div", undefined, "card-body");
    content.append(el("p", categories[p.category] || p.category, "product-meta"), el("h3", p.name_vi || p.name), el("p", p.name, "english-name"));
    const row = el("div", undefined, "card-row"); row.append(el("span", `${p.price.toFixed(2)}`, "price"), el("span", p.stock ? `Còn ${p.stock} sản phẩm` : "Tạm hết hàng", p.stock ? "stock" : "stock out")); content.append(row);
    if(ranked) content.append(el("p", `Điểm / Score  ${Number(item.score).toFixed(4)}`, "score"));
    const detail = el("button", "Xem chi tiết ↗", "details-button"); detail.setAttribute("aria-label", `Xem chi tiết ${p.name}`); detail.onclick = () => showDetails(p.product_id); content.append(detail);
    card.append(visual, content); $("results").append(card);
  });
}
function definition(list, key, value) { list.append(el("dt", key), el("dd", String(value))); }
function diagnostics(body) {
  $("diagnostics").hidden = false;
  const list = el("dl"); definition(list, "Input", body.input); definition(list, "Chế độ", body.mode);
  definition(list, "Processing", body.mode === "image" ? "Pixel ảnh → CLIP ViT-B/32 pre-trained → vector ngữ nghĩa 512 chiều → cosine similarity → ranking" : `${body.mode === "voice" ? "Transcript giọng nói (có thể đã chỉnh sửa) → " : ""}Chuẩn hóa Việt–Anh → khớp từ khóa → ranking`);
  definition(list, "Query chuẩn hóa", body.query.text || `${body.query.model} · ${body.query.embedding_dimension} chiều`);
  definition(list, "Ranking", "Điểm giảm dần; cùng điểm theo ID tăng dần; lấy top-k.");
  definition(list, "Thời gian backend", `${body.diagnostics.backend_processing_ms.toFixed(2)} ms`);
  $("diagnostic-content").replaceChildren(list, el("pre", JSON.stringify(body, null, 2)));
}
async function runSearch(requestMode) {
  const value = $("search-input").value.trim(), topK = Number($("top-k").value);
  if(requestMode !== "image" && !value) { status("Hãy nhập tên sản phẩm hoặc nội dung câu nói.", true); $("search-input").focus(); return; }
  if(requestMode === "image" && !selectedImage) { status("Hãy chọn hoặc tải lên một ảnh trước.", true); return; }
  cancelSearch(); const version = searchVersion; searchController = new AbortController();
  const payload = {top_k: topK};
  if(requestMode === "text") payload.text = value;
  else if(requestMode === "voice") payload.transcript = value;
  else payload.sample_id = selectedImage.kind === "sample" ? selectedImage.sample.sample_id : null;
  pending(true); status("Đang tìm sản phẩm phù hợp…"); $("diagnostics").hidden = true;
  $("results-title").textContent = "Kết quả tìm kiếm"; $("result-count").textContent = "";
  $("results-context").textContent = "Đang xử lý truy vấn…"; empty("Đang tìm…", "");
  try {
    let options;
    if(requestMode === "image") { const form = new FormData(); form.append("top_k", String(topK)); if(selectedImage.kind === "upload") form.append("image", selectedImage.file); else form.append("sample_id", selectedImage.sample.sample_id); options = {method:"POST", body:form, signal:searchController.signal}; }
    else options = {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload), signal:searchController.signal};
    const body = await api(`/api/search/${requestMode}`, options);
    if(version !== searchVersion) return;
    renderProducts(body.results, true); diagnostics(body);
    $("results-context").textContent = requestMode === "image" ? `${body.input} · CLIP ViT-B/32 · Điểm tương đồng cosine` : `“${value}” · ${requestMode === "voice" ? "Tìm bằng giọng nói" : "Tìm bằng văn bản"}`;
    status(`Đã tìm thấy ${body.results.length} sản phẩm. Điểm xếp hạng hiển thị bên dưới mỗi kết quả.`);
  } catch(e) { if(e.name !== "AbortError" && version === searchVersion) { status(e.message, true); empty("Chưa thể tìm kiếm", "Vui lòng kiểm tra nội dung nhập và thử lại."); $("results-context").textContent = "Yêu cầu chưa hoàn tất."; } }
  finally { if(version === searchVersion) pending(false); }
}
$("search-form").onsubmit = event => { event.preventDefault(); if(!$("search-button").disabled) runSearch(mode); };
async function loadCatalog() {
  microphone.cancel();
  cancelSearch(); const version = searchVersion; searchController = new AbortController(); pending(true);
  $("diagnostics").hidden = true;
  try {
    const body = await api("/api/catalog", {signal: searchController.signal}); if(version !== searchVersion) return;
    renderProducts(body.products, false); $("results-title").textContent = "Một chút cảm hứng cho bạn"; $("results-context").textContent = `${body.products.length} món đồ thường ngày · Giá minh họa, chưa quy định đơn vị tiền tệ`; status("Nhập từ khóa hoặc chọn mic / máy ảnh để bắt đầu.");
  } catch(e) { if(e.name !== "AbortError" && version === searchVersion) { status(e.message, true); empty("Chưa tải được catalog", "Nhấn Xem tất cả để thử lại."); } }
  finally { if(version === searchVersion) pending(false); }
}
$("all-products").onclick = loadCatalog;
async function showDetails(id) {
  const version = ++detailVersion; detailController?.abort(); detailController = new AbortController();
  $("detail-title").textContent = "Chi tiết sản phẩm"; $("detail-content").replaceChildren(el("p", "Đang tải…")); $("product-dialog").showModal();
  try {
    const body = await api(`/api/products/${id}`, {signal:detailController.signal}); if(version !== detailVersion || !$("product-dialog").open) return;
    $("detail-title").textContent = body.product.name_vi || body.product.name;
    const img = el("img"); img.src = body.image_url; img.alt = body.product.name;
    const list = el("dl"); for(const [key,value] of Object.entries(body.product)) definition(list,key,value);
    $("detail-content").replaceChildren(img, list, el("p", "Ảnh chụp sản phẩm thật dùng minh họa; thông tin catalog là dữ liệu demo.", "photo-note"));
  } catch(e) { if(e.name !== "AbortError" && version === detailVersion) $("detail-content").replaceChildren(el("p", e.message)); }
}
$("close-details").onclick = () => $("product-dialog").close();
$("product-dialog").onclose = () => { detailVersion++; detailController?.abort(); };
loadSamples(); loadCatalog();

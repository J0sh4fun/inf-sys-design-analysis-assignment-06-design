"use strict";

// The browser captures microphone audio and performs speech recognition.
// The application server receives only the final transcript, never an audio file.
class MicrophoneSearch {
  constructor(callbacks) {
    this.callbacks = callbacks;
    this.recognition = null;
    this.timer = null;
    this.endTimer = null;
  }
  get active() { return this.recognition !== null; }
  cancel() {
    const recognition = this.recognition;
    this.recognition = null;
    clearTimeout(this.timer); clearTimeout(this.endTimer);
    if (recognition) {
      recognition.abort();
      this.callbacks.cancel();
      this.callbacks.state("idle");
    }
  }
  stop() {
    const recognition = this.recognition;
    if (!recognition || this.stopping) return;
    this.stopping = true;
    this.callbacks.state("stopping");
    recognition.stop();
    this.endTimer = setTimeout(() => {
      if (this.recognition !== recognition) return;
      this.cancel();
      this.callbacks.error("Nhận diện mất quá lâu. Hãy thử lại hoặc nhập từ khóa.");
    }, 5000);
  }
  start(language) {
    this.cancel();
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!window.isSecureContext) {
      this.callbacks.error("Microphone cần HTTPS hoặc localhost. Hãy mở web bằng địa chỉ localhost.");
      return;
    }
    if (!Recognition) {
      this.callbacks.error("Trình duyệt này chưa hỗ trợ nhận diện giọng nói. Hãy mở bằng Chrome hỗ trợ Web Speech hoặc tiếp tục nhập từ khóa.");
      return;
    }
    const recognition = new Recognition();
    this.recognition = recognition;
    this.stopping = false;
    recognition.lang = language;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    let finalText = "", failed = false;
    const current = () => this.recognition === recognition;
    recognition.onstart = () => { if (current()) this.callbacks.state("listening"); };
    recognition.onresult = event => {
      if (!current() || failed) return;
      const finalParts = [], previewParts = [];
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i], text = result[0].transcript.trim();
        previewParts.push(text);
        if (result.isFinal) finalParts.push(text);
      }
      finalText = finalParts.join(" ").trim();
      this.callbacks.preview(previewParts.join(" "));
    };
    recognition.onerror = event => {
      if (!current()) return;
      failed = true;
      const messages = {
        "not-allowed": "Quyền microphone bị từ chối. Cho phép microphone trong cài đặt trang rồi thử lại.",
        "service-not-allowed": "Dịch vụ nhận diện bị trình duyệt chặn. Hãy thử trình duyệt hỗ trợ khác.",
        "audio-capture": "Không truy cập được microphone. Kiểm tra thiết bị và quyền microphone của hệ điều hành.",
        "no-speech": "Chưa nghe thấy giọng nói. Nhấn mic và nói lại gần microphone.",
        "network": "Không kết nối được dịch vụ nhận diện. Kiểm tra Internet và thử lại.",
        "language-not-supported": "Dịch vụ chưa hỗ trợ ngôn ngữ đã chọn. Thử ngôn ngữ khác.",
        "aborted": "Đã dừng nhận diện giọng nói.",
      };
      this.cancel();
      this.callbacks.error(messages[event.error] || "Không nhận diện được giọng nói. Hãy thử lại hoặc nhập từ khóa.");
    };
    recognition.onend = () => {
      if (!current()) return;
      this.recognition = null;
      clearTimeout(this.timer); clearTimeout(this.endTimer);
      this.callbacks.state("idle");
      if (!failed && finalText) this.callbacks.final(finalText);
      else if (!failed) {
        this.callbacks.cancel();
        this.callbacks.error("Chưa nhận được câu nói hoàn chỉnh. Nhấn mic để thử lại.");
      }
    };
    this.callbacks.state("starting");
    try {
      recognition.start();
      this.timer = setTimeout(() => this.stop(), 20000);
    } catch (error) {
      this.cancel();
      this.callbacks.error("Không khởi động được microphone. Kiểm tra quyền truy cập rồi thử lại.");
    }
  }
}
window.MicrophoneSearch = MicrophoneSearch;

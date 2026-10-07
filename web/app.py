"""FastAPI presentation adapter; all retrieval goes through existing services."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from bootstrap import ROOT, build_services
from web.schemas import TextRequest, VoiceRequest, ImageRequest

STATIC = Path(__file__).resolve().parent / "static"
IMAGE_ROOT = (ROOT / "datasets/images").resolve()
logger = logging.getLogger(__name__)


def image_url(path: str) -> str:
    """Expose only PNG basenames beneath the dedicated image directory."""
    resolved = (ROOT / path).resolve()
    if resolved.parent != IMAGE_ROOT or resolved.suffix.lower() != ".png":
        raise ValueError("Image asset is outside the allowed directory.")
    return f"/images/{resolved.name}"


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = build_services()
        # Opaque IDs are assigned to registered paths, never accepted as paths.
        app.state.samples = {
            f"sample-{index}": {"path": path, "name": f"Sample {index}", "image_url": image_url(path)}
            for index, path in enumerate(app.state.services.image.supported_images(), 1)
        }
        yield

    app = FastAPI(title="Multimodal Search Lab", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        messages = [f"{'.'.join(str(p) for p in error['loc'][1:]) or 'request'}: {error['msg']}" for error in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})

    @app.exception_handler(FileNotFoundError)
    async def missing_asset(request: Request, exc: FileNotFoundError):
        logger.error("Required local asset is missing", exc_info=exc)
        return JSONResponse(status_code=503, content={"detail": "A required sample file is missing on the server."})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("Unexpected web request failure", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Unexpected server error. See the server log for details."})

    @app.get("/api/health")
    def health():
        return {"status": "ok", "voice": "browser microphone recognition; transcript API",
                "image": f"uploaded pixels; {app.state.services.image.model_name}"}

    @app.get("/api/image-samples")
    def samples():
        return {"samples": [{"sample_id": key, "name": value["name"], "image_url": value["image_url"]}
                            for key, value in app.state.samples.items()]}

    def search_response(mode: str, original: str, query: dict, top_k: int, started: float) -> dict:
        results = app.state.services.search.search(query, top_k)
        # Keep product fields and scores intact; add a separate presentation URL.
        rendered = [{**item, "image_url": image_url(item["product"]["image"])} for item in results]
        public_query = query if mode != "image" else {
            "type": "image", "embedding_dimension": len(query["embedding"]),
            "model": app.state.services.image.model_name, "filters": query["filters"]
        }
        return {"mode": mode, "input": original, "query": public_query, "top_k": top_k, "results": rendered,
                "diagnostics": {
                    "retrieval_method": f"{app.state.services.image.model_name} inference from pixels; cosine similarity against all catalog images" if mode == "image" else "Whole-token matching; shared unique tokens across name, category, color and description",
                    "ranking_method": "Score descending, product ID ascending for ties; top-k selection",
                    "returned_results": len(rendered),
                    "backend_processing_ms": (perf_counter() - started) * 1000,
                    "duration_scope": "Query preparation, retrieval, ranking and response construction; excludes network and JSON serialization",
                }}

    @app.post("/api/search/text")
    def text_search(body: TextRequest):
        started = perf_counter()
        try:
            query = app.state.services.query.text_query(body.text)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return search_response("text", body.text, query, body.top_k, started)

    @app.post("/api/search/voice")
    def voice_search(body: VoiceRequest):
        started = perf_counter()
        services = app.state.services
        transcript = services.speech.transcribe(body.transcript)
        if not transcript.strip():
            raise HTTPException(422, "Voice transcript must not be empty.")
        try:
            query = services.query.voice_query(transcript)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return search_response("voice", body.transcript, query, body.top_k, started)

    @app.post("/api/search/image")
    async def image_search(request: Request):
        started = perf_counter()
        services = app.state.services
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                body = ImageRequest.model_validate(await request.json())
            except Exception as exc:
                raise HTTPException(422, "A valid sample_id and top_k are required.") from exc
            sample = app.state.samples.get(body.sample_id)
            if sample is None:
                raise HTTPException(404, "Unsupported image sample. Choose a registered sample.")
            embedding = services.image.encode(sample["path"])
            original, top_k = body.sample_id, body.top_k
        elif content_type.startswith("multipart/form-data"):
            form = await request.form()
            raw_top_k = str(form.get("top_k", "5"))
            if not raw_top_k.isdigit() or int(raw_top_k) <= 0:
                raise HTTPException(422, "top_k must be a positive integer.")
            top_k = int(raw_top_k)
            upload = form.get("image")
            sample_id = str(form.get("sample_id", ""))
            if upload is not None and hasattr(upload, "read"):
                if upload.content_type not in {"image/jpeg", "image/png", "image/webp"}:
                    await upload.close()
                    raise HTTPException(415, "Upload a JPEG, PNG, or WebP image.")
                content = await upload.read(8 * 1024 * 1024 + 1)
                await upload.close()
                if not content:
                    raise HTTPException(422, "The uploaded image is empty.")
                if len(content) > 8 * 1024 * 1024:
                    raise HTTPException(413, "The uploaded image must not exceed 8 MB.")
                try:
                    embedding = services.image.encode_upload(content)
                except ValueError as exc:
                    raise HTTPException(422, str(exc)) from exc
                original = Path(upload.filename or "uploaded-image").name
            else:
                sample = app.state.samples.get(sample_id)
                if sample is None:
                    raise HTTPException(422, "Choose or upload an image.")
                embedding = services.image.encode(sample["path"])
                original = sample_id
        else:
            raise HTTPException(415, "Use multipart/form-data to upload an image.")
        query = services.query.image_query(embedding)
        return search_response("image", original, query, top_k, started)

    @app.get("/api/products/{product_id}")
    def product_details(product_id: int):
        if product_id <= 0:
            raise HTTPException(422, "Product ID must be a positive integer.")
        product = app.state.services.search.get_product(product_id)
        if product is None:
            raise HTTPException(404, "Product not found.")
        return {"product": product, "image_url": image_url(product["image"])}

    @app.get("/api/catalog")
    def catalog():
        return {"products": [{"product": product, "image_url": image_url(product["image"])}
                             for product in app.state.services.search.list_products()]}

    @app.get("/images/{filename}")
    def image_asset(filename: str):
        candidate = (IMAGE_ROOT / filename).resolve()
        if candidate.parent != IMAGE_ROOT or candidate.suffix.lower() != ".png" or not candidate.is_file():
            raise HTTPException(404, "Image not found.")
        return FileResponse(candidate, media_type="image/png")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()

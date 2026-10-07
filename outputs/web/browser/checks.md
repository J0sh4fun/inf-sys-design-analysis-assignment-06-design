# Browser verification — 6 October 2026

Tested the actual local FastAPI server at `http://127.0.0.1:8000/` using the in-app browser. Search responses came from the existing Python services; no mocked search results were used.

## Observed passing behavior

- Initial screen displayed labeled controls and an empty starting state.
- Text `black shoes`, submitted with Enter, returned IDs 1, 2, 3, 4, 7 with scores 2, 1, 1, 1, 1. Product 3 remained visible as out of stock.
- Product 1's View details action opened a modal containing all nine record fields and the image; Escape dismissed it.
- Voice sample action filled `find running shoes`; search returned IDs 2, 3, 1, 10, with scores 2, 2, 1, 1.
- A whitespace-only voice transcript displayed a clear validation error.
- Image gallery showed all three registered samples. Selecting Sample 2 updated the preview; search returned IDs 5, 4, 11, 12, 1 with displayed cosine scores 1.0000, 0.8000, 0.8000, 0.2000, 0.0000.
- Expanded diagnostics showed the actual embedding, methods, top-k, returned count, measured backend duration and complete response, including unrounded scores.
- `sneakers` returned a successful no-matching-products state.
- Top-k values `0` and `1.5` displayed validation feedback; top-k `2` returned two products.
- ArrowRight moved from the text tab to the voice tab. Keyboard activation and Enter submission worked.
- At a 390 × 844 viewport, the image gallery, preview, results and text/voice workflows remained usable. DOM measurements were `window.innerWidth = 390` and `document.documentElement.scrollWidth = 390`: no horizontal overflow. The temporary viewport override was reset after verification.
- No browser warnings/errors were reported during the successful search interactions.
- After stopping the owned test server, another search displayed “Cannot reach the local server. Check that Uvicorn is running, then try again.” The button was re-enabled and the result area showed request failure.

## Screenshots

- `text-desktop.jpg`: text results on desktop.
- `product-details.jpg`: product-details modal.
- `image-diagnostics.jpg`: image search and expanded diagnostics.
- `image-mobile.jpg`: registered-image search and results at mobile width.
- `voice-mobile.jpg`: simulated voice results at mobile width.
- `empty-mobile.jpg`: no-match state on mobile.
- `network-error.jpg`: actual connection failure after server shutdown.

## Verification boundaries

API tests separately exercised unsupported samples, missing products/files, malformed requests, asset traversal attempts, and an unexpected backend exception. These uncommon backend errors were not each induced through the browser. Request cancellation/version guards and disabled duplicate submission are implemented; deliberately delayed, out-of-order responses were not stress-tested. The complete range of browsers, screen readers and mobile devices was not tested. No real voice recognition or image understanding is provided or evaluated.

The test server was stopped after verification. Start it using the README command to use the interface.

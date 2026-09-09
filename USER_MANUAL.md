# Image Warp Correction — User Manual

This guide walks through using the web app to straighten a photographed document or extract a sticker label.

You will work in a browser. The left sidebar holds settings and actions. The main area shows upload, the original image, and the result.

---

## 1. Start the app

You need **Python 3.11+** and **Node.js 18+**.

**First time only** — install dependencies:

```bash
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

**Every time you use the app** — start both servers in separate terminals:

```bash
# Terminal 1 — backend (port 8000)
python -m uvicorn backend.main:app --reload --port 8000
```

```bash
# Terminal 2 — frontend (port 5173)
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

The frontend forwards `/api` requests to the backend. If the page loads but upload fails, confirm the backend terminal is still running.

---

## 2. Upload an image

1. On the home screen, drag a photo onto the dashed upload area, or click the area to browse.
2. Accepted types: **PNG, JPG, JPEG, WebP**.
3. Wait for the toast **Image uploaded successfully**.
4. The page shows a session badge and the image size (for example `1920 x 1080`).

To start over with a different photo, click **New Image** in the top-right (you do not need to refresh the page).

---

## 3. Choose a correction mode

In the left sidebar, under **Correction Mode**, pick one:

| Mode | Use when |
|------|----------|
| **Automatic** | You want the app to find a sticker label (or document edges) for you. |
| **Manual** | Automatic detection failed, or you want to place the four corners yourself. |

You can switch modes at any time after upload.

---

## 4. Optional: nonlinear correction

In the sidebar, turn on **Nonlinear Correction** only if the photo has mild barrel/pincushion (lens) distortion.

- This runs **after** perspective correction.
- It is experimental. It will not fully flatten a curved page.
- Leave it **off** for a typical flat document or label photo.

---

## 5. Automatic: extract a sticker label

This is the primary automatic path.

1. Leave **Correction Mode** on **Automatic**.
2. Click **Extract Label** in the sidebar.
3. Wait for the spinner (**Extracting sticker label...**).
4. On success, the right pane titled **Extracted Labels** shows the cropped, straightened label.
5. A toast reports how long extraction took.

**Rotate the extracted label** (display only) using the two buttons in the top-right of the result:

- Left arrow: rotate 90° counter-clockwise
- Right arrow: rotate 90° clockwise

Rotation is for viewing. It does not change the saved file until you download after a full **Correct Image** pass (see Manual mode).

**If extraction fails:** a warning toast explains why (for example, no label found). Switch to **Manual** and place the corners yourself.

---

## 6. Automatic: detect document boundaries

Use this when you want the app to find a **full document quad**, not a sticker crop.

1. Stay in **Automatic**.
2. Click **Detect Boundaries**.
3. On success, a toast shows a detection score (higher is better).
4. Switch to **Manual** if you want to inspect or nudge those corners, then click **Correct Image**.

If detection fails, the toast says **Detection failed. Try manual mode.** Follow section 7.

---

## 7. Manual: place four corners and correct

1. Set **Correction Mode** to **Manual**.
2. A red quadrilateral appears on the photo under **Manual Bounding Box**.
3. Drag the **red circular handles** (not the outline) to the four corners of the document or label:
   - Top-left
   - Top-right
   - Bottom-right
   - Bottom-left
4. Place handles on the **edges of the subject**, not the photo frame.
5. Click **Reset** to return the box to a default inset rectangle.
6. Click **Correct Image**.
7. Wait for the spinner (**Correcting image...**).
8. The right pane **Corrected** shows the flattened rectangle.

Small handle errors produce a skewed or stretched result. If the output looks wrong, adjust the handles and click **Correct Image** again.

---

## 8. Compare original and result

The main view is side by side:

| Left: **Original** | Right: result |
|--------------------|---------------|
| The uploaded photo. After a successful correction, detected corners may be drawn on top. | **Extracted Labels** after Extract Label, or **Corrected** after Correct Image. |

Until you run a successful action, the right pane says **Corrected image will appear here**.

---

## 9. Inspect processing details

After a successful extract or correct:

1. Expand **Processing Details** at the bottom of the page.
2. For label extraction, review labels found, score, output size, and time.
3. For perspective correction, review:
   - Source and output dimensions
   - Timing
   - Corner coordinates (TL, TR, BR, BL)
   - Homography matrix
   - Whether nonlinear correction was applied

Collapse the section when you are done.

---

## 10. Download the corrected image

After **Correct Image** (manual or boundary-based correction):

1. Under the corrected preview, click **Download Corrected Image**.
2. The file saves as `corrected_image.png`.

Label extraction shows the crop in the browser. To save a full perspective-corrected PNG with the download button, use **Manual** → **Correct Image** (or detect boundaries, then correct).

---

## 11. Process another image

1. Click **New Image**.
2. Upload the next photo.
3. Repeat from section 3.

Closing the browser tab ends the in-memory session. Uploaded images are not stored on disk by the app.

---

## Quick reference

```text
Start servers → open http://localhost:5173
        ↓
   Upload PNG / JPG / WebP
        ↓
   ┌──── Automatic ────┐          ┌──── Manual ────┐
   │ Extract Label     │          │ Drag 4 red     │
   │   or              │          │ corner handles │
   │ Detect Boundaries │          │ Correct Image  │
   └────────┬──────────┘          └────────┬───────┘
            ↓                              ↓
     Compare original vs result
            ↓
   Expand Processing Details (optional)
            ↓
   Download Corrected Image  /  New Image
```

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| Page will not load | Confirm `npm run dev` is running and you opened `http://localhost:5173`, not port 8000. |
| Upload fails | Confirm the FastAPI backend is running on port 8000. Check the toast for the error message. |
| File type rejected | Use PNG, JPG, JPEG, or WebP. Other formats are not accepted. |
| **Extract Label** finds nothing | Use a clearer photo (even lighting, less glare). Or switch to **Manual** and place corners on the label. |
| **Detect Boundaries** fails | Common on low contrast, cluttered backgrounds, or glossy reflections. Use **Manual**. |
| Handles are hard to grab | Zoom the browser. Drag the **red circles**, not the red outline. |
| Corrected image looks stretched | The four corners are wrong. Reset, place them on the subject edges, and correct again. |
| Output is still slightly curved | Homography cannot flatten a curved page. Nonlinear Correction only helps mild lens distortion. |
| Large photos feel slow | Detection uses a smaller working copy. Only the final warp uses full resolution. Wait for the spinner to finish. |
| Want to undo and retry | Click **New Image**, or stay on the same upload, adjust corners, and click **Correct Image** again. |

---

## What the app can and cannot do

**Works well for**

- Documents or labels photographed at an angle
- Rotation and skew
- Trapezoid (perspective) distortion
- Mild lens warping (if Nonlinear Correction is on)

**Does not fully fix**

- Strongly curved pages
- Severe barrel distortion
- Low-contrast or highly cluttered scenes (automatic detection)
- Inaccurate manual corners

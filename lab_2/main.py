import cv2
import numpy as np
import base64
from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Глобальная переменная для хранения последнего загруженного изображения в памяти
# (В реальном продакшене так делать нельзя, но для лабы это упрощает жизнь -
# не нужно гонять файл туда-сюда при каждом движении ползунка)
last_uploaded_image = None


def image_to_base64(img):
    if img is None: return None
    _, buffer = cv2.imencode('.png', img)
    img_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/png;base64,{img_str}"


async def read_image(file: UploadFile):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    global last_uploaded_image
    last_uploaded_image = await read_image(file)
    return JSONResponse({"status": "ok", "image": image_to_base64(last_uploaded_image)})


@app.post("/api/process")
async def api_process_image(
        method: str = Form(...),
        kernel_size: int = Form(5),
        block_size: int = Form(11),
        c_val: int = Form(2)
):
    global last_uploaded_image

    if last_uploaded_image is None:
        return JSONResponse({"error": "No image uploaded"}, status_code=400)

    original_img = last_uploaded_image.copy()
    processed_img = None

    # --- ЛОГИКА ОБРАБОТКИ (ВАРИАНТ 15) ---

    if method == "median":
        # Ядро должно быть нечетным
        if kernel_size % 2 == 0: kernel_size += 1
        processed_img = cv2.medianBlur(original_img, kernel_size)

    elif method == "adaptive_mean":
        gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
        # Размер блока должен быть нечетным и > 1
        if block_size % 2 == 0: block_size += 1
        if block_size < 3: block_size = 3

        processed_img = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY, block_size, c_val
        )
        processed_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)

    elif method == "adaptive_gaussian":
        gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
        if block_size % 2 == 0: block_size += 1
        if block_size < 3: block_size = 3

        processed_img = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, c_val
        )
        processed_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2BGR)

    else:
        processed_img = original_img

    return JSONResponse({
        "processed_image": image_to_base64(processed_img)
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
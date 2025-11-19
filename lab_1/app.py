import math
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Tuple, Dict, Any




class RGBColor(BaseModel):
    r: int = Field(..., ge=0, le=255)
    g: int = Field(..., ge=0, le=255)
    b: int = Field(..., ge=0, le=255)


class CMYKColor(BaseModel):
    c: float = Field(..., ge=0, le=1)
    m: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)
    k: float = Field(..., ge=0, le=1)


class HLSColor(BaseModel):
    h: int = Field(..., ge=0, le=360)
    l: float = Field(..., ge=0, le=1)  # Lightness
    s: float = Field(..., ge=0, le=1)  # Saturation


class AllColorModels(BaseModel):
    rgb: RGBColor
    cmyk: CMYKColor
    hls: HLSColor


# Логика конвертации

# CMYK <-> RGB
def rgb_to_cmyk(r: int, g: int, b: int) -> CMYKColor:
    if r == 0 and g == 0 and b == 0:
        return CMYKColor(c=0, m=0, y=0, k=1)

    r_p = r / 255.0
    g_p = g / 255.0
    b_p = b / 255.0

    k = 1 - max(r_p, g_p, b_p)
    if k == 1:
        return CMYKColor(c=0, m=0, y=0, k=1)

    c = (1 - r_p - k) / (1 - k)
    m = (1 - g_p - k) / (1 - k)
    y = (1 - b_p - k) / (1 - k)

    return CMYKColor(c=round(c, 4), m=round(m, 4), y=round(y, 4), k=round(k, 4))


def cmyk_to_rgb(c: float, m: float, y: float, k: float) -> RGBColor:
    r = 255 * (1 - c) * (1 - k)
    g = 255 * (1 - m) * (1 - k)
    b = 255 * (1 - y) * (1 - k)
    return RGBColor(r=int(round(r)), g=int(round(g)), b=int(round(b)))


# RGB <-> HLS
def rgb_to_hls(r: int, g: int, b: int) -> HLSColor:
    r_p = r / 255.0
    g_p = g / 255.0
    b_p = b / 255.0

    max_val = max(r_p, g_p, b_p)
    min_val = min(r_p, g_p, b_p)
    delta = max_val - min_val

    # Lightness (L)
    l = (max_val + min_val) / 2

    h = 0
    s = 0

    if delta == 0:
        h = 0
        s = 0
    else:
        # Saturation (S)
        s = delta / (1 - abs(2 * l - 1))

        # Hue (H)
        if max_val == r_p:
            h = 60 * (((g_p - b_p) / delta) % 6)
        elif max_val == g_p:
            h = 60 * ((b_p - r_p) / delta + 2)
        elif max_val == b_p:
            h = 60 * ((r_p - g_p) / delta + 4)

        if h < 0:
            h += 360

    return HLSColor(h=int(round(h)), l=round(l, 4), s=round(s, 4))


def hls_to_rgb(h: int, l: float, s: float) -> RGBColor:
    if s == 0:
        r = g = b = l * 255
        return RGBColor(r=int(round(r)), g=int(round(g)), b=int(round(b)))

    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs(((h / 60) % 2) - 1))
    m = l - c / 2

    r_p, g_p, b_p = 0, 0, 0

    if 0 <= h < 60:
        r_p, g_p, b_p = c, x, 0
    elif 60 <= h < 120:
        r_p, g_p, b_p = x, c, 0
    elif 120 <= h < 180:
        r_p, g_p, b_p = 0, c, x
    elif 180 <= h < 240:
        r_p, g_p, b_p = 0, x, c
    elif 240 <= h < 300:
        r_p, g_p, b_p = x, 0, c
    elif 300 <= h <= 360:
        r_p, g_p, b_p = c, 0, x

    r = (r_p + m) * 255
    g = (g_p + m) * 255
    b = (b_p + m) * 255

    return RGBColor(r=int(round(r)), g=int(round(g)), b=int(round(b)))




app = FastAPI(title="Lab 1: Color Models (HLS Variant)")


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")



@app.get("/", response_class=HTMLResponse)
async def get_main_page(request: Request):
    """Отдает главную HTML страницу"""
    # Начальный цвет (белый)
    initial_rgb = RGBColor(r=255, g=255, b=255)
    initial_cmyk = rgb_to_cmyk(initial_rgb.r, initial_rgb.g, initial_rgb.b)
    initial_hls = rgb_to_hls(initial_rgb.r, initial_rgb.g, initial_rgb.b)

    initial_data = AllColorModels(rgb=initial_rgb, cmyk=initial_cmyk, hls=initial_hls)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "initial_data": initial_data.dict()
    })


@app.post("/convert", response_model=AllColorModels)
async def convert_color(source_model: str = Form(...), values: str = Form(...)):
    """
    Принимает цвет в одной модели и возвращает его во всех трех.
    Это ядро "автоматического пересчета" [cite: 10, 14]
    """

    import json
    v = json.loads(values)

    rgb = RGBColor(r=0, g=0, b=0)
    cmyk = CMYKColor(c=0, m=0, y=0, k=1)
    hls = HLSColor(h=0, l=0, s=0)

    try:
        if source_model == "rgb":
            rgb = RGBColor(r=int(v['r']), g=int(v['g']), b=int(v['b']))
            cmyk = rgb_to_cmyk(rgb.r, rgb.g, rgb.b)
            hls = rgb_to_hls(rgb.r, rgb.g, rgb.b)

        elif source_model == "cmyk":
            cmyk = CMYKColor(c=float(v['c']), m=float(v['m']), y=float(v['y']), k=float(v['k']))
            rgb = cmyk_to_rgb(cmyk.c, cmyk.m, cmyk.y, cmyk.k)
            hls = rgb_to_hls(rgb.r, rgb.g, rgb.b)

        elif source_model == "hls":
            hls = HLSColor(h=int(v['h']), l=float(v['l']), s=float(v['s']))
            rgb = hls_to_rgb(hls.h, hls.l, hls.s)
            cmyk = rgb_to_cmyk(rgb.r, rgb.g, rgb.b)

        return AllColorModels(rgb=rgb, cmyk=cmyk, hls=hls)

    except Exception as e:
        print(f"Error converting color: {e}")
        return JSONResponse(status_code=400, content={"message": "Invalid color values"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
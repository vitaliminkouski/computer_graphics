import math
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field


# Модели данных

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
    l: float = Field(..., ge=0, le=1)
    s: float = Field(..., ge=0, le=1)


class AllColorModels(BaseModel):
    rgb: RGBColor
    cmyk: CMYKColor
    hls: HLSColor



def rgb_to_cmyk(r: int, g: int, b: int) -> CMYKColor:
    if r == 0 and g == 0 and b == 0:
        return CMYKColor(c=0, m=0, y=0, k=1)

    r_p = r / 255.0
    g_p = g / 255.0
    b_p = b / 255.0

    # Вычисляем K (Black Key)
    k = 1 - max(r_p, g_p, b_p)

    if k == 1:
        return CMYKColor(c=0, m=0, y=0, k=1)

    # Вычисляем C, M, Y по стандартной формуле
    c = (1 - r_p - k) / (1 - k)
    m = (1 - g_p - k) / (1 - k)
    y = (1 - b_p - k) / (1 - k)

    return CMYKColor(c=round(c, 5), m=round(m, 5), y=round(y, 5), k=round(k, 5))


def cmyk_to_rgb(c: float, m: float, y: float, k: float) -> RGBColor:
    r = 255 * (1 - c) * (1 - k)
    g = 255 * (1 - m) * (1 - k)
    b = 255 * (1 - y) * (1 - k)
    return RGBColor(r=int(round(r)), g=int(round(g)), b=int(round(b)))


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
        s = 0  # Серый цвет, насыщенность 0
    else:
        # Saturation (S) - формула зависит от яркости L
        if l < 0.5:
            s = delta / (max_val + min_val)
        else:
            s = delta / (2.0 - max_val - min_val)

        # Hue (H)
        if max_val == r_p:
            h = (g_p - b_p) / delta
        elif max_val == g_p:
            h = 2.0 + (b_p - r_p) / delta
        elif max_val == b_p:
            h = 4.0 + (r_p - g_p) / delta

        h *= 60
        if h < 0:
            h += 360

    return HLSColor(h=int(round(h)), l=round(l, 5), s=round(s, 5))


def hls_to_rgb(h: int, l: float, s: float) -> RGBColor:
    if s == 0:
        # Серый цвет
        val = int(round(l * 255))
        return RGBColor(r=val, g=val, b=val)

    def hue_to_rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1 / 6: return p + (q - p) * 6 * t
        if t < 1 / 2: return q
        if t < 2 / 3: return p + (q - p) * (2 / 3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    h_norm = h / 360.0

    r = hue_to_rgb(p, q, h_norm + 1 / 3)
    g = hue_to_rgb(p, q, h_norm)
    b = hue_to_rgb(p, q, h_norm - 1 / 3)

    return RGBColor(r=int(round(r * 255)), g=int(round(g * 255)), b=int(round(b * 255)))


# Приложение FastAPI

app = FastAPI(title="Lab 1: Color Models (Corrected Math)")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def get_main_page(request: Request):
    initial_rgb = RGBColor(r=118, g=84, b=32)  # Ваш тестовый цвет
    initial_cmyk = rgb_to_cmyk(initial_rgb.r, initial_rgb.g, initial_rgb.b)
    initial_hls = rgb_to_hls(initial_rgb.r, initial_rgb.g, initial_rgb.b)

    initial_data = AllColorModels(rgb=initial_rgb, cmyk=initial_cmyk, hls=initial_hls)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "initial_data": initial_data.dict()
    })


@app.post("/convert", response_model=AllColorModels)
async def convert_color(source_model: str = Form(...), values: str = Form(...)):
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
        print(f"Error: {e}")
        return JSONResponse(status_code=400, content={"message": "Error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
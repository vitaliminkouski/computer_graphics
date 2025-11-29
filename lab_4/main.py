from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Tuple, Optional
import math

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# --- Модели данных ---
class Point(BaseModel):
    x: float
    y: float


class Segment(BaseModel):
    p1: Point
    p2: Point


class Rect(BaseModel):
    xmin: float
    ymin: float
    xmax: float
    ymax: float


# --- Вспомогательные функции ---

def get_region_code(p: Point, win: Rect) -> int:
    """Вычисление кода области  для помощи в алгоритме средней точки"""
    code = 0
    if p.x < win.xmin: code |= 1  # Left
    if p.x > win.xmax: code |= 2  # Right
    if p.y < win.ymin: code |= 4  # Bottom
    if p.y > win.ymax: code |= 8  # Top
    return code


# --- 1. Алгоритм средней точки (Midpoint Subdivision) ---

def midpoint_clip_line(p1: Point, p2: Point, win: Rect, precision=0.1) -> Optional[Segment]:
    code1 = get_region_code(p1, win)
    code2 = get_region_code(p2, win)

    # Тривиальное принятие
    if (code1 | code2) == 0:
        return Segment(p1=p1, p2=p2)

    # Тривиальное отвержение
    if (code1 & code2) != 0:
        return None

    # Если отрезок слишком маленький (достигли точности), проверяем, нужно ли его рисовать
    # Если одна точка внутри, а другая снаружи, мы приближаемся к границе.
    dist = math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)
    if dist < precision:
        return None

        # Делим отрезок пополам
    mid = Point(x=(p1.x + p2.x) / 2, y=(p1.y + p2.y) / 2)

    # Рекурсивно обрабатываем две половинки



    seg1 = midpoint_clip_line(p1, mid, win, precision)
    seg2 = midpoint_clip_line(mid, p2, win, precision)

    if seg1 and seg2:
        # Если обе половины видимы (или их части), объединяем их
        return Segment(p1=seg1.p1, p2=seg2.p2)
    elif seg1:
        return seg1
    elif seg2:
        return seg2
    else:
        return None


# --- 2. Алгоритм Сазерленда-Ходжмана (Отсечение выпуклого многоугольника) ---

def clip_polygon(subject_polygon: List[Point], win: Rect) -> List[Point]:
    """
    Отсекает полигон прямоугольным окном.
    Порядок обхода окна: Лево, Право, Низ, Верх
    """

    def inside(p: Point, edge: int) -> bool:
        if edge == 0: return p.x >= win.xmin  # Left
        if edge == 1: return p.x <= win.xmax  # Right
        if edge == 2: return p.y >= win.ymin  # Bottom
        if edge == 3: return p.y <= win.ymax  # Top
        return False

    def compute_intersection(p1: Point, p2: Point, edge: int) -> Point:
        # Формула пересечения прямой (p1, p2) с краем окна
        # y = y1 + slope * (x - x1)
        # x = x1 + (1/slope) * (y - y1)

        dx = p2.x - p1.x
        dy = p2.y - p1.y
        slope = dy / dx if dx != 0 else 0

        if edge == 0:  # Left x = xmin
            x = win.xmin
            y = p1.y + slope * (x - p1.x)
        elif edge == 1:  # Right x = xmax
            x = win.xmax
            y = p1.y + slope * (x - p1.x)
        elif edge == 2:  # Bottom y = ymin
            y = win.ymin
            if dx == 0:
                x = p1.x
            else:
                x = p1.x + (y - p1.y) / slope
        elif edge == 3:  # Top y = ymax
            y = win.ymax
            if dx == 0:
                x = p1.x
            else:
                x = p1.x + (y - p1.y) / slope
        else:
            x, y = 0, 0

        return Point(x=x, y=y)

    output_list = subject_polygon

    # Для каждого из 4 краев окна
    for edge in range(4):
        input_list = output_list
        output_list = []

        if not input_list:
            break

        S = input_list[-1]  # Последняя точка

        for E in input_list:
            if inside(E, edge):
                if not inside(S, edge):
                    output_list.append(compute_intersection(S, E, edge))
                output_list.append(E)
            elif inside(S, edge):
                output_list.append(compute_intersection(S, E, edge))
            S = E

    return output_list


# --- Маршруты API ---

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/process")
async def process_data(
        raw_data: str = Form(...),
        mode: str = Form(...)  # "lines" или "polygon"
):
    try:
        lines = raw_data.strip().split('\n')
        lines = [L.strip() for L in lines if L.strip()]

        # Парсинг формата из задания
        # Строка 1: n
        n = int(lines[0])
        segments_data = []

        # Читаем n строк с координатами
        for i in range(1, n + 1):
            parts = list(map(float, lines[i].split()))
            segments_data.append(Segment(
                p1=Point(x=parts[0], y=parts[1]),
                p2=Point(x=parts[2], y=parts[3])
            ))

        # Последняя строка: окно
        win_parts = list(map(float, lines[n + 1].split()))
        window = Rect(xmin=win_parts[0], ymin=win_parts[1], xmax=win_parts[2], ymax=win_parts[3])

        result_geometry = []

        if mode == "lines":
            # Вариант 15 Ч.1: Алгоритм средней точки
            for seg in segments_data:
                clipped = midpoint_clip_line(seg.p1, seg.p2, window)
                if clipped:
                    result_geometry.append([
                        {"x": clipped.p1.x, "y": clipped.p1.y},
                        {"x": clipped.p2.x, "y": clipped.p2.y}
                    ])
        else:
            # Отсечение полигона
            # Собираем точки из сегментов в один список вершин
            # Предполагаем, что входные сегменты идут последовательно и образуют замкнутый контур
            poly_points = []
            for seg in segments_data:
                poly_points.append(seg.p1)
            # Примечание: обычно последняя точка сегмента N совпадает с первой точкой сегмента N+1

            clipped_poly = clip_polygon(poly_points, window)

            # Преобразуем результат в формат списка точек для JSON
            res_points = [{"x": p.x, "y": p.y} for p in clipped_poly]
            if res_points:
                result_geometry.append(res_points)

        return {
            "window": {"xmin": window.xmin, "ymin": window.ymin, "xmax": window.xmax, "ymax": window.ymax},
            "original_lines": [
                [{"x": s.p1.x, "y": s.p1.y}, {"x": s.p2.x, "y": s.p2.y}] for s in segments_data
            ],
            "result": result_geometry,
            "mode": mode
        }

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)

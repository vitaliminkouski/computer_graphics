import math
import time
from typing import List, Tuple, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")


class DrawRequest(BaseModel):
    algorithm: str
    x1: int
    y1: int
    x2: Optional[int] = 0
    y2: Optional[int] = 0
    radius: Optional[int] = 0


class DrawResponse(BaseModel):
    points: List[Tuple[int, int, float]]
    execution_time_ns: int


# --- 1. Пошаговый алгоритм  ---
def step_by_step(x1, y1, x2, y2):
    points = []
    if x1 == x2 and y1 == y2:
        return [(x1, y1, 1.0)]

    if abs(x2 - x1) >= abs(y2 - y1):
        k = (y2 - y1) / (x2 - x1) if x1 != x2 else 0
        b = y1 - k * x1
        step = 1 if x2 > x1 else -1
        for x in range(x1, x2 + step, step):
            y = k * x + b
            points.append((x, round(y), 1.0))
    else:
        k = (x2 - x1) / (y2 - y1) if y1 != y2 else 0
        b = x1 - k * y1
        step = 1 if y2 > y1 else -1
        for y in range(y1, y2 + step, step):
            x = k * y + b
            points.append((round(x), y, 1.0))
    return points


# --- 2. Алгоритм ЦДА ---
def dda(x1, y1, x2, y2):
    points = []
    dx = x2 - x1
    dy = y2 - y1
    steps = max(abs(dx), abs(dy))

    if steps == 0: return [(x1, y1, 1.0)]

    x_inc = dx / steps
    y_inc = dy / steps
    x, y = x1, y1

    for _ in range(steps + 1):
        points.append((round(x), round(y), 1.0))
        x += x_inc
        y += y_inc
    return points


# --- 3. Алгоритм Брезенхема (Линия) ---
def bresenham_line(x1, y1, x2, y2):
    points = []
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy

    curr_x, curr_y = x1, y1
    while True:
        points.append((curr_x, curr_y, 1.0))
        if curr_x == x2 and curr_y == y2: break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            curr_x += sx
        if e2 < dx:
            err += dx
            curr_y += sy
    return points


# --- 4. Алгоритм Брезенхема (Окружность) ---
def bresenham_circle(xc, yc, r):
    points = []
    x = 0
    y = r
    d = 3 - 2 * r

    def plot(xc, yc, x, y):
        return [
            (xc + x, yc + y, 1.0), (xc - x, yc + y, 1.0), (xc + x, yc - y, 1.0), (xc - x, yc - y, 1.0),
            (xc + y, yc + x, 1.0), (xc - y, yc + x, 1.0), (xc + y, yc - x, 1.0), (xc - y, yc - x, 1.0)
        ]

    points.extend(plot(xc, yc, x, y))
    while y >= x:
        x += 1
        if d > 0:
            y -= 1
            d = d + 4 * (x - y) + 10
        else:
            d = d + 4 * x + 6
        points.extend(plot(xc, yc, x, y))
    return list(set(points))


# --- 5. Алгоритм Ву ---
def wu_line(x1, y1, x2, y2):
    points = []

    def ipart(x):
        return int(x)

    def round_func(x):
        return ipart(x + 0.5)

    def fpart(x):
        return x - ipart(x)

    def rfpart(x):
        return 1 - fpart(x)

    steep = abs(y2 - y1) > abs(x2 - x1)
    if steep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1

    dx = x2 - x1
    dy = y2 - y1
    gradient = dy / dx if dx != 0 else 1.0

    # Первая точка
    xend = round_func(x1)
    yend = y1 + gradient * (xend - x1)
    xgap = rfpart(x1 + 0.5)
    xpxl1 = xend
    ypxl1 = ipart(yend)

    if steep:
        points.append((ypxl1, xpxl1, rfpart(yend) * xgap))
        points.append((ypxl1 + 1, xpxl1, fpart(yend) * xgap))
    else:
        points.append((xpxl1, ypxl1, rfpart(yend) * xgap))
        points.append((xpxl1, ypxl1 + 1, fpart(yend) * xgap))

    intery = yend + gradient

    # Вторая точка
    xend = round_func(x2)
    yend = y2 + gradient * (xend - x2)
    xgap = fpart(x2 + 0.5)
    xpxl2 = xend
    ypxl2 = ipart(yend)

    if steep:
        points.append((ypxl2, xpxl2, rfpart(yend) * xgap))
        points.append((ypxl2 + 1, xpxl2, fpart(yend) * xgap))
    else:
        points.append((xpxl2, ypxl2, rfpart(yend) * xgap))
        points.append((xpxl2, ypxl2 + 1, fpart(yend) * xgap))

    # Основной цикл
    for x in range(xpxl1 + 1, xpxl2):
        if steep:
            points.append((ipart(intery), x, rfpart(intery)))
            points.append((ipart(intery) + 1, x, fpart(intery)))
        else:
            points.append((x, ipart(intery), rfpart(intery)))
            points.append((x, ipart(intery) + 1, fpart(intery)))
        intery += gradient
    return points


# --- 6. Алгоритм Кастла-Питвея ---
def castle_pitteway(x1, y1, x2, y2):
    points = []

    # Определяем размеры сторон прямоугольника, в котором лежит отрезок
    w = abs(x2 - x1)
    h = abs(y2 - y1)

    # Определяем направление шагов (+1 или -1)
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1

    # Сводим задачу к первому октанту (канонический случай 0 < slope < 1)
    # Если Высота > Ширины, меняем оси местами для расчета строки шагов
    swap_xy = h > w
    if swap_xy:
        a, b = h, w
    else:
        a, b = w, h


    # a - длинная сторона, b - короткая

    sequence = ""

    if b == 0:
        # Прямая линия (горизонталь или вертикаль)
        sequence = "s" * a
    elif a == b:
        # Диагональ
        sequence = "d" * a
    else:
        # Основной алгоритм (Евклида для строк)
        y_val = b
        x_val = a - b

        m1 = "s"  # simple step (шаг по длинной стороне)
        m2 = "d"  # diagonal step (шаг по диагонали)

        while x_val != y_val:
            if x_val > y_val:
                x_val = x_val - y_val
                m2 = m1 + m2  # m2 = m1 (+) ~ m2
            else:
                y_val = y_val - x_val
                m1 = m2 + m1  # m1 = m2 (+) ~ m1

        # Результирующая последовательность
        sequence = (m2 + m1) * x_val

    # --- Отрисовка по строке ---
    curr_x, curr_y = x1, y1
    points.append((curr_x, curr_y, 1.0))

    for move in sequence:
        if swap_xy:
            # Если оси меняли (Y - главная)
            if move == 's':
                curr_y += sy  # Шаг только по Y
            else:  # move == 'd'
                curr_y += sy
                curr_x += sx
        else:
            # Стандартный случай (X - главная)
            if move == 's':
                curr_x += sx  # Шаг только по X
            else:  # move == 'd'
                curr_x += sx
                curr_y += sy

        points.append((curr_x, curr_y, 1.0))

    return points



@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/calculate", response_model=DrawResponse)
async def calculate_points(data: DrawRequest):
    algo_func = None
    args = []

    if data.algorithm == "step":
        algo_func = step_by_step
        args = [data.x1, data.y1, data.x2, data.y2]
    elif data.algorithm == "dda":
        algo_func = dda
        args = [data.x1, data.y1, data.x2, data.y2]
    elif data.algorithm == "bresenham_line":
        algo_func = bresenham_line
        args = [data.x1, data.y1, data.x2, data.y2]
    elif data.algorithm == "bresenham_circle":
        algo_func = bresenham_circle
        args = [data.x1, data.y1, data.radius]
    elif data.algorithm == "wu":
        algo_func = wu_line
        args = [data.x1, data.y1, data.x2, data.y2]
    elif data.algorithm == "castle_pitteway":
        algo_func = castle_pitteway
        args = [data.x1, data.y1, data.x2, data.y2]

    if algo_func:
        # Прогрев
        algo_func(*args)

        ITERATIONS = 1000
        # Для строкового алгоритма и Ву ставим чуть меньше итераций,
        # так как операции со строками в Python тяжелее математики
        if data.algorithm in ["wu", "castle_pitteway"]:
            ITERATIONS = 500

        start_time = time.perf_counter_ns()
        for _ in range(ITERATIONS):
            result_points = algo_func(*args)
        end_time = time.perf_counter_ns()

        avg_time = (end_time - start_time) / ITERATIONS

        return DrawResponse(
            points=result_points,
            execution_time_ns=int(avg_time)
        )
    return DrawResponse(points=[], execution_time_ns=0)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
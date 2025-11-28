import math
import time
from typing import List, Tuple, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# Модели данных для запроса и ответа
class DrawRequest(BaseModel):
    algorithm: str
    x1: int
    y1: int
    x2: Optional[int] = 0
    y2: Optional[int] = 0
    radius: Optional[int] = 0


class DrawResponse(BaseModel):
    points: List[Tuple[int, int]]
    execution_time_ns: int


# --- Реализация алгоритмов ---

def step_by_step(x1, y1, x2, y2):
    """Пошаговый алгоритм (на основе уравнения прямой y = kx + b)"""
    points = []
    if x1 == x2 and y1 == y2:
        return [(x1, y1)]

    # Обработка вертикальной линии (чтобы избежать деления на 0)
    if x1 == x2:
        step = 1 if y2 > y1 else -1
        for y in range(y1, y2 + step, step):
            points.append((x1, y))
        return points

    # Если изменение по X больше или равно изменению по Y
    if abs(x2 - x1) >= abs(y2 - y1):
        k = (y2 - y1) / (x2 - x1)
        b = y1 - k * x1
        step = 1 if x2 > x1 else -1
        for x in range(x1, x2 + step, step):
            y = k * x + b
            points.append((x, round(y)))
    else:
        # Если линия крутая, меняем местами роли x и y
        k = (x2 - x1) / (y2 - y1)
        b = x1 - k * y1
        step = 1 if y2 > y1 else -1
        for y in range(y1, y2 + step, step):
            x = k * y + b
            points.append((round(x), y))

    return points


def dda(x1, y1, x2, y2):
    """Алгоритм ЦДА (Цифровой Дифференциальный Анализатор)"""
    points = []
    dx = x2 - x1
    dy = y2 - y1

    steps = max(abs(dx), abs(dy))

    if steps == 0:
        return [(x1, y1)]

    x_inc = dx / steps
    y_inc = dy / steps

    x = x1
    y = y1

    for _ in range(steps + 1):
        points.append((round(x), round(y)))
        x += x_inc
        y += y_inc

    return points


def bresenham_line(x1, y1, x2, y2):
    """Алгоритм Брезенхема для отрезков (только целочисленная арифметика)"""
    points = []
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)

    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1

    err = dx - dy

    curr_x, curr_y = x1, y1

    while True:
        points.append((curr_x, curr_y))

        if curr_x == x2 and curr_y == y2:
            break

        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            curr_x += sx
        if e2 < dx:
            err += dx
            curr_y += sy

    return points


def bresenham_circle(xc, yc, r):
    """Алгоритм Брезенхема для окружности"""
    points = []
    x = 0
    y = r
    d = 3 - 2 * r

    def plot_circle_points(xc, yc, x, y):
        # Отражение точки в 8 октантов
        return [
            (xc + x, yc + y), (xc - x, yc + y),
            (xc + x, yc - y), (xc - x, yc - y),
            (xc + y, yc + x), (xc - y, yc + x),
            (xc + y, yc - x), (xc - y, yc - x)
        ]

    points.extend(plot_circle_points(xc, yc, x, y))

    while y >= x:
        x += 1
        if d > 0:
            y -= 1
            d = d + 4 * (x - y) + 10
        else:
            d = d + 4 * x + 6
        points.extend(plot_circle_points(xc, yc, x, y))

    # Удаление дубликатов (могут возникнуть на стыках октантов)
    return list(set(points))


# --- Роутинг ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/calculate", response_model=DrawResponse)
async def calculate_points(data: DrawRequest):
    # 1. Выбираем функцию алгоритма
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

    # 2. "Прогрев" (Warm-up) - один запуск, чтобы подгрузить всё в кэш процессора
    points = algo_func(*args)

    # 3. МНОГОКРАТНЫЙ ЗАПУСК для точности
    ITERATIONS = 5000  # Количество повторений

    start_time = time.perf_counter_ns()

    for _ in range(ITERATIONS):
        algo_func(*args)

    end_time = time.perf_counter_ns()

    # Считаем среднее время одного запуска
    avg_duration = (end_time - start_time) / ITERATIONS

    return DrawResponse(
        points=points,
        # Возвращаем целое число наносекунд
        execution_time_ns=int(avg_duration)
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
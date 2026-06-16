def set_canvas_message(canvas, msg, muted_color, font_name):
    canvas.delete("all")
    canvas.create_text(16, 23, text=msg, anchor="w", fill=muted_color, font=(font_name, 10))


def compose_forecast_run(canvas, x0, data, height, weather_app):
    """Draw one run of the ticker line starting at x0; return its end x."""
    cy = height // 2
    ib = weather_app.draw_weather_symbol(canvas, x0, cy - 13, data.get("code"), 26)
    x = ib[2] + 10
    t = canvas.create_text(x, cy, text=f"{data['temp']}°F  {data['condition']}",
                           anchor="w", fill=weather_app.TEXT, font=("Ubuntu", 13, "bold"))
    x = canvas.bbox(t)[2] + 14
    details = []
    if data.get("feels_like") is not None:
        details.append(f"Feels {data['feels_like']}°")
    if data.get("humidity") is not None:
        details.append(f"Humidity {data['humidity']}%")
    if data.get("wind") is not None:
        details.append(f"Wind {data['wind']} mph")
    if details:
        t = canvas.create_text(x, cy, text="  ·  ".join(details), anchor="w",
                               fill=weather_app.MUTED, font=("Ubuntu", 10, "bold"))
        x = canvas.bbox(t)[2] + 28
    for day in data.get("forecast", [])[:7]:
        t = canvas.create_text(x, cy, text=day["date_obj"].strftime("%a"), anchor="w",
                               fill=weather_app.MUTED, font=("Ubuntu", 11, "bold"))
        x = canvas.bbox(t)[2] + 6
        ib = weather_app.draw_weather_symbol(canvas, x, cy - 9, day.get("code"), 18)
        x = ib[2] + 6
        t = canvas.create_text(x, cy, text=f"{day['hi']}°/{day['lo']}°",
                               anchor="w", fill=weather_app.TEMP,
                               font=("Ubuntu", 11, "bold"))
        x = canvas.bbox(t)[2] + 24
    t = canvas.create_text(x, cy, anchor="w", fill=weather_app.DIM, font=("Ubuntu", 9),
                           text=(f"{data['location']} · Updated {data['updated']} · click = open widget"))
    return canvas.bbox(t)[2]

import itertools
from typing import Dict, List
from PIL import ImageDraw
from PIL.Image import Image as PILImage
import math


def draw_polygon_on_pil_img(
    pil_img: PILImage,
    polygon: List[dict],
    outline_color: str = "red",
    outline_width: int = 1,
) -> PILImage:
    """
    Draws a polygon on the given PIL image.

    Args:
        pil_img: The PIL image to draw the polygon on.
        polygon: List of dictionaries containing "x" and "y" keys for each point.
        outline_color: The color of the polygon outline.
        outline_width: The width of the polygon outline.

    Returns:
        The PIL image with the polygon drawn on it.
    """
    pil_img = pil_img.copy()
    draw = ImageDraw.Draw(pil_img)
    # Convert to list of tuples, as expected by PIL
    draw_polygon = [(point["x"], point["y"]) for point in polygon]
    if len(draw_polygon) < 3:
        draw.polygon(draw_polygon, outline=outline_color, width=outline_width)
        return pil_img
    # Calculate centroid
    cx = sum([p[0] for p in draw_polygon]) / len(draw_polygon)
    cy = sum([p[1] for p in draw_polygon]) / len(draw_polygon)
    # Expand each point outward from centroid
    offset = outline_width + 1
    expanded_polygon = []
    for x, y in draw_polygon:
        dx = x - cx
        dy = y - cy
        length = math.hypot(dx, dy)
        if length == 0:
            expanded_polygon.append((x, y))
        else:
            scale = (length + offset) / length
            ex = cx + dx * scale
            ey = cy + dy * scale
            expanded_polygon.append((ex, ey))
    draw.polygon(expanded_polygon, outline=outline_color, width=outline_width)
    return pil_img


def flat_poly_list_to_poly_dict_list(
    flat_poly_list: List[float],
) -> List[Dict[str, float]]:
    """
    Converts a flat list of polygon coordinates to a list of dictionaries.

    Args:
        flat_poly_list: The flat list of polygon coordinates (x0, y0, x1, y1, ...).

    Returns:
        A list of dictionaries with "x" and "y" keys.
    """
    return [
        {"x": flat_poly_list[i], "y": flat_poly_list[i + 1]}
        for i in range(0, len(flat_poly_list), 2)
    ]


def scale_flat_poly_list(
    polygon: list[float],
    existing_scale: tuple[float, float],
    new_scale: tuple[float, float],
) -> list[float]:
    """
    Scales a flat list of polygon coordinates to a new scale.

    Args:
        polygon: The flat list of polygon coordinates to scale.
        existing_scale: The existing scale as a tuple (width, height).
        new_scale: The new scale as a tuple (width, height).

        Returns:
        The scaled flat list of polygon coordinates.

    """
    x_coords = polygon[::2]
    x_coords = [x / existing_scale[0] * new_scale[0] for x in x_coords]
    y_coords = polygon[1::2]
    y_coords = [y / existing_scale[1] * new_scale[1] for y in y_coords]
    return list(itertools.chain.from_iterable(zip(x_coords, y_coords)))

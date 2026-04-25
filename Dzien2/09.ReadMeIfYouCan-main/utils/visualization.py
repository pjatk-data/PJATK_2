import os
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image as PILImage
from utils.image import (
    draw_polygon_on_pil_img,
    flat_poly_list_to_poly_dict_list,
    scale_flat_poly_list,
)


def visualize_all_field_polygons(
    di_confidence: Dict[str, Any],
    pages: List[PILImage.Image],
    output_folder: Optional[str] = None,
    outline_color: str = "lime",
    outline_width: int = 4,
    original_filename: Optional[str] = None,
) -> List[Tuple[str, PILImage.Image, int]]:
    """
    Visualizes all field polygons from the document intelligence confidence object.

    Args:
        di_confidence: The document intelligence confidence object.
        pages: The list of pages as PIL images.
        output_folder: Optional folder to save the images with polygons drawn.
                      If None, images are not saved to disk.
        outline_color: The color of the outline for the polygons.
        outline_width: The width of the outline for the polygons.
        original_filename: Optional original PDF filename to use as prefix in output filenames.

    Returns:
        List of tuples containing (field_name, image_with_polygon, page_index)
    """
    # Initialize a dictionary to store polygons per page
    # Key: page_index, Value: list of (field_name, matching_line) tuples
    polygons_by_page = {}

    # Skip the overall confidence score which doesn't have polygons
    fields_to_skip = ["_overall"]

    # Process each field in the di_confidence object to collect polygons by page
    for field_name, field_data in di_confidence.items():
        if field_name in fields_to_skip:
            continue

        # Process nested dictionaries
        if (
            isinstance(field_data, dict)
            and "matching_lines" in field_data
            and "page_numbers" in field_data
        ):
            # Process this field
            collect_field_polygons_by_page(field_name, field_data, polygons_by_page)
        elif isinstance(field_data, dict):
            # Recursively process nested dictionaries (like 'cost', 'policyholder', etc.)
            for nested_field_name, nested_field_data in field_data.items():
                full_field_name = f"{field_name}.{nested_field_name}"

                if (
                    isinstance(nested_field_data, dict)
                    and "matching_lines" in nested_field_data
                    and "page_numbers" in nested_field_data
                ):
                    collect_field_polygons_by_page(
                        full_field_name, nested_field_data, polygons_by_page
                    )

    # Now create visualizations for each page
    result_images = []
    for page_index, field_polygons in polygons_by_page.items():
        if 0 <= page_index < len(pages):
            # Get the image for the page
            img_input = pages[page_index].copy()

            # Draw all polygons for this page
            for field_name, matching_line in field_polygons:
                if (
                    hasattr(matching_line, "normalized_polygon")
                    and matching_line.normalized_polygon is not None
                ):
                    # Scale polygon to image dimensions
                    existing_scale = (1, 1)  # Normalized scale (0-1)
                    new_scale = (img_input.width, img_input.height)  # Pixel dimensions

                    pixel_based_polygon = scale_flat_poly_list(
                        matching_line.normalized_polygon,
                        existing_scale=existing_scale,
                        new_scale=new_scale,
                    )
                    pixel_based_polygon_dict = flat_poly_list_to_poly_dict_list(
                        pixel_based_polygon
                    )

                    # Draw the polygon on the image
                    img_input = draw_polygon_on_pil_img(
                        img_input,
                        pixel_based_polygon_dict,
                        outline_color=outline_color,
                        outline_width=outline_width,
                    )  # Save the image with all polygons if an output folder is provided
            if output_folder is not None:
                os.makedirs(output_folder, exist_ok=True)

                # Create filename with original filename as prefix if provided
                if original_filename:
                    # Remove extension and any path from the original filename
                    base_name = os.path.splitext(os.path.basename(original_filename))[0]
                    file_name = f"{base_name}_page_{page_index}.png"
                else:
                    file_name = f"page_{page_index}.png"

                output_path = os.path.join(output_folder, file_name)
                img_input.save(output_path)

            # Store the result image
            result_images.append((f"page_{page_index}", img_input, page_index))

    return result_images


def collect_field_polygons_by_page(
    field_name: str,
    field_data: Dict[str, Any],
    polygons_by_page: Dict[int, List[Tuple[str, Any]]],
) -> None:
    """
    Helper function to collect field polygons by page.

    Args:
        field_name: The name of the field.
        field_data: The field data containing matching_lines and page_numbers.
        polygons_by_page: Dictionary to store polygons by page.
    """
    # Process each matching line for the field
    for idx, matching_line in enumerate(field_data["matching_lines"]):
        if (
            not hasattr(matching_line, "normalized_polygon")
            or matching_line.normalized_polygon is None
        ):
            continue

        # Get the page index for this matching line
        page_index = (
            field_data["page_numbers"][idx]
            if idx < len(field_data["page_numbers"])
            else field_data["page_numbers"][0]
        )

        # Add this field polygon to the page's collection
        if page_index not in polygons_by_page:
            polygons_by_page[page_index] = []

        polygons_by_page[page_index].append((field_name, matching_line))

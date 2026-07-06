from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class PartInput:
    internal_code: str
    name: str
    description: str
    category_id: int
    component_value: str
    component_unit: str
    model_name: str
    current_quantity: int
    minimum_quantity: int
    physical_location: str
    notes: str
    image_path: Optional[str] = None

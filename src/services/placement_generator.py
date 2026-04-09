from typing import Dict, Any, List

class PlacementInstructionsGenerator:
    """Generate detailed placement instructions for furniture items"""
    
    def __init__(self):
        self.placement_rules = {
            "nightstands": {
                "placement_type": "floor",
                "clearance_front": "24 inches",
                "clearance_sides": "6 inches",
                "positioning_text": "Place 6-12 inches from bed, aligned with mattress height"
            },
            "table_lamps": {
                "placement_type": "surface",
                "surface_clearance": "2 inches from edges",
                "overhead_clearance": "18 inches minimum",
                "positioning_text": "Center on surface, positioned toward back for stability"
            },
            "rugs": {
                "placement_type": "floor",
                "bed_extension_foot": "18-24 inches",
                "bed_extension_sides": "12 inches each",
                "positioning_text": "Extend beyond bed foot and sides, nightstand legs on edge"
            },
            "dressers": {
                "placement_type": "floor",
                "wall_clearance": "2-4 inches",
                "walkway_clearance": "36 inches",
                "positioning_text": "Against wall with adequate walkway space"
            }
        }
    
    def generate_placement_instructions(self, product: Dict[str, Any], 
                                      room_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate specific placement instructions for a product"""
        
        # Determine product type
        product_name = product['name'].lower()
        category = product.get('category', 'furniture')
        
        if 'nightstand' in product_name:
            rules = self.placement_rules['nightstands']
            location = self._determine_nightstand_location(room_analysis)
        elif 'lamp' in product_name and category == 'lighting':
            rules = self.placement_rules['table_lamps']
            location = "nightstand_top"
        elif 'rug' in product_name:
            rules = self.placement_rules['rugs']
            location = "bed_area"
        elif 'dresser' in product_name:
            rules = self.placement_rules['dressers']
            location = "wall_adjacent"
        else:
            rules = self._get_default_rules(category)
            location = self._determine_default_location(product, room_analysis)
        
        return {
            "placement_type": rules["placement_type"],
            "location": location,
            "positioning_text": rules["positioning_text"],
            "spatial_requirements": self._extract_spatial_requirements(rules),
            "ar_anchor_points": self._determine_anchor_points(rules["placement_type"]),
            "height_from_floor": self._calculate_height(product, rules),
            "orientation": self._determine_orientation(product, location),
            "dependency": self._check_dependencies(product, location)
        }
    
    def _determine_nightstand_location(self, room_analysis: Dict[str, Any]) -> str:
        """Determine optimal nightstand placement"""
        existing_furniture = room_analysis.get('existing_furniture', [])
        
        if any('nightstand' in item.lower() for item in existing_furniture):
            return "bedside_left"
        else:
            return "bedside_right"
    
    def _extract_spatial_requirements(self, rules: Dict[str, Any]) -> Dict[str, str]:
        """Extract spatial clearance requirements"""
        spatial_reqs = {}
        
        for key, value in rules.items():
            if 'clearance' in key or 'extension' in key:
                spatial_reqs[key] = value
        
        return spatial_reqs
    
    def _determine_anchor_points(self, placement_type: str) -> List[str]:
        """Determine AR anchor points"""
        if placement_type == "floor":
            return ["floor_contact", "wall_reference"]
        elif placement_type == "surface":
            return ["surface_contact"]
        elif placement_type == "wall":
            return ["wall_mount"]
        else:
            return ["floor_contact"]
    
    def _calculate_height(self, product: Dict[str, Any], rules: Dict[str, Any]) -> str:
        """Calculate height from floor"""
        placement_type = rules["placement_type"]
        
        if placement_type == "floor":
            return "0 inches"
        elif placement_type == "surface":
            return "surface_height"
        else:
            return "0 inches"
    
    def _determine_orientation(self, product: Dict[str, Any], location: str) -> str:
        """Determine item orientation"""
        if 'nightstand' in product['name'].lower():
            return "face_room_center"
        elif 'lamp' in product['name'].lower():
            return "angled_toward_bed"
        else:
            return "natural_orientation"
    
    def _check_dependencies(self, product: Dict[str, Any], location: str) -> str:
        """Check if item depends on another item"""
        if location == "nightstand_top":
            return "requires_nightstand"
        else:
            return None
    
    def _get_default_rules(self, category: str) -> Dict[str, Any]:
        """Get default placement rules for category"""
        return {
            "placement_type": "floor",
            "positioning_text": f"Place {category} according to room layout and traffic flow"
        }
    
    def _determine_default_location(self, product: Dict[str, Any], room_analysis: Dict[str, Any]) -> str:
        """Determine default location for product"""
        return "room_center"

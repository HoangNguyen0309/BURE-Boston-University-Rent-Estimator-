# bure/view.py

from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.urls import reverse
from bure_ml.prediction import predict_price
from django.http import JsonResponse



def get_location_amenities(request):
    location = request.GET.get("location", "")

    if location == "allston":
        amenity_keys = allston_amenities
    elif location == "back_bay":
        amenity_keys = back_bay_amenities
    elif location == "beacon_hill":
        amenity_keys = beacon_hill_amenities
    elif location == "south_boston":
        amenity_keys = south_boston_amenities
    else:
        amenity_keys = []

    amenities = [
        {
            "name": key,
            "label": AMENITY_LABELS.get(key, key),
        }
        for key in amenity_keys
    ]

    print("these are amenities ", amenities)

    return JsonResponse({"amenities": amenities})



# Create your views here.
class HomeView(TemplateView):
    '''A simple view to show the home page'''
    template_name = "bure/home.html"


class AboutView(TemplateView):
    '''A simple view to show the about page'''

    template_name = "bure/about.html"
    

class DataView(TemplateView):
    '''A simple view to show the data page'''

    template_name = "bure/data.html"



allston_features = [
    "baths",
    "beds",
    "sqft",
    "Amenity_Concierge",
    "Amenity_A_24_Hour_Access",
    "Amenity_Washer_Dryer",
    "Amenity_Fitness_Center",
    "Amenity_Double_Vanities",
    "Amenity_Conference_Rooms",
    "Amenity_Island_Kitchen",
    "Amenity_Walk_In_Closets",
    "Amenity_Package_Service",
    "Amenity_On_Site_Retail",
    "Amenity_Air_Conditioning",
    "Amenity_Public_Transportation",
    "Amenity_Bicycle_Storage",
    "Amenity_Elevator",
    "Amenity_EV_Charging",
    "Amenity_Recycling",
    "Amenity_Views",
]

beacon_hill_features = [
"sqft",
"beds",
"baths",
"Amenity_Air_Conditioning",
"Amenity_Balcony",
"Amenity_Trash_Pickup_Curbside",
"Amenity_Storage_Space",
"Amenity_Elevator",
"Amenity_Washer_Dryer",
"Amenity_Dishwasher",
"Amenity_Breakfast_Nook",
"Amenity_Dining_Room",
"Amenity_Gated",
"Amenity_High_Ceilings",
"Amenity_Floor_to_Ceiling_Windows",
"Amenity_Loft_Layout",
"Amenity_Smoke_Free",
"Amenity_Furnished_Units_Available",
"Amenity_High_Speed_Internet_Access",
"Amenity_Microwave",
"Amenity_Furnished"
]

back_bay_features = [
"sqft",
"baths",
"beds",
"Amenity_Washer_Dryer",
"Amenity_Air_Conditioning",
"Amenity_Balcony",
"Amenity_Elevator",
"Amenity_Concierge",
"Amenity_Conference_Rooms",
"Amenity_Sundeck",
"Amenity_Fitness_Center",
"Amenity_Stainless_Steel_Appliances",
"Amenity_Package_Service",
"Amenity_Lounge"
]

south_boston_features = [
"sqft",
"baths",
"beds",
"Amenity_Freezer",
"Amenity_Island_Kitchen",
"Amenity_Ice_Maker",
"Amenity_Stainless_Steel_Appliances",
"Amenity_Basement",
"Amenity_Disposal",
"Amenity_Balcony",
"Amenity_Controlled_Access",
"Amenity_Dishwasher",
"Amenity_Oven", 
"Amenity_Refrigerator",
"Amenity_Sprinkler_System",
"Amenity_Double_Pane_Windows",
"Amenity_High_Speed_Internet_Access",
"Amenity_Views",
"Amenity_Air_Conditioning",
"Amenity_Deck"
]


allston_amenities = [
    "Amenity_Concierge",
    "Amenity_A_24_Hour_Access",
    "Amenity_Washer_Dryer",
    "Amenity_Fitness_Center",
    "Amenity_Double_Vanities",
    "Amenity_Conference_Rooms",
    "Amenity_Island_Kitchen",
    "Amenity_Walk_In_Closets",
    "Amenity_Package_Service",
    "Amenity_On_Site_Retail",
    "Amenity_Air_Conditioning",
    "Amenity_Public_Transportation",
    "Amenity_Bicycle_Storage",
    "Amenity_Elevator",
    "Amenity_EV_Charging",
    "Amenity_Recycling",
    "Amenity_Views",
]

beacon_hill_amenities = [
    "Amenity_Air_Conditioning",
    "Amenity_Balcony",
    "Amenity_Trash_Pickup_Curbside",
    "Amenity_Storage_Space",
    "Amenity_Elevator",
    "Amenity_Washer_Dryer",
    "Amenity_Dishwasher",
    "Amenity_Breakfast_Nook",
    "Amenity_Dining_Room",
    "Amenity_Gated",
    "Amenity_High_Ceilings",
    "Amenity_Floor_to_Ceiling_Windows",
    "Amenity_Loft_Layout",
    "Amenity_Smoke_Free",
    "Amenity_Furnished_Units_Available",
    "Amenity_High_Speed_Internet_Access",
    "Amenity_Microwave",
    "Amenity_Furnished",
]

back_bay_amenities = [
    "Amenity_Washer_Dryer",
    "Amenity_Air_Conditioning",
    "Amenity_Balcony",
    "Amenity_Elevator",
    "Amenity_Concierge",
    "Amenity_Conference_Rooms",
    "Amenity_Sundeck",
    "Amenity_Fitness_Center",
    "Amenity_Stainless_Steel_Appliances",
    "Amenity_Package_Service",
    "Amenity_Lounge",
]

south_boston_amenities = [
    "Amenity_Freezer",
    "Amenity_Island_Kitchen",
    "Amenity_Ice_Maker",
    "Amenity_Stainless_Steel_Appliances",
    "Amenity_Basement",
    "Amenity_Disposal",
    "Amenity_Balcony",
    "Amenity_Controlled_Access",
    "Amenity_Dishwasher",
    "Amenity_Oven",
    "Amenity_Refrigerator",
    "Amenity_Sprinkler_System",
    "Amenity_Double_Pane_Windows",
    "Amenity_High_Speed_Internet_Access",
    "Amenity_Views",
    "Amenity_Air_Conditioning",
    "Amenity_Deck",
]

AMENITY_OPTIONS = [
    {"name": "Amenity_A_24_Hour_Access", "label": "24-Hour Access"},
    {"name": "Amenity_Air_Conditioning", "label": "Air Conditioning"},
    {"name": "Amenity_Balcony", "label": "Balcony"},
    {"name": "Amenity_Basement", "label": "Basement"},
    {"name": "Amenity_Bicycle_Storage", "label": "Bicycle Storage"},
    {"name": "Amenity_Breakfast_Nook", "label": "Breakfast Nook"},
    {"name": "Amenity_Concierge", "label": "Concierge"},
    {"name": "Amenity_Conference_Rooms", "label": "Conference Rooms"},
    {"name": "Amenity_Controlled_Access", "label": "Controlled Access"},
    {"name": "Amenity_Deck", "label": "Deck"},
    {"name": "Amenity_Dining_Room", "label": "Dining Room"},
    {"name": "Amenity_Dishwasher", "label": "Dishwasher"},
    {"name": "Amenity_Disposal", "label": "Garbage Disposal"},
    {"name": "Amenity_Double_Pane_Windows", "label": "Double-Pane Windows"},
    {"name": "Amenity_Double_Vanities", "label": "Double Vanities"},
    {"name": "Amenity_EV_Charging", "label": "EV Charging"},
    {"name": "Amenity_Elevator", "label": "Elevator"},
    {"name": "Amenity_Fitness_Center", "label": "Fitness Center"},
    {"name": "Amenity_Floor_to_Ceiling_Windows", "label": "Floor-to-Ceiling Windows"},
    {"name": "Amenity_Freezer", "label": "Freezer"},
    {"name": "Amenity_Furnished", "label": "Furnished"},
    {"name": "Amenity_Furnished_Units_Available", "label": "Furnished Units Available"},
    {"name": "Amenity_Gated", "label": "Gated Community"},
    {"name": "Amenity_High_Ceilings", "label": "High Ceilings"},
    {"name": "Amenity_High_Speed_Internet_Access", "label": "High-Speed Internet Access"},
    {"name": "Amenity_Ice_Maker", "label": "Ice Maker"},
    {"name": "Amenity_Island_Kitchen", "label": "Island Kitchen"},
    {"name": "Amenity_Loft_Layout", "label": "Loft Layout"},
    {"name": "Amenity_Lounge", "label": "Resident Lounge"},
    {"name": "Amenity_Microwave", "label": "Microwave"},
    {"name": "Amenity_On_Site_Retail", "label": "On-Site Retail"},
    {"name": "Amenity_Oven", "label": "Oven"},
    {"name": "Amenity_Package_Service", "label": "Package Service"},
    {"name": "Amenity_Public_Transportation", "label": "Close to Public Transportation"},
    {"name": "Amenity_Recycling", "label": "Recycling"},
    {"name": "Amenity_Refrigerator", "label": "Refrigerator"},
    {"name": "Amenity_Smoke_Free", "label": "Smoke-Free"},
    {"name": "Amenity_Sprinkler_System", "label": "Sprinkler System"},
    {"name": "Amenity_Stainless_Steel_Appliances", "label": "Stainless Steel Appliances"},
    {"name": "Amenity_Storage_Space", "label": "Storage Space"},
    {"name": "Amenity_Sundeck", "label": "Sundeck / Roof Deck"},
    {"name": "Amenity_Trash_Pickup_Curbside", "label": "Curbside Trash Pickup"},
    {"name": "Amenity_Views", "label": "View / City View"},
    {"name": "Amenity_Walk_In_Closets", "label": "Walk-In Closets"},
    {"name": "Amenity_Washer_Dryer", "label": "In-Unit Washer/Dryer"},
]

AMENITY_LABELS = {opt["name"]: opt["label"] for opt in AMENITY_OPTIONS}


LOCATION_LABELS  = {
    "allston": "Allston",
    "back_bay": "Back Bay",
    "beacon_hill": "Beacon Hill",
    "south_boston": "South Boston"
}


class RentEstimateSearch(TemplateView):


    template_name = "bure/search_results.html"
    form_template_name = "bure/search.html"

    def _get_selected_features(self, location):
        if location == "allston":
            return allston_features
        elif location == "back_bay":
            return back_bay_features
        elif location == "beacon_hill":
            return beacon_hill_features
        elif location == "south_boston":
            return south_boston_features
        else:
            return []
        
    def _get_amenities(self, location):
        if location == "allston":
            return allston_amenities
        elif location == "back_bay":
            return back_bay_amenities
        elif location == "beacon_hill":
            return beacon_hill_amenities
        elif location == "south_boston":
            return south_boston_amenities
        else:
            return []
    
    def _get_amenity_options(self, location):
        amenity_keys = self._get_amenities(location)   # e.g. allston_amenities
        return [
            {
                "name": key,
                "label": AMENITY_LABELS.get(key, key),
            }
            for key in amenity_keys
        ]


    def get(self, request, *args, **kwargs):
        selected_location = request.GET.get("location", "")
        print("This is the location: ", selected_location)

        SELECTED_FEATURES = self._get_selected_features(selected_location)
        amenity_options = self._get_amenity_options(selected_location)

        if "beds" not in request.GET or "baths" not in request.GET or "sqft" not in request.GET:
            
            print(amenity_options)
            context = {
                "selected_location": selected_location,
            }
            return render(request, self.form_template_name, context)


        def _to_float(val, default=0.0):
            try:
                return float(val)
            except (TypeError, ValueError):
                return default

        baths = _to_float(request.GET.get("baths"))
        beds = _to_float(request.GET.get("beds"))
        sqft = _to_float(request.GET.get("sqft"))

        feature_dict = {"baths": baths, "beds": beds, "sqft": sqft}
        basic_vals = {"baths": baths, "beds": beds, "sqft": sqft}

        for fname in SELECTED_FEATURES:
            if fname in ("baths", "beds", "sqft"):
                continue
            feature_dict[fname] = 1.0 if request.GET.get(fname) else 0.0

        enabled_amenities = [
            label
            for name, label in AMENITY_LABELS.items()
            if feature_dict.get(name)
            ]


        choices = {
            "allston": "allston_linear_model.joblib",
            "back_bay": "backbay_linear_model.joblib",
            "beacon_hill": "BeaconHill_linear_model.joblib",
            "south_boston": "southBoston_linear_model.joblib",
            "": "invalid",
        }

        location_model = choices.get(selected_location, "invalid")

        est_price = 0
        if location_model != "invalid":
            est_price = predict_price(feature_dict, location_model)

        context = {
            "est_price": round(est_price, 0),
            "selected_locations": [LOCATION_LABELS.get(selected_location, selected_location)],
            "basic_vals": basic_vals,
            "enabled_amenities": enabled_amenities,
        }

        return render(request, self.template_name, context)

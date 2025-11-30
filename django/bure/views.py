# bure/view.py


from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.urls import reverse
# from bure_ml.prediction import predict_price


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


SELECTED_FEATURES = [
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


AMENITY_LABELS = {
    "Amenity_Concierge": "Concierge",
    "Amenity_A_24_Hour_Access": "24-Hour Access",
    "Amenity_Washer_Dryer": "Washer/Dryer",
    "Amenity_Fitness_Center": "Fitness Center",
    "Amenity_Double_Vanities": "Double Vanities",
    "Amenity_Conference_RoomS": "Conference Rooms",
    "Amenity_Island_Kitchen": "Island Kitchen",
    "Amenity_Walk_In_Closets": "Walk-In Closets",
    "Amenity_Package_Service": "Package Service",
    "Amenity_On_Site_Retail": "On-Site Retail",
    "Amenity_Air_Conditioning": "Air Conditioning",
    "Amenity_Public_Transportation": "Public Transportation",
    "Amenity_Bicycle_Storage": "Bicycle Storage",
    "Amenity_Elevator": "Elevator",
    "Amenity_EV_Charging": "EV Charging",
    "Amenity_Recycling": "Recycling",
    "Amenity_Views": "Views",
}

class RentEstimateSearch(View):
    ''' 
        A view that shows search form if no feature inputs, 
        then uses the ml model to estimate rent
    '''

    template_name = "bure/search_results.html"
    form_template_name = "bure/search.html"

    def get(self,request, *args, **kwargs):
        '''shows form if user hasn't submitted any feature inputs'''

        if not any(name in request.GET for name in SELECTED_FEATURES):
            return render(request, self.form_template_name)
        

        def _to_float(val,default=0.0):
            try: 
                return float(val)
            except (TypeError, ValueError): 
                return default
            
        baths = _to_float(request.GET.get("baths"))
        beds = _to_float(request.GET.get("beds"))
        sqft = _to_float(request.GET.get("sqft"))

        feature_dict = { "baths": baths, "beds": beds, "sqft": sqft }
        basic_vals = { "baths": baths, "beds": beds, "sqft": sqft }


        est_price = baths+beds+sqft
        for fname in SELECTED_FEATURES:
            if fname in ("baths", "beds", "sqft"):
                continue
        
            feature_dict[fname] = 1.0 if request.GET.get(fname) else 0.0
            est_price += 1 if request.GET.get(fname) else 0.0


        # est_price = predict_price(feature_dict)

        enabled_amenities = [AMENITY_LABELS[key] for key in AMENITY_LABELS.keys() if feature_dict.get(key)]

        context = {
            "est_price": round(est_price, 0),
            "basic_vals": basic_vals,
            "enabled_amenities": enabled_amenities,
        }

        return render(request, self.template_name, context)
        

        
    
    

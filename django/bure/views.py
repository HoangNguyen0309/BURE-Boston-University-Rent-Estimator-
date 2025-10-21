# bure/view.py


from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse

# Create your views here.

def HomeView(request): # defined as a simple request view for now, but we can change later depending on what we want to do - iwc
    '''A simple view to show the home page'''

    template_name = "bure/home.html" # location of html template - iwc
    context = {} # any other variables or data we may need - iwc

    return render(request, template_name, context) # renders the html

def AboutView(request): # defined as a simple request view for now, but we can change later depending on what we want to do - iwc
    '''A simple view to show the home page'''

    template_name = "bure/about.html" # location of html template - iwc
    context = {} # any other variables or data we may need - iwc

    return render(request, template_name, context) # renders the html

    
def DataView(request): # defined as a simple request view for now, but we can change later depending on what we want to do - iwc
    '''A simple view to show the home page'''

    template_name = "bure/data.html" # location of html template - iwc
    context = {} # any other variables or data we may need - iwc

    return render(request, template_name, context) # renders the html

    
# BURE-Boston-University-Rent-Estimator-

CS506 Project Proposal
BURE: Boston University Rent Estimator

Github Repo: https://github.com/HoangNguyen0309/BURE-Boston-University-Rent-Estimator-

Members:

Ian Campbell 		- iwc3@bu.edu
Hoang Nguyen 	- hnguy@bu.edu 
































Purpose:
As many students progress in their college education, they begin seeking opportunities to become more independent individuals. One of the most common ways this happens is through moving into off-campus housing, which provides students with valuable lessons in responsibility, budgeting, and decision making. Every year, beginning around February, thousands of students begin the search for housing that best meets their needs. Comfort, proximity to campus, and most importantly to the majority, affordability are at the top of their priorities.
To address this annual challenge, we propose the development of a web-based application called BURE, the Boston University Rent Estimator. The goal of this platform is to simplify the off-campus housing search process by giving students a centralized, accessible, and reliable tool. Students will be able to input preferences such as location, price range, amenities, and number of roommates to view tailored housing options that fit their needs.
Through BURE, we aim to close the gap in information that often forces students into time-consuming searches and uncertain decisions. Not only will this tool help students compare housing options more effectively, but it will also highlight how certain preferences impact overall rent, allowing for smarter financial planning. 
BURE arises from the clear need among students for a more efficient and transparent way to search for housing. Current solutions are often fragmented, outdated, or too generalized to address the specific needs of a student population. By leveraging live rental data and user friendly design, our application will save students time, reduce stress, and ultimately empower them to make confident, well informed decisions about where to live during their college years.


Functional Requirements:

Be able to predict the price of rental properties given the variables: Square feet, number of bedrooms, number of bathrooms, location, . . . (to be added or removed later)
Maintain an updated dataset
Provide evaluation metrics to measure accuracy





Design Outline
High-Level Overview

Client
Provides the user interface to view rent estimates.
Communicates with the server via RESTful HTTP requests

Server
A Flask server in Python handles API requests from the client and processes them.
It uses linear regression algorithms (to be changed later if necessary) to estimate rent based on user inputs and database data.
Manages communication with the database and external APIs

Database
Stores housing data which is used by the server to train the linear regression model.























Sequence Diagram:

This diagram depicts the sequence of events that will occur when a user wishes to estimate the rent for their desired features. The user first enters the configuration of features that they want. When the user clicks the ‘estimate/calculate’ button, the server will update the database to save the user’s latest chosen configuration. Then it will request data from the configuration which will be inputted into the ML model to generate an output of the estimate of the rent price which would then be displayed to the user in the appropriate format.








Machine Learning Algorithms:

Linear regression:

Pros:

Simplicity & Interpretability: Easy to implement, fast to train, and coefficients show how much each feature contributes to price. 
Scalability: Works well with large datasets, and predictions are very fast. 
Good with linear relationships: If features (square feet, bedrooms, etc.) have an approximately linear effect on rent, LR captures it well.

Cons:
Feature engineering required: Needs transformations to handle non-linear effects (distance to a campus center or distance to city center).


Limited flexibility: Cannot capture complex neighborhood effects unless explicitly modeled.

K Nearest Neighbors (KNN):


Pros:
Flexible and non-parametric: Makes no assumptions about the underlying data distribution, so it can capture complex, non-linear relationships in predictions regarding rent.
Intuitive & simple: Easy to understand that similar inputs should yield similar results (similar houses have similar rents)
Adaptability: Naturally adapts to patterns in the data (e.g., neighborhood clusters)
Cons:
Scalability issues: Prediction requires comparing to all data sets, so it's inefficient and slow for larger datasets.
Feature sensitivity: Results depend heavily on feature scaling
Choice of k matters: too small a k value will yield noisy predictions, while too large will be more generalized.
Too many attributes: Performance worsens as too many attributes that may be irrelevant get added.

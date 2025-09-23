# CS506 Project Proposal  
## BURE: Boston University Rent Estimator  

**Github Repo:** [BURE-Boston-University-Rent-Estimator](https://github.com/HoangNguyen0309/BURE-Boston-University-Rent-Estimator-)  

**Members:**  
Ian Campbell — iwc3@bu.edu <br>  
Hoang Nguyen — hnguy@bu.edu  

---

## Purpose  
As many students progress in their college education, they begin seeking opportunities to become more independent individuals. One of the most common ways this happens is through moving into off-campus housing, which provides students with valuable lessons in responsibility, budgeting, and decision making. Every year, beginning around February, thousands of students begin the search for housing that best meets their needs. Comfort, proximity to campus, and most importantly to the majority, affordability are at the top of their priorities.  

To address this annual challenge, we propose the development of a web-based application called **BURE**, the Boston University Rent Estimator. The goal of this platform is to simplify the off-campus housing search process by giving students a centralized, accessible, and reliable tool. Students will be able to input preferences such as location, price range, amenities, and number of roommates to view tailored housing options that fit their needs.  

Through BURE, we aim to close the gap in information that often forces students into time-consuming searches and uncertain decisions. Not only will this tool help students compare housing options more effectively, but it will also highlight how certain preferences impact overall rent, allowing for smarter financial planning.  

BURE arises from the clear need among students for a more efficient and transparent way to search for housing. Current solutions are often fragmented, outdated, or too generalized to address the specific needs of a student population. By leveraging live rental data and user-friendly design, our application will save students time, reduce stress, and ultimately empower them to make confident, well-informed decisions about where to live during their college years.  

---

## Functional Requirements  
- Be able to predict the price of rental properties given the variables: square feet, number of bedrooms, number of bathrooms, location, etc. (to be added or removed later) <br>  
- Maintain an updated dataset <br>  
- Provide evaluation metrics to measure accuracy <br>  

---

## Design Outline  

### High-Level Overview  
**Client** <br>
- Provides the user interface to view rent estimates. <br>
- Communicates with the server via RESTful HTTP requests. <br>

**Server** <br>
- A Flask server in Python handles API requests from the client and processes them. <br>
- Uses linear regression algorithms (to be changed later if necessary) to estimate rent based on user inputs and database data. <br>
- Manages communication with the database and external APIs. <br>

**Database** <br>
- Stores housing data which is used by the server to train the linear regression model. <br>  

---

## Sequence Diagram  
This diagram depicts the sequence of events that will occur when a user wishes to estimate the rent for their desired features.  

1. The user enters the configuration of features they want. <br>
2. When the user clicks the **estimate/calculate** button, the server updates the database to save the user’s chosen configuration. <br>
3. The server requests data from the configuration which is inputted into the ML model. <br>
4. The model generates an estimate of the rent price. <br>
5. The server displays the result to the user in the appropriate format. <br>  

---

## Machine Learning Algorithms  

### Linear Regression  
**Pros:**  
- Simplicity & Interpretability: Easy to implement, fast to train, and coefficients show how much each feature contributes to price. <br>
- Scalability: Works well with large datasets, and predictions are very fast. <br>
- Good with linear relationships: If features (square feet, bedrooms, etc.) have an approximately linear effect on rent, LR captures it well. <br>

**Cons:**  
- Feature engineering required: Needs transformations to handle non-linear effects (e.g., distance to a campus center or city center). <br>
- Limited flexibility: Cannot capture complex neighborhood effects unless explicitly modeled. <br>  

---

### K Nearest Neighbors (KNN)  
**Pros:**  
- Flexible and non-parametric: Makes no assumptions about the underlying data distribution, so it can capture complex, non-linear relationships in rent predictions. <br>
- Intuitive & simple: Similar inputs → similar results (similar houses have similar rents). <br>
- Adaptability: Naturally adapts to patterns in the data (e.g., neighborhood clusters). <br>

**Cons:**  
- Scalability issues: Prediction requires comparing to all datasets, so it’s inefficient and slow for larger datasets. <br>
- Feature sensitivity: Results depend heavily on feature scaling. <br>
- Choice of k matters: Too small → noisy predictions; too large → overly generalized. <br>
- High dimensionality: Performance worsens as irrelevant attributes get added. <br>  

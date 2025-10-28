**Midterm Report -- Boston University Rent Estimator**
======================================================


**1\. Introduction**
--------------------

The goal of this project is to predict apartment rental prices across Boston using data scraped from **Apartments.com**.\
Our motivation is to identify which features --- such as size, number of rooms, and amenities --- most influence rent levels, and whether **neighborhood-specific models** improve prediction accuracy.

We selected **Apartments.com** as our primary data source because it provides a large number of listings with structured and detailed attributes. Using a custom Python scraper built with **BeautifulSoup**, we extracted the following fields for each property:

-   Price

-   Number of bedrooms and bathrooms

-   Square footage

-   Address and listing URL

-   100+ one-hot encoded amenity features (e.g., *Washer/Dryer*, *Fitness Center*, *Concierge Service*, *Air Conditioning*)

So far, we've collected approximately **2,000 listings across the greater Boston area**, plus an additional **3,000 listings specifically focused on neighborhoods such as Allston and Fenway**.\
These subsets allow us to analyze both **citywide patterns** and **localized neighborhood dynamics**.

* * * * *

**2\. Data Processing**
-----------------------

The raw HTML data from Apartments.com was parsed and transformed into structured datasets using Python.\
Below is an overview of the processing pipeline:

### **2.1 Data Extraction**

-   Parsed property cards with **BeautifulSoup**, storing key attributes in CSV and XLSX formats.

-   Extracted `price`, `beds`, `baths`, `sqft`, `address`, and all available amenities from each listing.

### **2.2 Data Cleaning and Normalization**

-   Converted text-based numeric values (e.g., "1 Bed", "750 Sq Ft") into integers or floats.

-   Removed symbols such as `$`, `,`, and text labels like "sqft" or "beds".

-   Used `pandas.to_numeric(errors='coerce')` to handle type conversion safely.

-   Dropped rows with missing or invalid values **only for modeling**, not for EDA.

### **2.3 Feature Engineering**

-   Created **one-hot encoded columns** for every amenity tag, resulting in roughly **160 total columns**.

-   Standardized column names and types across datasets to ensure smooth merging.

After cleaning, the dataset is consistent, numerically encoded, and ready for visualization and modeling.

* * * * *

**3\. Preliminary Visualizations**
----------------------------------

### **3.1 Price Distribution**

A histogram of rental prices shows a **right-skewed distribution** --- most apartments rent between **$2,000 and $5,000**, with a smaller number of luxury listings exceeding $10,000.\
This skew indicates significant variation across neighborhoods and property types.

* * * * *

### **3.2 Price vs Key Numeric Features**

Scatter plots for **price vs. square footage**, **beds**, and **baths** show strong positive trends.\
Each additional bedroom, bathroom, or square foot generally increases rent, supporting the idea that **size and room count** are dominant factors.

* * * * *

### **3.3 Amenity Impact and Correlation Analysis (PCC Values)**

To identify which features most influence price beyond structural ones, we calculated the **Pearson Correlation Coefficient (PCC)** between `price` and every numeric column --- totaling approximately **160 features**, mostly representing binary amenities.

#### **Computation Details**

-   PCC quantifies linear association, ranging from **-1 (perfect negative)** to **+1 (perfect positive)**.

-   Used Pandas `.corr(method="pearson")` to compute a **160×160 correlation matrix**.

-   The results were visualized as a **heatmap**, highlighting feature clusters.

#### **Findings**

-   **Top positive correlations** with `price` (structural):

    -   `baths` → **+0.60**

    -   `beds` → **+0.55**

    -   `sqft` → **+0.44**

-   **Top correlated amenities**:

    -   `Amenity_Concierge` → **+0.31**

    -   `Amenity_24_Hour_Access` → **+0.23**

    -   `Amenity_Washer_Dryer` → **+0.22**

    -   `Amenity_Fitness_Center` → **+0.22**

    -   `Amenity_Double_Vanities` → **+0.21**

    -   `Amenity_Conference_Rooms` → **+0.20**

    -   `Amenity_Island_Kitchen` → **+0.20**

These correlations guided feature selection for our baseline model.

#### **Low-Impact Features**

Many amenities such as *Clubhouse*, *Pet Park*, and *High Speed Internet* had near-zero correlation, implying minimal direct price influence.

#### **Visualization**

A **PCC heatmap** visualized how certain amenities group together --- for example, luxury-related features (Concierge, Double Vanities, Package Service) tend to correlate with each other, indicating **multicollinearity** among higher-end properties.

* * * * *

**4\. Data Modeling Methods**
-----------------------------

### **4.1 Feature Selection Using PCC**

The correlation analysis helped identify the most relevant predictors for modeling.\
We selected the **top 15 features with the highest absolute correlation** to `price`, which significantly improved model interpretability and computational efficiency by excluding redundant or low-impact variables.

* * * * *

### **4.2 Linear Regression (Baseline Model)**

We used **Linear Regression** as our baseline to predict apartment prices.\
The model used 13--15 features (depending on neighborhood availability), including both **structural** and **amenity-based** variables.

#### **Model Configuration**

-   Train-test split: **80/20**

-   Repeated **100 random splits** for robust averaging

-   Metrics: **R²** (explained variance) and **MAE** (Mean Absolute Error)

#### **Results (Citywide Model)**

| Metric | Average | Std. Dev | Min | Max |
| --- | --- | --- | --- | --- |
| **R²** | 0.50 | 0.19 | -0.70 | 0.66 |
| **MAE ($)** | 603 | --- | --- | --- |

The citywide model explains roughly **50% of the variance** in rental prices --- a solid baseline given the data's diversity and scale.

* * * * *

### **4.3 Area-Specific Modeling (Fenway Subset)**

To explore the impact of geographic focus, we trained a second model using only **Fenway listings** (~900 rows).

| Metric | Citywide | Fenway |
| --- | --- | --- |
| **Avg R²** | 0.49 | **0.84** |
| **Std R²** | 0.21 | 0.02 |
| **Avg MAE ($)** | 607 | **358** |

#### **Interpretation**

-   Fenway's model shows a **+0.35 R² improvement** and **$250 lower MAE**, demonstrating that **localized models** capture market-specific relationships more effectively.

-   This suggests the Boston rental market is **heterogeneous**, and neighborhood segmentation significantly boosts predictive performance.

* * * * *

**5\. Preliminary Results and Findings**
----------------------------------------

1.  **Linear relationships confirmed:** Rent increases proportionally with square footage, bedrooms, and bathrooms.

2.  **Amenity influence:** Premium features like *Washer/Dryer* and *Fitness Center* are consistently associated with higher rents.

3.  **Modeling performance:**

    -   Citywide model → R² ≈ 0.50 (moderate accuracy).

    -   Fenway model → R² ≈ 0.84 (high accuracy).

4.  **Key insight:** Price prediction accuracy improves dramatically when modeling neighborhoods individually rather than treating Boston as a single market.

* * * * *

**6\. Next Steps**
------------------

-   **Neighborhood Segmentation:** Develop per-area models and combine them into a hierarchical ensemble for better generalization.

-   **Model Validation:** Apply k-fold cross-validation and test cross-neighborhood transferability.

* * * * *

**7\. Conclusion**
------------------

Our preliminary results show that even a simple **linear regression model** can explain a significant portion of rental price variation in Boston.\
However, the analysis also reveals that **location matters greatly** --- Fenway-specific models outperform citywide ones by a wide margin.

By leveraging **PCC-based feature selection**, **localized modeling**, and future spatial features, our project aims to build a highly interpretable and accurate **Boston Rent Estimator** that reflects real-world housing dynamics.
















































# CS506 Project Proposal  
## BURE: Boston University Rent Estimator  

**Github Repo:** [BURE-Boston-University-Rent-Estimator](https://github.com/HoangNguyen0309/BURE-Boston-University-Rent-Estimator-)  

**Members:**  
Ian Campbell — iwc3@bu.edu <br>  
Hoang Nguyen — hnguy@bu.edu  

---

## Dataset Description

<details>
<summary><b>2.1 Data Collection</b></summary>

Data was collected through web scraping using automated Python scripts built with **Selenium** and **BeautifulSoup**.  
Each property page was parsed to extract both **floorplan-level** and **amenity-level** information.

</details>

<details>
<summary><b>2.2 Dataset Structure</b></summary>

The data is saved as:   apartments_boston_minimal_amenities.csv


Each row represents one apartment unit or floorplan, with the following columns:

| Feature | Description |
|----------|-------------|
| `listing_url` | URL of the apartment listing |
| `address` | Property location |
| `price` | Monthly rent in USD |
| `beds`, `baths` | Number of bedrooms and bathrooms |
| `sqft` | Apartment area in square feet |
| `Amenity_*` | Binary (0/1) columns for each amenity, e.g. `Amenity_Pool`, `Amenity_Gym`, `Amenity_Stainless_Steel_Appliances` |

This dataset serves as the foundation for both **exploratory data analysis (EDA)** and **predictive modeling**.

</details>

---

## Methodology

<details>
<b>Data Preprocessing</b>

- Missing values were handled by dropping incomplete rows or imputing reasonable estimates where appropriate.  
- Amenities were represented using **one-hot encoding**, converting each amenity into a binary column.  
- The dataset was randomly split into **training (80%)** and **testing (20%)** sets for model evaluation.

</details>

## Exploratory Data Analysis (EDA)

<details>
<summary><b>4.1 Correlation Analysis</b></summary>

A **Pearson Correlation Coefficient (PCC)** heatmap was generated to identify linear relationships among numeric variables such as price, square footage, and number of bedrooms.

This visualization highlights which attributes most strongly correlate with rental price.

</details>
<details> <summary><b>4.2 Price Relationship Plots</b></summary>

Scatter plots were generated to visualize price trends across key attributes:

Price vs. Square Footage

Price vs. Number of Bedrooms

Price vs. Number of Bathrooms

These plots provide insight into how each numerical feature individually impacts rent values.

plt.scatter(df['sqft'], df['price'])
plt.title('Price vs. Square Footage')

</details>
<details> <summary><b>4.3 Boxplots for Amenity Features</b></summary>

Boxplots were used to compare median and distribution of prices between apartments with and without specific amenities.


</details>

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

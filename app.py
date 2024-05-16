import streamlit as st
import plotly.express as px
from policyengine_us import Simulation
from policyengine_core.charts import format_fig
from policyengine_us.variables.household.demographic.geographic.state_code import (
    StateCode,
)
from policyengine_us.variables.household.income.household.household_benefits import household_benefits as HouseholdBenefits
from policyengine_us.variables.household.income.household.household_tax_before_refundable_credits import household_tax_before_refundable_credits as HouseholdTaxBeforeRefundableCredits
from policyengine_us.variables.household.income.household.household_refundable_tax_credits import household_refundable_tax_credits as HouseholdRefundableTaxCredits
import numpy as np
import pandas as pd
import hashlib
# Create a function to get net income for the household, married or separate.
def get_heatmap_values(state_code, children_ages, tax_unit):
    # Tuple of net income for separate and married.
    net_income_married = get_marital_values(
        state_code, True, children_ages, tax_unit
    )
    net_income_separate = get_marital_values(state_code,False,children_ages, tax_unit)
    final_separate = []
    for val in net_income_separate:
        temp_array = []
        for val2 in net_income_separate:
            temp_array.append(val + val2)
        final_separate.append(temp_array)

    return net_income_married, final_separate

DEFAULT_AGE = 40
YEAR = "2024"
HEAT_MAP_OUTPUTS = {
    "Income": ["household_net_income","employment_income"],
    "Benefits":["household_benefits", "employment_income"],
    "Taxes": ["household_tax_before_refundable_credits","employment_income"] , 
    "Credits": ["household_refundable_tax_credits", "employment_income"]
}

def get_programs(state_code, head_employment_income, spouse_employment_income=None, children_ages = {}):
    # Start by adding the single head.
    situation = {
        "people": {
            "you": {
                "age": {YEAR: DEFAULT_AGE},
                "employment_income": {YEAR: head_employment_income},
            }
        }
    }
    members = ["you"]
    if spouse_employment_income is not None:
        situation["people"]["your partner"] = {
            "age": {YEAR: DEFAULT_AGE},
            "employment_income": {YEAR: spouse_employment_income},
        }
        # Add your partner to members list.
        members.append("your partner")
    for key, value in children_ages.items():
        situation["people"][f"child {key}"] = {
            "age": {YEAR: value},
            "employment_income": {YEAR: 0}
        }
        # Add child to members list.
        members.append(f"child {key}")
    # Create all parent entities.
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members, "state_name": {YEAR: state_code}}
    }
    simulation = Simulation(situation=situation)

    household_net_income = int(simulation.calculate("household_net_income", YEAR))
    household_benefits = int(simulation.calculate("household_benefits", YEAR))
    household_refundable_tax_credits = int(simulation.calculate("household_refundable_tax_credits", int(YEAR)))
    household_tax_before_refundable_credits = int(simulation.calculate("household_tax_before_refundable_credits", int(YEAR)))
    
    # benefits breakdown
    benefits_categories = HouseholdBenefits.adds
    benefits_dic ={}
    for benefit in benefits_categories:
        try:
            benefit_amount = int(simulation.calculate(benefit, YEAR)[0])
        except ValueError:
            benefit_amount = 0
            
        benefits_dic[benefit]=benefit_amount
    
    # tax before refundable credits breakdown
    # tax_before_refundable_credits = HouseholdTaxBeforeRefundableCredits.adds
    tax_adds = [
        "employee_payroll_tax",
        "self_employment_tax",
        "income_tax_before_refundable_credits",
        "flat_tax",
        "household_state_tax_before_refundable_credits",
    ]
    
    tax_bf_r_credits_dic = {}
    for tax in tax_adds:
        try:
            tax_amount = int(simulation.calculate(tax, YEAR)[0])
        except ValueError:
            tax_amount = 0
            
        tax_bf_r_credits_dic[tax]=tax_amount
    
    # refundable tax breakdown
    # refundable_tax_categories = HouseholdRefundableTaxCredits.adds
    refundable_tax_categories = [
        "income_tax_refundable_credits",
        "household_refundable_state_tax_credits",
    ]
    refundable_tax_dic ={}
    for refundable_tax in refundable_tax_categories:
        try:
            refundable_tax_amount = int(simulation.calculate(refundable_tax, YEAR)[0])
        except ValueError:
            refundable_tax_amount = 0
            
        refundable_tax_dic[refundable_tax]=refundable_tax_amount
    
    print(refundable_tax_dic)
    

    return [household_net_income ,household_benefits ,household_refundable_tax_credits,household_tax_before_refundable_credits, benefits_dic, tax_bf_r_credits_dic, refundable_tax_dic]
   
def get_categorized_programs(state_code, head_employment_income, spouse_employment_income, children_ages):
    programs_married = get_programs(state_code, head_employment_income, spouse_employment_income, children_ages)
    programs_head = get_programs(state_code, head_employment_income, None, children_ages)
    programs_spouse = get_programs(state_code, spouse_employment_income, None, {})  # Pass an empty dictionary for children_ages
    return [programs_married, programs_head, programs_spouse]

# Create a function to get net income for household
def get_marital_values(state_code, spouse, children_ages, tax_unit):
    # Start by adding the single head.
    situation = {
        "people": {
            "you": {
                "age": {YEAR: DEFAULT_AGE},
            }
        }
    }
    members = ["you"]
    if spouse:
        situation["people"]["your partner"] = {
            "age": {YEAR: DEFAULT_AGE},
        }
        # Add your partner to members list.
        members.append("your partner")
    for key, value in children_ages.items():
        situation["people"][f"child {key}"] = {
            "age": {YEAR: value},
        }
        # Add child to members list.
        members.append(f"child {key}")
    # Create all parent entities.
    situation["families"] = {"your family": {"members": members}}
    situation["marital_units"] = {"your marital unit": {"members": members}}
    situation["tax_units"] = {"your tax unit": {"members": members}}
    situation["spm_units"] = {"your spm_unit": {"members": members}}
    situation["households"] = {
        "your household": {"members": members, "state_name": {YEAR: state_code}}
    }
    if spouse:
        situation["axes"]= [
            [
            {
                "name": HEAT_MAP_OUTPUTS[tax_unit][1],
                "count": 8,
                "index": 0,
                "min": 10000,
                "max": 80000,
                "period": YEAR
            }
            ],
            [
            {
                "name": HEAT_MAP_OUTPUTS[tax_unit][1],
                "count": 8,
                "index": 1,
                "min": 10000,
                "max": 80000,
                "period": YEAR
            }
            ]
        ]
    else:
         situation["axes"]= [
            [
            {
                "name": HEAT_MAP_OUTPUTS[tax_unit][1],
                "count": 8,
                "min": 10000,
                "max": 80000,
                "period": YEAR
            }
          
            ]
           
        ]

  

    simulation = Simulation(situation=situation)
    return simulation.calculate(HEAT_MAP_OUTPUTS[tax_unit][0], int(YEAR))

#Streamlit heading and description
header = st.header("Marriage Incentive Calculator")  
header_description = st.write("This application evaluates marriage penalties and bonuses of couples, based on state and individual employment income")
repo_link = st.markdown("This application utilizes <a href='https://github.com/PolicyEngine/us-marriage-incentive'>the policyengine API</a>", unsafe_allow_html=True)  


# Create Streamlit inputs for state code, head income, and spouse income.
statecodes = [s.value for s in StateCode]
us_territories = {
    "GU" : "Guam", 
    "MP" : "Northern Mariana Islands",
    "PW" : "Palau",
    "PR" : "Puerto Rico",
    "VI" : "Virgin Islands",
    "AA" :"Armed Forces Americas (Except Canada)",
    "AE" : "Armed Forces Africa/Canada/Europe/Middle East",
    "AP" : "Armed Forces Pacific"
}
options = [value for value in statecodes if value not in us_territories]
state_code = st.selectbox("State Code", options)
head_employment_income = st.number_input("Head Employment Income", step=10000, value=0)
spouse_employment_income = st.number_input("Spouse Employment Income", step=10000, value=0)
num_children = st.number_input("Number of Children", 0)
children_ages = {}
for num in range(1,num_children + 1):
    children_ages[num] = st.number_input(f"Child {num} Age", 0)
#Heatmap values type 
#heatmap_button = st.button("Generate Heatmap")
tax_unit_options= ["Income","Benefits", "Taxes", "Credits" ]
heatmap_tax_unit = st.selectbox("Heat Map Variable", tax_unit_options)

#submit button
submit = st.button("Calculate")

#submit.click()
# Get net incomes.

if submit:  
    programs = get_categorized_programs(state_code, head_employment_income, spouse_employment_income,  children_ages)
    
    # benefits breakdowns
    benefits_categories = programs[0][-3].keys()
    benefits_married = programs[0][-3].values()
    benefits_head = programs[1][-3].values()
    benefits_spouse = programs[2][-3].values()
    benefits_separate = [x + y for x, y in zip(benefits_head, benefits_spouse)]
    benefits_delta = [x - y for x, y in zip(benefits_married, benefits_separate)]
    benefits_delta_percent = [(x - y) / x if x != 0 else 0 for x, y in zip(benefits_married, benefits_separate)]

    # format benefits breakdowns
    formatted_benefits_married = list(map(lambda x: "${:,}".format(round(x)), benefits_married))
    formatted_benefits_separate = list(map(lambda x: "${:,}".format(round(x)), benefits_separate))
    formatted_benefits_delta = list(map(lambda x: "${:,}".format(round(x)), benefits_delta))
    formatted_benefits_delta_percent = list(map(lambda x: "{:.1%}".format(x), benefits_delta_percent))

    # tax bf refundable credits breakdowns
    tax_categories = programs[0][-2].keys()
    tax_married = programs[0][-2].values()
    tax_head = programs[1][-2].values()
    tax_spouse = programs[2][-2].values()
    tax_separate = [x + y for x, y in zip(tax_head, tax_spouse)]
    tax_delta = [x - y for x, y in zip(tax_married, tax_separate)]
    tax_delta_percent = [(x - y) / x if x != 0 else 0 for x, y in zip(tax_married, tax_separate)]

    # format tax breakdowns
    formatted_tax_married = list(map(lambda x: "${:,}".format(round(x)), tax_married))
    formatted_tax_separate = list(map(lambda x: "${:,}".format(round(x)), tax_separate))
    formatted_tax_delta = list(map(lambda x: "${:,}".format(round(x)), tax_delta))
    formatted_tax_delta_percent = list(map(lambda x: "{:.1%}".format(x), tax_delta_percent))

    # refundable tax credits breakdowns
    refundable_tax_categories = programs[0][-1].keys()
    refundable_tax_married = programs[0][-1].values()
    refundable_tax_head = programs[1][-1].values()
    refundable_tax_spouse = programs[2][-1].values()
    refundable_tax_separate = [x + y for x, y in zip(refundable_tax_head, refundable_tax_spouse)]
    refundable_tax_delta = [x - y for x, y in zip(refundable_tax_married, refundable_tax_separate)]
    refundable_tax_delta_percent = [(x - y) / x if x != 0 else 0 for x, y in zip(refundable_tax_married, refundable_tax_separate)]

    # format refundable tax credits breakdowns
    formatted_refundable_tax_married = list(map(lambda x: "${:,}".format(round(x)), refundable_tax_married))
    formatted_refundable_tax_separate = list(map(lambda x: "${:,}".format(round(x)), refundable_tax_separate))
    formatted_refundable_tax_delta = list(map(lambda x: "${:,}".format(round(x)), refundable_tax_delta))
    formatted_refundable_tax_delta_percent = list(map(lambda x: "{:.1%}".format(x), refundable_tax_delta_percent))

    # married programs
    married_programs = programs[0][:-3] # we exclude the last element which is the dictionary of benefits breakdown 
    formatted_married_programs = list(map(lambda x: "${:,}".format(round(x)), married_programs))
    
    # separate programs
    head_separate = programs[1][:-3] # we exclude the last element which is the dictionary of benefits breakdown 
    spouse_separate = programs[2][:-3] # we exclude the last element which is the dictionary of benefits breakdown 
    separate = [x + y for x, y in zip(head_separate, spouse_separate)]
    formatted_separate = list(map(lambda x: "${:,}".format(round(x)), separate))
    
    # delta
    delta = [x - y for x, y in zip(married_programs, separate)]
    delta_percent = [(x - y) / x if x != 0 and x != 0 else 0 for x, y in zip(married_programs, separate)]
    formatted_delta = list(map(lambda x: "${:,}".format(round(x)), delta))
    formatted_delta_percent = list(map(lambda x: "{:.1%}".format(x), delta_percent))

    programs = ["Net Income", "Benefits", "Refundable tax credits", "Taxes before refundable credits"]


    # Determine marriage penalty or bonus, and extent in dollars and percentage.
    marriage_bonus = married_programs[0] - separate[0]
    marriage_bonus_percent = marriage_bonus / married_programs[0]
    def summarize_marriage_bonus(marriage_bonus):
        # Create a string to summarize the marriage bonus or penalty.
        return (
            f"If you file separately, your combined net income will be ${abs(marriage_bonus):,.2f} "
            f"{'less' if marriage_bonus > 0 else 'more'} "
            f"({abs(marriage_bonus_percent):.1%}) than if you file together."
        )


    if marriage_bonus > 0:
        st.write("You face a marriage BONUS.")
    elif marriage_bonus < 0:
        st.write("You face a marriage PENALTY.")
    else:
        st.write("You face no marriage penalty or bonus.")

    st.write(summarize_marriage_bonus(marriage_bonus))

    # Formatting for visual display
    # Sample data for main table
    table_data = {
        'Program': programs,
        'Not Married': formatted_separate,
        'Married': formatted_married_programs,
        'Delta': formatted_delta,
        'Delta Percentage': formatted_delta_percent
    }

    # Benefits breakdown table
    benefits_table = {
        'Program': benefits_categories,
        'Not Married': formatted_benefits_separate,
        'Married': formatted_benefits_married,
        'Delta': formatted_benefits_delta,
        'Delta Percentage': formatted_benefits_delta_percent
        
    }
    # filter benefits to keep only the non-zero values
    benefits_df = pd.DataFrame(benefits_table)
    filtered_benefits_df = benefits_df[(benefits_df['Not Married'] != "$0") | (benefits_df['Married'] != "$0")]

    # Tax Before Refundable Credits breakdown table
    tax_bf_refundable_credits_table = {
        'Program': tax_categories,
        'Not Married': formatted_tax_separate,
        'Married': formatted_tax_married,
        'Delta': formatted_tax_delta,
        'Delta Percentage': formatted_tax_delta_percent
        
    }
    # filter tax before refundable credits to keep only the non-zero values
    tax_before_refundable_credits_df = pd.DataFrame(tax_bf_refundable_credits_table)
    filtered_tax_df = tax_before_refundable_credits_df[(tax_before_refundable_credits_df['Not Married'] != "$0") | (tax_before_refundable_credits_df['Married'] != "$0")]

    # Refundable Tax Credits breakdown table
    refundable_tax_table = {
        'Program': refundable_tax_categories,
        'Not Married': formatted_refundable_tax_separate,
        'Married': formatted_refundable_tax_married,
        'Delta': formatted_refundable_tax_delta,
        'Delta Percentage': formatted_refundable_tax_delta_percent
        
    }
    # filter benefits to keep only the non-zero values
    refundable_tax_df = pd.DataFrame(refundable_tax_table)
    filtered_refundable_tax_df = refundable_tax_df[(refundable_tax_df['Not Married'] != "$0") | (refundable_tax_df['Married'] != "$0")]
    
    # Display the tables in Streamlit
    if not filtered_benefits_df.empty and not filtered_tax_df.empty and not filtered_refundable_tax_df.empty: # all tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Benefits Breakdown", "Refundable Tax Credits", "Tax Before Refundable Credits Breakdown"])
        with tab1:
            st.dataframe(table_data, hide_index=True)

        with tab2:
            st.dataframe(filtered_benefits_df, hide_index=True)

        with tab3:
            st.dataframe(filtered_refundable_tax_df, hide_index=True)
        
        with tab4:
            st.dataframe(filtered_tax_df, hide_index=True)

    elif not filtered_benefits_df.empty and not filtered_tax_df.empty and filtered_refundable_tax_df.empty: # tab 2 and tab 4
        tab1, tab2, tab4 = st.tabs(["Summary", "Benefits Breakdown", "Tax Before Refundable Credits Breakdown"])
        with tab1:
            st.dataframe(table_data, hide_index=True)

        with tab2:
            st.dataframe(filtered_benefits_df, hide_index=True)
        
        with tab4:
            st.dataframe(filtered_tax_df, hide_index=True)

    elif not filtered_benefits_df.empty and filtered_tax_df.empty and not filtered_refundable_tax_df.empty: # tab 2 and tab 3
        tab1, tab2, tab3 = st.tabs(["Summary", "Benefits Breakdown", "Refundable Tax Credits Breakdown"])
        with tab1:
            st.dataframe(table_data, hide_index=True)

        with tab2:
            st.dataframe(filtered_benefits_df, hide_index=True)
        
        with tab3:
            st.dataframe(filtered_refundable_tax_df, hide_index=True)

    elif filtered_benefits_df.empty and not filtered_tax_df.empty and not filtered_refundable_tax_df.empty: # tab 3 and tab 4
        tab1, tab3, tab4 = st.tabs(["Summary", "Refundable Tax Credits Breakdown", "Tax Before Refundable Credits Breakdown"])
        with tab1:
            st.dataframe(table_data, hide_index=True)

        with tab3:
            st.dataframe(filtered_refundable_tax_df, hide_index=True)
        
        with tab4:
            st.dataframe(filtered_tax_df, hide_index=True)
    

    elif not filtered_benefits_df.empty and filtered_tax_df.empty and filtered_refundable_tax_df.empty: # tab 2
        tab1, tab2 = st.tabs(["Summary", "Benefits Breakdown"])
        with tab1:
            st.dataframe(table_data, hide_index=True)

        with tab2:
            st.dataframe(filtered_benefits_df, hide_index=True)
        
    elif filtered_benefits_df.empty and not filtered_tax_df.empty and filtered_refundable_tax_df.empty: # tab 4
        tab1, tab4 = st.tabs(["Summary", "Tax Before Refundable Credits Breakdown"])
        with tab1:
            st.dataframe(table_data, hide_index=True)

        with tab4:
            st.dataframe(filtered_tax_df, hide_index=True)

    elif filtered_benefits_df.empty and filtered_tax_df.empty and not filtered_refundable_tax_df.empty: # tab 3
        tab1, tab3 = st.tabs(["Summary", "Refundable Tax Credits Breakdown"])
        with tab1:
            st.dataframe(table_data, hide_index=True)

        with tab3:
            st.dataframe(filtered_refundable_tax_df, hide_index=True)

    else: # if we don't have benefits or tax before refundable credits, display just the main table
        st.dataframe(table_data, hide_index=True)
    
    def calculate_bonus():
        married_incomes , separate_incomes = get_net_incomes(state_code, children_ages)
        bonus_penalties = [x - y for x, y in zip(married_incomes.tolist(), separate_incomes.tolist())]
        array = np.array(bonus_penalties)
        nested_lists = np.reshape(array, (8, 8))
        return nested_lists

        
def get_chart(data, heatmap_tax_unit):
    # Function to calculate the input data (replace with your actual data calculation)
        # Set numerical values for x and y axes
        x_values = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000]
        y_values = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000]

        label_legend = {
            "Income": "Income Change",
            "Benefits": "Benefits Change",
            "Taxes": "Tax Change",
            "Credits": "Credit Change"
        }

        abs_max = max(abs(min(map(min, data))), abs(max(map(max, data))))
        z_min = -abs_max
        z_max = abs_max
        color_scale = [
                (0, '#616161'), 
                (0.5, '#FFFFFF'),  
                (1, '#2C6496')  
                ]
        # Display the chart once data calculation is complete
        fig = px.imshow(data,

                        labels=dict(x="Head Employment Income", y="Spouse Employment Income", color= label_legend[heatmap_tax_unit]),

                        x=x_values,
                        y=y_values,
                        zmin=z_min,
                        zmax=z_max,
                        color_continuous_scale=color_scale,
                        origin='lower'
                    )

        fig.update_xaxes(side="bottom")
        fig.update_layout(
            xaxis=dict(
                tickmode='array',
                tickvals=[10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000],
                ticktext=["{}k".format(int(val/1000)) for val in [10000,20000, 30000,40000,50000, 60000, 70000, 80000]],
                showgrid=True,
                zeroline=False,
                title=dict(text='Head Employment Income', standoff=15),
            ),
            yaxis=dict(
                tickmode='array',
                tickvals=[10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000],
                ticktext=["{}k".format(int(val/1000)) for val in [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000]],
                showgrid=True,
                zeroline=False,
                title=dict(text='Spouse Employment Income', standoff=15),
                scaleanchor="x",
                scaleratio=1,
            )
        )

 
        fig.update_layout(height=600, width=800)
        # Add header
        st.markdown("<h3 style='text-align: center; color: black;'>Marriage Incentive and Penalty Analysis</h3>", unsafe_allow_html=True)
        fig = format_fig(fig)
        # Display the chart
        
        st.plotly_chart(fig, use_container_width=True)
@st.cache_data(hash_funcs={dict: lambda _: None})
def heapmap_calculation(state_code, children_ages_hash, children_ages):
    final_lists = {}
  
    for key, _ in HEAT_MAP_OUTPUTS.items():
        married_incomes, separate_incomes = get_heatmap_values(state_code, children_ages, key)
        
        if isinstance(married_incomes, list):
            married_incomes_array = np.array(married_incomes)
        else:
            married_incomes_array = married_incomes
        
        if isinstance(separate_incomes[0], list):
            separate_incomes_array = np.array(separate_incomes)
        else:
            separate_incomes_array = separate_incomes
        
        married_incomes_2d = married_incomes_array.reshape(8, 8)
        bonus_penalties = married_incomes_2d - separate_incomes_array
        final_lists[key] = bonus_penalties.tolist()

    return final_lists

children_ages_hash = hashlib.md5(str(children_ages).encode()).hexdigest()

data = heapmap_calculation(state_code, children_ages_hash, children_ages)

# Check if the children_ages dictionary has changed and rerun the calculation
if "children_ages_hash" not in st.session_state:
    st.session_state.children_ages_hash = children_ages_hash
else:
    # Check if the children_ages dictionary has changed and update the hash
    if st.session_state.children_ages_hash != children_ages_hash:
        st.session_state.children_ages_hash = children_ages_hash




selected_heatmap_values = data[heatmap_tax_unit]
get_chart(selected_heatmap_values, heatmap_tax_unit)


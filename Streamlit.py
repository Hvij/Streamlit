import streamlit as st
import numpy as np
import pandas as pd

# Set the page layout to wide
st.set_page_config(layout="wide")

@st.cache_data(ttl=900)
def get_data():
    df = pd.read_excel('Inventory Distribution model.xlsx','Base Data')
    df_putaway=pd.read_excel('Inventory Distribution model.xlsx','Pending_putaway')
    df_sto=pd.read_excel('Inventory Distribution model.xlsx','sto_transit')
    df_rto=pd.read_excel('Inventory Distribution model.xlsx','rto_transit')
    df_return=pd.read_excel('Inventory Distribution model.xlsx','pending_return_checkin')

    return df, df_putaway, df_sto, df_rto, df_return  # Return all 5 dataframes

def user_input(df):
    # Create three columns
    st.subheader('Filters')
    col1, col2, col3 = st.columns(3)

    # Column 1: Minimum inventory days and warehouses
    with col1:
        x = st.number_input('Min Inventory Days', min_value=0, value=15, step=1)
        warehouses = df['warehouse'].unique()
        selected_warehouses = st.multiselect('Select Warehouses', warehouses, None)

    # Column 2: Product variants and brands
    with col2:
        variants = df['product_variant_id'].unique()
        selected_variants = st.multiselect('Select Variant IDs', variants, None)
        brands = df['brand'].unique()
        selected_brands = st.multiselect('Select Brands', brands, None)

    # Column 3: Channel and category
    with col3:
        channel = df['channel'].unique()
        selected_channel = st.multiselect('Select Channels', channel, None)
        category = df['category'].unique()
        selected_category = st.multiselect('Select Categories', category, None)

    return x, selected_warehouses, selected_variants, selected_brands, selected_channel, selected_category

def Risk_rev(filtered_df, x):
    df = filtered_df
    # Adding New Columns
    df['Total Revenue'] = (df['last_30_day_revenue'] * (df['wd1'])/30).round(2)
    df['No Risk Revenue'] = np.round(np.where(df['wd1'] >= x, df['last_30_day_revenue'] * (df['wd1'] - x) / 30, 0), 2)
    df['Revenue at OOS Risk'] = np.round(np.where((df['wd1'] < x) & (df['wd2'] < x) & (df['nd1'] < x), df['last_30_day_revenue'] * (x - df['wd1']) / 30, 0), 2)
    df['Revenue at NRF Risk'] = np.round(np.where((df['wd1'] < x) & (df['wd2'] < x) & (df['nd1'] >= x), df['last_30_day_revenue'] * (x - df['wd1']) / 30, 0), 2)
    df['Revenue at FUD Risk'] = np.round(np.where((df['wd1'] < x) & (df['wd2'] >= x), df['last_30_day_revenue'] * (x - df['wd1']) / 30, 0), 2)
    return df

def net_risk_revenues(filtered_df):
    # Calculation of net revenues under different risks without filters
    net_rev = {
        'Net Revenue': filtered_df['Total Revenue'].sum(),
        'Net_NO_risk_rev': filtered_df['No Risk Revenue'].sum(),
        'Net_OOS_risk_rev': filtered_df['Revenue at OOS Risk'].sum(),
        'Net_NRF_risk_rev': filtered_df['Revenue at NRF Risk'].sum(),
        'Net_FUD_risk_rev': filtered_df['Revenue at FUD Risk'].sum()
    }
    return net_rev

def filter(df,df_putaway, df_sto, df_rto, df_return, selected_warehouses, selected_variants, selected_brands, selected_channel, selected_category):
    # Start with the full DataFrame
    filtered_df = df
    filtered_putaway_df = df_putaway
    filtered_sto_df = df_sto
    filtered_rto_df = df_rto
    filtered_return_df = df_return

    # Apply filters if selections are made
    if selected_warehouses:
        filtered_df = filtered_df[filtered_df['warehouse'].isin(selected_warehouses)]
    if selected_variants:
        filtered_df = filtered_df[filtered_df['product_variant_id'].isin(selected_variants)]
    if selected_brands:
        filtered_df = filtered_df[filtered_df['brand'].isin(selected_brands)]
    if selected_channel:
        filtered_df = filtered_df[filtered_df['channel'].isin(selected_channel)]
    if selected_category:
        filtered_df = filtered_df[filtered_df['category'].isin(selected_category)]

    # Apply filters to the other DataFrames (only based on warehouse and variant)
    if selected_warehouses:
        filtered_putaway_df = filtered_putaway_df[filtered_putaway_df['warehouse'].isin(selected_warehouses)]
        filtered_sto_df = filtered_sto_df[filtered_sto_df['warehouse'].isin(selected_warehouses)]
        filtered_rto_df = filtered_rto_df[filtered_rto_df['warehouse'].isin(selected_warehouses)]
        filtered_return_df = filtered_return_df[filtered_return_df['warehouse'].isin(selected_warehouses)]

    if selected_variants:
        filtered_putaway_df = filtered_putaway_df[filtered_putaway_df['product_variant_id'].isin(selected_variants)]
        filtered_sto_df = filtered_sto_df[filtered_sto_df['product_variant_id'].isin(selected_variants)]
        filtered_rto_df = filtered_rto_df[filtered_rto_df['product_variant_id'].isin(selected_variants)]
        filtered_return_df = filtered_return_df[filtered_return_df['product_variant_id'].isin(selected_variants)]

    return filtered_df, filtered_putaway_df, filtered_sto_df, filtered_rto_df, filtered_return_df

def generate_filtered_tables(filtered_df):
    # Generate tables under different risks after filters
    dataframes = {}
    
    if filtered_df['Revenue at OOS Risk'].gt(0).any():
        oos_risk_df = filtered_df[filtered_df['Revenue at OOS Risk'] > 0][['product_variant_id', 'warehouse', 'Revenue at OOS Risk']]
        dataframes['Revenue at OOS Risk'] = oos_risk_df
    
    if filtered_df['Revenue at NRF Risk'].gt(0).any():
        nrf_risk_df = filtered_df[filtered_df['Revenue at NRF Risk'] > 0][['product_variant_id', 'warehouse', 'Revenue at NRF Risk']]
        dataframes['Revenue at NRF Risk'] = nrf_risk_df

    if filtered_df['Revenue at FUD Risk'].gt(0).any():
        fud_risk_df = filtered_df[filtered_df['Revenue at FUD Risk'] > 0][['product_variant_id', 'warehouse', 'Revenue at FUD Risk']]
        dataframes['Revenue at FUD Risk'] = fud_risk_df
    
    return dataframes

def pivot_table_dashboard(filtered_df):
    # Create a new column for projected daily demand and round it
    filtered_df['Projected Daily Demand'] = (filtered_df['last_30_day_sale'] / 30).round(2)

    # User selects whether to group by Brand, Warehouse, or Channel
    pivot_option = st.selectbox("Select Pivot Category", ['brand', 'warehouse', 'channel'])

    # Create Pivot Table
    pivot_df = pd.pivot_table(
        filtered_df,
        index=pivot_option,
        values=['available_inventory', 'Projected Daily Demand', 'No Risk Revenue', 'Revenue at OOS Risk', 'booked_quantity'],
        aggfunc={
            'available_inventory': 'sum',
            'Projected Daily Demand': 'sum',
            'No Risk Revenue': 'sum',
            'Revenue at OOS Risk': 'sum',
            'booked_quantity': 'sum'
        }
    )

    # Calculate days on inventory after pivot and round to 2 decimal places
    pivot_df['Days of Inventory'] = ((pivot_df['available_inventory'] - pivot_df['booked_quantity']) / pivot_df['Projected Daily Demand']).round(2)
    
    # Rename columns for clarity
    pivot_df.columns = ['Inventory', 'Projected Daily Demand', 'Risk-Free Revenue', 'OOS Risk', 'Booked Quantity', 'Days of Inventory']

    # Display the Pivot Table
    st.dataframe(pivot_df)


if __name__ == "__main__":

    df, df_putaway, df_sto, df_rto, df_return = get_data()

    df = df.round(2)

     # Get user inputs
    x, selected_warehouses, selected_variants, selected_brands, selected_channel, selected_category = user_input(df)

    # Filter DataFrame based on user selections
    filtered_df, filtered_putaway_df, filtered_sto_df, filtered_rto_df, filtered_return_df = filter(df, df_putaway, df_sto, df_rto, df_return, selected_warehouses, selected_variants, selected_brands, selected_channel, selected_category)

    filtered_df = filtered_df.round(2)

    # Perform the risk revenue operations (add columns)
    filtered_df = Risk_rev(filtered_df, x)

    # Calculate the net revenues
    net_revenues = net_risk_revenues(filtered_df)
    
    # Generate filtered tables
    tables = generate_filtered_tables(filtered_df)

    tab1, tab2, tab3 = st.tabs(["Overview","Risk Type", "Actions"])
     # Fetch cached data

    with tab1:

        st.title("Streamlit Risk Revenue Calculations")

        # Dashboard Main Panel Arrangement
        col = st.columns((1, 1, 1), gap='medium')

        with col[0]:

            # Current Inventory
            st.metric(label="Current Inventory", value=f"{df['available_inventory'].sum()} Units")

            if net_revenues['Net Revenue'] != 0:
                # Net OOS Risk Revenue as a percentage
                st.metric(label="Net OOS Risk Revenue", value=f"{(net_revenues['Net_OOS_risk_rev'] * 100 / net_revenues['Net Revenue']):.2f}%")
            else:
                st.metric(label="Net OOS Risk Revenue", value="0%", delta="No Revenue")

        with col[1]:

            # Projected Daily Demand
            st.metric(label="Projected Daily Demand", value=f"{(df['last_30_day_sale'].sum())/30:.0f} Units")

            if net_revenues['Net Revenue'] != 0:
                # Net NRF Risk Revenue as a percentage
                st.metric(label="Net NRF Risk Revenue", value=f"{(net_revenues['Net_NRF_risk_rev'] * 100 / net_revenues['Net Revenue']):.2f}%")
            else:
                st.metric(label="Net NRF Risk Revenue", value="0%", delta="No Revenue")

        with col[2]:

            if net_revenues['Net Revenue'] != 0:
                # Net No Risk Revenue as a percentage
                st.metric(label="Net No Risk Revenue", value=f"{(net_revenues['Net_NO_risk_rev'] * 100 / net_revenues['Net Revenue']):.2f}%")
                
                # Net FUD Risk Revenue as a percentage
                st.metric(label="Net FUD Risk Revenue", value=f"{(net_revenues['Net_FUD_risk_rev'] * 100 / net_revenues['Net Revenue']):.2f}%")
            else:
                st.metric(label="Net No Risk Revenue", value="0%", delta="No Revenue")
                st.metric(label="Net FUD Risk Revenue", value="0%", delta="No Revenue")

        st.subheader("Inventory Dashboard - Pivot Table")

        # Display Pivot Table based on selection
        pivot_table_dashboard(filtered_df)

        # Optionally display the raw data with new columns
        st.write("Raw Data from Redshift with Risk Revenues:", df)

    with tab2:
        
        for title, table_df in tables.items():
            st.subheader(title)
            st.dataframe(table_df)  # Display dataframe

    
    with tab3:

        st.subheader("Putaway Data")
        st.dataframe(filtered_putaway_df)

        st.subheader("STO Transit Data")
        st.dataframe(filtered_sto_df)

        st.subheader("RTO Transit Data")
        st.dataframe(filtered_rto_df)

        st.subheader("Pending Return Check-in Data")
        st.dataframe(filtered_return_df)

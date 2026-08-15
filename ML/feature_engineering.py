def run_feature_engineering(df):
    # ============================================================
    # UC10 - Feature Engineering for Claims/Pharmacy/Auth Dataset
    # Run this in Google Colab
    # ============================================================
    
    # ---- 1. Install/Import ----
    import pandas as pd
    import numpy as np
    
    # ---- 2. Load the dataset ----
    
    
    
    
    print("Loaded shape:", df.shape)
    
    # ---- 3. Parse date columns ----
    date_cols = ['Service_Date', 'Service_End_Date', 'Submission_Date',
                 'Processed_Date', 'Decision_Date', 'Ingestion_Timestamp']
    for c in date_cols:
        df[c] = pd.to_datetime(df[c], errors='coerce')
    
    # Derive a clean "Batch_Date" from Batch_ID (format: BATCH_YYYYMMDD)
    df['Batch_Date'] = pd.to_datetime(
        df['Batch_ID'].str.replace('BATCH_', '', regex=False),
        format='%Y%m%d', errors='coerce'
    )
    
    # ============================================================
    # FEATURE 1: Provider-level denial/rejection rate
    # ============================================================
    denied_like = df['Status'].isin(['DENIED', 'REJECTED'])
    provider_stats = (
        df.groupby('Provider_NPI')
          .agg(Provider_Total_Records=('Record_ID', 'count'),
               Provider_Denied_Records=('Status', lambda s: s.isin(['DENIED', 'REJECTED']).sum()))
          .reset_index()
    )
    provider_stats['Provider_Denial_Rate'] = (
        provider_stats['Provider_Denied_Records'] / provider_stats['Provider_Total_Records']
    ).round(4)
    
    df = df.merge(
        provider_stats[['Provider_NPI', 'Provider_Total_Records', 'Provider_Denial_Rate']],
        on='Provider_NPI', how='left'
    )
    
    # ============================================================
    # FEATURE 2: Batch-level daily volume & SLA-breach-rate trend
    # (rolling 7-day average, compared against each batch's own rate)
    # ============================================================
    batch_daily = (
        df.groupby('Batch_Date')
          .agg(Batch_Volume=('Record_ID', 'count'),
               Batch_SLA_Breach_Rate=('SLA_Breach_Flag', lambda s: (s == 'Y').mean()))
          .reset_index()
          .sort_values('Batch_Date')
    )
    batch_daily['Rolling_7D_Avg_Volume'] = (
        batch_daily['Batch_Volume'].rolling(window=7, min_periods=1).mean().round(2)
    )
    batch_daily['Rolling_7D_Avg_SLA_Breach_Rate'] = (
        batch_daily['Batch_SLA_Breach_Rate'].rolling(window=7, min_periods=1).mean().round(4)
    )
    # Volume/SLA anomaly vs. its own trailing trend
    batch_daily['Volume_Vs_Trend_Ratio'] = (
        batch_daily['Batch_Volume'] / batch_daily['Rolling_7D_Avg_Volume']
    ).round(2)
    batch_daily['SLA_Breach_Rate_Vs_Trend_Diff'] = (
        batch_daily['Batch_SLA_Breach_Rate'] - batch_daily['Rolling_7D_Avg_SLA_Breach_Rate']
    ).round(4)
    
    df = df.merge(
        batch_daily[['Batch_Date', 'Batch_Volume', 'Rolling_7D_Avg_Volume',
                     'Volume_Vs_Trend_Ratio', 'Batch_SLA_Breach_Rate',
                     'Rolling_7D_Avg_SLA_Breach_Rate', 'SLA_Breach_Rate_Vs_Trend_Diff']],
        on='Batch_Date', how='left'
    )
    
    # ============================================================
    # FEATURE 3: Beneficiary claim frequency (how many records per member)
    # ============================================================
    bene_freq = (
        df.groupby('BENE_ID')
          .size()
          .reset_index(name='Beneficiary_Record_Count')
    )
    df = df.merge(bene_freq, on='BENE_ID', how='left')
    
    # Flag unusually high-frequency beneficiaries (top 1% by record count)
    if df['Beneficiary_Record_Count'].notna().sum() > 0:
        freq_threshold = df['Beneficiary_Record_Count'].quantile(0.99)
        df['High_Frequency_Beneficiary_Flag'] = df['Beneficiary_Record_Count'] > freq_threshold
    else:
        df['High_Frequency_Beneficiary_Flag'] = False
    
    # ============================================================
    # FEATURE 4: Claim <-> Prior-Auth linkage
    # Populate Auth_Linked_ID by matching claims (that require auth) to a
    # PRIOR_AUTH record for the same beneficiary within a reasonable time window,
    # then flag claims that require auth but have NO matching auth record.
    # ============================================================
    auth_records = df[df['Record_Type'] == 'PRIOR_AUTH'][
        ['Record_ID', 'BENE_ID', 'Submission_Date', 'Status']
    ].rename(columns={'Record_ID': 'Matched_Auth_Record_ID',
                       'Submission_Date': 'Auth_Submission_Date',
                       'Status': 'Auth_Status'})
    
    needs_auth = df[(df['Auth_Required_Flag'] == 'Y') & (df['Record_Type'] != 'PRIOR_AUTH')].copy()
    
    # Nearest prior PRIOR_AUTH submission date per BENE_ID
    matches = needs_auth.merge(auth_records, on='BENE_ID', how='left')
    matches = matches[matches['Auth_Submission_Date'] <= matches['Submission_Date']]
    matches['Days_Between'] = (matches['Submission_Date'] - matches['Auth_Submission_Date']).dt.days
    matches = matches.sort_values('Days_Between').drop_duplicates(subset='Record_ID', keep='first')
    
    link_map = matches.set_index('Record_ID')['Matched_Auth_Record_ID']
    df['Auth_Linked_ID'] = df['Record_ID'].map(link_map).combine_first(df['Auth_Linked_ID'])
    
    df['Missing_Required_Auth_Link'] = (
        (df['Auth_Required_Flag'] == 'Y') &
        (df['Record_Type'] != 'PRIOR_AUTH') &
        (df['Auth_Linked_ID'].isna())
    )
    
    # ============================================================
    # FEATURE 5: Time since last batch per source system (pipeline gap detection)
    # ============================================================
    sys_batches = (
        df[['Source_System', 'Batch_Date']]
        .dropna()
        .drop_duplicates()
        .sort_values(['Source_System', 'Batch_Date'])
    )
    sys_batches['Days_Since_Prev_Batch'] = (
        sys_batches.groupby('Source_System')['Batch_Date'].diff().dt.days
    )
    df = df.merge(sys_batches, on=['Source_System', 'Batch_Date'], how='left')
    
    # Flag a pipeline gap if the gap is unusually large (> 3x the median gap for that system)
    gap_threshold_map = sys_batches.groupby('Source_System')['Days_Since_Prev_Batch'].median() * 3
    df['Pipeline_Gap_Flag'] = df.apply(
        lambda r: (r['Days_Since_Prev_Batch'] > gap_threshold_map.get(r['Source_System'], np.inf))
        if pd.notna(r['Days_Since_Prev_Batch']) else False,
        axis=1
    )
    
    # ============================================================
    # FEATURE 6: Day-of-week seasonality-normalized SLA breach rate
    # ============================================================
    df['Submission_Day_Of_Week'] = df['Submission_Date'].dt.day_name()
    
    dow_breach_rate = (
        df.groupby('Submission_Day_Of_Week')['SLA_Breach_Flag']
          .apply(lambda s: (s == 'Y').mean())
          .rename('DOW_Avg_SLA_Breach_Rate')
          .reset_index()
    )
    df = df.merge(dow_breach_rate, on='Submission_Day_Of_Week', how='left')
    
    df['Record_SLA_Breach_Numeric'] = (df['SLA_Breach_Flag'] == 'Y').astype(int)
    df['SLA_Breach_Vs_DOW_Norm'] = (
        df['Record_SLA_Breach_Numeric'] - df['DOW_Avg_SLA_Breach_Rate']
    ).round(4)
    
    # ============================================================
    # 4. Save the feature-engineered dataset
    # ============================================================
    output_path = "claims_pharmacy_auth_monitor_dataset_features.csv"
    df.to_csv(output_path, index=False)
    print("Saved:", output_path)
    print("Final shape:", df.shape)
    print("\nNew feature columns added:")
    new_cols = ['Provider_Total_Records', 'Provider_Denial_Rate',
                'Batch_Volume', 'Rolling_7D_Avg_Volume', 'Volume_Vs_Trend_Ratio',
                'Batch_SLA_Breach_Rate', 'Rolling_7D_Avg_SLA_Breach_Rate', 'SLA_Breach_Rate_Vs_Trend_Diff',
                'Beneficiary_Record_Count', 'High_Frequency_Beneficiary_Flag',
                'Auth_Linked_ID', 'Missing_Required_Auth_Link',
                'Days_Since_Prev_Batch', 'Pipeline_Gap_Flag',
                'Submission_Day_Of_Week', 'DOW_Avg_SLA_Breach_Rate', 'SLA_Breach_Vs_DOW_Norm']
    for c in new_cols:
        print(" -", c)
    
    df.head(10)
    return df

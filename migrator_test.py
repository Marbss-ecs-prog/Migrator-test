import base64
import pandas as pd
import streamlit as st

st.title("Ecomsniper Listing Migration Tool")
st.write(
    "Upload your SellerPilot CSV export and your eBay template file below."
)

# 1. File Uploaders
sellerpilot_file = st.file_uploader(
    "1. Upload SellerPilot Export (CSV)", type=["csv"]
)
ebay_file = st.file_uploader(
    "2. Upload eBay Price & Stock Template (CSV)", type=["csv"]
)

if sellerpilot_file and ebay_file:
  try:
    # Read CSVs
    df_sp = pd.read_csv(sellerpilot_file)
    df_ebay = pd.read_csv(ebay_file)

    # Standardize column headers to remove accidental trailing spaces
    df_sp.columns = df_sp.columns.str.strip()
    df_ebay.columns = df_ebay.columns.str.strip()

    # Define your exact column names
    sp_item_id_col = "eBay Item ID"
    sp_asin_col = "ASIN"

    ebay_item_id_col = "Item number"
    ebay_sku_col = "Custom label (SKU)"

    # Verify that the required columns exist in both files
    missing_sp = [
        col for col in [sp_item_id_col, sp_asin_col] if col not in df_sp.columns
    ]
    missing_ebay = [
        col
        for col in [ebay_item_id_col, ebay_sku_col]
        if col not in df_ebay.columns
    ]

    if missing_sp:
      st.error(
          f"SellerPilot CSV is missing columns: {missing_sp}. Found columns:"
          f" {list(df_sp.columns)}"
      )
    elif missing_ebay:
      st.error(
          f"eBay CSV is missing columns: {missing_ebay}. Found columns:"
          f" {list(df_ebay.columns)}"
      )
    else:
      # Normalize IDs to string to ensure clean matching
      df_sp[sp_item_id_col] = df_sp[sp_item_id_col].astype(str).str.strip()
      df_ebay[ebay_item_id_col] = (
          df_ebay[ebay_item_id_col].astype(str).str.strip()
      )

      # Base64 encoder function
      def encode_asin(asin):
        if pd.isna(asin) or str(asin).strip() == "" or str(asin) == "nan":
          return ""
        return base64.b64encode(str(asin).strip().encode("utf-8")).decode(
            "utf-8"
        )

      # Create a lookup dictionary mapping eBay Item ID -> Base64 encoded ASIN
      sp_mapping = dict(
          zip(df_sp[sp_item_id_col], df_sp[sp_asin_col].apply(encode_asin))
      )

      # Process rows starting from index 1 (skipping index 0 which contains eBay connectors)
      for idx in range(len(df_ebay)):
        if idx == 0:
          continue  # Leave the first data row untouched

        item_num = df_ebay.loc[idx, ebay_item_id_col]

        # Check if item number matches and has a valid encoded ASIN
        if item_num in sp_mapping and sp_mapping[item_num]:
          df_ebay.loc[idx, ebay_sku_col] = sp_mapping[item_num]
        else:
          df_ebay.loc[idx, ebay_sku_col] (
              ""
          )  # Populate empty if no match or missing SKU

      st.success("CSVs successfully matched and converted!")
      st.dataframe(df_ebay.head(10))  # Preview first 10 rows

      # Generate downloadable CSV file
      csv_data = df_ebay.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Download Ecomsniper-Ready eBay CSV",
          data=csv_data,
          file_name="Ecomsniper_Ready_eBay_Template.csv",
          mime="text/csv",
      )

  except Exception as e:
    st.error(f"An error occurred: {e}")

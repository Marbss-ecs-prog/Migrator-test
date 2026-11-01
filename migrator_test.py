import base64
import pandas as pd
import streamlit as st

st.title("ECS Listing Migration Tool")
st.write("Upload your Past Vendor CSV export and your eBay template file below.")

# 1. File Uploaders
vendor_file = st.file_uploader(
    "1. Upload Past Vendor Export (CSV)", type=["csv"]
)
ebay_file = st.file_uploader(
    "2. Upload eBay Price & Stock Template (CSV)", type=["csv"]
)

if vendor_file and ebay_file:
  try:
    # Read CSVs
    df_vendor = pd.read_csv(vendor_file)
    df_ebay = pd.read_csv(ebay_file)

    # Standardize column headers to remove accidental trailing spaces
    df_vendor.columns = df_vendor.columns.str.strip()
    df_ebay.columns = df_ebay.columns.str.strip()

    # Define your exact column names
    vendor_item_id_col = "eBay Item ID"
    vendor_asin_col = "ASIN"

    ebay_item_id_col = "Item number"
    ebay_sku_col = "Custom label (SKU)"

    # Verify that the required columns exist in both files
    missing_vendor = [
        col
        for col in [vendor_item_id_col, vendor_asin_col]
        if col not in df_vendor.columns
    ]
    missing_ebay = [
        col
        for col in [ebay_item_id_col, ebay_sku_col]
        if col not in df_ebay.columns
    ]

    if missing_vendor:
      st.error(
          f"Past Vendor CSV is missing columns: {missing_vendor}. Found"
          f" columns: {list(df_vendor.columns)}"
      )
    elif missing_ebay:
      st.error(
          f"eBay CSV is missing columns: {missing_ebay}. Found columns:"
          f" {list(df_ebay.columns)}"
      )
    else:
      # Normalize IDs to string
      df_vendor[vendor_item_id_col] = (
          df_vendor[vendor_item_id_col].astype(str).str.strip()
      )
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

      # CLEAN VENDOR FILE: Filter out connector rows (index 0 / rows with '*', blanks, or non-digits)
      valid_vendor_rows = df_vendor[
          df_vendor[vendor_item_id_col].notna()
          & (df_vendor[vendor_item_id_col] != "")
          & (df_vendor[vendor_item_id_col].str.lower() != "nan")
          & (~df_vendor[vendor_item_id_col].str.contains(r"\*", na=False))
          & (df_vendor[vendor_item_id_col].str.isdigit())
      ].copy()

      # Create the lookup dictionary using only clean, valid rows
      valid_vendor_rows["encoded_asin"] = valid_vendor_rows[
          vendor_asin_col
      ].apply(encode_asin)
      vendor_mapping = dict(
          zip(valid_vendor_rows[vendor_item_id_col], valid_vendor_rows["encoded_asin"])
      )

      # PROCESS EBAY TEMPLATE: Loop through rows and match
      for idx in range(len(df_ebay)):
        item_num = df_ebay.loc[idx, ebay_item_id_col]

        # Check if the eBay row is a connector/metadata row (e.g., contains '*', is blank, or non-numeric)
        if (
            pd.isna(item_num)
            or item_num == ""
            or str(item_num).lower() == "nan"
            or "*" in str(item_num)
            or not str(item_num).isdigit()
        ):
          # Leave connector or header rows completely untouched
          continue

        # Match and populate SKU or clear if no match
        if item_num in vendor_mapping and vendor_mapping[item_num]:
          df_ebay.loc[idx, ebay_sku_col] = vendor_mapping[item_num]
        else:
          df_ebay.loc[idx, ebay_sku_col] = (
              ""  # Populate empty if no match found
          )

      st.success("CSVs successfully matched and converted!")
      st.dataframe(df_ebay.head(10))  # Preview first 10 rows

      # Generate downloadable CSV file
      csv_data = df_ebay.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Download ECS-Ready eBay CSV",
          data=csv_data,
          file_name="ECS_Ready_eBay_Template.csv",
          mime="text/csv",
      )

  except Exception as e:
    st.error(f"An error occurred: {e}")

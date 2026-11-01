import base64
import pandas as pd
import streamlit as st

st.title("Ecomsniper Listing Migration Tool")
st.write(
    "Upload your AutoDS/SellerPilot CSV and your eBay Template to format your listing."
)

# 1. File Uploaders
autods_file = st.file_uploader(
    "1. Upload AutoDS / SellerPilot Export (ASIN + Item ID)", type=["csv"]
)
ebay_file = st.file_uploader(
    "2. Upload eBay Price & Stock Template", type=["csv"]
)

if autods_file and ebay_file:
  try:
    # Read CSVs
    df_autods = pd.read_csv(autods_file)
    df_ebay = pd.read_csv(ebay_file)

    # Standardize column headers to handle slight typos or lowercase inputs
    df_autods.columns = df_autods.columns.str.strip()
    df_ebay.columns = df_ebay.columns.str.strip()

    # 2. Merge on Item ID key
    # Adjust column names inside get() if your actual exports use different header titles
    item_id_col = "Item ID"
    asin_col = "ASIN"

    if item_id_col in df_autods.columns and item_id_col in df_ebay.columns:
      # Merge ASIN into eBay template based on matching Item ID
      merged_df = pd.merge(
          df_ebay,
          df_autods[[item_id_col, asin_col]],
          on=item_id_col,
          how="left",
      )

      # 3. Base64 Encode ASIN into the SKU column
      def encode_asin(asin):
        if pd.isna(asin):
          return ""
        return base64.b64encode(str(asin).encode("utf-8")).decode("utf-8")

      merged_df["SKU"] = merged_df[asin_col].apply(encode_asin)

      # Clean up extra ASIN column if not needed in the final eBay output format
      final_df = merged_df.drop(columns=[asin_col])

      st.success("CSVs successfully matched and converted!")
      st.dataframe(final_df.head(10))  # Preview first 10 rows

      # 4. Generate downloadable CSV file
      csv_data = final_df.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Download Ecomsniper CSV",
          data=csv_data,
          file_name="Ecomsniper_Ready_Listings.csv",
          mime="text/csv",
      )
    else:
      st.error(
          f"Could not find '{item_id_col}' header in one or both of the CSV files."
      )

  except Exception as e:
    st.error(f"An error occurred: {e}")
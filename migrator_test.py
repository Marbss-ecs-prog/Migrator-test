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


# Smart Header Hunter: Automatically skips #INFO versions, metadata, and sep= lines
def load_csv_safely(uploaded_file, target_columns):
  uploaded_file.seek(0)
  lines = uploaded_file.readlines()
  header_row_index = 0

  for idx, line in enumerate(lines[:15]):
    line_str = line.decode("utf-8", errors="ignore")
    if any(target in line_str for target in target_columns):
      header_row_index = idx
      break

  sample_header = lines[header_row_index].decode("utf-8", errors="ignore")
  sep = (
      ";"
      if ";" in sample_header and "," not in sample_header.splitlines()[0]
      else ","
  )

  uploaded_file.seek(0)
  return pd.read_csv(
      uploaded_file,
      skiprows=header_row_index,
      encoding="utf-8",
      dtype=str,
      sep=sep,
  )


if vendor_file and ebay_file:
  try:
    vendor_target_cols = ["eBay Item ID", "ASIN"]
    ebay_target_cols = ["Item number", "Custom label (SKU)"]

    df_vendor = load_csv_safely(vendor_file, vendor_target_cols)
    df_ebay = load_csv_safely(ebay_file, ebay_target_cols)

    # Standardize column headers
    df_vendor.columns = df_vendor.columns.str.strip()
    df_ebay.columns = df_ebay.columns.str.strip()

    vendor_item_id_col = "eBay Item ID"
    vendor_asin_col = "ASIN"

    ebay_item_id_col = "Item number"
    ebay_sku_col = "Custom label (SKU)"

    missing_vendor = [
        col for col in vendor_target_cols if col not in df_vendor.columns
    ]
    missing_ebay = [
        col for col in ebay_target_cols if col not in df_ebay.columns
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
      # --- FIX: NORMALIZE STRINGS FIRST BEFORE FILTERING ---
      df_vendor[vendor_item_id_col] = (
          df_vendor[vendor_item_id_col].astype(str).str.strip()
      )
      df_vendor[vendor_asin_col] = (
          df_vendor[vendor_asin_col].astype(str).str.strip()
      )
      df_ebay[ebay_item_id_col] = (
          df_ebay[ebay_item_id_col].astype(str).str.strip()
      )

      # Base64 encoder function
      def encode_asin(asin):
        if pd.isna(asin) or asin == "" or asin.lower() == "nan":
          return ""
        return base64.b64encode(asin.encode("utf-8")).decode("utf-8")

      # CLEAN VENDOR FILE: Keep valid item IDs (not empty, not NaN, no '*' or '#')
      valid_vendor_rows = df_vendor[
          df_vendor[vendor_item_id_col].notna()
          & (df_vendor[vendor_item_id_col] != "")
          & (df_vendor[vendor_item_id_col].str.lower() != "nan")
          & (~df_vendor[vendor_item_id_col].str.contains(r"\*|#", na=False))
      ].copy()

      # Create lookup dictionary
      valid_vendor_rows["encoded_asin"] = valid_vendor_rows[
          vendor_asin_col
      ].apply(encode_asin)
      vendor_mapping = dict(
          zip(
              valid_vendor_rows[vendor_item_id_col],
              valid_vendor_rows["encoded_asin"],
          )
      )

      # PROCESS EBAY TEMPLATE
      for idx in range(len(df_ebay)):
        item_num = df_ebay.loc[idx, ebay_item_id_col]

        # Skip metadata, #INFOVersion, connector (*), or blank rows
        if (
            pd.isna(item_num)
            or item_num == ""
            or item_num.lower() == "nan"
            or "*" in item_num
            or item_num.startswith("#")
        ):
          continue

        # Match and populate SKU or clear if no match
        if item_num in vendor_mapping and vendor_mapping[item_num]:
          df_ebay.loc[idx, ebay_sku_col] = vendor_mapping[item_num]
        else:
          df_ebay.loc[idx, ebay_sku_col] = ""

      st.success("CSVs successfully matched and converted!")
      st.dataframe(df_ebay.head(10))

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

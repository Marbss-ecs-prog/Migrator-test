import base64
import pandas as pd
import streamlit as st

st.title("ECS Listing Migration Tool")
st.write("Upload your Past Vendor CSV export and your eBay template file below.")

vendor_file = st.file_uploader(
    "1. Upload Past Vendor Export (CSV)", type=["csv"]
)
ebay_file = st.file_uploader(
    "2. Upload eBay Price & Stock Template (CSV)", type=["csv"]
)


# Simple, reliable CSV loader with semicolon/comma auto-detection
def load_csv_clean(uploaded_file):
  uploaded_file.seek(0)
  sample = uploaded_file.read(2048).decode("utf-8", errors="ignore")
  uploaded_file.seek(0)

  sep = ";" if ";" in sample and "," not in sample.splitlines()[0] else ","

  # Read lines, skip any metadata lines starting with # or sep=
  df = pd.read_csv(uploaded_file, sep=sep, dtype=str, skiprows=lambda x: x < 0)

  # Drop rows where columns are metadata junk
  df = df.dropna(how="all")
  return df


if vendor_file and ebay_file:
  try:
    df_vendor = load_csv_clean(vendor_file)
    df_ebay = load_csv_clean(ebay_file)

    # Clean column headers
    df_vendor.columns = df_vendor.columns.str.strip()
    df_ebay.columns = df_ebay.columns.str.strip()

    vendor_item_col = "eBay Item ID"
    vendor_asin_col = "ASIN"
    ebay_item_col = "Item number"
    ebay_sku_col = "Custom label (SKU)"

    # Verify columns exist
    if (
        vendor_item_col not in df_vendor.columns
        or vendor_asin_col not in df_vendor.columns
    ):
      st.error(
          f"Past Vendor CSV missing required columns. Found:"
          f" {list(df_vendor.columns)}"
      )
    elif (
        ebay_item_col not in df_ebay.columns
        or ebay_sku_col not in df_ebay.columns
    ):
      st.error(
          f"eBay CSV missing required columns. Found: {list(df_ebay.columns)}"
      )
    else:
      # --- CRITICAL FIX: Clean IDs and strip any '.0' artifacts ---
      def clean_id(val):
        if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan":
          return ""
        v = str(val).strip()
        if v.endswith(".0"):
          v = v[:-2]
        return v

      df_vendor["clean_id"] = df_vendor[vendor_item_col].apply(clean_id)
      df_ebay["clean_id"] = df_ebay[ebay_item_col].apply(clean_id)

      # Base64 encoder
      def encode_asin(asin):
        if pd.isna(asin) or str(asin).strip() == "" or str(asin).lower() == "nan":
          return ""
        return base64.b64encode(str(asin).strip().encode("utf-8")).decode(
            "utf-8"
        )

      # Build dictionary mapping (Item ID -> Base64 ASIN)
      vendor_mapping = {}
      for _, row in df_vendor.iterrows():
        item_id = row["clean_id"]
        asin = row[vendor_asin_col]
        if item_id and item_id.isdigit():  # Ensure it's a valid number ID
          vendor_mapping[item_id] = encode_asin(asin)

      # Track matches for feedback
      match_count = 0

      # Process eBay template
      for idx, row in df_ebay.iterrows():
        item_id = row["clean_id"]

        # Skip header/connector rows like * or #INFO
        if not item_id or not item_id.isdigit() or item_id.startswith("#"):
          continue

        if item_id in vendor_mapping and vendor_mapping[item_id]:
          df_ebay.loc[idx, ebay_sku_col] = vendor_mapping[item_id]
          match_count += 1
        else:
          df_ebay.loc[idx, ebay_sku_col] = ""

      # Drop temporary helper column before download
      df_ebay = df_ebay.drop(columns=["clean_id"])

      st.success(
          f"Successfully processed! Matched {match_count} items with Base64"
          " SKUs."
      )
      st.dataframe(df_ebay.head(10))

      csv_data = df_ebay.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Download ECS-Ready eBay CSV",
          data=csv_data,
          file_name="ECS_Ready_eBay_Template.csv",
          mime="text/csv",
      )

  except Exception as e:
    st.error(f"An error occurred: {e}")

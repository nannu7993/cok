import streamlit as st
import pandas as pd
import subprocess
import os
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

def setup_page():
    st.set_page_config(page_title="Carrier Data Scraper", layout="wide")
    st.title("Carrier Data Scraper")
    
    st.markdown("""
        <style>
        .stButton>button {
            width: 100%;
            height: 50px;
            margin: 10px 0;
        }
        .stProgress > div > div > div > div {
            background-color: #1f77b4;
        }
        .stAlert {
            margin: 15px 0;
        }
        </style>
    """, unsafe_allow_html=True)

def initialize_browser():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=False,
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    return page, browser, playwright

def scrape_data(page):
    data = []
    try:
        # Wait for entries to load
        page.wait_for_selector("[data-mesh-id*='comp-m1fdjkhd1']", timeout=10000)
        entries = page.query_selector_all("[data-mesh-id*='comp-m1fdjkhd1']")
        
        for entry in entries:
            try:
                # Type (Broker/Carrier)
                company_type = entry.query_selector(
                    "div[data-testid='richTextElement'] p.wixui-rich-text__text"
                ).inner_text()
                
                # Company Name
                company_name = entry.query_selector(
                    "button[class*='StylableButton2545352419__root'][aria-label*='TRANSPORT']"
                ).get_attribute('aria-label')
                
                # MC#
                mc_element = entry.query_selector(
                    "button[aria-label^='MC#'] .StylableButton2545352419__label"
                )
                mc_number = mc_element.inner_text().replace('MC#', '').strip()
                
                # DOT#
                dot_element = entry.query_selector(
                    "button[aria-label^='DOT#'] .StylableButton2545352419__label"
                )
                dot_number = dot_element.inner_text().replace('DOT#', '').strip()
                
                # Fleet Size
                fleet_element = entry.query_selector(
                    "button[aria-label^='FLEET SIZE'] .StylableButton2545352419__label"
                )
                fleet_size = fleet_element.inner_text().replace('FLEET SIZE:', '').strip()
                
                # Email
                email_element = entry.query_selector(
                    "a[href^='mailto:']"
                )
                email = email_element.get_attribute('href').replace('mailto:', '').lower()
                
                data.append({
                    'Type': company_type,
                    'Company Name': company_name,
                    'MC#': mc_number,
                    'DOT#': dot_number,
                    'Fleet Size': fleet_size,
                    'Email': email
                })
                
            except Exception as e:
                st.error(f"Error scraping entry: {str(e)}")
                continue
                
    except Exception as e:
        st.error(f"Error waiting for page elements: {str(e)}")
    
    return data

def handle_pagination(page, progress_bar, status_text, current_page, max_pages):
    try:
        # Click next page button
        next_button = page.query_selector("button.next-page")
        if next_button:
            next_button.click()
            time.sleep(2)  # Wait for page load
            return True
        else:
            st.warning("No more pages available")
            return False
    except Exception as e:
        st.error(f"Error during pagination: {str(e)}")
        return False

def handle_login_and_scraping(page):
    # Initial URL
    initial_url = "https://www.carrier-ok.com/results?entity_type=Carrier&location=Moorefield%2C+WV%2C+26836&location_radius=100&authority=common&authority_age_min=12&fleet_size_min=4&equipment=Dry+Van"
    
    try:
        page.goto(initial_url)
        st.info("Please login in the browser window. After login and setting parameters, click 'Start Scraping' below")
        
        col1, col2 = st.columns(2)
        
        with col1:
            return st.button("Start Scraping")
        with col2:
            if st.button("Cancel"):
                st.stop()
                
        return False
        
    except Exception as e:
        st.error(f"Error accessing website: {str(e)}")
        return False

def main():
    setup_page()
    
    if 'scraped_data' not in st.session_state:
        st.session_state.scraped_data = []
    
    try:
        # Initialize browser
        page, browser, playwright = initialize_browser()
        
        # Handle login and wait for user to be ready
        if handle_login_and_scraping(page):
            st.info("Starting to scrape data...")
            
            # Get number of pages to scrape
            max_pages = st.number_input("Number of pages to scrape:", min_value=1, value=1)
            
            if st.button("Confirm and Continue"):
                all_data = []
                current_page = 1
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                while current_page <= max_pages:
                    try:
                        status_text.text(f"Scraping page {current_page} of {max_pages}")
                        
                        # Scrape current page
                        page_data = scrape_data(page)
                        if page_data:
                            all_data.extend(page_data)
                        
                        # Update progress
                        progress = current_page / max_pages
                        progress_bar.progress(progress)
                        
                        # Handle pagination
                        if current_page < max_pages:
                            if not handle_pagination(page, progress_bar, status_text, current_page, max_pages):
                                break
                        
                        current_page += 1
                        
                    except Exception as e:
                        st.error(f"Error on page {current_page}: {str(e)}")
                        break
                
                # Process and display results
                if all_data:
                    df = pd.DataFrame(all_data)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    st.success("Scraping completed!")
                    st.write("Scraped Data:")
                    st.dataframe(df)
                    
                    # Download options
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"carrier_data_{timestamp}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        # Create Excel file
                        excel_file = f"carrier_data_{timestamp}.xlsx"
                        df.to_excel(excel_file, index=False, engine='openpyxl')
                        
                        with open(excel_file, 'rb') as f:
                            excel_data = f.read()
                        
                        st.download_button(
                            label="Download Excel",
                            data=excel_data,
                            file_name=excel_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        # Clean up
                        os.remove(excel_file)
                else:
                    st.warning("No data was scraped. Please check the website structure and try again.")
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
    
    finally:
        # Clean up
        if 'page' in locals():
            page.close()
        if 'browser' in locals():
            browser.close()
        if 'playwright' in locals():
            playwright.stop()

if __name__ == "__main__":
    main()

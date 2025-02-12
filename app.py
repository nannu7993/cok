import streamlit as st
import pandas as pd
import subprocess
import os

# Install playwright browsers if not already installed
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    subprocess.run(["playwright", "install", "chromium"])

from playwright.sync_api import sync_playwright
import time
from datetime import datetime

def setup_page():
    st.set_page_config(page_title="Carrier Data Scraper", layout="wide")
    st.title("Carrier Data Scraper")

def initialize_browser():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    
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

def main():
    setup_page()
    
    st.info("Click 'Open Browser' to start. Once you've logged in and navigated to the desired page, click 'Start Scraping'")
    
    if 'browser_started' not in st.session_state:
        st.session_state.browser_started = False
    
    if st.button("Open Browser"):
        st.session_state.browser_started = True
        try:
            page, browser, playwright = initialize_browser()
            st.session_state.page = page
            st.session_state.browser = browser
            st.session_state.playwright = playwright
            
            # Navigate to the site
            page.goto("https://www.carrier-ok.com")
            
    if st.session_state.browser_started:
        # Get number of pages to scrape
        max_pages = st.number_input("Number of pages to scrape:", min_value=1, value=1)
        
        # Wait for user to be ready
        if st.button("Start Scraping"):
            try:
                page = st.session_state.page
                browser = st.session_state.browser
                playwright = st.session_state.playwright
                
                # Start scraping
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                all_data = []
                for current_page in range(1, max_pages + 1):
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
                        next_button = page.query_selector("button.next-page")
                        if next_button:
                            next_button.click()
                            page.wait_for_timeout(2000)
                        else:
                            st.warning("No more pages available")
                            break
                
                if all_data:
                    df = pd.DataFrame(all_data)
                    st.success("Scraping completed!")
                    st.dataframe(df)
                    
                    # Download options
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # CSV download
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"carrier_data_{timestamp}.csv",
                        mime="text/csv"
                    )
                    
                    # Excel download
                    excel_file = f"carrier_data_{timestamp}.xlsx"
                    df.to_excel(excel_file, index=False)
                    with open(excel_file, 'rb') as f:
                        excel_data = f.read()
                    st.download_button(
                        label="Download Excel",
                        data=excel_data,
                        file_name=excel_file,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    os.remove(excel_file)
                
            except Exception as e:
                st.error(f"Error during scraping: {str(e)}")
            
            finally:
                # Cleanup
                if 'browser' in st.session_state:
                    st.session_state.browser.close()
                if 'playwright' in st.session_state:
                    st.session_state.playwright.stop()
                st.session_state.browser_started = False
        
    # Reset button
    if st.session_state.browser_started:
        if st.button("Reset"):
            if 'browser' in st.session_state:
                st.session_state.browser.close()
            if 'playwright' in st.session_state:
                st.session_state.playwright.stop()
            st.session_state.browser_started = False
            st.rerun()

if __name__ == "__main__":
    main()

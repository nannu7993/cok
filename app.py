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
    browser = playwright.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    context = browser.new_context()
    page = context.new_page()
    return page, browser, playwright

def main():
    setup_page()
    
    # Initialize session state variables
    if 'login_state' not in st.session_state:
        st.session_state.login_state = 'not_started'
    if 'credentials_entered' not in st.session_state:
        st.session_state.credentials_entered = False
    if 'scraping_started' not in st.session_state:
        st.session_state.scraping_started = False

    # Login Form
    if st.session_state.login_state == 'not_started':
        st.subheader("Login Details")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if username and password:
                st.session_state.username = username
                st.session_state.password = password
                st.session_state.login_state = 'credentials_entered'
                st.rerun()

    # After credentials are entered
    if st.session_state.login_state == 'credentials_entered':
        try:
            page, browser, playwright = initialize_browser()
            
            # Navigate to site and login
            page.goto("https://www.carrier-ok.com/login")
            page.fill('input[type="email"]', st.session_state.username)
            page.fill('input[type="password"]', st.session_state.password)
            page.click('button[type="submit"]')
            
            # Wait for navigation
            page.wait_for_load_state('networkidle')
            
            # Navigate to the search results page
            page.goto("https://www.carrier-ok.com/results?entity_type=Carrier&location=Moorefield%2C+WV%2C+26836&location_radius=100&authority=common&authority_age_min=12&fleet_size_min=4&equipment=Dry+Van")
            
            st.success("Successfully logged in!")
            st.session_state.login_state = 'logged_in'
            
            # Cleanup
            browser.close()
            playwright.stop()
            
            st.rerun()

        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            st.session_state.login_state = 'not_started'

    # After successful login
    if st.session_state.login_state == 'logged_in':
        if not st.session_state.scraping_started:
            max_pages = st.number_input("Number of pages to scrape:", min_value=1, value=1)
            if st.button("Start Scraping"):
                st.session_state.max_pages = max_pages
                st.session_state.scraping_started = True
                st.rerun()

        # When scraping is started
        if st.session_state.scraping_started:
            try:
                page, browser, playwright = initialize_browser()
                
                # Navigate and login again (since we're in headless mode)
                page.goto("https://www.carrier-ok.com/login")
                page.fill('input[type="email"]', st.session_state.username)
                page.fill('input[type="password"]', st.session_state.password)
                page.click('button[type="submit"]')
                page.wait_for_load_state('networkidle')
                
                # Navigate to results page
                page.goto("https://www.carrier-ok.com/results?entity_type=Carrier&location=Moorefield%2C+WV%2C+26836&location_radius=100&authority=common&authority_age_min=12&fleet_size_min=4&equipment=Dry+Van")
                
                # Start scraping
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                all_data = []
                for current_page in range(1, st.session_state.max_pages + 1):
                    status_text.text(f"Scraping page {current_page} of {st.session_state.max_pages}")
                    
                    # Your existing scraping code here
                    page_data = scrape_data(page)
                    if page_data:
                        all_data.extend(page_data)
                    
                    progress = current_page / st.session_state.max_pages
                    progress_bar.progress(progress)
                    
                    # Handle pagination
                    if current_page < st.session_state.max_pages:
                        next_button = page.query_selector("button.next-page")
                        if next_button:
                            next_button.click()
                            page.wait_for_timeout(2000)
                
                # Display results
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
                
                # Cleanup
                browser.close()
                playwright.stop()
                
                # Reset state for new scraping
                st.session_state.scraping_started = False
                
            except Exception as e:
                st.error(f"An error occurred during scraping: {str(e)}")
                st.session_state.scraping_started = False

    # Reset button
    if st.session_state.login_state != 'not_started':
        if st.button("Start Over"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()

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

def initialize_browser():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=True,  # Must be headless on Streamlit Cloud
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = context.new_page()
    return page, browser, playwright

def scrape_data(page):
    data = []
    try:
        st.info("Waiting for page to load...")
        # First wait for any content to verify page is loaded
        page.wait_for_load_state('networkidle')
        page.wait_for_load_state('domcontentloaded')
        
        # Let's check what content is available
        st.info("Looking for data elements...")
        
        # Debug: Show what elements we can find
        company_cards = page.query_selector_all(".company-card")  # Try different selector
        if company_cards:
            st.success(f"Found {len(company_cards)} company cards")
        else:
            st.warning("No company cards found. Please verify you're on the correct page")
            # Take screenshot for debugging
            screenshot = page.screenshot()
            st.image(screenshot, caption="Current page state")
            return data

        # Now try to scrape each card
        for card in company_cards:
            try:
                company_data = {
                    'Type': '',
                    'Company Name': '',
                    'MC#': '',
                    'DOT#': '',
                    'Fleet Size': '',
                    'Email': ''
                }

                # Try to get each field with error handling
                try:
                    company_type = card.query_selector(".type")
                    if company_type:
                        company_data['Type'] = company_type.inner_text()
                except Exception as e:
                    st.error(f"Error getting company type: {str(e)}")

                try:
                    company_name = card.query_selector(".company-name")
                    if company_name:
                        company_data['Company Name'] = company_name.inner_text()
                except Exception as e:
                    st.error(f"Error getting company name: {str(e)}")

                # Similar for other fields...
                
                data.append(company_data)
                
            except Exception as e:
                st.error(f"Error processing card: {str(e)}")
                continue
                
    except Exception as e:
        st.error(f"Error accessing page: {str(e)}")
        screenshot = page.screenshot()
        st.image(screenshot, caption="Error state")
    
    return data

def main():
    setup_page()
    
    # Initialize session state
    if 'step' not in st.session_state:
        st.session_state.step = 'start'
    
    st.info("This tool will help you scrape carrier data.")
    
    # Step 1: Initial state
    if st.session_state.step == 'start':
        if st.button("Start New Session"):
            st.session_state.step = 'credentials'
            st.rerun()
    
    # Step 2: Get credentials
    elif st.session_state.step == 'credentials':
        st.subheader("Enter Login Credentials")
        username = st.text_input("Username/Email")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login"):
                if username and password:
                    st.session_state.username = username
                    st.session_state.password = password
                    st.session_state.step = 'page_setup'
                    st.rerun()
                else:
                    st.error("Please enter both username and password")
        
        with col2:
            if st.button("Back"):
                st.session_state.step = 'start'
                st.rerun()
    
    # Step 3: Page setup and scraping
    elif st.session_state.step == 'page_setup':
        st.subheader("Scraping Setup")
        
        url = st.text_input("Enter the URL to scrape:", 
                           value="https://www.carrier-ok.com/results?entity_type=Carrier&location=Moorefield%2C+WV%2C+26836&location_radius=100&authority=common&authority_age_min=12&fleet_size_min=4&equipment=Dry+Van")
        
        max_pages = st.number_input("Number of pages to scrape:", min_value=1, value=1)
        
        col1, col2 = st.columns(2)
        with col1:
if st.button("Start Scraping"):
    try:
        page, browser, playwright = initialize_browser()
        
        # Navigate to site
        st.info("Accessing website...")
        page.goto("https://www.carrier-ok.com")
        page.wait_for_load_state('networkidle')
        
        # Handle login
        st.info("Logging in...")
        login_button = page.query_selector('button[data-testid="buttonElement"]')
        if login_button:
            login_button.click()
            page.wait_for_selector('input[name="email"]')
            page.fill('input[name="email"]', st.session_state.username)
            page.fill('input[name="password"]', st.session_state.password)
            page.click('button[data-testid="buttonElement"] span:has-text("Log In")')
            page.wait_for_load_state('networkidle')
        
        # Navigate to results page
        st.info("Navigating to results page...")
        page.goto(url)
        page.wait_for_load_state('networkidle')
        
        # Take screenshot to verify page state
        screenshot = page.screenshot()
        st.image(screenshot, caption="Page before scraping")
        
        # Start scraping
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_data = []
        for current_page in range(1, max_pages + 1):
            try:
                status_text.text(f"Scraping page {current_page} of {max_pages}")
                page_data = scrape_data(page)
                if page_data:
                    all_data.extend(page_data)
                
                progress = current_page / max_pages
                progress_bar.progress(progress)
                
                if current_page < max_pages:
                    next_button = page.query_selector("button.next-page")
                    if next_button:
                        next_button.click()
                        time.sleep(2)
                    else:
                        st.warning("No more pages available")
                        break
            except Exception as e:
                st.error(f"Error on page {current_page}: {str(e)}")
                break
        
        # Display results
        if all_data:
            df = pd.DataFrame(all_data)
            st.success("Scraping completed!")
            st.dataframe(df)
            
            # Save options
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"carrier_data_{timestamp}.csv",
                mime="text/csv"
            )
            
            # Excel
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
        
        browser.close()
        playwright.stop()
        
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        
        with col2:
            if st.button("Reset"):
                st.session_state.step = 'start'
                st.rerun()

if __name__ == "__main__":
    main()

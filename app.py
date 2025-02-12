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

def handle_login(page, username, password):
    try:
        # First navigate to main page
        st.info("Accessing main page...")
        page.goto("https://www.carrier-ok.com", wait_until='networkidle')
        page.wait_for_load_state('domcontentloaded')
        
        # Find and click login button
        st.info("Clicking login button...")
        login_button = page.get_by_role("button", name="Login")
        login_button.click()
        
        # Wait for login form to appear
        page.wait_for_selector('input[type="email"], input[type="text"]', timeout=5000)
        
        # Fill in credentials
        st.info("Entering credentials...")
        email_input = page.query_selector('input[type="email"], input[type="text"]')
        password_input = page.query_selector('input[type="password"]')
        
        if not email_input or not password_input:
            raise Exception("Could not find login form fields")
            
        email_input.fill(username)
        password_input.fill(password)
        
        # Find and click submit
        submit_button = page.query_selector('button[type="submit"]')
        if not submit_button:
            raise Exception("Could not find submit button")
            
        submit_button.click()
        
        # Wait for login to complete
        page.wait_for_load_state('networkidle', timeout=10000)
        
        return True
        
    except Exception as e:
        st.error(f"Login error: {str(e)}")
        return False

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
    
    if 'login_state' not in st.session_state:
        st.session_state.login_state = 'not_started'
        
    if st.session_state.login_state == 'not_started':
        st.subheader("Login Details")
        username = st.text_input("Username/Email")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if username and password:
                try:
                    page, browser, playwright = initialize_browser()
                    
                    if handle_login(page, username, password):
                        st.success("Login successful!")
                        st.session_state.username = username
                        st.session_state.password = password
                        st.session_state.login_state = 'logged_in'
                        
                        # Navigate to the search results
                        page.goto("https://www.carrier-ok.com/results?entity_type=Carrier&location=Moorefield%2C+WV%2C+26836&location_radius=100&authority=common&authority_age_min=12&fleet_size_min=4&equipment=Dry+Van")
                        
                        browser.close()
                        playwright.stop()
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                finally:
                    if 'browser' in locals():
                        browser.close()
                    if 'playwright' in locals():
                        playwright.stop()
    
    if st.session_state.login_state == 'logged_in':
        max_pages = st.number_input("Number of pages to scrape:", min_value=1, value=1)
        
        if st.button("Start Scraping"):
            try:
                page, browser, playwright = initialize_browser()
                
                # Login again since we're in a new browser session
                if handle_login(page, st.session_state.username, st.session_state.password):
                    # Navigate to results page
                    page.goto("https://www.carrier-ok.com/results?entity_type=Carrier&location=Moorefield%2C+WV%2C+26836&location_radius=100&authority=common&authority_age_min=12&fleet_size_min=4&equipment=Dry+Van")
                    
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
                
            except Exception as e:
                st.error(f"An error occurred during scraping: {str(e)}")

    # Reset button
    if st.session_state.login_state == 'logged_in':
        if st.button("Start Over"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()

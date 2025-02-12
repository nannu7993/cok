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
    st.set_page_config(page_title="Transport Company Scraper", layout="wide")
    st.title("Transport Company Data Scraper")
    
    st.markdown("""
        <style>
        .stButton>button {
            width: 100%;
        }
        .stProgress > div > div > div > div {
            background-color: #1f77b4;
        }
        .stAlert {
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

def initialize_browser():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=False,  # Show browser for login
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    context = browser.new_context()
    page = context.new_page()
    return page, browser, playwright

def handle_login(page):
    st.subheader("Login Options")
    login_method = st.radio("Choose login method:", ["Manual Login", "Automated Login"])
    
    if login_method == "Manual Login":
        st.info("Please log in through the browser window and click 'Login Complete' when done")
        if st.button("Login Complete"):
            return True
    else:
        username = st.text_input("Username", type="default")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            try:
                # Wait for login form and fill credentials
                page.wait_for_selector("input[type='email']")  # Adjust selector
                page.fill("input[type='email']", username)     # Adjust selector
                page.fill("input[type='password']", password)  # Adjust selector
                page.click("button[type='submit']")           # Adjust selector
                
                # Wait for login to complete
                page.wait_for_timeout(3000)
                
                return True
            except Exception as e:
                st.error(f"Login failed: {str(e)}")
                return False
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
    
    if 'scraped_data' not in st.session_state:
        st.session_state.scraped_data = []
        
    if 'login_completed' not in st.session_state:
        st.session_state.login_completed = False
    
    # Input fields
    col1, col2 = st.columns(2)
    with col1:
        url = st.text_input("Enter the URL to scrape:")
    with col2:
        max_pages = st.number_input("Number of pages to scrape:", min_value=1, value=1)
    
    # Start scraping button
    if st.button("Start Scraping"):
        if url:
            try:
                page, browser, playwright = initialize_browser()
                
                # Navigate to URL
                page.goto(url)
                st.info("Accessing the website. Please wait...")
                
                # Handle login
                if not st.session_state.login_completed:
                    if handle_login(page):
                        st.session_state.login_completed = True
                        st.success("Login successful!")
                
                if st.session_state.login_completed:
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
                            
                            # Click next page if not on last page
                            if current_page < max_pages:
                                next_button = page.query_selector("button.next-page")
                                if next_button:
                                    next_button.click()
                                    page.wait_for_timeout(2000)  # Wait for page load
                                else:
                                    st.warning("No more pages available")
                                    break
                            
                            current_page += 1
                            
                        except Exception as e:
                            st.error(f"Error on page {current_page}: {str(e)}")
                            break
                    
                    # Store and display results
                    if all_data:
                        df = pd.DataFrame(all_data)
                        
                        # Add timestamp
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
                                file_name=f"scraped_data_{timestamp}.csv",
                                mime="text/csv"
                            )
                        
                        with col2:
                            buffer = pd.ExcelWriter(f"scraped_data_{timestamp}.xlsx", engine='openpyxl')
                            df.to_excel(buffer, index=False)
                            buffer.close()
                            
                            with open(f"scraped_data_{timestamp}.xlsx", 'rb') as f:
                                excel_data = f.read()
                            
                            st.download_button(
                                label="Download Excel",
                                data=excel_data,
                                file_name=f"scraped_data_{timestamp}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
                            # Clean up the temporary file
                            os.remove(f"scraped_data_{timestamp}.xlsx")
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
        
        else:
            st.warning("Please enter a URL")

if __name__ == "__main__":
    main()

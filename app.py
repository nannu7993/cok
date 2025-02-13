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
       headless=True,
       args=['--no-sandbox', '--disable-dev-shm-usage']
   )
   context = browser.new_context(viewport={'width': 1920, 'height': 1080})
   page = context.new_page()
   return page, browser, playwright

def handle_login(page, username, password):
   try:
       # Find and click login button
       login_button = page.query_selector('button[data-testid="buttonElement"]')
       if login_button:
           login_button.click()
           time.sleep(2)  # Wait for login form to appear
           
           # Fill credentials
           page.fill('input[name="email"]', username)
           page.fill('input[name="password"]', password)
           
           # Click login
           submit_button = page.query_selector('button[data-testid="buttonElement"] span:has-text("Log In")')
           if submit_button:
               submit_button.click()
               
           # Wait for login to complete
           page.wait_for_load_state('networkidle')
           
           # Verify login was successful (wait for logged-in state)
           time.sleep(5)  # Give extra time for session to establish
           
           return True
   except Exception as e:
       st.error(f"Login failed: {str(e)}")
       return False

def scrape_data(page):
   data = []
   try:
       st.info("Waiting for page to load...")
       page.wait_for_load_state('networkidle')
       page.wait_for_load_state('domcontentloaded')
       
       # Add additional wait for dynamic content
       page.wait_for_timeout(5000)
       
       st.info("Looking for data elements...")
       company_cards = page.query_selector_all(".company-card")
       
       if company_cards:
           st.success(f"Found {len(company_cards)} company cards")
       else:
           st.warning("No company cards found. Please verify you're on the correct page")
           screenshot = page.screenshot()
           st.image(screenshot, caption="Current page state")
           return data

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
                   
                   # Navigate to site and login
                   st.info("Accessing website...")
                   page.goto("https://www.carrier-ok.com")
                   page.wait_for_load_state('networkidle')
                   
                   # Handle login
                   st.info("Logging in...")
                   if not handle_login(page, st.session_state.username, st.session_state.password):
                       st.error("Failed to login. Please check your credentials and try again.")
                       browser.close()
                       playwright.stop()
                       return
                       
                   # Verify we're logged in before proceeding
                   st.info("Verifying login...")
                   page.wait_for_timeout(3000)  # Wait a bit more
                   
                   # Navigate to results page
                   st.info("Navigating to results page...")
                   page.goto(url)
                   page.wait_for_load_state('networkidle')
                   page.wait_for_timeout(5000)  # Wait for dynamic content
                   
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

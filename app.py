import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

def setup_page():
    st.set_page_config(page_title="Transport Company Scraper", layout="wide")
    st.title("Transport Company Data Scraper")
    
    # Add custom CSS
    st.markdown("""
        <style>
        .stButton>button {
            width: 100%;
        }
        .stProgress > div > div > div > div {
            background-color: #1f77b4;
        }
        </style>
    """, unsafe_allow_html=True)

def create_browser():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Uncomment below line to run in headless mode
    # chrome_options.add_argument("--headless")
    
    browser = webdriver.Chrome(options=chrome_options)
    return browser

def scrape_data(browser, wait):
    data = []
    
    # Wait for entries to load
    entries = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-mesh-id*='comp-m1fdjkhd1']")))
    
    for entry in entries:
        try:
            # Type (Broker/Carrier)
            company_type = entry.find_element(
                By.CSS_SELECTOR, 
                "div[data-testid='richTextElement'] p.wixui-rich-text__text"
            ).text
            
            # Company Name
            company_name = entry.find_element(
                By.CSS_SELECTOR, 
                "button[class*='StylableButton2545352419__root'][aria-label*='TRANSPORT']"
            ).get_attribute('aria-label')
            
            # MC#
            mc_element = entry.find_element(
                By.CSS_SELECTOR, 
                "button[aria-label^='MC#'] .StylableButton2545352419__label"
            )
            mc_number = mc_element.text.replace('MC#', '').strip()
            
            # DOT#
            dot_element = entry.find_element(
                By.CSS_SELECTOR, 
                "button[aria-label^='DOT#'] .StylableButton2545352419__label"
            )
            dot_number = dot_element.text.replace('DOT#', '').strip()
            
            # Fleet Size
            fleet_element = entry.find_element(
                By.CSS_SELECTOR, 
                "button[aria-label^='FLEET SIZE'] .StylableButton2545352419__label"
            )
            fleet_size = fleet_element.text.replace('FLEET SIZE:', '').strip()
            
            # Email
            email_element = entry.find_element(
                By.CSS_SELECTOR, 
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
    
    return data

def main():
    setup_page()
    
    # Session state for storing data
    if 'scraped_data' not in st.session_state:
        st.session_state.scraped_data = []
    
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
                browser = create_browser()
                wait = WebDriverWait(browser, 20)
                
                # Open URL
                browser.get(url)
                
                # Wait for user login
                st.info("Please log in to the website if required. Once ready, click 'Continue Scraping' below.")
                
                if st.button("Continue Scraping"):
                    all_data = []
                    current_page = 1
                    
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    while current_page <= max_pages:
                        status_text.text(f"Scraping page {current_page} of {max_pages}")
                        
                        try:
                            # Scrape current page
                            page_data = scrape_data(browser, wait)
                            all_data.extend(page_data)
                            
                            # Update progress
                            progress = current_page / max_pages
                            progress_bar.progress(progress)
                            
                            # Click next page if not on last page
                            if current_page < max_pages:
                                next_button = wait.until(EC.element_to_be_clickable(
                                    (By.CSS_SELECTOR, "button.next-page")
                                ))
                                next_button.click()
                                time.sleep(2)  # Wait for page to load
                            
                            current_page += 1
                            
                        except TimeoutException:
                            st.warning(f"Timeout on page {current_page}. Moving to next page...")
                            current_page += 1
                            continue
                    
                    # Store data in session state
                    st.session_state.scraped_data = all_data
                    
                    # Create DataFrame and display results
                    if all_data:
                        df = pd.DataFrame(all_data)
                        st.success("Scraping completed!")
                        st.write("Scraped Data:")
                        st.dataframe(df)
                        
                        # Download options
                        col1, col2 = st.columns(2)
                        with col1:
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="Download CSV",
                                data=csv,
                                file_name="scraped_data.csv",
                                mime="text/csv"
                            )
                        with col2:
                            excel_buffer = df.to_excel(index=False, engine='openpyxl')
                            st.download_button(
                                label="Download Excel",
                                data=excel_buffer,
                                file_name="scraped_data.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.warning("No data was scraped. Please check the selectors and try again.")
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
            finally:
                if 'browser' in locals():
                    browser.quit()
        else:
            st.warning("Please enter a URL")

if __name__ == "__main__":
    main()

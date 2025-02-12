import streamlit as st
import pandas as pd
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
        </style>
    """, unsafe_allow_html=True)

def initialize_browser():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    context = browser.new_context()
    page = context.new_page()
    return page, browser, playwright

def scrape_data(page):
    data = []
    
    # Wait for entries to load
    page.wait_for_selector("[data-mesh-id*='comp-m1fdjkhd1']")
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
    
    return data

def main():
    setup_page()
    
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
                page, browser, playwright = initialize_browser()
                
                # Navigate to URL
                page.goto(url)
                st.info("Accessing the website. Please wait...")
                
                # Wait for login if needed
                st.info("If login is required, please wait for the login process...")
                time.sleep(5)  # Give time for page to load
                
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
                        output = df.to_excel(index=False, engine='openpyxl')
                        st.download_button(
                            label="Download Excel",
                            data=output,
                            file_name=f"scraped_data_{timestamp}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
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

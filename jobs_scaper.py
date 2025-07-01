import unicodedata
import dateparser
import time
import requests
from bs4 import BeautifulSoup
import csv
import re
import requests
from requests.exceptions import RequestException


def parse_salary_to_number(salary_str, convert_to='annual'):
    if not salary_str or 'N/A' in salary_str:
        return None

    salary_str = salary_str.lower().replace(',', '')

    match = re.search(r'\$?([\d.]+)', salary_str)
    if not match:
        return None

    amount = float(match.group(1))

    if 'hour' in salary_str:
        return amount * 2000 if convert_to == 'annual' else amount
    elif 'annual' in salary_str or 'year' in salary_str:
        return amount if convert_to == 'annual' else amount / 2000
    else:
        return None  # Can't tell what unit it is


def clean_text(text):
    if not isinstance(text, str):
        return text

    text = ''.join(ch if unicodedata.category(ch)[0] != 'C' else ' ' for ch in text)
    text = text.replace(',', '')
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def parse_date_to_iso(date_str):
    if not date_str or date_str.strip().lower() == 'n/a':
        return "N/A"
    dt = dateparser.parse(date_str)
    if dt:
        return dt.strftime("%Y-%m-%d")
    else:
        return "N/A"


def extract_jobs_from_soup(soup, max_to_add, already_added):
    job_articles = soup.select("article[id^='article-']")
    jobs = []

    for job in job_articles:
        if len(jobs) + already_added >= max_to_add:
            break

        title_elem = job.select_one("h3.title .noctitle")
        link_elem = job.select_one("a.job-title")
        date_elem = job.select_one(".date")
        business_elem = job.select_one(".business")
        location_elem = job.select_one(".location")
        source_elem = job.select_one(".source")
        salary_elem = job.select_one(".salary")

        title_text = clean_text(title_elem.get_text()) if title_elem else "N/A"
        url = "https://www.jobbank.gc.ca" + link_elem['href'] if link_elem and link_elem.has_attr('href') else "N/A"
        url = clean_text(url)
        date_text = parse_date_to_iso(date_elem.get_text()) if date_elem else "N/A"
        date_text = clean_text(date_text)
        business_text = clean_text(business_elem.get_text()) if business_elem else "N/A"
        location_text = clean_text(location_elem.get_text()) if location_elem else "N/A"
        if location_text.lower().startswith("location"):
            location_text = location_text[len("location"):].strip()

        source_text = clean_text(source_elem.get_text()) if source_elem else "N/A"

        salary_text = "N/A"
        if salary_elem:
            text_parts = [str(t) for t in salary_elem.contents if not getattr(t, 'name', None) == 'span']
            salary_text = " ".join(text_parts).replace("Salary:", "")
            salary_text = clean_text(salary_text)

        normalized_salary = parse_salary_to_number(salary_text, convert_to='annual')


        jobs.append({
            "title": title_text,
            "url": url,
            "date": date_text,
            "business": business_text,
            "location": location_text,
            "salary": normalized_salary,
            "source": source_text
        })

    return jobs


def get_job_postings(job_title, location="Canada", max_results=20):
    query = job_title.replace(' ', '+')
    base_url = "https://www.jobbank.gc.ca"
    search_url = f"{base_url}/jobsearch/jobsearch?searchstring={query}&locationstring={location}"
    ajax_url = f"{base_url}/jobsearch/job_search_loader.xhtml"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    session = requests.Session()
    resp = session.get(search_url, headers=headers)
    if resp.status_code != 200:
        print("Initial request failed.")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract the token from Set-Cookie
    token = None
    for cookie in session.cookies:
        if cookie.name == "oam.Flash.RENDERMAP.TOKEN":
            token = cookie.value
            break

    if not token:
        print("Token not found.")
        return []

    # Parse initial results
    all_jobs = extract_jobs_from_soup(soup, max_results, 0)

    print(f'{len(all_jobs)} jobs extracted on first request.')

    while max_results > len(all_jobs):
        time.sleep(5)

        cookies = {
            "oam.Flash.RENDERMAP.TOKEN": token
        }
        ajax_headers = headers.copy()
        ajax_headers["Referer"] = search_url

        try:
            ajax_resp = session.get(ajax_url, headers=ajax_headers, cookies=cookies, timeout=10)

            if ajax_resp.status_code == 200 and ajax_resp.text.strip():
                ajax_soup = BeautifulSoup(ajax_resp.text, "html.parser")
                more_jobs = extract_jobs_from_soup(ajax_soup, max_results, len(all_jobs))

                if not more_jobs:
                    print("No more jobs found in AJAX response. Ending loop.")
                    break

                all_jobs.extend(more_jobs)
                print(f'Added {len(more_jobs)} to list. Total: {len(all_jobs)}')
            else:
                print(f"AJAX response failed or was empty (status {ajax_resp.status_code}). Stopping.")
                break

        except RequestException as e:
            print(f"[ERROR] Failed to fetch more jobs from AJAX: {str(e)}")
            break

    if(len(all_jobs) == max_results):
        print('Reached max results')

    return all_jobs

def save_to_csv(jobs, filename="job_postings.csv"):
    if not jobs:
        print("No job data to save.")
        return

    keys = ["title", "business", "location", "date", "salary", "source", "url"]

    with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        for job in jobs:
            writer.writerow(job)

    print(f"Saved {len(jobs)} jobs to '{filename}'")


if __name__ == "__main__":
    job_title = input("Enter job title: ")
    try:
        max_results = int(input("Enter the maximum number of results to fetch: "))
    except ValueError:
        print("Invalid input. Using default of 100 results.")
        max_results = 100
    jobs = get_job_postings(job_title, location="Canada", max_results=max_results)
    save_to_csv(jobs)



